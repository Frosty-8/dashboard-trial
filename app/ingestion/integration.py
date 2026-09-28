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
    Builds a deterministic integration plan for a workbook.

    Supports:
    - Multi-sheet SAP workbooks
    - Single-sheet workbooks
    - Workbooks without detected relationships
    - Workbooks without an explicitly classified primary role
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
            workbook=workbook,
            classifications=classifications,
        )

        integrations: list[SheetIntegration] = []

        for classification in classifications:

            role = classification.role

            selected = (
                role in self.PRIMARY_ROLES
                or role in self.SUPPORTING_ROLES
            )

            # Always keep the selected primary source.
            if classification.sheet_name == primary_sheet:
                selected = True

            # Supporting/unknown sheets remain excluded unless
            # one of them became the fallback primary source.
            if (
                role in self.IGNORED_ROLES
                and classification.sheet_name != primary_sheet
            ):
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
        workbook: WorkbookProfile,
        classifications: list[SheetClassification],
    ) -> str | None:

        # ---------------------------------------------------------
        # 1. Normal case
        # ---------------------------------------------------------

        candidates = [
            item
            for item in classifications
            if item.role in self.PRIMARY_ROLES
        ]

        if candidates:
            return max(
                candidates,
                key=lambda item: item.score,
            ).sheet_name

        # ---------------------------------------------------------
        # 2. Fallback for a single-sheet workbook
        # ---------------------------------------------------------

        if len(workbook.sheets) == 1:
            return workbook.sheets[0].name

        # ---------------------------------------------------------
        # 3. Fallback for multi-sheet workbooks where no primary
        #    role was confidently detected.
        # ---------------------------------------------------------

        likely_sheets = [
            sheet
            for sheet in workbook.sheets
            if sheet.likely_data_sheet
        ]

        if likely_sheets:
            best_sheet = max(
                likely_sheets,
                key=lambda sheet: sheet.score,
            )

            return best_sheet.name

        # ---------------------------------------------------------
        # 4. Last-resort fallback.
        #
        # Do not fail workbook analysis merely because the
        # classifier could not identify a semantic role.
        # ---------------------------------------------------------

        if classifications:
            return max(
                classifications,
                key=lambda item: item.score,
            ).sheet_name

        return None

    def _selection_reason(
        self,
        classification: SheetClassification,
        primary_sheet: str | None,
    ) -> str:

        if classification.sheet_name == primary_sheet:
            return "Selected as primary source dataset."

        if classification.role in self.PRIMARY_ROLES:
            return "Selected because it contains a primary business dataset."

        if classification.role in self.SUPPORTING_ROLES:
            return (
                f"Selected as supporting {classification.role} "
                "data."
            )

        return "Excluded because it is not required for the canonical dataset."

    def _build_joins(
        self,
        relationships: list[ColumnMatch],
        classification_map: dict[str, SheetClassification],
        primary_sheet: str | None,
    ) -> list[JoinPlan]:

        if primary_sheet is None:
            return []

        joins: list[JoinPlan] = []

        for relationship in relationships:

            left = relationship.left_sheet
            right = relationship.right_sheet

            # -----------------------------------------------------
            # Only build joins involving the primary source.
            # This prevents unrelated supporting sheets from
            # being blindly joined together.
            # -----------------------------------------------------

            if primary_sheet not in {
                left,
                right,
            }:
                continue

            other_sheet = (
                right
                if left == primary_sheet
                else left
            )

            other_classification = classification_map.get(
                other_sheet
            )

            if other_classification is None:
                continue

            if other_classification.role in self.IGNORED_ROLES:
                continue

            joins.append(
                JoinPlan(
                    left_sheet=relationship.left_sheet,
                    left_column=relationship.left_column,
                    right_sheet=relationship.right_sheet,
                    right_column=relationship.right_column,
                    key_type=relationship.key_type,
                    confidence=relationship.confidence,
                    join_type="left",
                )
            )

        return joins