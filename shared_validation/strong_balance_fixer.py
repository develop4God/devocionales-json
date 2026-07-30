"""Preview and apply Strong-code parenthesis fixes.

This module keeps the established Strong-code repair workflow. It only
creates a fix for a malformed ``(G####)`` or ``(H####)`` citation and never
changes unrelated prose punctuation. Generic parenthesis validation belongs
to the post-fix diff check in :mod:`gap_check`.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List, NamedTuple

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


def _actions_for_text(
    filepath: str, field_path: str, text: str
) -> List[BalanceFixAction]:
    """Return Strong-pattern repairs for one text field."""
    patterns = (
        ("double_open", re.compile(rf"\(\(({_CODE})\)"), lambda code: f"({code})"),
        ("double_close", re.compile(rf"\(({_CODE})\)\)"), lambda code: f"({code})"),
        ("missing_open", re.compile(rf"(?<!\()\b({_CODE})\)"), lambda code: f"({code})"),
        ("missing_close", re.compile(rf"\(({_CODE})(?![\d)])"), lambda code: f"({code})"),
    )
    actions = []
    occupied = set()
    for issue_type, pattern, replacement in patterns:
        for match in pattern.finditer(text):
            span = (match.start(), match.end())
            if span in occupied:
                continue
            occupied.add(span)
            code = match.group(1)
            actions.append(
                BalanceFixAction(
                    filepath, field_path, code, match.group(0), replacement(code),
                    match.start(), match.end(), issue_type,
                )
            )
    return actions


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
            actions.extend(preview_balance_fixes_for_text(filepath, field_path, value))

    collect(data)
    return actions


def preview_balance_fixes_for_text(
    filepath: str, field_path: str, text: str
) -> List[BalanceFixAction]:
    """Preview Strong-code balance repairs for one already-loaded field.

    This lets the read-only diff checker inspect the text *after* simulated
    Strong fixes without writing a temporary JSON file.
    """
    actions = []
    return _actions_for_text(filepath, field_path, text)


def apply_balance_fixes(filepath: str, actions: List[BalanceFixAction]) -> FixResult:
    """Apply previously-previewed Strong-code balance fixes."""
    return apply_fixes(filepath, actions)


def validate_after_fix(filepath: str) -> tuple[bool, int]:
    """Return whether any Strong-pattern repair remains after fixing."""
    remaining = preview_balance_fixes(filepath)
    return not remaining, len(remaining)
