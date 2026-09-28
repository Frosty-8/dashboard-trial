# Future Scope — Faster, Safer, More Explainable

> Where this project can go next. Each item says **what it is, why it matters, and how to do it in this codebase**. Items are grouped by theme and ranked at the end.

---

## 0. Starting point (what the code does today)

Understanding the current behaviour makes the roadmap obvious:

- `/api/dashboard` **re-reads the Parquet and re-runs clean → map → calculate → all analytics on every request**.
- Uploads are analyzed **inside the web request** (synchronously).
- Every upload **overwrites** one shared `canonical_procurement.parquet`.
- Insights are **rule-based** (deterministic), with thresholds set in more than one place.
- No authentication, no upload size limit, stack traces returned in error responses, Flask runs with `debug=True`.

---

## 1. Speed

### 1.1 Cache the dashboard report  ⭐ highest value, lowest effort
**Problem:** the same result is recomputed for every page load and refresh.
**Idea:** compute the report once per dataset version and reuse it.

| Level | How | Good for |
|---|---|---|
| **A. In-process cache** | Keep `AnalyticsReport().build(df)` in a dict keyed by the Parquet file's modified time (`mtime`) or a content hash | Single user / demo, ~10 lines of code |
| **B. Precompute on upload** | At the end of `/api/workbook/analyze`, build the report and save `report.json` next to the Parquet; `/api/dashboard` just reads it | Fast loads, no cache to invalidate |
| **C. Shared cache (Redis)** | Store the report JSON under `report:{dataset_id}:{version}` with a TTL | Multiple app instances / users |

**Invalidate** whenever a new dataset is written (version bump or new key).
**Also cache:** the raw Parquet dataframe in memory, and HTTP responses with `ETag` / `Cache-Control` so the browser can skip unchanged payloads.

### 1.2 Stop repeating the transformation
`load_processed_data()` re-cleans and re-maps data that was already cleaned. Save the **fully transformed** dataset (after the calculator) and load that directly. Keep the raw canonical file only for reprocessing.

### 1.3 Use Polars lazily
Switch to `pl.scan_parquet(...)` and lazy expressions so Polars reads only needed columns and runs the whole chain in one optimized plan. Many analytics functions touch just a few columns.

### 1.4 Compute once, reuse many times
`coverage_status` is derived in the calculator and again as a fallback inside inventory analytics; several modules group by `supplier_name` separately. Compute shared aggregates once and pass them along.

### 1.5 Background jobs for heavy work
Move workbook analysis to a queue (RQ / Celery / a simple thread pool at first).
Flow: upload → return a `job_id` immediately → UI polls `/api/jobs/{id}` → progress bar → dashboard opens when done. Large `.xlsb` files stop blocking the server.

### 1.6 Faster Excel reading
Excel parsing is the slowest step. Options: read only the sheets the plan selects (already partly done), convert `.xlsb` once and store as Parquet, cache the sheet profile keyed by file hash so re-uploading the same file is instant.

### 1.7 Paginate and slim payloads
Server-side pagination for large tables, return only fields the UI displays, and gzip JSON responses.

### 1.8 Query engine for big data
If data grows beyond memory: **DuckDB** over Parquet (SQL, very fast, zero server) or partitioned Parquet by month/plant.

---

## 2. Safety and security

### 2.1 Secure uploads  ⭐ high value
- Enforce **max file size** (`MAX_CONTENT_LENGTH`).
- Sanitize names with `werkzeug.utils.secure_filename` and store as `{uuid}_{name}` so uploads never overwrite each other.
- Validate **content**, not just extension (check the file signature / try-open in a sandbox).
- Reject macro-enabled files; scan with antivirus (e.g. ClamAV) in the pipeline.
- Cap sheets, rows and columns to prevent "zip bomb" style workbooks.
- Delete or archive uploads after a retention period.

### 2.2 Authentication and authorization
SSO (Azure AD / Okta) or at minimum login + roles: *viewer* (dashboard), *analyst* (upload), *admin* (rules and thresholds). Per-plant or per-department data scoping if needed.

### 2.3 Multi-user isolation
Give each upload a `dataset_id` and store under `data/processed/{dataset_id}/...`. Today a second user's upload silently replaces the first user's dashboard.

### 2.4 Production hardening
- Turn off `debug=True`; serve with **gunicorn / waitress** behind nginx.
- Return **generic error messages** to the client and log the stack trace server-side only (the API currently returns tracebacks).
- Add **rate limiting**, CSRF protection for forms, security headers (CSP, `X-Content-Type-Options`), HTTPS.
- Configuration via environment variables / secrets manager, not hard-coded values.

### 2.5 Data protection
Encryption at rest and in transit, masking of sensitive supplier or pricing fields by role, and a retention policy. Keep the **synthetic data generator** as the default for demos and screenshots.

### 2.6 Audit trail
Log who uploaded what, when, which plan was chosen, and which rule versions ran. Essential for a finance-adjacent procurement tool.

---

## 3. Data quality and correctness

### 3.1 Data validation rules
Add a schema check step (e.g. **Pandera** or **Great Expectations**): required columns present, no negative stock, price > 0, part numbers unique in the primary sheet, join keys mostly non-null.

### 3.2 Data-quality score
Turn the profiler output into a visible score (completeness, uniqueness, validity) on the dashboard and warn when quality is too low to trust.

### 3.3 Join safety checks
After each join, report matched vs unmatched rows and warn on **row-count explosion** (left join that unexpectedly multiplies rows). The integrator already keeps warnings; extend them.

### 3.4 Single source of truth for thresholds
Coverage limits (1 / 2 / 6) appear in `config.py`, `InsightRules`, `calculator.py` and `inventory.py`. Read them all from one settings object, ideally editable from an admin screen or a YAML file.

### 3.5 Unify the two processing paths
`/api/process` (→ `ppc_clean.parquet`) and `/api/workbook/analyze` (→ `canonical_procurement.parquet`) overlap. Converge on one path and one storage location.

### 3.6 Reconcile calculated vs reported values
The calculator produces `calculated_coverage`, `calculated_shortfall`, `calculated_inventory_value`, while the report supplies its own. Add a **reconciliation insight**: "N parts differ from SAP's own figure by more than X%". This catches SAP-side or spreadsheet formula errors.

### 3.7 Versioned datasets and history
Keep each processed dataset with a timestamp. Enables **trend over time** ("critical parts this week vs last week") and rollback.

---

## 4. Better insights and explainability

### 4.1 Richer rule library
Ideas that fit the existing rule engine:
- Coverage below threshold **and** no open PO / STO → "no recovery in sight"
- Open PO exists but coverage still critical → "PO too small or too late"
- Supplier concentration % of total shortfall (top 3 suppliers)
- Single-source risk (only one supplier for a critical part)
- Slow-moving stock (high coverage + low forecast)
- Forecast vs stock: month where projected ending stock turns negative
- Priority mismatch (high priority part with healthy coverage)

### 4.2 "Why?" drill-down
Every insight links to the **exact rows** that triggered it (`affected_records` already exists; add the row list) plus the formula and thresholds used. One click from "34 critical parts" to the 34 parts.

### 4.3 Recommendations, not just alerts
Attach a suggested action and owner: "Expedite PO for supplier X", "Raise STO from BLR to NCR", "Pause orders for excess parts". Keep them rule-derived so they stay auditable.

### 4.4 Severity scoring and prioritization
Score = shortfall × unit price × urgency. Rank parts by **business impact**, not just quantity.

### 4.5 Real forecasting
`ForecastAnalytics` currently summarizes forecast columns from the report. Add statistical forecasting (moving average, exponential smoothing, Prophet/statsforecast) with confidence bands, and an accuracy view (forecast vs actual).

### 4.6 Anomaly detection
Flag unusual changes: sudden stock drops, outlier prices, requirement spikes versus history (z-score / IQR first, ML later).

### 4.7 Optional LLM narrative layer (safely)
Use an LLM **only to phrase and summarize** numbers already computed by the rules — never to compute them.
- Input: the JSON report (KPIs + insights).
- Output: a short weekly summary in plain English, or a "chat with your data" that answers from precomputed aggregates.
- Guardrails: send aggregates instead of raw rows where possible, cite the `rule_id` behind every statement, keep the deterministic numbers as the source of truth, and log prompts and responses.

---

## 5. Product and user experience

- **Filters**: by plant (NCR / BLR), supplier, category, priority, project.
- **Export**: Excel/PDF/CSV of shortfall lists; scheduled email of the weekly report.
- **Alerts**: email/Teams/Slack when critical count rises.
- **Compare uploads**: this week vs last week.
- **Upload wizard**: show the integration plan and let the user override the primary sheet or a join before processing.
- **Mapping editor**: let admins add column aliases from a UI instead of editing `mapper.py`.
- **Better empty and error states**, loading skeletons, mobile layout.

---

## 6. Integration with SAP

- Replace manual Excel exports with **direct extraction**: SAP OData / RFC / BAPI, SAP Datasphere or BW extracts, scheduled SFTP drops.
- Land raw extracts in storage, run the same pipeline on a schedule (e.g. daily 6 AM).
- Write results back or publish to Power BI / Tableau as a governed dataset.

---

## 7. Engineering quality

- **Automated tests** (`pytest`): cleaner cases (each error token), mapper aliases, calculator formulas, coverage-status boundaries (0.99, 1.0, 1.99, 2.0, 6.0, 6.01), rule outputs on a small fixture, API tests with Flask's test client.
- **CI**: lint (ruff), type check (mypy), tests on every push.
- **Dependency hygiene**: `requirements.txt` is empty; either generate it from `pyproject.toml` or remove it. Pin versions.
- **Logging** instead of `print`, with request IDs.
- **Config per environment** (dev / test / prod).
- **Docker**: one image, reproducible run.
- **Monitoring**: timing per pipeline stage, error rates, dataset size, cache hit rate.
- **Docs**: replace the unreadable `ARCHITECTURE.md` in the repo with `02_ARCHITECTURE.md`.

---

## 8. Suggested roadmap

### Phase 1 — Quick wins (days)
| # | Item | Benefit |
|---|---|---|
| 1 | Cache report by file `mtime` (1.1 A) | Instant dashboard reloads |
| 2 | Save fully transformed data; skip re-cleaning (1.2) | Less work per request |
| 3 | Unique upload names + size limit + `secure_filename` (2.1) | Safer, no overwrites |
| 4 | Hide tracebacks; turn off debug in prod (2.4) | Closes an info leak |
| 5 | Central thresholds (3.4) | Consistent numbers |
| 6 | Unit tests for calculator, cleaner, rules (7) | Confidence when changing things |

### Phase 2 — Robustness (weeks)
| # | Item | Benefit |
|---|---|---|
| 7 | Precompute report on upload (1.1 B) | Predictable performance |
| 8 | `dataset_id` per upload, history (2.3, 3.7) | Multi-user, trends |
| 9 | Background jobs + progress (1.5) | No blocked requests |
| 10 | Validation + data-quality score (3.1, 3.2) | Trust in the data |
| 11 | Login and roles (2.2) | Access control |
| 12 | Richer insights + "why" drill-down (4.1, 4.2) | Real explainability |

### Phase 3 — Scale and intelligence (months)
| # | Item | Benefit |
|---|---|---|
| 13 | Redis cache, DuckDB/Postgres, Docker deployment (1.1 C, 1.8) | Team-scale |
| 14 | Direct SAP extraction on a schedule (6) | End-to-end automation |
| 15 | Forecasting + anomaly detection (4.5, 4.6) | Predict, not just report |
| 16 | LLM narrative summaries with guardrails (4.7) | Easier consumption |
| 17 | Audit log, encryption, monitoring (2.5, 2.6, 7) | Enterprise readiness |

---

## 9. Talking points (how to explain this in 30 seconds)

> "Today it's a working, explainable pipeline: upload a workbook, get a clean dataset and a dashboard with traceable insights.
> Next I'd make it **faster** by caching the report so it isn't recomputed every load and moving heavy work to background jobs; **safer** with hardened uploads, per-user datasets, authentication and audit logs; and **smarter** with richer rules, real forecasting, and an optional AI summary that only explains numbers the rules already produced."

---

*Related docs: `01_PROJECT_EXPLANATION.md` · `02_ARCHITECTURE.md` · `03_DIAGRAMS.md`*