from __future__ import annotations

import re

import polars as pl


class BusinessMapper:
    """
    Maps report-specific SAP/PPC fields into canonical business fields.

    The goal is to keep downstream analytics independent of the
    original SAP report column naming.
    """

    FIELD_ALIASES: dict[str, str] = {
        # ---------------------------------------------------------
        # Product / Part
        # ---------------------------------------------------------
        "part_no": "part_number",
        "part_number": "part_number",

        "description": "part_description",
        "part_description": "part_description",

        "project": "project",
        "category": "category",
        "hpg": "hpg",
        "series": "series",

        # ---------------------------------------------------------
        # Supplier
        # ---------------------------------------------------------
        "vendor_code": "supplier_code",
        "new_vc": "new_supplier_code",

        "supplier": "supplier_name",
        "supplier_name": "supplier_name",

        # ---------------------------------------------------------
        # Procurement / Demand
        # ---------------------------------------------------------
        "monthly_requirement": "monthly_requirement",
        "annual_sales_forecast": "annual_forecast",

        "exp_bo": "expected_backorder",
        "shortfall_quantity": "shortfall_quantity",

        "open_po": "open_po",
        "open_sto": "open_sto",
        "sto_intransit": "sto_intransit",

        # ---------------------------------------------------------
        # Inventory
        # ---------------------------------------------------------
        "stock_as_on_date": "current_stock",
        "actual_stock": "actual_stock",

        "ncr_stock": "ncr_stock",
        "blr_stock": "blr_stock",

        "total_mard": "total_mard",
        "total_vbbe": "total_vbbe",

        # ---------------------------------------------------------
        # Coverage
        # ---------------------------------------------------------
        "cov": "coverage",

        "ncr_cov_incl_i_t": "ncr_coverage",
        "blr_cov_incl_i_t": "blr_coverage",

        # ---------------------------------------------------------
        # Commercial
        # ---------------------------------------------------------
        "b_price": "unit_price",

        "inventory_value": "inventory_value",
        "fums_value": "fums_value",

        # ---------------------------------------------------------
        # Planning
        # ---------------------------------------------------------
        "priority": "priority",
        "priority_dispatch": "priority",

        "frequency": "frequency",

        # ---------------------------------------------------------
        # Other business fields
        # ---------------------------------------------------------
        "last_3_months_total_orders": "last_3_months_orders",

        "manual_sto_ncr": "manual_sto_ncr",
        "manual_sto_blr": "manual_sto_blr",

        "pan_india_coverage": "pan_india_coverage",
    }

    def map(
        self,
        df: pl.DataFrame,
    ) -> pl.DataFrame:
        """
        Rename known report fields into canonical names.

        Forecast and projection columns are normalized separately
        because their names contain dynamic month information.
        """

        rename_map: dict[str, str] = {}

        for column in df.columns:
            if column in self.FIELD_ALIASES:
                rename_map[column] = self.FIELD_ALIASES[column]

        df = df.rename(rename_map)

        df = self._map_forecast_columns(df)

        return df

    def unmapped_columns(
        self,
        df: pl.DataFrame,
    ) -> list[str]:
        """
        Return columns that are not represented in the canonical
        business model.
        """

        unmapped: list[str] = []

        for column in df.columns:
            if column in self.FIELD_ALIASES:
                continue

            if self._is_forecast_column(column):
                continue

            if self._is_projection_column(column):
                continue

            unmapped.append(column)

        return unmapped

    @staticmethod
    def _is_forecast_column(
        column: str,
    ) -> bool:
        return bool(
            re.match(
                r"^(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)_forecast$",
                column,
            )
        )

    @staticmethod
    def _is_projection_column(
        column: str,
    ) -> bool:
        return bool(
            re.match(
                r"^(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)_"
                r"(end_stock|end_coverage)$",
                column,
            )
        )

    @staticmethod
    def _map_forecast_columns(
        df: pl.DataFrame,
    ) -> pl.DataFrame:
        """
        Normalize monthly forecast/projection columns into a
        consistent naming convention.

        Example:

            sep_forecast
            sep_end_stock
            sep_end_coverage

        remain as explicit monthly fields because they are useful
        for dashboard and forecasting analytics.
        """

        rename_map: dict[str, str] = {}

        for column in df.columns:
            if column.endswith("_forecast"):
                rename_map[column] = column

            elif column.endswith("_end_stock"):
                rename_map[column] = column

            elif column.endswith("_end_coverage"):
                rename_map[column] = column

        if rename_map:
            df = df.rename(rename_map)

        return df