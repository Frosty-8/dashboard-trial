# app/ingestion/excel_reader.py

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import polars as pl


class ExcelReader:
    """
    Robust reader for SAP/PPC datasets.

    Responsibilities
    ----------------
    1. Read supported file formats.
    2. Discover Excel worksheets.
    3. Select the most relevant worksheet.
    4. Detect the actual header row.
    5. Flatten multi-row headers.
    6. Normalize problematic Excel values.
    7. Convert the result into Polars.
    """

    SUPPORTED_EXTENSIONS = {
        ".csv",
        ".xlsx",
        ".xlsb",
        ".parquet",
    }

    # ------------------------------------------------------------------
    # Business vocabulary used to identify relevant SAP/PPC sheets
    # ------------------------------------------------------------------

    BUSINESS_TERMS = {
        "part",
        "part no",
        "part number",
        "material",
        "material code",
        "description",
        "supplier",
        "vendor",
        "vendor code",
        "stock",
        "inventory",
        "requirement",
        "monthly requirement",
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
        "hpg",
        "series",
    }

    PREFERRED_SHEET_NAMES = {
        "ppc",
        "ppc report",
        "planning",
        "order details",
        "order_detail",
        "order details report",
    }

    MONTHS = {
        "jan",
        "january",
        "feb",
        "february",
        "mar",
        "march",
        "apr",
        "april",
        "may",
        "jun",
        "june",
        "jul",
        "july",
        "aug",
        "august",
        "sep",
        "sept",
        "september",
        "oct",
        "october",
        "nov",
        "november",
        "dec",
        "december",
    }

    def read(
        self,
        file_path: str | Path,
        sheet_name: str | None = None,
    ) -> pl.DataFrame:
        """
        Read a supported dataset.

        Parameters
        ----------
        file_path:
            Path to CSV/XLSX/XLSB/Parquet.

        sheet_name:
            Optional worksheet name.

            If omitted for Excel files, the reader automatically
            identifies the most relevant worksheet.
        """

        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(
                f"File not found: {path}"
            )

        extension = path.suffix.lower()

        if extension not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Unsupported file format: {extension}. "
                f"Supported formats: "
                f"{', '.join(sorted(self.SUPPORTED_EXTENSIONS))}"
            )

        # --------------------------------------------------------------
        # CSV
        # --------------------------------------------------------------

        if extension == ".csv":
            return pl.read_csv(path)

        # --------------------------------------------------------------
        # Parquet
        # --------------------------------------------------------------

        if extension == ".parquet":
            return pl.read_parquet(path)

        # --------------------------------------------------------------
        # XLSX
        # --------------------------------------------------------------

        if extension == ".xlsx":
            return self._read_excel(
                path=path,
                sheet_name=sheet_name,
                engine="openpyxl",
            )

        # --------------------------------------------------------------
        # XLSB
        # --------------------------------------------------------------

        if extension == ".xlsb":
            return self._read_excel(
                path=path,
                sheet_name=sheet_name,
                engine="pyxlsb",
            )

        raise ValueError(
            f"Unable to read file: {path}"
        )

    # ==================================================================
    # EXCEL READING
    # ==================================================================

    def _read_excel(
        self,
        path: Path,
        sheet_name: str | None,
        engine: str,
    ) -> pl.DataFrame:
        """
        Read an Excel workbook without assuming the first row is a header.
        """

        import pandas as pd

        try:
            excel = pd.ExcelFile(
                path,
                engine=engine,
            )
        except Exception as exc:
            raise ValueError(
                f"Unable to open Excel workbook '{path.name}': "
                f"{exc}"
            ) from exc

        available_sheets = [
            str(sheet).strip()
            for sheet in excel.sheet_names
        ]

        if not available_sheets:
            raise ValueError(
                f"Workbook '{path.name}' contains no worksheets."
            )

        # --------------------------------------------------------------
        # Select worksheet
        # --------------------------------------------------------------

        selected_sheet = self._select_sheet(
            excel=excel,
            available_sheets=available_sheets,
            requested_sheet=sheet_name,
        )

        # --------------------------------------------------------------
        # Read worksheet WITHOUT headers.
        #
        # This is the important change.
        # --------------------------------------------------------------

        raw = pd.read_excel(
            excel,
            sheet_name=selected_sheet,
            header=None,
        )

        if raw.empty:
            raise ValueError(
                f"Worksheet '{selected_sheet}' contains no data."
            )

        # --------------------------------------------------------------
        # Remove completely empty rows/columns.
        # --------------------------------------------------------------

        raw = self._remove_empty_axes(raw)

        if raw.empty:
            raise ValueError(
                f"Worksheet '{selected_sheet}' contains no usable data."
            )

        # --------------------------------------------------------------
        # Detect header row.
        # --------------------------------------------------------------

        header_row = self._detect_header_row(
            raw
        )

        # --------------------------------------------------------------
        # Build flattened headers.
        # --------------------------------------------------------------

        headers = self._build_headers(
            raw=raw,
            header_row=header_row,
        )

        # --------------------------------------------------------------
        # Extract actual data rows.
        # --------------------------------------------------------------

        data = raw.iloc[
            header_row + 1:
        ].copy()

        data.columns = headers

        # --------------------------------------------------------------
        # Remove rows that are completely empty.
        # --------------------------------------------------------------

        data = data.dropna(
            axis=0,
            how="all",
        )

        if data.empty:
            raise ValueError(
                f"Worksheet '{selected_sheet}' has headers "
                f"but no data rows."
            )

        # --------------------------------------------------------------
        # Remove columns with no usable values.
        # --------------------------------------------------------------

        data = data.dropna(
            axis=1,
            how="all",
        )

        # --------------------------------------------------------------
        # Clean mixed pandas object columns.
        # --------------------------------------------------------------

        data = self._normalize_pandas_types(
            data
        )

        # --------------------------------------------------------------
        # Convert to Polars.
        # --------------------------------------------------------------

        try:
            return pl.from_pandas(
                data,
                nan_to_null=True,
            )

        except Exception as exc:
            raise ValueError(
                f"Unable to convert worksheet "
                f"'{selected_sheet}' to Polars. "
                f"Detected header row: {header_row}. "
                f"Columns: {list(data.columns)}. "
                f"Original error: {exc}"
            ) from exc

    # ==================================================================
    # SHEET SELECTION
    # ==================================================================

    def _select_sheet(
        self,
        excel: Any,
        available_sheets: list[str],
        requested_sheet: str | None,
    ) -> str:
        """
        Select the worksheet to process.

        Explicit worksheet name wins.

        Otherwise:
            1. Prefer known PPC-like names.
            2. Score worksheets by business vocabulary.
            3. Select the highest scoring worksheet.
        """

        # --------------------------------------------------------------
        # Explicit sheet requested
        # --------------------------------------------------------------

        if requested_sheet:
            requested_normalized = (
                requested_sheet.strip().lower()
            )

            for sheet in available_sheets:
                if sheet.lower() == requested_normalized:
                    return sheet

            raise ValueError(
                f"Worksheet '{requested_sheet}' was not found. "
                f"Available worksheets: "
                f"{', '.join(available_sheets)}"
            )

        # --------------------------------------------------------------
        # Preferred names
        # --------------------------------------------------------------

        for sheet in available_sheets:
            normalized = self._normalize_text(sheet)

            if normalized in {
                self._normalize_text(name)
                for name in self.PREFERRED_SHEET_NAMES
            }:
                return sheet

        # --------------------------------------------------------------
        # Automatic scoring
        # --------------------------------------------------------------

        best_sheet = None
        best_score = float("-inf")

        for sheet in available_sheets:
            try:
                sample = pd_read_excel_preview(
                    excel=excel,
                    sheet_name=sheet,
                    rows=30,
                )

                score = self._score_sheet(
                    sheet_name=sheet,
                    sample=sample,
                )

                if score > best_score:
                    best_score = score
                    best_sheet = sheet

            except Exception:
                continue

        if best_sheet is None:
            return available_sheets[0]

        return best_sheet

    def _score_sheet(
        self,
        sheet_name: str,
        sample: Any,
    ) -> float:
        """
        Score a worksheet based on how closely it resembles
        a business dataset.
        """

        score = 0.0

        normalized_sheet = self._normalize_text(
            sheet_name
        )

        # Strong signal from sheet name.
        if normalized_sheet in {
            self._normalize_text(name)
            for name in self.PREFERRED_SHEET_NAMES
        }:
            score += 100

        if "ppc" in normalized_sheet:
            score += 80

        if "planning" in normalized_sheet:
            score += 40

        if "order" in normalized_sheet:
            score += 30

        # --------------------------------------------------------------
        # Inspect cell contents.
        # --------------------------------------------------------------

        for row in sample.itertuples(
            index=False,
            name=None,
        ):
            for value in row:
                if value is None:
                    continue

                text = str(value).strip().lower()

                if not text:
                    continue

                normalized = self._normalize_text(
                    text
                )

                for term in self.BUSINESS_TERMS:
                    if normalized == self._normalize_text(
                        term
                    ):
                        score += 5

                    elif (
                        self._normalize_text(term)
                        in normalized
                    ):
                        score += 1

        return score

    # ==================================================================
    # HEADER DETECTION
    # ==================================================================

    def _detect_header_row(
        self,
        raw: Any,
        max_rows: int = 30,
    ) -> int:
        """
        Detect the most likely header row.

        The algorithm looks for rows containing:
            - many non-empty cells
            - business vocabulary
            - text-like column names
            - fewer purely numeric values
        """

        candidates = min(
            max_rows,
            len(raw),
        )

        best_row = 0
        best_score = float("-inf")

        for row_index in range(candidates):
            row = raw.iloc[row_index]

            values = [
                value
                for value in row.tolist()
                if not self._is_empty(value)
            ]

            if not values:
                continue

            non_empty = len(values)

            text_values = 0
            numeric_values = 0
            business_matches = 0

            for value in values:
                if self._is_numeric(value):
                    numeric_values += 1
                    continue

                text_values += 1

                normalized = self._normalize_text(
                    str(value)
                )

                for term in self.BUSINESS_TERMS:
                    term_normalized = (
                        self._normalize_text(term)
                    )

                    if (
                        normalized == term_normalized
                        or term_normalized
                        in normalized
                    ):
                        business_matches += 1
                        break

            # ----------------------------------------------------------
            # Header scoring
            # ----------------------------------------------------------

            score = 0.0

            # Wide populated rows are more likely to be headers.
            score += min(
                non_empty * 1.5,
                40,
            )

            # Text-heavy rows are preferred.
            score += text_values * 0.5

            # Business vocabulary is a strong signal.
            score += business_matches * 8

            # Header rows normally contain fewer pure numbers.
            score -= numeric_values * 1.5

            # Penalize title-like rows.
            if non_empty <= 3:
                score -= 15

            if score > best_score:
                best_score = score
                best_row = row_index

        return best_row

    # ==================================================================
    # HEADER CONSTRUCTION
    # ==================================================================

    def _build_headers(
        self,
        raw: Any,
        header_row: int,
    ) -> list[str]:
        """
        Build clean column names.

        Supports structures such as:

            Row 0:       Jan       Jan       Feb       Feb
            Row 1:       Forecast  Stock     Forecast  Stock

        Producing:

            jan_forecast
            jan_stock
            feb_forecast
            feb_stock
        """

        if header_row == 0:
            header_rows = [0]
        else:
            # Use up to three rows immediately preceding
            # the detected header row.
            start = max(
                0,
                header_row - 2,
            )

            header_rows = list(
                range(
                    start,
                    header_row + 1,
                )
            )

        matrix: list[list[str | None]] = []

        for row_index in header_rows:
            row = raw.iloc[row_index].tolist()

            cleaned_row = []

            for value in row:
                if self._is_empty(value):
                    cleaned_row.append(None)
                else:
                    cleaned_row.append(
                        str(value).strip()
                    )

            matrix.append(cleaned_row)

        # --------------------------------------------------------------
        # Forward-fill header groups horizontally.
        #
        # This is useful for merged Excel cells.
        # --------------------------------------------------------------

        for row in matrix:
            previous = None

            for index, value in enumerate(row):
                if value:
                    previous = value
                elif previous:
                    row[index] = previous

        # --------------------------------------------------------------
        # Build one name per column.
        # --------------------------------------------------------------

        column_count = raw.shape[1]
        headers: list[str] = []

        for column_index in range(column_count):
            parts: list[str] = []

            for row in matrix:
                if column_index >= len(row):
                    continue

                value = row[column_index]

                if not value:
                    continue

                normalized = self._normalize_text(
                    value
                )

                if not normalized:
                    continue

                if normalized not in parts:
                    parts.append(normalized)

            # ----------------------------------------------------------
            # Fallback
            # ----------------------------------------------------------

            if not parts:
                parts = [
                    f"column_{column_index + 1}"
                ]

            header = "_".join(parts)

            headers.append(header)

        return self._make_unique_headers(
            headers
        )

    # ==================================================================
    # PANDAS TYPE NORMALIZATION
    # ==================================================================

    def _normalize_pandas_types(
        self,
        dataframe: Any,
    ) -> Any:
        """
        Normalize mixed Excel columns before converting to Polars.

        Object columns can contain combinations such as:

            100
            "100"
            "ABC"

        Arrow/Polars may reject such mixed values, so we make
        the intended type explicit.
        """

        import pandas as pd

        for column in dataframe.columns:
            series = dataframe[column]

            if not (
                pd.api.types.is_object_dtype(series)
                or pd.api.types.is_string_dtype(series)
                or pd.api.types.is_categorical_dtype(series)
            ):
                continue

            # ----------------------------------------------------------
            # Convert obvious error/null markers.
            # ----------------------------------------------------------

            series = series.map(
                lambda value: (
                    None
                    if self._is_empty(value)
                    else value
                )
            )

            non_null = series.dropna()

            if non_null.empty:
                dataframe[column] = series
                continue

            # ----------------------------------------------------------
            # Try numeric conversion.
            # ----------------------------------------------------------

            numeric = pd.to_numeric(
                non_null,
                errors="coerce",
            )

            numeric_ratio = (
                numeric.notna().mean()
            )

            if numeric_ratio >= 0.90:
                dataframe[column] = pd.to_numeric(
                    series,
                    errors="coerce",
                )

                continue

            # ----------------------------------------------------------
            # Otherwise keep as string.
            # ----------------------------------------------------------

            dataframe[column] = series.map(
                lambda value: (
                    None
                    if pd.isna(value)
                    else str(value).strip()
                )
            )

        return dataframe

    # ==================================================================
    # DATAFRAME CLEANUP
    # ==================================================================

    @staticmethod
    def _remove_empty_axes(
        dataframe: Any,
    ) -> Any:
        dataframe = dataframe.dropna(
            axis=0,
            how="all",
        )

        dataframe = dataframe.dropna(
            axis=1,
            how="all",
        )

        return dataframe

    # ==================================================================
    # HEADER UTILITIES
    # ==================================================================

    @staticmethod
    def _make_unique_headers(
        headers: list[str],
    ) -> list[str]:
        result: list[str] = []
        counts: dict[str, int] = {}

        for header in headers:
            base = header or "column"

            count = counts.get(
                base,
                0,
            )

            if count == 0:
                result.append(base)
            else:
                result.append(
                    f"{base}_{count + 1}"
                )

            counts[base] = count + 1

        return result

    @staticmethod
    def _normalize_text(
        value: str,
    ) -> str:
        text = str(value).strip().lower()

        text = (
            text
            .replace("%", " percent ")
            .replace("&", " and ")
        )

        text = re.sub(
            r"[^a-z0-9]+",
            "_",
            text,
        )

        text = re.sub(
            r"_+",
            "_",
            text,
        )

        return text.strip("_")

    @staticmethod
    def _is_empty(
        value: Any,
    ) -> bool:
        if value is None:
            return True

        try:
            import pandas as pd

            if pd.isna(value):
                return True

        except (TypeError, ValueError):
            pass

        text = str(value).strip()

        return text in {
            "",
            "nan",
            "none",
            "null",
            "nat",
        }

    @staticmethod
    def _is_numeric(
        value: Any,
    ) -> bool:
        if value is None:
            return False

        try:
            float(value)
            return True
        except (
            TypeError,
            ValueError,
        ):
            return False


def pd_read_excel_preview(
    excel: Any,
    sheet_name: str,
    rows: int = 30,
) -> Any:
    """
    Small helper used during automatic sheet discovery.

    Kept outside ExcelReader to make the sheet-scoring method
    easy to test independently.
    """

    import pandas as pd

    return pd.read_excel(
        excel,
        sheet_name=sheet_name,
        header=None,
        nrows=rows,
    )