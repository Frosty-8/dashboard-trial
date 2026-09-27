# app/insights/rules.py

from __future__ import annotations

from dataclasses import dataclass

import polars as pl


@dataclass(frozen=True)
class InsightRule:
    rule_id: str
    severity: str
    title: str
    description: str


class InsightRules:
    """Configurable business rules for procurement insights."""

    def __init__(
        self,
        critical_coverage: float = 1.0,
        low_coverage: float = 2.0,
        excess_coverage: float = 6.0,
    ) -> None:
        self.critical_coverage = critical_coverage
        self.low_coverage = low_coverage
        self.excess_coverage = excess_coverage

    def evaluate(
        self,
        df: pl.DataFrame,
    ) -> list[dict]:
        insights: list[dict] = []

        insights.extend(
            self._coverage_insights(df)
        )
        insights.extend(
            self._shortfall_insights(df)
        )
        insights.extend(
            self._supplier_insights(df)
        )
        insights.extend(
            self._inventory_insights(df)
        )
        insights.extend(
            self._transit_insights(df)
        )

        return insights

    def _coverage_insights(
        self,
        df: pl.DataFrame,
    ) -> list[dict]:
        if "coverage" not in df.columns:
            return []

        valid = df.filter(
            pl.col("coverage").is_not_null()
        )

        critical = valid.filter(
            pl.col("coverage")
            < self.critical_coverage
        ).height

        low = valid.filter(
            (pl.col("coverage") >= self.critical_coverage)
            & (
                pl.col("coverage")
                < self.low_coverage
            )
        ).height

        excess = valid.filter(
            pl.col("coverage")
            > self.excess_coverage
        ).height

        insights = []

        if critical:
            insights.append(
                {
                    "rule_id": "COVERAGE_CRITICAL",
                    "severity": "critical",
                    "title": "Critical stock coverage",
                    "description": (
                        f"{critical:,} parts have less than "
                        f"{self.critical_coverage:g} month of "
                        "stock coverage."
                    ),
                    "affected_records": critical,
                }
            )

        if low:
            insights.append(
                {
                    "rule_id": "COVERAGE_LOW",
                    "severity": "warning",
                    "title": "Low stock coverage",
                    "description": (
                        f"{low:,} parts have between "
                        f"{self.critical_coverage:g} and "
                        f"{self.low_coverage:g} months "
                        "of coverage."
                    ),
                    "affected_records": low,
                }
            )

        if excess:
            insights.append(
                {
                    "rule_id": "COVERAGE_EXCESS",
                    "severity": "info",
                    "title": "Potential excess inventory",
                    "description": (
                        f"{excess:,} parts have more than "
                        f"{self.excess_coverage:g} months "
                        "of stock coverage."
                    ),
                    "affected_records": excess,
                }
            )

        return insights

    def _shortfall_insights(
        self,
        df: pl.DataFrame,
    ) -> list[dict]:
        if "shortfall_quantity" not in df.columns:
            return []

        shortfall = df.filter(
            pl.col("shortfall_quantity") > 0
        )

        if shortfall.is_empty():
            return []

        quantity = shortfall[
            "shortfall_quantity"
        ].sum()

        return [
            {
                "rule_id": "PROCUREMENT_SHORTFALL",
                "severity": "critical",
                "title": "Procurement shortfall detected",
                "description": (
                    f"{shortfall.height:,} parts have a "
                    f"combined shortfall of "
                    f"{quantity:,.0f} units."
                ),
                "affected_records": shortfall.height,
            }
        ]

    def _supplier_insights(
        self,
        df: pl.DataFrame,
    ) -> list[dict]:
        required = {
            "supplier_name",
            "shortfall_quantity",
        }

        if not required.issubset(df.columns):
            return []

        supplier_data = (
            df.group_by("supplier_name")
            .agg(
                pl.col("shortfall_quantity")
                .sum()
                .alias("shortfall")
            )
            .sort(
                "shortfall",
                descending=True,
            )
        )

        if supplier_data.is_empty():
            return []

        top_supplier = supplier_data.row(
            0,
            named=True,
        )

        if not top_supplier["shortfall"]:
            return []

        return [
            {
                "rule_id": "SUPPLIER_SHORTFALL_CONCENTRATION",
                "severity": "warning",
                "title": "Supplier shortfall concentration",
                "description": (
                    f"{top_supplier['supplier_name']} "
                    f"has the largest supplier-level "
                    f"shortfall at "
                    f"{top_supplier['shortfall']:,.0f} units."
                ),
                "affected_records": 1,
            }
        ]

    def _inventory_insights(
        self,
        df: pl.DataFrame,
    ) -> list[dict]:
        required = {
            "inventory_value",
            "coverage",
        }

        if not required.issubset(df.columns):
            return []

        excess = df.filter(
            pl.col("coverage")
            > self.excess_coverage
        )

        if excess.is_empty():
            return []

        value = excess[
            "inventory_value"
        ].sum()

        return [
            {
                "rule_id": "EXCESS_INVENTORY_VALUE",
                "severity": "warning",
                "title": "Inventory tied in high coverage",
                "description": (
                    f"{value:,.2f} of inventory value "
                    f"is associated with parts above "
                    f"{self.excess_coverage:g} months "
                    "of coverage."
                ),
                "affected_records": excess.height,
            }
        ]

    def _transit_insights(
        self,
        df: pl.DataFrame,
    ) -> list[dict]:
        if "sto_intransit" not in df.columns:
            return []

        transit = df.filter(
            pl.col("sto_intransit") > 0
        )

        if transit.is_empty():
            return []

        quantity = transit[
            "sto_intransit"
        ].sum()

        return [
            {
                "rule_id": "STO_IN_TRANSIT",
                "severity": "info",
                "title": "Stock transfer in transit",
                "description": (
                    f"{quantity:,.0f} units are currently "
                    "recorded as stock in transit."
                ),
                "affected_records": transit.height,
            }
        ]