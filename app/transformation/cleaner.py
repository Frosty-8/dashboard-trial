# app/transformation/cleaner.py

from __future__ import annotations

import re
from typing import Any

import polars as pl


class DataCleaner:
    """Cleans raw SAP/PPC report data before business transformation."""

    ERROR_VALUES = {
        "#DIV/0!",
        "#VALUE!",
        "#REF!",
        "#N/A",
        "#NAME?",
        "#NUM!",
        "#NULL!",
        "N/A",
        "NA",
        "NULL",
        "None",
        "-",
        "--",
        "",
    }

    def clean(self, df: pl.DataFrame) -> pl.DataFrame:
        df = self._normalize_column_names(df)
        df = self._clean_strings(df)
        df = self._replace_error_values(df)
        df = self._remove_html(df)
        df = self._normalize_numeric_columns(df)
        df = self._remove_empty_columns(df)
        df = self._remove_duplicate_rows(df)

        return df

    def _normalize_column_names(
        self,
        df: pl.DataFrame,
    ) -> pl.DataFrame:
        new_columns = []

        for column in df.columns:
            normalized = (
                column.strip()
                .lower()
                .replace("%", "percent")
                .replace("&", "and")
            )

            normalized = re.sub(
                r"[^a-z0-9]+",
                "_",
                normalized,
            )

            normalized = re.sub(
                r"_+",
                "_",
                normalized,
            ).strip("_")

            new_columns.append(normalized)

        return df.rename(
            dict(zip(df.columns, new_columns))
        )

    def _clean_strings(
        self,
        df: pl.DataFrame,
    ) -> pl.DataFrame:
        expressions: list[pl.Expr] = []

        for column in df.columns:
            if df[column].dtype == pl.String:
                expressions.append(
                    pl.col(column)
                    .str.strip_chars()
                    .alias(column)
                )

        if expressions:
            df = df.with_columns(expressions)

        return df

    def _replace_error_values(
        self,
        df: pl.DataFrame,
    ) -> pl.DataFrame:
        expressions: list[pl.Expr] = []

        for column in df.columns:
            if df[column].dtype == pl.String:
                expressions.append(
                    pl.when(
                        pl.col(column)
                        .str.strip_chars()
                        .str.to_uppercase()
                        .is_in(
                            [
                                value.upper()
                                for value in self.ERROR_VALUES
                            ]
                        )
                    )
                    .then(pl.lit(None))
                    .otherwise(pl.col(column))
                    .alias(column)
                )

        if expressions:
            df = df.with_columns(expressions)

        return df

    def _remove_html(
        self,
        df: pl.DataFrame,
    ) -> pl.DataFrame:
        expressions: list[pl.Expr] = []

        for column in df.columns:
            if df[column].dtype == pl.String:
                expressions.append(
                    pl.col(column)
                    .str.replace_all(
                        r"<[^>]+>",
                        "",
                    )
                    .str.strip_chars()
                    .alias(column)
                )

        if expressions:
            df = df.with_columns(expressions)

        return df

    def _normalize_numeric_columns(
        self,
        df: pl.DataFrame,
    ) -> pl.DataFrame:
        expressions: list[pl.Expr] = []

        numeric_hints = (
            "quantity",
            "requirement",
            "stock",
            "forecast",
            "coverage",
            "price",
            "value",
            "amount",
            "volume",
            "shortfall",
            "po",
            "sto",
            "mard",
            "vbbe",
            "percent",
        )

        for column in df.columns:
            if df[column].dtype != pl.String:
                continue

            if not any(
                hint in column
                for hint in numeric_hints
            ):
                continue

            expressions.append(
                pl.col(column)
                .str.replace_all(",", "")
                .str.strip_chars()
                .cast(
                    pl.Float64,
                    strict=False,
                )
                .alias(column)
            )

        if expressions:
            df = df.with_columns(expressions)

        return df

    def _remove_empty_columns(
        self,
        df: pl.DataFrame,
    ) -> pl.DataFrame:
        non_empty_columns: list[str] = []

        for column in df.columns:
            if df[column].null_count() < df.height:
                non_empty_columns.append(column)

        return df.select(non_empty_columns)

    def _remove_duplicate_rows(
        self,
        df: pl.DataFrame,
    ) -> pl.DataFrame:
        return df.unique(
            maintain_order=True
        )