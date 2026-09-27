from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
import polars as pl

from .integration import IntegrationPlan, JoinPlan
from .workbook_profiler import WorkbookProfiler


@dataclass
class IntegrationResult:
    dataframe: pl.DataFrame
    primary_sheet: str | None
    integrated_sheets: list[str]
    applied_joins: list[dict[str, Any]]
    warnings: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "rows": self.dataframe.height,
            "columns": self.dataframe.width,
            "primary_sheet": self.primary_sheet,
            "integrated_sheets": self.integrated_sheets,
            "applied_joins": self.applied_joins,
            "warnings": self.warnings,
        }


class WorkbookIntegrator:
    """
    Loads sheets selected by the IntegrationPlan and builds
    a canonical Polars dataset.

    The integrator preserves the original source sheet through
    the `_source_sheet` column.
    """

    def __init__(self) -> None:
        self.profiler = WorkbookProfiler()

    def integrate(
        self,
        file_path: str | Path,
        plan: IntegrationPlan,
    ) -> IntegrationResult:

        file_path = Path(file_path)

        warnings: list[str] = []
        integrated_sheets: list[str] = []
        applied_joins: list[dict[str, Any]] = []

        if not plan.primary_sheet:
            raise ValueError(
                "Integration plan does not contain a primary sheet."
            )

        excel = self.profiler._open_excel(file_path)

        try:
            datasets: dict[str, pl.DataFrame] = {}

            selected_sheets = [
                item
                for item in plan.sheets
                if item.selected
            ]

            for sheet in selected_sheets:
                try:
                    dataframe = self._read_sheet(
                        excel=excel,
                        sheet_name=sheet.sheet_name,
                    )

                    if dataframe.is_empty():
                        warnings.append(
                            f"Sheet '{sheet.sheet_name}' is empty."
                        )
                        continue

                    datasets[sheet.sheet_name] = dataframe
                    integrated_sheets.append(
                        sheet.sheet_name
                    )

                except Exception as exc:
                    warnings.append(
                        f"Could not read '{sheet.sheet_name}': {exc}"
                    )

            if plan.primary_sheet not in datasets:
                raise ValueError(
                    f"Primary sheet '{plan.primary_sheet}' "
                    "could not be loaded."
                )

            result = datasets[plan.primary_sheet].clone()

            for join in plan.joins:

                result, applied = self._apply_join(
                    result=result,
                    datasets=datasets,
                    join=join,
                    primary_sheet=plan.primary_sheet,
                )

                if applied:
                    applied_joins.append(applied)

            result = self._add_lineage(
                result,
                plan.primary_sheet,
            )

            return IntegrationResult(
                dataframe=result,
                primary_sheet=plan.primary_sheet,
                integrated_sheets=integrated_sheets,
                applied_joins=applied_joins,
                warnings=warnings,
            )

        finally:
            excel.close()

    def _read_sheet(
        self,
        excel: pd.ExcelFile,
        sheet_name: str,
    ) -> pl.DataFrame:

        raw = pd.read_excel(
            excel,
            sheet_name=sheet_name,
            header=None,
        )

        if raw.empty:
            return pl.DataFrame()

        header_row = self._detect_header_row(
            raw,
        )

        if header_row is None:
            header_row = 0

        headers = raw.iloc[header_row].tolist()

        columns = self._make_unique_columns(
            headers,
        )

        data = raw.iloc[
            header_row + 1:
        ].copy()

        data.columns = columns

        # Remove completely empty rows.
        data = data.dropna(
            how="all",
        )

        if data.empty:
            return pl.DataFrame()

        # Convert mixed pandas object columns safely.
        for column in data.columns:
            if data[column].dtype == "object":
                data[column] = data[column].map(
                    lambda value: (
                        str(value)
                        if pd.notna(value)
                        else None
                    )
                )

        return pl.from_pandas(
            data,
            include_index=False,
        )

    def _apply_join(
        self,
        result: pl.DataFrame,
        datasets: dict[str, pl.DataFrame],
        join: JoinPlan,
        primary_sheet: str,
    ) -> tuple[pl.DataFrame, dict[str, Any] | None]:

        if (
            join.left_sheet != primary_sheet
            and join.right_sheet != primary_sheet
        ):
            return result, None

        if join.left_sheet == primary_sheet:
            other_sheet = join.right_sheet
            left_column = join.left_column
            right_column = join.right_column

        else:
            other_sheet = join.left_sheet
            left_column = join.right_column
            right_column = join.left_column

        if other_sheet not in datasets:
            return result, None

        other = datasets[other_sheet]

        if left_column not in result.columns:
            return result, None

        if right_column not in other.columns:
            return result, None

        other = self._prepare_join_dataset(
            other,
            right_column,
            other_sheet,
        )

        if other.is_empty():
            return result, None

        result = result.join(
            other,
            left_on=left_column,
            right_on=right_column,
            how=join.join_type,
            suffix=f"_{self._safe_name(other_sheet)}",
        )

        return result, {
            "left_sheet": primary_sheet,
            "left_column": left_column,
            "right_sheet": other_sheet,
            "right_column": right_column,
            "key_type": join.key_type,
            "confidence": join.confidence,
            "join_type": join.join_type,
        }

    def _prepare_join_dataset(
        self,
        dataframe: pl.DataFrame,
        key_column: str,
        sheet_name: str,
    ) -> pl.DataFrame:

        dataframe = dataframe.clone()

        # Keep only useful columns that don't already exist
        # in the primary dataset at join time.
        dataframe = dataframe.unique(
            subset=[key_column],
            keep="first",
        )

        renamed: dict[str, str] = {}

        for column in dataframe.columns:
            if column == key_column:
                continue

            renamed[column] = (
                f"{self._safe_name(sheet_name)}__{column}"
            )

        return dataframe.rename(
            renamed,
        )

    @staticmethod
    def _add_lineage(
        dataframe: pl.DataFrame,
        primary_sheet: str,
    ) -> pl.DataFrame:

        return dataframe.with_columns(
            pl.lit(primary_sheet).alias(
                "_source_sheet"
            )
        )

    @staticmethod
    def _detect_header_row(
        dataframe: pd.DataFrame,
    ) -> int | None:

        best_row: int | None = None
        best_score = 0.0

        for index in range(
            min(20, len(dataframe))
        ):

            row = dataframe.iloc[index]

            values = [
                str(value).strip()
                for value in row.tolist()
                if pd.notna(value)
            ]

            if not values:
                continue

            text_values = [
                value
                for value in values
                if not value.replace(
                    ".",
                    "",
                    1,
                ).isdigit()
            ]

            score = (
                len(text_values) * 2
                + len(values)
            )

            if score > best_score:
                best_score = score
                best_row = index

        return best_row

    @staticmethod
    def _make_unique_columns(
        columns: list[Any],
    ) -> list[str]:

        seen: dict[str, int] = {}
        result: list[str] = []

        for column in columns:

            name = str(column).strip()

            if not name or name.lower() == "nan":
                name = "unnamed"

            count = seen.get(name, 0)

            if count == 0:
                result.append(name)
            else:
                result.append(
                    f"{name}_{count}"
                )

            seen[name] = count + 1

        return result

    @staticmethod
    def _safe_name(value: str) -> str:

        return (
            value.strip()
            .lower()
            .replace(" ", "_")
            .replace("-", "_")
            .replace(">", "_")
            .replace("/", "_")
        )