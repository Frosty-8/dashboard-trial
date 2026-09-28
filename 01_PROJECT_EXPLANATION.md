# SAP PPC Data Intelligence — Project Explanation

> A plain-language guide to explain this project to anyone: managers, teammates, or interviewers.

---

## 1. The one-minute pitch

> "SAP teams spend hours every week downloading messy Excel reports, cleaning them by hand, and building pivot tables to answer one question: **which parts are we about to run out of, and which supplier do we need to chase?**
>
> This project automates that whole loop. You upload the SAP/PPC Excel workbook, and the system **reads it, cleans it, understands it, calculates the business numbers, and shows a dashboard with plain-English insights** — in seconds, the same way every time."

---

## 2. The problem it solves

| Today (manual) | With this project (automated) |
|---|---|
| Open big Excel workbook with many sheets | Upload once |
| Find the right sheet and header row | Auto-detected |
| Fix `#DIV/0!`, blanks, duplicates, HTML junk by hand | Auto-cleaned |
| Rebuild formulas for coverage / shortfall every time | Calculated consistently |
| Build pivots and charts | Dashboard generated automatically |
| "Why is this red?" — nobody remembers the rule | Every insight names the rule that triggered it |

**Who benefits:** the SAP / PPC (Production Planning & Control) / procurement team, plus anyone who reads their reports.

---

## 3. What the system actually does (7 simple steps)

Think of it as an assembly line. Each station does one job:

1. **Ingest** — Read the file (`.xlsx`, `.xlsb`, `.csv`, `.parquet`). Find the right sheet. Find the real header row (SAP reports often have title rows and multi-row headers).
2. **Profile** — Look at the data *before* touching it: how many rows, how many blanks, how many duplicates, what looks like an error.
3. **Clean** — Fix column names, remove `#DIV/0!` / `N/A` / blanks, strip HTML tags like `<br>`, turn text numbers into real numbers, drop duplicates.
4. **Map** — Different reports call the same thing by different names (`Material`, `Part No`, `Item Code`). Map them all to **one standard name** (`part_number`). This is the "semantic model".
5. **Calculate** — Create the business metrics: coverage, shortfall, inventory value, status labels.
6. **Analyze** — Roll up into KPIs, supplier views, inventory views, procurement views, forecast views.
7. **Explain** — A rule-based insight engine writes human-readable findings, sorted by severity (critical → warning → info).

Then a **Flask API** serves the results and the **dashboard** draws them.

---

## 4. Key business terms (say these confidently)

| Term | Meaning | How it is computed here |
|---|---|---|
| **Monthly requirement** | How many units we need per month | From the report |
| **Current stock** | Units on hand today | From the report (`Stock as on date`) |
| **Coverage** | How many *months* current stock will last | `current_stock ÷ monthly_requirement` |
| **Shortfall** | Units we are short by | `max(requirement − stock, 0)` |
| **Inventory value** | Money tied up in stock | `stock × unit price` |
| **Open PO** | Purchase orders raised but not yet received | From the report |
| **Open STO / STO in-transit** | Stock transfer orders between plants, and those currently moving | From the report |

### Coverage status (the traffic-light rule)

| Coverage (months) | Status | Meaning |
|---|---|---|
| less than 1 | 🔴 **Critical** | Less than a month of stock — act now |
| 1 to less than 2 | 🟠 **Low** | Getting risky |
| 2 to 6 | 🟢 **Healthy** | Normal |
| more than 6 | 🔵 **Excess** | Too much cash tied up |
| missing / invalid | ⚪ **Unknown** | Data problem, not a stock problem |

These thresholds (1, 2, 6) live in `app/config.py` and can be changed.

---

## 5. What the user sees

The dashboard has six views:

- **Overview** — KPI cards, coverage chart, priority chart, top suppliers by shortfall, forecast trend, latest insights
- **Inventory** — coverage distribution, inventory by category, critical parts list
- **Procurement** — supplier shortfalls, priority distribution, parts in shortfall
- **Suppliers** — supplier exposure (shortfall %, open PO, STO, inventory value)
- **Forecast** — monthly forecast and projected ending stock
- **Insights** — the full explainable insight feed

There is also an **Upload** page to feed in a new workbook.

---

## 6. "Explainable" — what that means in this project

The system is **deterministic and rule-based**, not a black box. Every output can be traced:

- **Insights carry a `rule_id`** (e.g. `COVERAGE_CRITICAL`, `PROCUREMENT_SHORTFALL`, `SUPPLIER_SHORTFALL_CONCENTRATION`), a severity, a plain-English description, and the number of affected records.
- **Sheet selection is explained.** The workbook planner records *why* each sheet was selected or ignored ("Selected as primary source dataset", "Excluded because it is not required…").
- **Joins are explained.** Each join between sheets stores the matching columns and a confidence score.
- **Lineage is kept.** The integrator adds a `_source_sheet` column so you know where a row came from.
- **Formulas are visible.** Coverage, shortfall and inventory value are simple, documented formulas.

**Why this matters:** in procurement, a planner will only trust a number they can verify. "The AI said so" is not acceptable; "this rule fired on 34 parts" is.

---

## 7. Smart multi-sheet handling (the clever part)

Real SAP workbooks have many sheets (PPC report, stock, supplier list, PR>PO, schedule…). The system:

1. **Profiles** every sheet.
2. **Classifies** each into a role: `primary_transactional`, `planning`, `inventory`, `supplier_master`, `procurement`, `schedule`, or ignored (`supporting`, `unknown`).
3. **Detects relationships** between sheets by matching column names to known aliases (part / material / item, supplier / vendor, PO, PR, STO…) with a confidence score.
4. **Plans the integration**: picks one primary sheet and left-joins only the relevant supporting sheets to it — never blindly joining everything.
5. **Builds one canonical dataset** saved as `canonical_procurement.parquet`.

---

## 8. Tech stack in one line each

| Tool | Why it's used |
|---|---|
| **Python 3.11** | Language |
| **Polars** | Fast dataframe engine for all cleaning and analytics |
| **pandas + openpyxl + pyxlsb** | Only for reading messy Excel (`.xlsx` / `.xlsb`) |
| **PyArrow / Parquet** | Compact, fast storage for the processed dataset |
| **Flask** | Small web server + JSON API |
| **HTML / CSS / JavaScript** | Dashboard (custom charts, no heavy framework) |
| **Faker** | Generates realistic synthetic SAP data for demos and testing |

---

## 9. The demo data

`scripts/generate_faker_data.py` creates a synthetic PPC dataset **with deliberately injected problems**:

- missing supplier names
- missing descriptions
- duplicate rows
- `#DIV/0!` in coverage
- stray `<br>` HTML in text

This proves the cleaning layer works, and it means **no real company data is needed for a demo**.

---

## 10. How to run it

```bash
# 1. Generate demo data
python scripts/generate_faker_data.py

# 2. (Optional) Run the pipeline from the command line
python scripts/run_pipeline.py

# 3. Start the web app
python run.py
# open http://127.0.0.1:5000/upload  -> upload a workbook
# open http://127.0.0.1:5000/        -> dashboard
```

---

## 11. Likely questions and short answers

**Q: Is this AI?**
It is intelligent automation: profiling, classification, and rule-based insights. There is no LLM in the loop today, which is deliberate — results are repeatable and auditable. An AI narrative layer is planned on top (see `04_FUTURE_SCOPE.md`).

**Q: Why Polars instead of pandas?**
Polars is much faster for grouping and aggregations and uses less memory. pandas is used only where Excel readers require it.

**Q: What if a column is missing or named differently?**
The mapper translates known aliases to standard names, and every analytics function checks that required columns exist and returns an empty result instead of crashing. Unmapped columns are reported so nothing is silently lost.

**Q: What if the data is dirty?**
That's what the cleaning layer is for. Excel errors become nulls, coverage is cast safely so bad values become "Unknown" rather than breaking the run.

**Q: Can it handle a new report format?**
Yes, for formats that use known column names. For new ones you add aliases to the mapper (one line each). The design isolates report-specific names in a single place.

**Q: How do you make it faster and safer?**
Caching, background jobs, and stricter upload security — all detailed in `04_FUTURE_SCOPE.md`.

**Q: Where is the source of truth?**
The processed Parquet file in `data/processed/`. The dashboard reads from it.

---

## 12. Suggested 3-minute demo script

1. **(30s)** Show the messy Excel: multiple sheets, errors, blanks.
2. **(30s)** Upload it on `/upload`.
3. **(30s)** Show the workbook analysis: which sheet was chosen as primary and why, which joins were made.
4. **(60s)** Open the dashboard: KPIs → coverage chart → critical parts → top supplier by shortfall.
5. **(30s)** Open Insights: point to a `rule_id` and explain that it's traceable.

---

*Related docs: `02_ARCHITECTURE.md` · `03_DIAGRAMS.md` · `04_FUTURE_SCOPE.md`*