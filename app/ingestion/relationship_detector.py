from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .workbook_profiler import SheetProfile, WorkbookProfile


@dataclass
class ColumnMatch:
    left_sheet: str
    left_column: str
    right_sheet: str
    right_column: str
    key_type: str
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class RelationshipDetector:
    """
    Detects possible relationships between workbook sheets
    by comparing normalized column names.
    """

    COLUMN_ALIASES = {
        "part_number": {
            "part",
            "part no",
            "part number",
            "part_no",
            "part_number",
            "material",
            "material code",
            "material_code",
            "item",
            "item code",
        },
        "supplier": {
            "supplier",
            "supplier name",
            "supplier code",
            "supplier_code",
            "vendor",
            "vendor name",
            "vendor code",
            "vendor_code",
        },
        "po": {
            "po",
            "po no",
            "po number",
            "po_no",
            "po_number",
            "purchase order",
            "purchase order number",
        },
        "pr": {
            "pr",
            "pr no",
            "pr number",
            "pr_no",
            "pr_number",
            "purchase requisition",
        },
        "sto": {
            "sto",
            "sto no",
            "sto number",
            "sto_no",
            "sto_number",
        },
        "project": {
            "project",
            "project name",
            "project code",
            "project_code",
        },
        "category": {
            "category",
            "material group",
            "material_group",
            "family",
            "commodity",
        },
    }

    def detect(
        self,
        workbook: WorkbookProfile,
    ) -> list[ColumnMatch]:

        matches: list[ColumnMatch] = []

        sheets = workbook.sheets

        for index, left in enumerate(sheets):

            for right in sheets[index + 1:]:

                matches.extend(
                    self._compare_sheets(
                        left,
                        right,
                    )
                )

        return sorted(
            matches,
            key=lambda match: match.confidence,
            reverse=True,
        )

    def _compare_sheets(
        self,
        left: SheetProfile,
        right: SheetProfile,
    ) -> list[ColumnMatch]:

        matches: list[ColumnMatch] = []

        left_columns = self._classify_columns(
            left.sample_columns
        )

        right_columns = self._classify_columns(
            right.sample_columns
        )

        for left_column, left_type in left_columns.items():

            for right_column, right_type in right_columns.items():

                if left_type != right_type:
                    continue

                confidence = self._confidence(
                    left_column,
                    right_column,
                )

                if confidence < 50:
                    continue

                matches.append(
                    ColumnMatch(
                        left_sheet=left.name,
                        left_column=left_column,
                        right_sheet=right.name,
                        right_column=right_column,
                        key_type=left_type,
                        confidence=confidence,
                    )
                )

        return matches

    def _classify_columns(
        self,
        columns: list[str],
    ) -> dict[str, str]:

        result: dict[str, str] = {}

        for column in columns:

            normalized = self._normalize(column)

            for key_type, aliases in self.COLUMN_ALIASES.items():

                normalized_aliases = {
                    self._normalize(alias)
                    for alias in aliases
                }

                if normalized in normalized_aliases:
                    result[column] = key_type
                    break

        return result

    def _confidence(
        self,
        left_column: str,
        right_column: str,
    ) -> float:

        left = self._normalize(left_column)
        right = self._normalize(right_column)

        if left == right:
            return 100.0

        left_tokens = set(left.split())
        right_tokens = set(right.split())

        if not left_tokens or not right_tokens:
            return 0.0

        overlap = len(left_tokens & right_tokens)
        total = len(left_tokens | right_tokens)

        if total == 0:
            return 0.0

        return round(
            (overlap / total) * 100,
            2,
        )

    @staticmethod
    def _normalize(value: str) -> str:

        value = str(value).strip().lower()

        replacements = {
            "_": " ",
            "-": " ",
            "/": " ",
            ">": " ",
        }

        for old, new in replacements.items():
            value = value.replace(old, new)

        return " ".join(value.split())