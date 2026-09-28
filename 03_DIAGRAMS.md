# Diagrams — SAP PPC Data Intelligence

> All diagrams use [Mermaid](https://mermaid.js.org/). They render automatically on GitHub, GitLab, VS Code (Markdown Preview Mermaid Support extension), Obsidian and Notion. If your viewer shows raw code, paste the block into <https://mermaid.live>.

---

## 1. System overview (current)

```mermaid
flowchart TD
    A["SAP / Excel / CSV / Parquet"] --> B["Ingestion<br/>read · pick sheet · find header"]
    B --> C["Profiler<br/>rows · nulls · duplicates · errors"]
    C --> D["Cleaner<br/>errors · HTML · numbers · duplicates"]
    D --> E["Mapper<br/>aliases to canonical fields"]
    E --> F["Calculator<br/>coverage · shortfall · value · status"]
    F --> G[("Semantic model<br/>Parquet")]
    G --> H["Analytics<br/>KPIs · inventory · procurement<br/>suppliers · forecast"]
    G --> I["Insight engine<br/>rule based"]
    H --> J["Flask API"]
    I --> J
    J --> K["Dashboard<br/>HTML · CSS · JS"]
```

---

## 2. Multi-sheet workbook intelligence

How one messy workbook becomes one clean dataset.

```mermaid
flowchart TD
    W["Uploaded workbook<br/>.xlsx / .xlsb"] --> P["WorkbookProfiler<br/>profile every sheet"]
    P --> C["SheetClassifier<br/>assign a role per sheet"]
    P --> R["RelationshipDetector<br/>match part / supplier / PO / PR / STO columns"]
    C --> PL["WorkbookIntegrationPlanner"]
    R --> PL
    PL --> D1{"Primary role<br/>found?"}
    D1 -- yes --> PS["Highest scoring<br/>primary sheet"]
    D1 -- "no, single sheet" --> PS
    D1 -- "no, multi sheet" --> FB["Fallback: best likely<br/>data sheet"]
    FB --> PS
    PS --> J["Plan: selected sheets<br/>+ left joins to primary only"]
    J --> I["WorkbookIntegrator<br/>execute joins + add _source_sheet"]
    I --> O[("canonical_procurement<br/>.parquet")]
    I --> WR["Warnings<br/>unreadable or empty sheets"]
```

**Sheet roles**

```mermaid
flowchart LR
    S["Sheet"] --> R1["primary_transactional"]
    S --> R2["planning"]
    S --> R3["procurement"]
    S --> R4["inventory"]
    S --> R5["supplier_master"]
    S --> R6["schedule"]
    S --> R7["supporting / unknown"]
    R1 --> K["Kept"]
    R2 --> K
    R3 --> K
    R4 --> K
    R5 --> K
    R6 --> K
    R7 --> X["Ignored unless fallback primary"]
```

---

## 3. Sequence: upload to dashboard

```mermaid
sequenceDiagram
    autonumber
    actor U as Planner
    participant UI as Browser
    participant API as Flask API
    participant ING as Ingestion
    participant FS as data folder
    participant TR as Transform
    participant AN as Analytics + Insights

    U->>UI: Upload workbook on /upload
    UI->>API: POST /api/workbook/analyze
    API->>FS: Save file to data/uploads
    API->>ING: Profile, classify, detect relationships
    ING-->>API: Integration plan
    API->>ING: Integrate selected sheets
    ING-->>API: Canonical dataframe
    API->>FS: Write canonical_procurement.parquet
    API-->>UI: Plan, joins, warnings, row and column counts

    U->>UI: Open dashboard
    UI->>API: GET /api/dashboard
    API->>FS: Read Parquet
    API->>TR: Clean, map, calculate
    TR-->>API: Business dataset
    API->>AN: Build report
    AN-->>API: KPIs, views, insights
    API-->>UI: JSON payload
    UI-->>U: Charts, tables, insight cards
```

---

## 4. Data cleaning flow

```mermaid
flowchart LR
    R["Raw dataframe"] --> S1["Normalize<br/>column names"]
    S1 --> S2["Trim<br/>strings"]
    S2 --> S3["Error tokens to null<br/>#DIV/0! · N/A · - · blank"]
    S3 --> S4["Strip<br/>HTML tags"]
    S4 --> S5["Text to numbers<br/>remove commas, cast"]
    S5 --> S6["Drop fully<br/>empty columns"]
    S6 --> S7["Drop duplicate<br/>rows"]
    S7 --> C["Clean dataframe"]
```

---

## 5. Coverage status decision

```mermaid
flowchart TD
    A["coverage value"] --> B{"Valid number?"}
    B -- no --> U["Unknown"]
    B -- yes --> C{"less than 1 month?"}
    C -- yes --> CR["Critical"]
    C -- no --> D{"less than 2 months?"}
    D -- yes --> LO["Low"]
    D -- no --> E{"6 months or less?"}
    E -- yes --> H["Healthy"]
    E -- no --> EX["Excess"]

    style CR fill:#f8d7da,stroke:#c0392b,color:#000
    style LO fill:#ffe5b4,stroke:#e67e22,color:#000
    style H fill:#d4edda,stroke:#27ae60,color:#000
    style EX fill:#d6eaf8,stroke:#2980b9,color:#000
    style U fill:#e5e7e9,stroke:#7f8c8d,color:#000
```

---

## 6. Insight engine

```mermaid
flowchart LR
    DF["Business dataset"] --> RU["InsightRules"]
    RU --> R1["Coverage<br/>critical · low · excess"]
    RU --> R2["Procurement shortfall"]
    RU --> R3["Supplier concentration"]
    RU --> R4["Excess inventory value"]
    RU --> R5["STO in transit"]
    R1 --> EN["InsightEngine<br/>sort by severity + count"]
    R2 --> EN
    R3 --> EN
    R4 --> EN
    R5 --> EN
    EN --> OUT["critical → warning → info<br/>rule_id · description · affected_records"]
```

---

## 7. Dashboard map

```mermaid
flowchart TD
    D["Dashboard"] --> O["Overview<br/>KPIs · charts · latest insights"]
    D --> I["Inventory<br/>coverage · category · critical parts"]
    D --> P["Procurement<br/>supplier shortfall · priority · parts"]
    D --> S["Suppliers<br/>exposure · shortfall %"]
    D --> F["Forecast<br/>monthly demand · ending stock"]
    D --> N["Insights<br/>full explainable feed"]
```

---

## 8. Proposed future architecture

Target state with caching, background jobs, storage and security. Items in the dashed group are additions; see `04_FUTURE_SCOPE.md`.

```mermaid
flowchart TD
    U["User"] --> AUTH["Auth + roles<br/>SSO"]
    AUTH --> API["Flask / FastAPI API"]

    API --> UP["Secure upload<br/>size · type · virus scan"]
    UP --> OBJ[("Object storage<br/>raw files, versioned")]
    UP --> Q["Job queue"]

    Q --> W["Background workers<br/>ingest · clean · analyze"]
    W --> DB[("Processed store<br/>Parquet / DuckDB / Postgres")]
    W --> PRE["Precomputed report<br/>per dataset version"]

    API --> CACHE[("Cache<br/>Redis or in-memory")]
    CACHE --> PRE
    CACHE --> DB

    W --> AUD[("Audit log<br/>who · what · when")]
    W --> EXP["Explanation layer<br/>rules + optional LLM narrative"]
    EXP --> PRE

    API --> UI["Dashboard"]

    subgraph FUTURE["Additions"]
        Q
        W
        CACHE
        PRE
        AUD
        EXP
        AUTH
    end
```

---

## 9. Folder-to-layer map (for quick reference)

```mermaid
flowchart LR
    subgraph app
        A1["ingestion/"]
        A2["transformation/"]
        A3["analytics/"]
        A4["insights/"]
        A5["routes/"]
        A6["templates + static/"]
        A7["pipeline.py"]
        A8["config.py"]
    end
    A1 -->|"raw data"| A2
    A2 -->|"canonical data"| A3
    A2 --> A4
    A3 --> A5
    A4 --> A5
    A5 --> A6
    A7 -. "orchestrates" .-> A1
    A7 -. "orchestrates" .-> A2
    A7 -. "orchestrates" .-> A3
    A7 -. "orchestrates" .-> A4
    A8 -. "settings" .-> A1
    A8 -. "settings" .-> A4
```

---

*Related docs: `01_PROJECT_EXPLANATION.md` · `02_ARCHITECTURE.md` · `04_FUTURE_SCOPE.md`*