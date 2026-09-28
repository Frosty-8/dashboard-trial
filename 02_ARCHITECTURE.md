# Architecture — SAP PPC Data Intelligence

> How the system is built, layer by layer, and why.

---

## 1. Architecture at a glance

The project is a **layered data pipeline** with a thin web layer on top. Data flows in one direction; each layer has one job and does not know about the layers above it.

```
 SAP / Excel / CSV / Parquet
            │
            ▼
 ┌──────────────────────┐
 │  1. INGESTION        │  read, find sheet & header, classify, join
 └──────────┬───────────┘
            ▼
 ┌──────────────────────┐
 │  2. PROFILING        │  rows, nulls, duplicates, errors
 └──────────┬───────────┘
            ▼
 ┌──────────────────────┐
 │  3. TRANSFORMATION   │  clean → map (canonical names) → calculate
 └──────────┬───────────┘
            ▼
 ┌──────────────────────┐
 │  4. SEMANTIC MODEL   │  one standard dataset (Parquet)
 └──────────┬───────────┘
            ▼
   ┌────────┴────────┐
   ▼                 ▼
┌──────────┐   ┌───────────┐
│ ANALYTICS│   │ INSIGHTS  │  KPIs, views   |   rule-based findings
└────┬─────┘   └─────┬─────┘
     └───────┬───────┘
             ▼
 ┌──────────────────────┐
 │  5. FLASK API        │  JSON endpoints
 └──────────┬───────────┘
            ▼
 ┌──────────────────────┐
 │  6. DASHBOARD (UI)   │  HTML + CSS + JS charts
 └──────────────────────┘
```

---

## 2. Project structure and responsibility

```
app/
├── __init__.py          Flask app factory, registers blueprints
├── config.py            Paths (data folders) + thresholds (1 / 2 / 6 months)
├── pipeline.py          PPCPipeline: end-to-end orchestrator for one dataset
│
├── ingestion/           "Get the data in and understand its shape"
│   ├── excel_reader.py        Read csv/xlsx/xlsb/parquet; pick sheet; detect header row
│   ├── profiler.py            Column-level quality profile of a dataframe
│   ├── workbook_profiler.py   Sheet-level profile of a whole workbook
│   ├── sheet_classifier.py    Assign a business role to each sheet
│   ├── relationship_detector.py  Find joinable columns between sheets
│   ├── integration.py         Build the integration plan (primary sheet + joins)
│   └── workbook_integrator.py Execute the plan → one canonical dataframe
│
├── transformation/      "Make the data trustworthy and standard"
│   ├── cleaner.py             Fix names, errors, HTML, numbers, duplicates
│   ├── mapper.py              Alias → canonical field names
│   └── calculator.py          Derived metrics and status labels
│
├── analytics/           "Turn rows into answers"
│   ├── kpis.py                Headline numbers
│   ├── inventory.py           Coverage distribution, by category, critical parts
│   ├── procurement.py         Supplier shortfalls, priorities, shortfall parts
│   ├── suppliers.py           Supplier exposure and shortfall %
│   ├── forecast.py            Monthly forecast and ending-stock projection
│   └── report.py              AnalyticsReport: one payload for the frontend
│
├── insights/            "Explain in words"
│   ├── rules.py               Business rules (thresholds, messages)
│   └── engine.py              Run rules, sort by severity, count by level
│
├── routes/              "HTTP layer"
│   ├── api.py                 /api/health, /api/workbook/*, /api/process
│   ├── dashboard.py           / and /api/dashboard*
│   └── upload.py              /upload page
│
├── templates/           dashboard.html, upload.html
└── static/              dashboard.css, dashboard.js

scripts/
├── generate_faker_data.py   Synthetic data with injected quality issues
├── run_pipeline.py          CLI run + report
└── test_pipeline.py         CLI smoke test

data/  (auto-created by config.py)
├── raw/  generated/  uploads/  processed/  analytics/
```

---

## 3. Layer details

### 3.1 Ingestion
**Goal:** cope with how real SAP exports actually look.

- **Format support:** `.xlsx` (openpyxl), `.xlsb` (pyxlsb), `.csv`, `.parquet`.
- **Sheet selection:** explicit name wins → known names (`PPC Report`, `Planning`, `Order Details`…) → otherwise score each sheet by business vocabulary (part, supplier, stock, coverage, shortfall, PO, STO…).
- **Header detection:** the sheet is read with *no* header, empty rows/columns are dropped, the real header row is detected, and multi-row headers are flattened.
- **Workbook intelligence (multi-sheet):**
  1. `WorkbookProfiler` profiles every sheet.
  2. `SheetClassifier` assigns a role: `primary_transactional`, `planning`, `inventory`, `supplier_master`, `procurement`, `schedule`, or ignored (`supporting`, `unknown`).
  3. `RelationshipDetector` matches columns across sheets using alias groups (part, supplier, PO, PR, STO, project, category) and a 0–100 confidence score (exact match = 100; otherwise token overlap; below 50 is discarded).
  4. `WorkbookIntegrationPlanner` picks **one primary sheet** and only plans **left joins that involve the primary sheet** and a non-ignored partner sheet.
  5. `WorkbookIntegrator` executes the plan, records warnings, and adds a `_source_sheet` lineage column.

### 3.2 Profiling
`DataProfiler` reports rows, columns, duplicates, total nulls, per-column null %, unique counts, sample values, and potential errors. It runs *before* cleaning so the user can see how dirty the source was.

### 3.3 Transformation
- **Cleaner** (order matters): normalize column names → trim strings → convert error tokens (`#DIV/0!`, `#N/A`, `N/A`, `-`, empty…) to null → strip HTML tags → convert numeric-looking text (removing commas) to floats → drop fully empty columns → drop duplicate rows.
- **Mapper:** translates report-specific names to **canonical fields** (e.g. `stock_as_on_date → current_stock`, `b_price → unit_price`, `vendor/supplier → supplier_name`, `cov → coverage`). Also handles prefixed columns from integrated workbooks. Reports which columns it could not map.
- **Calculator:** adds `calculated_coverage`, `calculated_shortfall`, `calculated_inventory_value`, `shortfall_status`, `coverage_status`. Every calculation is **guarded** — it runs only if the needed columns exist, and casts with `strict=False` so bad values become null instead of crashing.

> **Design rule:** downstream code depends only on canonical field names. That is what makes the analytics reusable across different SAP reports.

### 3.4 Semantic model
The cleaned + mapped + calculated dataset, stored as Parquet:
- `data/processed/canonical_procurement.parquet` — from the multi-sheet workbook analysis (preferred by the dashboard)
- `data/processed/ppc_clean.parquet` — from the single-dataset `/api/process` pipeline (fallback)

### 3.5 Analytics
Pure functions over a Polars dataframe. Each returns a list of dicts (JSON-ready) and returns an empty list if required columns are absent.

| Module | Outputs |
|---|---|
| `KPIAnalytics` | total parts, inventory value, stock, requirement, shortfall, open PO/STO, in-transit, counts by coverage status, shortfall parts |
| `InventoryAnalytics` | coverage distribution, inventory by category, top-20 critical parts |
| `ProcurementAnalytics` | top-15 supplier shortfalls, priority distribution, top-50 shortfall parts |
| `SupplierAnalytics` | top-20 suppliers with parts, requirement, stock, shortfall, shortfall %, open PO/STO |
| `ForecastAnalytics` | monthly forecast totals, projected ending stock (columns like `jan_forecast`, `jan_end_stock`) |
| `AnalyticsReport` | bundles all of the above **plus** insights into one payload |

### 3.6 Insight engine
`InsightRules` evaluates configurable rules; `InsightEngine` sorts them and returns counts.

| Rule ID | Severity | Fires when |
|---|---|---|
| `COVERAGE_CRITICAL` | critical | any part < 1 month coverage |
| `COVERAGE_LOW` | warning | any part between 1 and 2 months |
| `COVERAGE_EXCESS` | info | any part > 6 months |
| `PROCUREMENT_SHORTFALL` | critical | any part with shortfall > 0 |
| `SUPPLIER_SHORTFALL_CONCENTRATION` | warning | names the supplier with the largest shortfall |
| `EXCESS_INVENTORY_VALUE` | warning | money tied up in parts > 6 months coverage |
| `STO_IN_TRANSIT` | info | stock transfers currently in transit |

Output shape:
```json
{
  "total_insights": 7,
  "critical": 2, "warning": 3, "info": 2,
  "items": [
    { "rule_id": "COVERAGE_CRITICAL", "severity": "critical",
      "title": "Critical stock coverage",
      "description": "34 parts have less than 1 month of stock coverage.",
      "affected_records": 34 }
  ]
}
```

### 3.7 API layer (Flask)

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/` | Dashboard page |
| GET | `/upload` | Upload page |
| GET | `/api/health` | Health check |
| POST | `/api/workbook/profile` | Explain what is inside a workbook (no transformation) |
| POST | `/api/workbook/analyze` | Profile → classify → detect relationships → plan → integrate → save canonical Parquet |
| POST | `/api/process` | Run the single-dataset pipeline and save `ppc_clean.parquet` |
| GET | `/api/dashboard` | Full analytics + insights payload |
| GET | `/api/dashboard/preview?limit=50` | Sample rows and schema (limit clamped 1–200) |
| GET | `/api/dashboard/status` | Is a processed dataset available? |

### 3.8 Frontend
Server-rendered shell (`dashboard.html`) plus vanilla JavaScript. `dashboard.js` calls `/api/dashboard`, then renders KPI cards, bar / line / coverage charts, tables and insight cards. Six sections: Overview, Inventory, Procurement, Suppliers, Forecast, Insights.

---

## 4. Request flow (upload → dashboard)

1. User opens `/upload` and posts a workbook to `/api/workbook/analyze`.
2. The file is saved to `data/uploads/`.
3. Profiling → classification → relationship detection → integration plan → integration.
4. The canonical dataset is written to `data/processed/canonical_procurement.parquet`.
5. The response includes the plan, the joins, warnings and row/column counts (so the user sees *what* was done).
6. User opens `/`. The browser calls `/api/dashboard`.
7. The server loads the Parquet, runs **clean → map → calculate → AnalyticsReport**, and returns JSON.
8. JavaScript renders the charts and insights.

---

## 5. Key design decisions

| Decision | Reason |
|---|---|
| **Layered pipeline** | Each stage is testable and replaceable on its own |
| **Canonical field names** | New SAP report = new aliases, not new analytics code |
| **Polars for compute** | Fast, low memory, expressive column expressions |
| **Parquet as storage** | Small, typed, columnar, quick to read |
| **Rule-based insights** | Deterministic, auditable, no hallucination risk |
| **Defensive analytics** | Missing columns → empty result, not a crash |
| **Explicit integration plan** | Sheet choices and joins are inspectable and explainable |
| **Left joins to primary only** | Prevents accidental row explosion from unrelated sheets |
| **Synthetic data with injected faults** | Safe demos; proves the cleaner works |

---

## 6. Current limitations (honest view)

These are observations from the code as it stands today, and they drive the roadmap in `04_FUTURE_SCOPE.md`.

1. **No caching.** `/api/dashboard` reloads the Parquet and re-runs clean → map → calculate → all analytics on every request.
2. **Single shared dataset.** Every upload overwrites the same `canonical_procurement.parquet`; there is no per-user or per-run separation and no history.
3. **Synchronous processing.** Upload analysis runs inside the web request.
4. **Upload safety is basic.** Extension is checked, but there is no size limit, no content validation, and files are saved under the user-supplied name (which can overwrite earlier uploads).
5. **No authentication or roles.**
6. **Error responses expose stack traces** to the client, and `run.py` starts Flask with `debug=True` (fine for development, not for production).
7. **Thresholds are duplicated** (`config.py`, `InsightRules`, `calculator.py`, `inventory.py`) instead of being read from one place.
8. **Two processing paths** (`/api/process` and `/api/workbook/analyze`) with different output files.
9. **Tests** are CLI scripts, not an automated test suite; `requirements.txt` is empty (dependencies live in `pyproject.toml`).

---

*Related docs: `01_PROJECT_EXPLANATION.md` · `03_DIAGRAMS.md` · `04_FUTURE_SCOPE.md`*


### Early architecture to define the flow of the project.


                    SAP / Excel / XLSB / CSV
                              │
                              ▼
                     ┌─────────────────┐
                     │    INGESTION    │
                     └────────┬────────┘
                              ▼
                     ┌─────────────────┐
                     │ DATA PROFILING  │
                     └────────┬────────┘
                              ▼
                     ┌─────────────────┐
                     │ DATA CLEANING   │
                     └────────┬────────┘
                              ▼
                     ┌─────────────────┐
                     │ BUSINESS MAPPER │
                     └────────┬────────┘
                              ▼
                     ┌─────────────────┐
                     │ CALCULATIONS    │
                     └────────┬────────┘
                              ▼
                    CANONICAL DATA MODEL
                              │
             ┌────────────────┼────────────────┐
             ▼                ▼                ▼
        Inventory        Procurement       Forecast
        Analytics         Analytics        Analytics
             │                │                │
             └────────────────┼────────────────┘
                              ▼
                     ┌─────────────────┐
                     │ INSIGHT ENGINE  │
                     └────────┬────────┘
                              ▼
                     ┌─────────────────┐
                     │  ACTION CENTER  │
                     └────────┬────────┘
                              ▼
                    ┌────────────────────┐
                    │   FLASK REST API   │
                    └─────────┬──────────┘
                              ▼
                    ┌────────────────────┐
                    │   WEB DASHBOARD    │
                    └────────────────────┘