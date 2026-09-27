# app/analytics/inventory.py

from __future__ import annotations

from typing import Any

import polars as pl


class InventoryAnalytics:
    """Analyzes stock, inventory value and coverage."""

    def coverage_distribution(
        self,
        df: pl.DataFrame,
    ) -> list[dict[str, Any]]:
        if "coverage_status" not in df.columns:
            return []

        result = (
            df.group_by("coverage_status")
            .agg(
                pl.len().alias("parts"),
                pl.col("current_stock")
                .sum()
                .alias("stock"),
                pl.col("inventory_value")
                .sum()
                .alias("inventory_value"),
            )
            .sort("parts", descending=True)
        )

        return result.to_dicts()

    def inventory_by_category(
        self,
        df: pl.DataFrame,
    ) -> list[dict[str, Any]]:
        required = {
            "category",
            "inventory_value",
            "current_stock",
        }

        if not required.issubset(df.columns):
            return []

        result = (
            df.group_by("category")
            .agg(
                pl.len().alias("parts"),
                pl.col("current_stock")
                .sum()
                .alias("stock"),
                pl.col("inventory_value")
                .sum()
                .alias("inventory_value"),
            )
            .sort(
                "inventory_value",
                descending=True,
            )
        )

        return result.to_dicts()

    def critical_parts(
        self,
        df: pl.DataFrame,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        required = {
            "part_number",
            "supplier_name",
            "current_stock",
            "monthly_requirement",
            "coverage",
            "shortfall_quantity",
        }

        if not required.issubset(df.columns):
            return []

        result = (
            df.filter(
                pl.col("coverage_status")
                == "Critical"
            )
            .select(
                [
                    "part_number",
                    "part_description",
                    "supplier_name",
                    "current_stock",
                    "monthly_requirement",
                    "coverage",
                    "shortfall_quantity",
                    "inventory_value",
                ]
            )
            .sort(
                "shortfall_quantity",
                descending=True,
            )
            .head(limit)
        )

        return result.to_dicts()