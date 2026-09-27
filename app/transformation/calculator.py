from __future__ import annotations

import polars as pl


class BusinessCalculator:
    """Creates derived business metrics from canonical fields."""

    def calculate(
        self,
        df: pl.DataFrame,
    ) -> pl.DataFrame:
        expressions: list[pl.Expr] = []

        # ---------------------------------------------------------
        # Calculated Coverage
        # ---------------------------------------------------------
        if self._has(
            df,
            "current_stock",
            "monthly_requirement",
        ):
            expressions.append(
                pl.when(
                    pl.col("monthly_requirement") > 0
                )
                .then(
                    (
                        pl.col("current_stock")
                        / pl.col("monthly_requirement")
                    ).round(2)
                )
                .otherwise(None)
                .alias("calculated_coverage")
            )

        # ---------------------------------------------------------
        # Calculated Shortfall
        # ---------------------------------------------------------
        if self._has(
            df,
            "monthly_requirement",
            "current_stock",
        ):
            expressions.append(
                (
                    pl.col("monthly_requirement")
                    - pl.col("current_stock")
                )
                .clip(lower_bound=0)
                .alias("calculated_shortfall")
            )

        # ---------------------------------------------------------
        # Calculated Inventory Value
        # ---------------------------------------------------------
        if self._has(
            df,
            "current_stock",
            "unit_price",
        ):
            expressions.append(
                (
                    pl.col("current_stock")
                    * pl.col("unit_price")
                )
                .round(2)
                .alias("calculated_inventory_value")
            )

        # ---------------------------------------------------------
        # Shortfall Status
        # ---------------------------------------------------------
        if self._has(
            df,
            "shortfall_quantity",
        ):
            expressions.append(
                pl.when(
                    pl.col("shortfall_quantity") > 0
                )
                .then(pl.lit("Shortfall"))
                .otherwise(pl.lit("No Shortfall"))
                .alias("shortfall_status")
            )

        # ---------------------------------------------------------
        # Coverage Status
        # ---------------------------------------------------------
        if self._has(
            df,
            "coverage",
        ):
            expressions.append(
                pl.when(
                    pl.col("coverage").is_null()
                )
                .then(pl.lit("Unknown"))
                .when(
                    pl.col("coverage") < 1
                )
                .then(pl.lit("Critical"))
                .when(
                    pl.col("coverage") < 2
                )
                .then(pl.lit("Low"))
                .when(
                    pl.col("coverage") <= 6
                )
                .then(pl.lit("Healthy"))
                .otherwise(pl.lit("Excess"))
                .alias("coverage_status")
            )

        # ---------------------------------------------------------
        # Apply Expressions
        # ---------------------------------------------------------
        if expressions:
            df = df.with_columns(expressions)

        return df

    @staticmethod
    def _has(
        df: pl.DataFrame,
        *columns: str,
    ) -> bool:
        return all(
            column in df.columns
            for column in columns
        )