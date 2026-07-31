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


_CODE_RE = re.compile(_CODE)


def _stack_balance_issues(text: str):
    """Stack-based ASCII paren balance check across the whole field.

    Unlike a regex pattern match, this correctly understands nesting depth —
    a code sitting inside a legitimately nested group like
    ``(word, (translit) (G1234))`` is NOT flagged, since every '(' in that
    span has a matching ')' at the correct nesting level. Only a genuine
    mismatch (an unmatched '(' or ')') is reported, tagged with the
    character position it occurred at.
    """
    stack = []
    issues = []  # (pos, kind) where kind is 'unmatched_close' or 'unclosed_open'
    for i, ch in enumerate(text):
        if ch == "(":
            stack.append(i)
        elif ch == ")":
            if stack:
                stack.pop()
            else:
                issues.append((i, "unmatched_close"))
    for pos in stack:
        issues.append((pos, "unclosed_open"))
    return issues


def _actions_for_text(
    filepath: str, field_path: str, text: str
) -> List[BalanceFixAction]:
    """Return Strong-code balance repairs for one text field.

    Two independent checks, each scoped to Strong-code citations only:

    1. missing_open / missing_close — a code that has only one of its two
       parens at all, e.g. bare ``G1568)`` or ``(G1568`` with no closer.
       Unambiguous regardless of surrounding nesting.
    2. Genuine structural imbalance — resolved via the stack-based checker
       above rather than a flat regex, so a legitimately nested closing
       paren (real corpus pattern: ``(word, (translit) (code))``) is never
       mistaken for an extra/missing paren. A code is only reported here
       if the paren immediately after it is the specific unmatched
       position the stack identified.
    """
    actions = []
    occupied = set()

    simple_patterns = (
        ("missing_open", re.compile(rf"(?<!\()\b({_CODE})\)"), lambda code: f"({code})"),
        ("missing_close", re.compile(rf"\(({_CODE})(?![\d)])"), lambda code: f"({code})"),
    )
    for issue_type, pattern, replacement in simple_patterns:
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

    stack_issues = _stack_balance_issues(text)
    if stack_issues:
        unmatched_close_positions = {
            pos for pos, kind in stack_issues if kind == "unmatched_close"
        }
        for m in _CODE_RE.finditer(text):
            code = m.group(0)
            close_pos = m.end()
            if (
                close_pos in unmatched_close_positions
                and close_pos < len(text)
                and text[close_pos] == ")"
            ):
                span = (m.start(), close_pos + 1)
                if span not in occupied:
                    occupied.add(span)
                    old = text[span[0]:span[1]]
                    actions.append(
                        BalanceFixAction(
                            filepath, field_path, code, old, f"({code})",
                            span[0], span[1], "real_imbalance",
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
