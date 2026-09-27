# app/analytics/inventory.py

from __future__ import annotations

from typing import Any

import polars as pl


class InventoryAnalytics:
    """Analyzes stock, inventory value and coverage."""

    @staticmethod
    def _coverage_status_expression() -> pl.Expr:
        """
        Build a safe coverage classification expression.

        Coverage may arrive from Excel/SAP data as either a numeric
        value or a string. Invalid/non-numeric values are converted
        to null instead of causing the analytics pipeline to fail.

        Classification:
            < 1       -> Critical
            < 2       -> Low
            <= 6      -> Healthy
            > 6       -> Excess
            null      -> Unknown
        """

        coverage = pl.col("coverage").cast(
            pl.Float64,
            strict=False,
        )

        return (
            pl.when(coverage.is_null())
            .then(pl.lit("Unknown"))
            .when(coverage < 1)
            .then(pl.lit("Critical"))
            .when(coverage < 2)
            .then(pl.lit("Low"))
            .when(coverage <= 6)
            .then(pl.lit("Healthy"))
            .otherwise(pl.lit("Excess"))
        )

    def coverage_distribution(
        self,
        df: pl.DataFrame,
    ) -> list[dict[str, Any]]:
        """Return inventory distribution by coverage status."""

        if "coverage_status" not in df.columns:
            return []

        result = (
            df.group_by("coverage_status")
            .agg(
                pl.len().alias("parts"),
                pl.col("current_stock")
                .cast(pl.Float64, strict=False)
                .sum()
                .alias("stock"),
                pl.col("inventory_value")
                .cast(pl.Float64, strict=False)
                .sum()
                .alias("inventory_value"),
            )
            .sort(
                "parts",
                descending=True,
            )
        )

        return result.to_dicts()

    def inventory_by_category(
        self,
        df: pl.DataFrame,
    ) -> list[dict[str, Any]]:
        """Return inventory value and stock grouped by category."""

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
                .cast(pl.Float64, strict=False)
                .sum()
                .alias("stock"),
                pl.col("inventory_value")
                .cast(pl.Float64, strict=False)
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
        """Return parts with critical inventory coverage."""

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

        # Make sure coverage_status exists and is based on
        # a numeric-safe version of coverage.
        if "coverage_status" not in df.columns:
            df = df.with_columns(
                self._coverage_status_expression().alias(
                    "coverage_status"
                )
            )

        result = (
            df.filter(
                pl.col("coverage_status") == "Critical"
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