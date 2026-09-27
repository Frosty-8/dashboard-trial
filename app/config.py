# app/config.py

from __future__ import annotations

from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]

DATA_DIR = BASE_DIR / "data"

RAW_DIR = DATA_DIR / "raw"

GENERATED_DIR = DATA_DIR / "generated"

PROCESSED_DIR = DATA_DIR / "processed"

ANALYTICS_DIR = DATA_DIR / "analytics"

UPLOAD_DIR = DATA_DIR / "uploads"

for directory in [
    RAW_DIR,
    GENERATED_DIR,
    PROCESSED_DIR,
    ANALYTICS_DIR,
    UPLOAD_DIR,
]:
    directory.mkdir(
        parents=True,
        exist_ok=True,
    )


class Settings:
    APP_NAME = "SAP PPC Data Intelligence"
    VERSION = "0.1.0"

    MAX_UPLOAD_SIZE_MB = 50

    CRITICAL_COVERAGE = 1.0
    LOW_COVERAGE = 2.0
    EXCESS_COVERAGE = 6.0

    ALLOWED_EXTENSIONS = {
        ".xlsx",
        ".xlsb",
        ".csv",
        ".parquet",
    }


settings = Settings()