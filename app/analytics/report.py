# app/analytics/report.py

from __future__ import annotations

from typing import Any

import polars as pl

from app.analytics import (
    ForecastAnalytics,
    InventoryAnalytics,
    KPIAnalytics,
    ProcurementAnalytics,
    SupplierAnalytics,
)
from app.insights import InsightEngine


class AnalyticsReport:
    """Builds one frontend-friendly analytics payload."""

    def __init__(self) -> None:
        self.kpis = KPIAnalytics()
        self.inventory = InventoryAnalytics()
        self.procurement = ProcurementAnalytics()
        self.suppliers = SupplierAnalytics()
        self.forecast = ForecastAnalytics()
        self.insights = InsightEngine()

    def build(
        self,
        df: pl.DataFrame,
    ) -> dict[str, Any]:
        return {
            "kpis": self.kpis.calculate(df),
            "inventory": {
                "coverage_distribution": (
                    self.inventory.coverage_distribution(df)
                ),
                "inventory_by_category": (
                    self.inventory.inventory_by_category(df)
                ),
                "critical_parts": (
                    self.inventory.critical_parts(df)
                ),
            },
            "procurement": {
                "supplier_shortfalls": (
                    self.procurement.supplier_shortfalls(df)
                ),
                "priority_distribution": (
                    self.procurement.priority_distribution(df)
                ),
                "shortfall_parts": (
                    self.procurement.shortfall_parts(df)
                ),
            },
            "suppliers": {
                "performance": (
                    self.suppliers.performance(df)
                )
            },
            "forecast": {
                "monthly_summary": (
                    self.forecast.monthly_summary(df)
                ),
                "stock_projection": (
                    self.forecast.stock_projection(df)
                ),
            },
            "insights": self.insights.analyze(df),
        }