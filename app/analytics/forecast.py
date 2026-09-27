# app/analytics/forecast.py

from __future__ import annotations

import re
from typing import Any

import polars as pl


class ForecastAnalytics:
    """Converts monthly forecast columns into analytical time-series data."""

    MONTHS = [
        "jan",
        "feb",
        "mar",
        "apr",
        "may",
        "jun",
        "jul",
        "aug",
        "sep",
        "oct",
        "nov",
        "dec",
    ]

    def monthly_summary(
        self,
        df: pl.DataFrame,
    ) -> list[dict[str, Any]]:
        forecast_columns = [
            column
            for column in df.columns
            if re.match(
                r"^(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)_forecast$",
                column,
            )
        ]

        if not forecast_columns:
            return []

        expressions = []

        for column in forecast_columns:
            month = column.split("_")[0].upper()

            expressions.append(
                pl.col(column)
                .sum()
                .alias(month)
            )

        result = df.select(expressions)

        return [
            {
                "month": month,
                "forecast": result[month][0] or 0,
            }
            for month in [
                column.split("_")[0].upper()
                for column in forecast_columns
            ]
        ]

    def stock_projection(
        self,
        df: pl.DataFrame,
    ) -> list[dict[str, Any]]:
        stock_columns = [
            column
            for column in df.columns
            if re.match(
                r"^(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)_end_stock$",
                column,
            )
        ]

        if not stock_columns:
            return []

        expressions = [
            pl.col(column)
            .sum()
            .alias(column)
            for column in stock_columns
        ]

        result = df.select(expressions)

        output = []

        for column in stock_columns:
            month = column.split("_")[0].upper()

            output.append(
                {
                    "month": month,
                    "ending_stock": (
                        result[column][0] or 0
                    ),
                }
            )

        return output