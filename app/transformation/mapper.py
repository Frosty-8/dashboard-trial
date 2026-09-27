from __future__ import annotations

import re

import polars as pl


class BusinessMapper:
    """
    Maps report-specific SAP/PPC fields into canonical business fields.

    The mapper supports both:

    1. Single-source datasets
       Example:
           monthly_requirement
           stock_as_on_date
           shortfall_quantity

    2. Integrated multi-sheet datasets
       Example:
           workbook_monthly_requirement
           workbook_actual_stock
           workbook_inventory_value
           schedule_jan26_cov

    Downstream analytics should only depend on the canonical fields.
    """

    # ------------------------------------------------------------------
    # Exact field aliases
    # ------------------------------------------------------------------

    FIELD_ALIASES: dict[str, str] = {
        # --------------------------------------------------------------
        # Product / Part
        # --------------------------------------------------------------
        "part_no": "part_number",
        "part_number": "part_number",
        "material": "part_number",
        "material_code": "part_number",
        "item_code": "part_number",

        "description": "part_description",
        "part_description": "part_description",

        "project": "project",
        "category": "category",
        "hpg": "hpg",
        "series": "series",

        # --------------------------------------------------------------
        # Supplier
        # --------------------------------------------------------------
        "vendor_code": "supplier_code",
        "supplier_code": "supplier_code",

        "new_vc": "new_supplier_code",
        "new_supplier_code": "new_supplier_code",

        "supplier": "supplier_name",
        "supplier_name": "supplier_name",

        "vendor": "supplier_name",
        "vendor_name": "supplier_name",

        # --------------------------------------------------------------
        # Procurement / Demand
        # --------------------------------------------------------------
        "monthly_requirement": "monthly_requirement",

        "annual_sales_forecast": "annual_forecast",
        "annual_forecast": "annual_forecast",

        "exp_bo": "expected_backorder",
        "expected_backorder": "expected_backorder",

        "shortfall_quantity": "shortfall_quantity",

        "open_po": "open_po",
        "open_sto": "open_sto",
        "sto_intransit": "sto_intransit",

        # --------------------------------------------------------------
        # Inventory
        # --------------------------------------------------------------
        "stock_as_on_date": "current_stock",
        "current_stock": "current_stock",

        "actual_stock": "actual_stock",

        "ncr_stock": "ncr_stock",
        "blr_stock": "blr_stock",

        "total_mard": "total_mard",
        "total_vbbe": "total_vbbe",

        # --------------------------------------------------------------
        # Coverage
        # --------------------------------------------------------------
        "cov": "coverage",
        "coverage": "coverage",

        "ncr_cov_incl_i_t": "ncr_coverage",
        "blr_cov_incl_i_t": "blr_coverage",

        "pan_india_coverage": "pan_india_coverage",

        # --------------------------------------------------------------
        # Commercial
        # --------------------------------------------------------------
        "b_price": "unit_price",
        "unit_price": "unit_price",

        "inventory_value": "inventory_value",
        "fums_value": "fums_value",

        # --------------------------------------------------------------
        # Planning
        # --------------------------------------------------------------
        "priority": "priority",
        "priority_dispatch": "priority",

        "frequency": "frequency",

        # --------------------------------------------------------------
        # Other business fields
        # --------------------------------------------------------------
        "last_3_months_total_orders": "last_3_months_orders",

        "manual_sto_ncr": "manual_sto_ncr",
        "manual_sto_blr": "manual_sto_blr",
    }

    # ------------------------------------------------------------------
    # Source preference
    #
    # When multiple integrated sheets contain the same business field,
    # these prefixes determine which source should be preferred.
    # ------------------------------------------------------------------

    SOURCE_PRIORITY: dict[str, list[str]] = {
        "part_number": [
            "workbook_",
            "planning_",
            "ppc_",
            "order_details_",
            "supplier_bifurcation_",
            "inventory_reduction_plan_",
        ],
        "part_description": [
            "workbook_",
            "planning_",
            "ppc_",
            "order_details_",
        ],
        "supplier_name": [
            "workbook_",
            "supplier_bifurcation_",
            "planning_",
            "ppc_",
            "order_details_",
        ],
        "supplier_code": [
            "workbook_",
            "supplier_bifurcation_",
            "planning_",
            "ppc_",
            "order_details_",
        ],
        "new_supplier_code": [
            "workbook_",
            "supplier_bifurcation_",
            "planning_",
            "ppc_",
        ],
        "monthly_requirement": [
            "workbook_",
            "planning_",
            "ppc_",
            "order_details_",
        ],
        "current_stock": [
            "workbook_",
            "inventory_reduction_plan_",
            "planning_",
            "ppc_",
        ],
        "shortfall_quantity": [
            "workbook_",
            "planning_",
            "ppc_",
            "order_details_",
        ],
        "inventory_value": [
            "workbook_",
            "inventory_reduction_plan_",
            "planning_",
            "ppc_",
        ],
        "unit_price": [
            "workbook_",
            "planning_",
            "ppc_",
        ],
        "open_po": [
            "workbook_",
            "planning_",
            "pr_po_",
            "ppc_",
        ],
        "open_sto": [
            "workbook_",
            "planning_",
            "pr_po_",
            "ppc_",
        ],
        "sto_intransit": [
            "workbook_",
            "planning_",
            "pr_po_",
            "ppc_",
        ],
        "category": [
            "workbook_",
            "planning_",
            "inventory_reduction_plan_",
            "ppc_",
        ],
        "coverage": [
            "workbook_",
            "planning_",
            "ppc_",
            "inventory_reduction_plan_",
        ],
        "priority": [
            "workbook_",
            "planning_",
            "ppc_",
        ],
    }

    # ------------------------------------------------------------------
    # Numeric canonical fields
    # ------------------------------------------------------------------

    NUMERIC_FIELDS: set[str] = {
        "monthly_requirement",
        "annual_forecast",
        "expected_backorder",
        "shortfall_quantity",
        "open_po",
        "open_sto",
        "sto_intransit",
        "current_stock",
        "actual_stock",
        "ncr_stock",
        "blr_stock",
        "total_mard",
        "total_vbbe",
        "coverage",
        "ncr_coverage",
        "blr_coverage",
        "pan_india_coverage",
        "unit_price",
        "inventory_value",
        "fums_value",
        "last_3_months_orders",
        "manual_sto_ncr",
        "manual_sto_blr",
    }

    # ------------------------------------------------------------------
    # Main mapping
    # ------------------------------------------------------------------

    def map(
        self,
        df: pl.DataFrame,
    ) -> pl.DataFrame:
        """
        Convert source-specific fields into canonical business fields.

        Existing canonical columns are preserved.

        If a canonical field does not exist, the mapper searches for
        source-prefixed variants such as:

            workbook_monthly_requirement
            planning_monthly_requirement
            ppc_monthly_requirement

        and creates:

            monthly_requirement
        """

        # --------------------------------------------------------------
        # 1. Exact mappings
        # --------------------------------------------------------------

        df = self._map_exact_columns(df)

        # --------------------------------------------------------------
        # 2. Source-prefixed mappings
        # --------------------------------------------------------------

        df = self._map_prefixed_columns(df)

        # --------------------------------------------------------------
        # 3. Forecast / projection fields
        # --------------------------------------------------------------

        df = self._map_forecast_columns(df)

        # --------------------------------------------------------------
        # 4. Normalize numeric business fields
        # --------------------------------------------------------------

        df = self._normalize_numeric_fields(df)

        # --------------------------------------------------------------
        # 5. Normalize coverage
        # --------------------------------------------------------------

        df = self._normalize_coverage(df)

        return df

    # ------------------------------------------------------------------
    # Exact mapping
    # ------------------------------------------------------------------

    def _map_exact_columns(
        self,
        df: pl.DataFrame,
    ) -> pl.DataFrame:
        """
        Map exact source column names.

        Example:

            stock_as_on_date
                ↓
            current_stock
        """

        rename_map: dict[str, str] = {}

        existing_targets = set(df.columns)

        for column in df.columns:
            target = self.FIELD_ALIASES.get(column)

            if target is None:
                continue

            # Do not rename if the canonical target already exists.
            if (
                target != column
                and target in existing_targets
            ):
                continue

            rename_map[column] = target

        if rename_map:
            df = df.rename(rename_map)

        return df

    # ------------------------------------------------------------------
    # Prefixed mapping
    # ------------------------------------------------------------------

    def _map_prefixed_columns(
        self,
        df: pl.DataFrame,
    ) -> pl.DataFrame:
        """
        Find source-prefixed columns and create canonical columns.

        Example:

            workbook_actual_stock
                ↓
            current_stock

            workbook_monthly_requirement
                ↓
            monthly_requirement

            workbook_inventory_value
                ↓
            inventory_value
        """

        for target, prefixes in self.SOURCE_PRIORITY.items():
            # Do not overwrite a canonical field that already exists.
            if target in df.columns:
                continue

            candidates = self._find_candidates(
                df=df,
                target=target,
                prefixes=prefixes,
            )

            if not candidates:
                continue

            source_column = candidates[0]

            df = df.with_columns(
                pl.col(source_column).alias(target)
            )

        return df

    # ------------------------------------------------------------------
    # Candidate discovery
    # ------------------------------------------------------------------

    def _find_candidates(
        self,
        df: pl.DataFrame,
        target: str,
        prefixes: list[str],
    ) -> list[str]:
        """
        Find source columns that represent a canonical field.

        Supports special source-specific aliases such as:

            workbook_actual_stock
                → current_stock

            workbook_stock_as_on_date
                → current_stock

            workbook_cov
                → coverage
        """

        candidates: list[str] = []

        # Direct aliases that may appear after a source prefix.
        aliases = {
            target,
            *(
                source
                for source, mapped_target
                in self.FIELD_ALIASES.items()
                if mapped_target == target
            ),
        }

        # Special inventory aliases.
        if target == "current_stock":
            aliases.update(
                {
                    "actual_stock",
                    "stock_as_on_date",
                    "actual_stock_total_mard_total_vbbe",
                }
            )

        # Special coverage aliases.
        if target == "coverage":
            aliases.update(
                {
                    "cov",
                    "coverage",
                    "schdl_cov",
                    "pan_india_coverage",
                }
            )

        # Search according to source priority.
        for prefix in prefixes:
            for alias in aliases:
                candidate = f"{prefix}{alias}"

                if candidate in df.columns:
                    candidates.append(candidate)

        # Also support exact alias without a prefix.
        for alias in aliases:
            if alias in df.columns:
                candidates.append(alias)

        # Remove duplicates while preserving order.
        return list(dict.fromkeys(candidates))

    # ------------------------------------------------------------------
    # Numeric normalization
    # ------------------------------------------------------------------

    def _normalize_numeric_fields(
        self,
        df: pl.DataFrame,
    ) -> pl.DataFrame:
        """
        Safely convert canonical numeric fields to Float64.

        Invalid Excel/SAP values become null rather than crashing
        the analytics pipeline.
        """

        expressions: list[pl.Expr] = []

        for column in self.NUMERIC_FIELDS:
            if column not in df.columns:
                continue

            expressions.append(
                pl.col(column)
                .cast(
                    pl.Float64,
                    strict=False,
                )
                .alias(column)
            )

        if expressions:
            df = df.with_columns(expressions)

        return df

    # ------------------------------------------------------------------
    # Coverage normalization
    # ------------------------------------------------------------------

    def _normalize_coverage(
        self,
        df: pl.DataFrame,
    ) -> pl.DataFrame:
        """
        Normalize coverage into a numeric Float64 field.

        Handles values such as:

            2
            2.5
            "2.5"
            "2.5x"
            ""
            "N/A"

        Invalid values become null.
        """

        if "coverage" not in df.columns:
            return df

        coverage = (
            pl.col("coverage")
            .cast(
                pl.String,
                strict=False,
            )
            .str.strip_chars()
            .str.replace(
                r"[^0-9.\-]+",
                "",
            )
            .cast(
                pl.Float64,
                strict=False,
            )
        )

        return df.with_columns(
            coverage.alias("coverage")
        )

    # ------------------------------------------------------------------
    # Forecast / projection mapping
    # ------------------------------------------------------------------

    @staticmethod
    def _map_forecast_columns(
        df: pl.DataFrame,
    ) -> pl.DataFrame:
        """
        Normalize monthly forecast/projection columns.

        Existing explicit month fields are preserved.

        Examples:

            sep_forecast
            sep_end_stock
            sep_end_coverage
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

    # ------------------------------------------------------------------
    # Unmapped columns
    # ------------------------------------------------------------------

    def unmapped_columns(
        self,
        df: pl.DataFrame,
    ) -> list[str]:
        """
        Return columns that are not represented in the canonical
        business model.

        Source-prefixed columns are considered mapped when their
        underlying business field is recognized.
        """

        unmapped: list[str] = []

        canonical_fields = set(
            self.FIELD_ALIASES.values()
        )

        for column in df.columns:
            # Canonical field.
            if column in canonical_fields:
                continue

            # Direct source alias.
            if column in self.FIELD_ALIASES:
                continue

            # Forecast/projection.
            if self._is_forecast_column(column):
                continue

            if self._is_projection_column(column):
                continue

            # Source-prefixed canonical field.
            if self._is_prefixed_business_column(
                column
            ):
                continue

            unmapped.append(column)

        return unmapped

    # ------------------------------------------------------------------
    # Prefixed field detection
    # ------------------------------------------------------------------

    def _is_prefixed_business_column(
        self,
        column: str,
    ) -> bool:
        """
        Determine whether a column looks like a source-prefixed
        version of a known business field.

        Example:

            workbook_monthly_requirement
            workbook_actual_stock
            planning_priority
        """

        known_fields = set(
            self.FIELD_ALIASES.keys()
        )

        known_fields.update(
            self.FIELD_ALIASES.values()
        )

        # Inventory-specific aliases.
        known_fields.update(
            {
                "actual_stock",
                "stock_as_on_date",
                "cov",
                "coverage",
                "schdl_cov",
            }
        )

        for field in known_fields:
            if column.endswith(f"_{field}"):
                return True

        return False

    # ------------------------------------------------------------------
    # Forecast detection
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Projection detection
    # ------------------------------------------------------------------

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