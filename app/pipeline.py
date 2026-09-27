# app/pipeline.py

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import polars as pl

from app.analytics import (
    ForecastAnalytics,
    InventoryAnalytics,
    KPIAnalytics,
    ProcurementAnalytics,
    SupplierAnalytics,
)
from app.ingestion import DataProfiler, ExcelReader
from app.insights import InsightEngine
from app.transformation import (
    BusinessCalculator,
    BusinessMapper,
    DataCleaner,
)


@dataclass
class PipelineResult:
    raw: pl.DataFrame
    cleaned: pl.DataFrame
    transformed: pl.DataFrame
    profile: dict[str, Any]
    kpis: dict[str, Any]
    inventory: dict[str, Any]
    procurement: dict[str, Any]
    suppliers: dict[str, Any]
    forecast: dict[str, Any]
    insights: dict[str, Any]
    unmapped_columns: list[str]


class PPCPipeline:
    """
    End-to-end processing pipeline.

    Input:
        XLSX / XLSB / CSV / Parquet

    Output:
        Clean business dataset
        KPIs
        Analytics
        Insights
    """

    def __init__(self) -> None:
        self.reader = ExcelReader()
        self.profiler = DataProfiler()

        self.cleaner = DataCleaner()
        self.mapper = BusinessMapper()
        self.calculator = BusinessCalculator()

        self.kpis = KPIAnalytics()
        self.inventory = InventoryAnalytics()
        self.procurement = ProcurementAnalytics()
        self.suppliers = SupplierAnalytics()
        self.forecast = ForecastAnalytics()

        self.insights = InsightEngine()

    def run(
        self,
        file_path: str | Path,
        sheet_name: str | None = None,
    ) -> PipelineResult:
        # ---------------------------------------------------------
        # 1. INGEST
        # ---------------------------------------------------------
        raw_df = self.reader.read(
            file_path,
            sheet_name=sheet_name,
        )

        # ---------------------------------------------------------
        # 2. PROFILE
        # ---------------------------------------------------------
        profile = self.profiler.profile(
            raw_df,
            file_path=file_path,
        )

        profile_summary = self.profiler.summary(
            profile
        )

        # ---------------------------------------------------------
        # 3. CLEAN
        # ---------------------------------------------------------
        cleaned_df = self.cleaner.clean(
            raw_df
        )

        # ---------------------------------------------------------
        # 4. MAP TO BUSINESS MODEL
        # ---------------------------------------------------------
        unmapped_columns = (
            self.mapper.unmapped_columns(
                cleaned_df
            )
        )

        transformed_df = self.mapper.map(
            cleaned_df
        )

        # ---------------------------------------------------------
        # 5. CALCULATE BUSINESS METRICS
        # ---------------------------------------------------------
        transformed_df = (
            self.calculator.calculate(
                transformed_df
            )
        )

        # ---------------------------------------------------------
        # 6. ANALYTICS
        # ---------------------------------------------------------
        kpis = self.kpis.calculate(
            transformed_df
        )

        inventory = {
            "coverage_distribution": (
                self.inventory.coverage_distribution(
                    transformed_df
                )
            ),
            "inventory_by_category": (
                self.inventory.inventory_by_category(
                    transformed_df
                )
            ),
            "critical_parts": (
                self.inventory.critical_parts(
                    transformed_df
                )
            ),
        }

        procurement = {
            "supplier_shortfalls": (
                self.procurement.supplier_shortfalls(
                    transformed_df
                )
            ),
            "priority_distribution": (
                self.procurement.priority_distribution(
                    transformed_df
                )
            ),
            "shortfall_parts": (
                self.procurement.shortfall_parts(
                    transformed_df
                )
            ),
        }

        suppliers = {
            "performance": (
                self.suppliers.performance(
                    transformed_df
                )
            )
        }

        forecast = {
            "monthly_summary": (
                self.forecast.monthly_summary(
                    transformed_df
                )
            ),
            "stock_projection": (
                self.forecast.stock_projection(
                    transformed_df
                )
            ),
        }

        # ---------------------------------------------------------
        # 7. INSIGHT ENGINE
        # ---------------------------------------------------------
        insights = self.insights.analyze(
            transformed_df
        )

        return PipelineResult(
            raw=raw_df,
            cleaned=cleaned_df,
            transformed=transformed_df,
            profile=profile_summary,
            kpis=kpis,
            inventory=inventory,
            procurement=procurement,
            suppliers=suppliers,
            forecast=forecast,
            insights=insights,
            unmapped_columns=unmapped_columns,
        )

    def run_and_save(
        self,
        file_path: str | Path,
        output_path: str | Path,
        sheet_name: str | None = None,
    ) -> PipelineResult:
        result = self.run(
            file_path=file_path,
            sheet_name=sheet_name,
        )

        output_path = Path(output_path)
        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        result.transformed.write_parquet(
            output_path
        )

        return result