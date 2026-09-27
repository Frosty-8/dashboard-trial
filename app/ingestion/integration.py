from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .relationship_detector import ColumnMatch
from .sheet_classifier import SheetClassification
from .workbook_profiler import WorkbookProfile


@dataclass
class SheetIntegration:
    sheet_name: str
    role: str
    selected: bool
    priority: int
    reason: str


@dataclass
class JoinPlan:
    left_sheet: str
    left_column: str
    right_sheet: str
    right_column: str
    key_type: str
    confidence: float
    join_type: str = "left"


@dataclass
class IntegrationPlan:
    primary_sheet: str | None
    sheets: list[SheetIntegration] = field(default_factory=list)
    joins: list[JoinPlan] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class WorkbookIntegrationPlanner:
    """
    Converts workbook classification and detected relationships
    into a deterministic integration plan.

    This class creates a plan only.
    It does not modify or merge the actual datasets yet.
    """

    PRIMARY_ROLES = {
        "primary_transactional",
        "planning",
    }

    SUPPORTING_ROLES = {
        "supplier_master",
        "inventory",
        "procurement",
        "schedule",
    }

    IGNORED_ROLES = {
        "supporting",
        "unknown",
    }

    ROLE_PRIORITY = {
        "primary_transactional": 100,
        "planning": 90,
        "procurement": 80,
        "inventory": 70,
        "supplier_master": 60,
        "schedule": 50,
        "supporting": 10,
        "unknown": 0,
    }

    def build(
        self,
        workbook: WorkbookProfile,
        classifications: list[SheetClassification],
        relationships: list[ColumnMatch],
    ) -> IntegrationPlan:

        classification_map = {
            item.sheet_name: item
            for item in classifications
        }

        primary_sheet = self._select_primary_sheet(
            classifications
        )

        integrations: list[SheetIntegration] = []

        for classification in classifications:

            role = classification.role

            selected = (
                role in self.PRIMARY_ROLES
                or role in self.SUPPORTING_ROLES
            )

            if classification.sheet_name == primary_sheet:
                selected = True

            if role in self.IGNORED_ROLES:
                selected = False

            reason = self._selection_reason(
                classification,
                primary_sheet,
            )

            integrations.append(
                SheetIntegration(
                    sheet_name=classification.sheet_name,
                    role=role,
                    selected=selected,
                    priority=self.ROLE_PRIORITY.get(
                        role,
                        0,
                    ),
                    reason=reason,
                )
            )

        joins = self._build_joins(
            relationships=relationships,
            classification_map=classification_map,
            primary_sheet=primary_sheet,
        )

        return IntegrationPlan(
            primary_sheet=primary_sheet,
            sheets=sorted(
                integrations,
                key=lambda item: item.priority,
                reverse=True,
            ),
            joins=joins,
        )

    def _select_primary_sheet(
        self,
        classifications: list[SheetClassification],
    ) -> str | None:

        candidates = [
            item
            for item in classifications
            if item.role in self.PRIMARY_ROLES
        ]

        if not candidates:
            return None

        return max(
            candidates,
            key=lambda item: item.score,
        ).sheet_name

    def _build_joins(
        self,
        relationships: list[ColumnMatch],
        classification_map: dict[str, SheetClassification],
        primary_sheet: str | None,
    ) -> list[JoinPlan]:

        joins: list[JoinPlan] = []

        for relationship in relationships:

            left_role = classification_map.get(
                relationship.left_sheet
            )

            right_role = classification_map.get(
                relationship.right_sheet
            )

            if left_role is None or right_role is None:
                continue

            if left_role.role in self.IGNORED_ROLES:
                continue

            if right_role.role in self.IGNORED_ROLES:
                continue

            # Prefer relationships connected to the
            # selected primary dataset.
            confidence = relationship.confidence

            if (
                primary_sheet is not None
                and (
                    relationship.left_sheet == primary_sheet
                    or relationship.right_sheet == primary_sheet
                )
            ):
                confidence = min(
                    confidence + 10,
                    100,
                )

            joins.append(
                JoinPlan(
                    left_sheet=relationship.left_sheet,
                    left_column=relationship.left_column,
                    right_sheet=relationship.right_sheet,
                    right_column=relationship.right_column,
                    key_type=relationship.key_type,
                    confidence=round(
                        confidence,
                        2,
                    ),
                )
            )

        return sorted(
            joins,
            key=lambda join: join.confidence,
            reverse=True,
        )

    def _selection_reason(
        self,
        classification: SheetClassification,
        primary_sheet: str | None,
    ) -> str:

        if classification.sheet_name == primary_sheet:
            return "Selected as the primary procurement dataset."

        if classification.role == "planning":
            return "Planning data can enrich procurement requirements and demand."

        if classification.role == "supplier_master":
            return "Supplier data can enrich supplier identity and reporting."

        if classification.role == "inventory":
            return "Inventory data can enrich stock and shortage calculations."

        if classification.role == "procurement":
            return "Procurement data can enrich PR, PO, and STO information."

        if classification.role == "schedule":
            return "Schedule data can enrich timing and release information."

        if classification.role == "supporting":
            return "Supporting data is excluded from the canonical dataset by default."

        return "Sheet requires further inspection before integration."