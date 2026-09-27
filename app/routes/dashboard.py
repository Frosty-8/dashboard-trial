from __future__ import annotations

from flask import Blueprint, jsonify, render_template

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


def load_processed_data():
    file_path = PROCESSED_DIR / "ppc_clean.parquet"

    if not file_path.exists():
        return None

    reader = ExcelReader()
    cleaner = DataCleaner()
    mapper = BusinessMapper()
    calculator = BusinessCalculator()

    df = reader.read(file_path)

    df = cleaner.clean(df)
    df = mapper.map(df)
    df = calculator.calculate(df)

    return df


@dashboard_page_bp.get("/")
def dashboard():
    """
    Main application dashboard.
    """
    return render_template("dashboard.html")


@dashboard_api_bp.get("")
def dashboard_data():
    """
    JSON API used by the dashboard frontend.
    """
    df = load_processed_data()

    if df is None:
        return jsonify(
            {
                "success": False,
                "message": (
                    "No processed PPC dataset found. "
                    "Run the pipeline first."
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


@dashboard_api_bp.get("/status")
def dashboard_status():
    file_path = PROCESSED_DIR / "ppc_clean.parquet"

    return jsonify(
        {
            "success": True,
            "available": file_path.exists(),
            "dataset": file_path.name
            if file_path.exists()
            else None,
        }
    )