# app/ingestion/profiler.py

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import polars as pl


@dataclass
class ColumnProfile:
    name: str
    dtype: str
    null_count: int
    null_percentage: float
    unique_count: int
    sample_values: list[Any] = field(default_factory=list)


@dataclass
class DataProfile:
    file_name: str
    rows: int
    columns: int
    duplicate_rows: int
    total_nulls: int
    column_profiles: list[ColumnProfile]
    numeric_columns: list[str]
    categorical_columns: list[str]
    date_columns: list[str]
    potential_errors: list[dict[str, Any]]


class DataProfiler:
    """Profiles incoming SAP/PPC datasets before transformation."""

    ERROR_MARKERS = {
        "#DIV/0!",
        "#VALUE!",
        "#REF!",
        "#N/A",
        "#NAME?",
        "#NUM!",
        "#NULL!",
    }

    def profile(
        self,
        df: pl.DataFrame,
        file_path: str | Path | None = None,
    ) -> DataProfile:
        column_profiles: list[ColumnProfile] = []
        numeric_columns: list[str] = []
        categorical_columns: list[str] = []
        date_columns: list[str] = []
        potential_errors: list[dict[str, Any]] = []

        for column in df.columns:
            series = df.get_column(column)

            null_count = series.null_count()
            row_count = df.height

            null_percentage = (
                (null_count / row_count) * 100
                if row_count
                else 0.0
            )

            unique_count = series.n_unique()

            sample_values = (
                series.drop_nulls()
                .head(5)
                .to_list()
            )

            dtype_name = str(series.dtype)

            column_profiles.append(
                ColumnProfile(
                    name=column,
                    dtype=dtype_name,
                    null_count=null_count,
                    null_percentage=round(
                        null_percentage,
                        2,
                    ),
                    unique_count=unique_count,
                    sample_values=sample_values,
                )
            )

            if self._is_numeric(series):
                numeric_columns.append(column)

            elif self._is_date(series):
                date_columns.append(column)

            else:
                categorical_columns.append(column)

            errors = self._find_error_markers(
                series,
                column,
            )

            potential_errors.extend(errors)

        duplicate_rows = (
            df.height - df.unique().height
        )

        total_nulls = sum(
            profile.null_count
            for profile in column_profiles
        )

        return DataProfile(
            file_name=(
                Path(file_path).name
                if file_path
                else "in-memory dataset"
            ),
            rows=df.height,
            columns=df.width,
            duplicate_rows=duplicate_rows,
            total_nulls=total_nulls,
            column_profiles=column_profiles,
            numeric_columns=numeric_columns,
            categorical_columns=categorical_columns,
            date_columns=date_columns,
            potential_errors=potential_errors,
        )

    def _is_numeric(
        self,
        series: pl.Series,
    ) -> bool:
        return series.dtype.is_numeric()

    def _is_date(
        self,
        series: pl.Series,
    ) -> bool:
        return series.dtype in {
            pl.Date,
            pl.Datetime,
            pl.Time,
        }

    def _find_error_markers(
        self,
        series: pl.Series,
        column: str,
    ) -> list[dict[str, Any]]:
        if series.dtype not in {
            pl.String,
            pl.Categorical,
            pl.Enum,
        }:
            return []

        errors: list[dict[str, Any]] = []

        values = series.drop_nulls().to_list()

        for marker in self.ERROR_MARKERS:
            count = values.count(marker)

            if count:
                errors.append(
                    {
                        "column": column,
                        "type": "spreadsheet_error",
                        "value": marker,
                        "count": count,
                    }
                )

        return errors

    def summary(
        self,
        profile: DataProfile,
    ) -> dict[str, Any]:
        return {
            "file_name": profile.file_name,
            "rows": profile.rows,
            "columns": profile.columns,
            "duplicate_rows": profile.duplicate_rows,
            "total_nulls": profile.total_nulls,
            "numeric_columns": len(
                profile.numeric_columns
            ),
            "categorical_columns": len(
                profile.categorical_columns
            ),
            "date_columns": len(
                profile.date_columns
            ),
            "potential_errors": len(
                profile.potential_errors
            ),
        }