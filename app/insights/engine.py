# app/insights/engine.py

from __future__ import annotations

from typing import Any

import polars as pl

from .rules import InsightRules


class InsightEngine:
    """Runs business rules and produces a structured insight feed."""

    def __init__(
        self,
        rules: InsightRules | None = None,
    ) -> None:
        self.rules = rules or InsightRules()

    def analyze(
        self,
        df: pl.DataFrame,
    ) -> dict[str, Any]:
        insights = self.rules.evaluate(df)

        severity_order = {
            "critical": 0,
            "warning": 1,
            "info": 2,
        }

        insights.sort(
            key=lambda item: severity_order.get(
                item["severity"],
                99,
            )
        )

        return {
            "total_insights": len(insights),
            "critical": sum(
                insight["severity"] == "critical"
                for insight in insights
            ),
            "warning": sum(
                insight["severity"] == "warning"
                for insight in insights
            ),
            "info": sum(
                insight["severity"] == "info"
                for insight in insights
            ),
            "items": insights,
        }