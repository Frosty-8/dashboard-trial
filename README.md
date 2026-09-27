# README.md
              SYNTHETIC / SAP DATA
                       │
                       ▼
                ┌─────────────┐
                │  INGESTION  │
                └──────┬──────┘
                       ▼
                ┌─────────────┐
                │   PROFILER  │
                └──────┬──────┘
                       ▼
                ┌─────────────┐
                │TRANSFORMATION│
                └──────┬──────┘
                       ▼
                ┌─────────────┐
                │   SEMANTIC  │
                │    MODEL    │
                └──────┬──────┘
                       ▼
              ┌────────┴────────┐
              ▼                 ▼
          ANALYTICS          INSIGHTS
              │                 │
              └────────┬────────┘
                       ▼
                    FLASK API
                       │
                       ▼
                  DASHBOARD