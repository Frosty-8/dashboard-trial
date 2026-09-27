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
            current_stock = pl.col(
                "current_stock"
            ).cast(
                pl.Float64,
                strict=False,
            )

            monthly_requirement = pl.col(
                "monthly_requirement"
            ).cast(
                pl.Float64,
                strict=False,
            )

            expressions.append(
                pl.when(
                    monthly_requirement > 0
                )
                .then(
                    (
                        current_stock
                        / monthly_requirement
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
            monthly_requirement = pl.col(
                "monthly_requirement"
            ).cast(
                pl.Float64,
                strict=False,
            )

            current_stock = pl.col(
                "current_stock"
            ).cast(
                pl.Float64,
                strict=False,
            )

            expressions.append(
                (
                    monthly_requirement
                    - current_stock
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
            current_stock = pl.col(
                "current_stock"
            ).cast(
                pl.Float64,
                strict=False,
            )

            unit_price = pl.col(
                "unit_price"
            ).cast(
                pl.Float64,
                strict=False,
            )

            expressions.append(
                (
                    current_stock
                    * unit_price
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
            shortfall_quantity = pl.col(
                "shortfall_quantity"
            ).cast(
                pl.Float64,
                strict=False,
            )

            expressions.append(
                pl.when(
                    shortfall_quantity > 0
                )
                .then(
                    pl.lit("Shortfall")
                )
                .otherwise(
                    pl.lit("No Shortfall")
                )
                .alias("shortfall_status")
            )

        # ---------------------------------------------------------
        # Coverage Status
        # ---------------------------------------------------------
        if self._has(
            df,
            "coverage",
        ):
            # SAP/Excel may provide coverage as:
            #
            #     1.5
            #     "1.5"
            #     "6"
            #     ""
            #     "N/A"
            #
            # Convert safely to Float64 before comparing.
            coverage = pl.col(
                "coverage"
            ).cast(
                pl.Float64,
                strict=False,
            )

            expressions.append(
                pl.when(
                    coverage.is_null()
                )
                .then(
                    pl.lit("Unknown")
                )
                .when(
                    coverage < 1
                )
                .then(
                    pl.lit("Critical")
                )
                .when(
                    coverage < 2
                )
                .then(
                    pl.lit("Low")
                )
                .when(
                    coverage <= 6
                )
                .then(
                    pl.lit("Healthy")
                )
                .otherwise(
                    pl.lit("Excess")
                )
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
        """Return True when all requested columns exist."""

        return all(
            column in df.columns
            for column in columns
        )