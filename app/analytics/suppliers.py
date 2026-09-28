# app/analytics/suppliers.py

from __future__ import annotations

from typing import Any

import polars as pl


class SupplierAnalytics:
    """Analyzes supplier-level procurement exposure."""

    def performance(
        self,
        df: pl.DataFrame,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        if "supplier_name" not in df.columns:
            return []

        # --------------------------------------------------------------
        # Required business fields
        # --------------------------------------------------------------

        required = {
            "shortfall_quantity",
            "monthly_requirement",
            "inventory_value",
        }

        if not required.issubset(df.columns):
            return []

        # --------------------------------------------------------------
        # Optional numeric fields
        #
        # Some SAP workbooks do not contain every procurement field.
        # Missing fields are treated as zero instead of crashing
        # dashboard analytics.
        # --------------------------------------------------------------

        numeric_defaults = {
            "current_stock": 0.0,
            "open_po": 0.0,
            "open_sto": 0.0,
            "sto_intransit": 0.0,
        }

        expressions: list[pl.Expr] = []

        for column, default in numeric_defaults.items():
            if column not in df.columns:
                expressions.append(
                    pl.lit(default).alias(column)
                )

        if expressions:
            df = df.with_columns(expressions)

        # --------------------------------------------------------------
        # Supplier aggregation
        # --------------------------------------------------------------

        result = (
            df.group_by("supplier_name")
            .agg(
                pl.len().alias("parts"),

                pl.col("monthly_requirement")
                .sum()
                .alias("monthly_requirement"),

                pl.col("current_stock")
                .sum()
                .alias("current_stock"),

                pl.col("shortfall_quantity")
                .sum()
                .alias("shortfall"),

                pl.col("inventory_value")
                .sum()
                .alias("inventory_value"),

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
            .with_columns(
                pl.when(
                    pl.col("monthly_requirement") > 0
                )
                .then(
                    pl.col("shortfall")
                    / pl.col("monthly_requirement")
                    * 100
                )
                .otherwise(0)
                .round(2)
                .alias("shortfall_percent")
            )
            .sort(
                "shortfall",
                descending=True,
            )
            .head(limit)
        )

        return result.to_dicts()