"""Preview and apply Strong-code parenthesis fixes.

The generic :mod:`paren_balance` checker identifies unmatched parentheses.
This module keeps the established Strong-code repair workflow: it only
creates a fix when an unmatched parenthesis belongs to a nearby ``(G####)``
or ``(H####)`` citation. It never changes unrelated prose punctuation.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List, NamedTuple

from shared_validation.paren_balance import check_balance, ParenIssue
from shared_validation.strong_applier import apply_fixes, FixResult


_CODE = r"[GH]\d{1,5}"


class BalanceFixAction(NamedTuple):
    """A replacement that corrects one unbalanced Strong-code citation."""

    filepath: str
    field_path: str
    code: str
    old: str
    new: str
    start: int
    end: int
    issue_type: str


def _action_for_issue(
    filepath: str, field_path: str, text: str, issue: ParenIssue
) -> BalanceFixAction | None:
    """Translate a generic balance finding into a safe Strong-code repair."""
    position = issue.position

    if issue.issue_type == "missing_open":
        # (G123)) -> (G123): the unmatched final ')' is simply removed.
        double_close = re.search(rf"\(({_CODE})\)\)$", text[: position + 1])
        if double_close:
            return BalanceFixAction(
                filepath, field_path, double_close.group(1), ")", "",
                position, position + 1, "double_close",
            )

        # G123) -> (G123): add the missing opener around the full citation.
        bare_close = re.search(rf"(?<!\()({_CODE})\)$", text[: position + 1])
        if bare_close:
            start = bare_close.start(1)
            old = text[start : position + 1]
            return BalanceFixAction(
                filepath, field_path, bare_close.group(1), old, f"({old}",
                start, position + 1, "missing_open",
            )

    elif issue.issue_type == "missing_close":
        # ((G123) -> (G123): remove the unmatched first opener.
        double_open = re.match(rf"\(\(({_CODE})\)", text[position:])
        if double_open:
            return BalanceFixAction(
                filepath, field_path, double_open.group(1), "(", "",
                position, position + 1, "double_open",
            )

        # (G123 -> (G123): close the citation after its code.
        bare_open = re.match(rf"\(({_CODE})(?!\))", text[position:])
        if bare_open:
            old = bare_open.group(0)
            return BalanceFixAction(
                filepath, field_path, bare_open.group(1), old, f"{old})",
                position, position + len(old), "missing_close",
            )

    return None


def preview_balance_fixes(filepath: str) -> List[BalanceFixAction]:
    """Return Strong-code balance fixes without modifying ``filepath``."""
    path = Path(filepath)
    with path.open(encoding="utf-8") as file:
        data = json.load(file)

    actions: List[BalanceFixAction] = []

    def collect(value: object, field_path: str = "") -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                collect(child, f"{field_path}.{key}" if field_path else key)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                collect(child, f"{field_path}[{index}]")
        elif isinstance(value, str):
            for issue in check_balance(value):
                action = _action_for_issue(filepath, field_path, value, issue)
                if action:
                    actions.append(action)

    collect(data)
    return actions


def apply_balance_fixes(filepath: str, actions: List[BalanceFixAction]) -> FixResult:
    """Apply previously-previewed Strong-code balance fixes."""
    return apply_fixes(filepath, actions)


def validate_after_fix(filepath: str) -> tuple[bool, int]:
    """Return whether every string field in ``filepath`` is balanced."""
    with Path(filepath).open(encoding="utf-8") as file:
        data = json.load(file)

    issue_count = 0

    def collect(value: object) -> None:
        nonlocal issue_count
        if isinstance(value, dict):
            for child in value.values():
                collect(child)
        elif isinstance(value, list):
            for child in value:
                collect(child)
        elif isinstance(value, str):
            issue_count += len(check_balance(value))

    collect(data)
    return issue_count == 0, issue_count
