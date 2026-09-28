# app/analytics/procurement.py

from __future__ import annotations

from typing import Any

import polars as pl


class ProcurementAnalytics:
    """Analyzes procurement requirements and shortfalls."""

    def supplier_shortfalls(
        self,
        df: pl.DataFrame,
        limit: int = 15,
    ) -> list[dict[str, Any]]:
        required = {
            "supplier_name",
            "shortfall_quantity",
        }
    
        if not required.issubset(df.columns):
            return []
    
        # Optional procurement fields
        optional_numeric = {
            "open_po": 0.0,
            "open_sto": 0.0,
            "sto_intransit": 0.0,
        }
    
        expressions: list[pl.Expr] = []
    
        for column, default in optional_numeric.items():
            if column not in df.columns:
                expressions.append(
                    pl.lit(default).alias(column)
                )
    
        if expressions:
            df = df.with_columns(expressions)
    
        result = (
            df.group_by("supplier_name")
            .agg(
                pl.len().alias("parts"),
    
                pl.col("shortfall_quantity")
                .sum()
                .alias("shortfall"),
    
                pl.col("open_po")
                .sum()
                .alias("open_po"),
    
                pl.col("open_sto")
                .sum()
                .alias("open_sto"),
    
                pl.col("sto_intransit")
                .sum()
                .alias("sto_intransit"),
            )
            .sort(
                "shortfall",
                descending=True,
            )
            .head(limit)
        )
    
        return result.to_dicts()

    def priority_distribution(
        self,
        df: pl.DataFrame,
    ) -> list[dict[str, Any]]:
        if "priority" not in df.columns:
            return []

        result = (
            df.group_by("priority")
            .agg(
                pl.len().alias("parts")
            )
            .sort(
                "parts",
                descending=True,
            )
        )

        return result.to_dicts()

    def shortfall_parts(
        self,
        df: pl.DataFrame,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        required = {
            "part_number",
            "supplier_name",
            "shortfall_quantity",
        }

        if not required.issubset(df.columns):
            return []

        columns = [
            "part_number",
            "part_description",
            "supplier_name",
            "monthly_requirement",
            "current_stock",
            "shortfall_quantity",
            "coverage",
            "priority",
        ]

        columns = [
            column
            for column in columns
            if column in df.columns
        ]

        result = (
            df.filter(
                pl.col("shortfall_quantity") > 0
            )
            .select(columns)
            .sort(
                "shortfall_quantity",
                descending=True,
            )
            .head(limit)
        )

        return result.to_dicts()