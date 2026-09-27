from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

from .workbook_profiler import SheetProfile, WorkbookProfile


@dataclass
class SheetClassification:
    sheet_name: str
    role: str
    purpose: str
    relevance: str
    score: float
    reasons: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SheetClassifier:
    """
    Classifies workbook sheets into business-oriented roles.

    The classifier uses the sheet name, detected columns,
    and profiler score. It does not modify the original workbook.
    """

    ROLE_RULES = {
        "primary_transactional": {
            "terms": {
                "ppc",
                "order",
                "order details",
                "purchase",
                "procurement",
            },
            "purpose": "Primary procurement or transactional data",
        },
        "planning": {
            "terms": {
                "planning",
                "plan",
                "forecast",
                "requirement",
            },
            "purpose": "Planning, demand, requirement, or forecast data",
        },
        "inventory": {
            "terms": {
                "inventory",
                "stock",
                "stock coverage",
                "inventory reduction",
            },
            "purpose": "Inventory and stock-related data",
        },
        "supplier_master": {
            "terms": {
                "supplier",
                "supplier bifurcation",
                "vendor",
                "vendor master",
            },
            "purpose": "Supplier or vendor reference data",
        },
        "procurement": {
            "terms": {
                "pr",
                "po",
                "pr>po",
                "purchase order",
                "purchase requisition",
                "sto",
            },
            "purpose": "Purchase requisition, purchase order, or STO data",
        },
        "schedule": {
            "terms": {
                "schedule",
                "release",
                "communication",
                "hoto",
            },
            "purpose": "Production or procurement schedule data",
        },
    }

    SUPPORTING_TERMS = {
        "backup",
        "matrix",
        "summary",
        "sheet",
        "helper",
        "template",
    }

    def classify(
        self,
        workbook: WorkbookProfile,
    ) -> list[SheetClassification]:

        classifications: list[SheetClassification] = []

        for sheet in workbook.sheets:
            classifications.append(
                self._classify_sheet(sheet)
            )

        return sorted(
            classifications,
            key=lambda item: item.score,
            reverse=True,
        )

    def _classify_sheet(
        self,
        sheet: SheetProfile,
    ) -> SheetClassification:

        name = sheet.name.strip().lower()

        columns = " ".join(
            column.lower()
            for column in sheet.sample_columns
        )

        combined = f"{name} {columns}"

        role_scores: dict[str, float] = {}
        reasons: list[str] = []

        for role, rule in self.ROLE_RULES.items():

            score = 0.0

            for term in rule["terms"]:
                if term in name:
                    score += 30
                    reasons.append(
                        f"Sheet name contains '{term}'"
                    )

                elif term in columns:
                    score += 10
                    reasons.append(
                        f"Columns contain '{term}'"
                    )

            role_scores[role] = score

        # Use the profiler's existing relevance score
        # as supporting evidence.
        if sheet.likely_data_sheet:
            for role in role_scores:
                role_scores[role] += min(
                    sheet.score * 0.10,
                    10,
                )

        best_role = max(
            role_scores,
            key=lambda role : role_scores[role],
            default="unknown",
        )

        best_score = role_scores.get(
            best_role,
            0,
        )

        if best_score <= 10:

            if any(
                term in name
                for term in self.SUPPORTING_TERMS
            ):
                best_role = "supporting"
                purpose = (
                    "Supporting, backup, helper, "
                    "or intermediate workbook data"
                )
                relevance = "low"

            else:
                best_role = "unknown"
                purpose = (
                    "Purpose could not be determined "
                    "from the available workbook metadata"
                )
                relevance = "unknown"

        else:
            purpose = self.ROLE_RULES[best_role]["purpose"]

            if best_score >= 50:
                relevance = "high"
            elif best_score >= 25:
                relevance = "medium"
            else:
                relevance = "low"

        if not reasons:
            reasons.append(
                "Classification based primarily on "
                "workbook profiler metadata"
            )

        return SheetClassification(
            sheet_name=sheet.name,
            role=best_role,
            purpose=purpose,
            relevance=relevance,
            score=round(best_score, 2),
            reasons=list(dict.fromkeys(reasons)),
        )