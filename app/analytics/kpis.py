# app/analytics/kpis.py

from __future__ import annotations

from typing import Any

import polars as pl


class KPIAnalytics:
    """Generates high-level procurement and inventory KPIs."""

    def calculate(self, df: pl.DataFrame) -> dict[str, Any]:
        total_parts = df.height

        return {
            "total_parts": total_parts,
            "total_inventory_value": self._sum(
                df,
                "inventory_value",
            ),
            "total_current_stock": self._sum(
                df,
                "current_stock",
            ),
            "total_monthly_requirement": self._sum(
                df,
                "monthly_requirement",
            ),
            "total_shortfall": self._sum(
                df,
                "shortfall_quantity",
            ),
            "total_open_po": self._sum(
                df,
                "open_po",
            ),
            "total_open_sto": self._sum(
                df,
                "open_sto",
            ),
            "total_sto_intransit": self._sum(
                df,
                "sto_intransit",
            ),
            "critical_parts": self._count(
                df,
                "coverage_status",
                "Critical",
            ),
            "low_coverage_parts": self._count(
                df,
                "coverage_status",
                "Low",
            ),
            "healthy_parts": self._count(
                df,
                "coverage_status",
                "Healthy",
            ),
            "excess_parts": self._count(
                df,
                "coverage_status",
                "Excess",
            ),
            "shortfall_parts": self._count(
                df,
                "shortfall_status",
                "Shortfall",
            ),
        }

    @staticmethod
    def _sum(
        df: pl.DataFrame,
        column: str,
    ) -> float:
        if column not in df.columns:
            return 0.0

        value = df[column].sum()

        return round(
            float(value or 0),
            2,
        )

    @staticmethod
    def _count(
        df: pl.DataFrame,
        column: str,
        value: str,
    ) -> int:
        if column not in df.columns:
            return 0

        return df.filter(
            pl.col(column) == value
        ).height