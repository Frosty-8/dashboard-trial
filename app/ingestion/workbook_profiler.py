# app/ingestion/workbook_profiler.py

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd


@dataclass
class SheetProfile:
    name: str
    rows: int
    columns: int
    non_empty_cells: int
    header_row: int | None
    likely_data_sheet: bool
    score: float
    sample_columns: list[str]
    preview: list[dict[str, Any]]


@dataclass
class WorkbookProfile:
    file_name: str
    file_type: str
    sheet_count: int
    sheets: list[SheetProfile]

    @property
    def likely_sheets(self) -> list[SheetProfile]:
        return sorted(
            self.sheets,
            key=lambda sheet: sheet.score,
            reverse=True,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_name": self.file_name,
            "file_type": self.file_type,
            "sheet_count": self.sheet_count,
            "sheets": [
                asdict(sheet)
                for sheet in self.sheets
            ],
        }


class WorkbookProfiler:
    """
    Profiles an entire SAP Excel/XLSB workbook.

    This class does NOT transform the business data.

    Its responsibility is to understand the workbook first:

        Workbook
            ↓
        Sheets
            ↓
        Sheet dimensions
            ↓
        Header candidates
            ↓
        Business relevance
            ↓
        Sheet profile
    """

    BUSINESS_TERMS = {
        "part",
        "part no",
        "part number",
        "material",
        "material code",
        "description",
        "supplier",
        "supplier name",
        "vendor",
        "vendor code",
        "stock",
        "inventory",
        "requirement",
        "forecast",
        "shortfall",
        "coverage",
        "open po",
        "open sto",
        "sto",
        "priority",
        "price",
        "category",
        "project",
        "planning",
        "order",
        "schedule",
        "purchase",
        "procurement",
    }

    PREFERRED_NAMES = {
        "ppc",
        "ppc report",
        "planning",
        "order details",
        "supplier bifurcation",
        "inventory reduction plan",
        "pr>po",
    }

    def profile(
        self,
        file_path: str | Path,
        preview_rows: int = 5,
        inspect_rows: int = 30,
    ) -> WorkbookProfile:

        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(
                f"Workbook not found: {path}"
            )

        extension = path.suffix.lower()

        if extension not in {
            ".xlsx",
            ".xlsb",
        }:
            raise ValueError(
                "WorkbookProfiler supports only "
                "XLSX and XLSB files."
            )

        engine = (
            "pyxlsb"
            if extension == ".xlsb"
            else "openpyxl"
        )

        excel = pd.ExcelFile(
            path,
            engine=engine,
        )

        sheet_profiles: list[SheetProfile] = []

        for sheet_name in excel.sheet_names:

            profile = self._profile_sheet(
                excel=excel,
                sheet_name=sheet_name,
                preview_rows=preview_rows,
                inspect_rows=inspect_rows,
            )

            sheet_profiles.append(profile)

        return WorkbookProfile(
            file_name=path.name,
            file_type=extension.replace(".", "").upper(),
            sheet_count=len(sheet_profiles),
            sheets=sheet_profiles,
        )

    # ==============================================================
    # SHEET PROFILING
    # ==============================================================

    def _profile_sheet(
        self,
        excel: pd.ExcelFile,
        sheet_name: str,
        preview_rows: int,
        inspect_rows: int,
    ) -> SheetProfile:

        raw = pd.read_excel(
            excel,
            sheet_name=sheet_name,
            header=None,
            nrows=inspect_rows,
        )

        if raw.empty:
            return SheetProfile(
                name=sheet_name,
                rows=0,
                columns=0,
                non_empty_cells=0,
                header_row=None,
                likely_data_sheet=False,
                score=0,
                sample_columns=[],
                preview=[],
            )

        non_empty_cells = int(
            raw.notna().sum().sum()
        )

        header_row = self._detect_header_row(
            raw
        )

        score = self._score_sheet(
            sheet_name=sheet_name,
            dataframe=raw,
            header_row=header_row,
        )

        sample_columns = self._extract_columns(
            raw=raw,
            header_row=header_row,
        )

        preview = self._preview(
            raw=raw,
            header_row=header_row,
            rows=preview_rows,
        )

        return SheetProfile(
            name=sheet_name,
            rows=len(raw),
            columns=len(raw.columns),
            non_empty_cells=non_empty_cells,
            header_row=header_row,
            likely_data_sheet=score >= 20,
            score=round(score, 2),
            sample_columns=sample_columns,
            preview=preview,
        )

    # ==============================================================
    # HEADER DETECTION
    # ==============================================================

    def _detect_header_row(
        self,
        dataframe: pd.DataFrame,
        max_rows: int = 20,
    ) -> int | None:

        best_row: int | None = None
        best_score = float("-inf")

        limit = min(
            max_rows,
            len(dataframe),
        )

        for row_index in range(limit):

            row = dataframe.iloc[row_index]

            values = [
                value
                for value in row.tolist()
                if not self._empty(value)
            ]

            if not values:
                continue

            text_count = 0
            numeric_count = 0
            business_matches = 0

            for value in values:

                text = str(value).strip()

                try:
                    float(text)
                    numeric_count += 1
                    continue
                except ValueError:
                    pass

                text_count += 1

                normalized = text.lower()

                for term in self.BUSINESS_TERMS:

                    if term in normalized:
                        business_matches += 1
                        break

            score = (
                len(values) * 1.5
                + text_count
                + business_matches * 8
                - numeric_count * 1.5
            )

            if len(values) <= 2:
                score -= 10

            if score > best_score:
                best_score = score
                best_row = row_index

        return best_row

    # ==============================================================
    # SHEET SCORING
    # ==============================================================

    def _score_sheet(
        self,
        sheet_name: str,
        dataframe: pd.DataFrame,
        header_row: int | None,
    ) -> float:

        score = 0.0

        normalized_sheet = (
            sheet_name.strip().lower()
        )

        # ----------------------------------------------------------
        # Sheet name signals
        # ----------------------------------------------------------

        if normalized_sheet in self.PREFERRED_NAMES:
            score += 50

        if "ppc" in normalized_sheet:
            score += 40

        if "planning" in normalized_sheet:
            score += 30

        if "order" in normalized_sheet:
            score += 20

        if "supplier" in normalized_sheet:
            score += 15

        if "inventory" in normalized_sheet:
            score += 15

        if "purchase" in normalized_sheet:
            score += 15

        # ----------------------------------------------------------
        # Header signals
        # ----------------------------------------------------------

        if header_row is not None:

            row = dataframe.iloc[header_row]

            for value in row.tolist():

                if self._empty(value):
                    continue

                normalized = (
                    str(value)
                    .strip()
                    .lower()
                )

                for term in self.BUSINESS_TERMS:

                    if term in normalized:
                        score += 5
                        break

        return score

    # ==============================================================
    # COLUMN EXTRACTION
    # ==============================================================

    def _extract_columns(
        self,
        raw: pd.DataFrame,
        header_row: int | None,
    ) -> list[str]:

        if header_row is None:
            return []

        row = raw.iloc[header_row]

        columns = []

        for index, value in enumerate(
            row.tolist()
        ):

            if self._empty(value):
                columns.append(
                    f"column_{index + 1}"
                )
            else:
                columns.append(
                    str(value).strip()
                )

        return columns

    # ==============================================================
    # PREVIEW
    # ==============================================================

    def _preview(
        self,
        raw: pd.DataFrame,
        header_row: int | None,
        rows: int,
    ) -> list[dict[str, Any]]:
        if raw.empty:
            return []
    
        data = raw.copy()
    
        # If a header row was detected, use it to create readable
        # column names for the preview.
        if header_row is not None and header_row < len(data):
            headers = data.iloc[header_row].tolist()
    
            columns = self._make_unique_columns(
                pd.Index(headers)
            )
    
            data = data.iloc[header_row + 1:].copy()
            data.columns = columns
    
        else:
            data.columns = self._make_unique_columns(
                data.columns
            )
    
        data = data.head(rows)
    
        # Convert NaN / NaT to JSON-safe None.
        data = data.astype(object).where(
            pd.notna(data),
            None,
        )
    
        return data.to_dict(
            orient="records"
        )

    # ==============================================================
    # HELPERS
    # ==============================================================

    @staticmethod
    def _empty(
        value: Any,
    ) -> bool:

        if value is None:
            return True

        try:
            if pd.isna(value):
                return True
        except (
            TypeError,
            ValueError,
        ):
            pass

        return str(value).strip() == ""

    @staticmethod
    def _make_unique_columns(
        columns: pd.Index,
    ) -> list[str]:
        seen: dict[str, int] = {}
        result: list[str] = []
    
        for column in columns:
            name = str(column).strip()
    
            if not name:
                name = "unnamed"
    
            count = seen.get(name, 0)
    
            if count == 0:
                result.append(name)
            else:
                result.append(f"{name}_{count}")
    
            seen[name] = count + 1
    
        return result

    def _open_excel(
        self,
        file_path: str | Path,
    ) -> pd.ExcelFile:
    
        file_path = Path(file_path)
    
        if file_path.suffix.lower() == ".xlsb":
            return pd.ExcelFile(
                file_path,
                engine="pyxlsb",
            )
    
        return pd.ExcelFile(
            file_path,
            engine="openpyxl",
        )