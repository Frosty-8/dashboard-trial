from __future__ import annotations

from flask import (
    Blueprint,
    jsonify,
    render_template,
    request,
)
import polars as pl
from app.analytics.report import AnalyticsReport
from app.config import PROCESSED_DIR
from app.ingestion.excel_reader import ExcelReader
from app.transformation.calculator import BusinessCalculator
from app.transformation.cleaner import DataCleaner
from app.transformation.mapper import BusinessMapper


dashboard_api_bp = Blueprint(
    "dashboard_api",
    __name__,
    url_prefix="/api/dashboard",
)

dashboard_page_bp = Blueprint(
    "dashboard_page",
    __name__,
)


def get_processed_file():
    """
    Prefer the new canonical procurement dataset.

    Fall back to the legacy PPC dataset so the existing
    pipeline continues to work.
    """

    canonical_path = (
        PROCESSED_DIR
        / "canonical_procurement.parquet"
    )

    legacy_path = (
        PROCESSED_DIR
        / "ppc_clean.parquet"
    )

    if canonical_path.exists():
        return canonical_path

    if legacy_path.exists():
        return legacy_path

    return None


def load_processed_data():
    """
    Load the latest available processed dataset and run it
    through the existing business transformation pipeline.
    """

    file_path = get_processed_file()

    if file_path is None:
        return None

    

    reader = ExcelReader()
    cleaner = DataCleaner()
    mapper = BusinessMapper()
    calculator = BusinessCalculator()

    if file_path.suffix.lower() == ".parquet":
    
        df = pl.read_parquet(file_path)
    else:
        df = reader.read(file_path)

    # ---------------------------------------------------------
    # Load
    # ---------------------------------------------------------

    df = reader.read(file_path)

    # ---------------------------------------------------------
    # Existing transformation pipeline
    # ---------------------------------------------------------

    df = cleaner.clean(df)

    df = mapper.map(df)

    df = calculator.calculate(df)

    return df


@dashboard_page_bp.get("/")
def dashboard():
    """
    Main application dashboard.
    """

    return render_template(
        "dashboard.html"
    )


@dashboard_api_bp.get("")
def dashboard_data():
    """
    JSON API used by the dashboard frontend.
    """

    try:

        df = load_processed_data()

        if df is None:

            return jsonify(
                {
                    "success": False,
                    "message": (
                        "No processed procurement dataset "
                        "found. Analyze a workbook first."
                    ),
                }
            ), 404

        report = AnalyticsReport().build(df)

        return jsonify(
            {
                "success": True,
                "data": report,
            }
        )

    except Exception as exc:

        print("\n" + "=" * 70)
        print("DASHBOARD ANALYTICS FAILED")
        print("=" * 70)

        print(
            f"Exception type : {type(exc).__name__}"
        )

        print(
            f"Exception      : {exc}"
        )

        print("=" * 70)

        return jsonify(
            {
                "success": False,
                "error_type": type(exc).__name__,
                "message": str(exc),
            }
        ), 500


@dashboard_api_bp.get("/preview")
def dashboard_preview():
    """
    Return a lightweight preview of the active processed dataset.

    Query parameters:
        limit: number of rows to return.
               Default 50, maximum 200.
    """

    file_path = get_processed_file()

    if file_path is None:

        return jsonify(
            {
                "success": False,
                "message": (
                    "No processed dataset found. "
                    "Analyze a workbook first."
                ),
            }
        ), 404

    # ---------------------------------------------------------
    # Limit preview size
    # ---------------------------------------------------------

    try:

        limit = int(
            request.args.get(
                "limit",
                50,
            )
        )

    except (
        TypeError,
        ValueError,
    ):

        limit = 50

    limit = max(
        1,
        min(limit, 200),
    )

    # ---------------------------------------------------------
    # Load processed dataset
    # ---------------------------------------------------------

    try:

        reader = ExcelReader()

        df = reader.read(
            file_path
        )

        total_rows = df.height
        total_columns = df.width

        preview = df.head(
            limit
        )

        # -----------------------------------------------------
        # Schema information
        # -----------------------------------------------------

        schema = [
            {
                "name": name,
                "dtype": str(dtype),
            }
            for name, dtype
            in preview.schema.items()
        ]

        # -----------------------------------------------------
        # JSON-safe data
        # -----------------------------------------------------

        records = preview.to_dicts()

        return jsonify(
            {
                "success": True,

                "dataset": {
                    "filename": file_path.name,
                    "rows": total_rows,
                    "columns": total_columns,
                },

                "preview": {
                    "limit": limit,
                    "returned_rows": preview.height,
                    "schema": schema,
                    "data": records,
                },
            }
        )

    except Exception as exc:

        return jsonify(
            {
                "success": False,
                "error_type": type(exc).__name__,
                "message": str(exc),
            }
        ), 500


@dashboard_api_bp.get("/status")
def dashboard_status():
    """
    Return the status of the active processed dataset.
    """

    file_path = get_processed_file()

    return jsonify(
        {
            "success": True,

            "available": file_path is not None,

            "dataset": (
                file_path.name
                if file_path is not None
                else None
            ),
        }
    )