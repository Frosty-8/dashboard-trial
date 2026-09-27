# app/ingestion/excel_reader.py

from __future__ import annotations

from pathlib import Path

import polars as pl


class ExcelReader:
    """Reads supported SAP report file formats."""

    SUPPORTED_EXTENSIONS = {
        ".csv",
        ".xlsx",
        ".xlsb",
        ".parquet",
    }

    def read(
        self,
        file_path: str | Path,
        sheet_name: str | None = None,
    ) -> pl.DataFrame:
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

        if extension == ".csv":
            return pl.read_csv(path)

        if extension == ".parquet":
            return pl.read_parquet(path)

        if extension == ".xlsx":
            return self._read_xlsx(
                path,
                sheet_name,
            )

        if extension == ".xlsb":
            return self._read_xlsb(
                path,
                sheet_name,
            )

        raise ValueError(
            f"Unable to read file: {path}"
        )

    def _read_xlsx(
        self,
        path: Path,
        sheet_name: str | None,
    ) -> pl.DataFrame:
        import pandas as pd

        kwargs = {}

        if sheet_name:
            kwargs["sheet_name"] = sheet_name

        pandas_df = pd.read_excel(
            path,
            engine="openpyxl",
            **kwargs,
        )

        return pl.from_pandas(
            pandas_df,
            nan_to_null=True,
        )

    def _read_xlsb(
        self,
        path: Path,
        sheet_name: str | None,
    ) -> pl.DataFrame:
        import pandas as pd

        kwargs = {
            "engine": "pyxlsb",
        }

        if sheet_name:
            kwargs["sheet_name"] = sheet_name

        pandas_df = pd.read_excel(
            path,
            **kwargs,
        )

        return pl.from_pandas(
            pandas_df,
            nan_to_null=True,
        )