"""balance_fixer.py — Fix parenthesis balance issues in Strong code patterns.

Uses the balance checker to identify issues, then applies fixes to balance
parentheses around Strong codes. Re-validates after fixes to confirm clean.

Fixes:
  - ((GXXXX)  → (GXXXX)   [double_open]
  - (GXXXX))  → (GXXXX)   [double_close]
  - GXXXX)    → (GXXXX)   [missing_open]
  - (GXXXX    → (GXXXX)   [missing_close]

Usage:
    from shared_validation.strong_balance_fixer import preview_balance_fixes, apply_balance_fixes

    # Preview what will change
    actions = preview_balance_fixes('discovery/es/passed_from_death_es_001.json')
    for a in actions:
        print(f"  {a.old:20s} → {a.new}")

    # Apply the fixes
    apply_balance_fixes('discovery/es/passed_from_death_es_001.json', actions)
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List, NamedTuple

from shared_validation.balance_checker import check_balance, BalanceIssue
from shared_validation.strong_applier import apply_fixes, FixResult


class BalanceFixAction(NamedTuple):
    """A single balance fix: replace `old` with `new` at a position."""

    filepath: str
    field_path: str
    code: str
    old: str
    new: str
    start: int
    end: int
    issue_type: str


def _fix_balance_issue(issue: BalanceIssue, text: str) -> str:
    """Apply a fix for a single balance issue.
    
    Returns the fixed text.
    """
    code = issue.code
    old_match = issue.match
    issue_type = issue.issue_type
    
    # Find the exact match in text at the position
    actual_match = text[issue.start:issue.end]
    
    if issue_type == "double_open":
        # ((GXXXX) → (GXXXX)
        # Remove one opening paren before the code
        new_match = actual_match.replace('((', '(', 1)
    elif issue_type == "double_close":
        # (GXXXX)) → (GXXXX)
        # Remove one closing paren after the code
        new_match = actual_match.replace('))', ')', 1)
    elif issue_type == "missing_open":
        # GXXXX) → (GXXXX)
        # Add opening paren before the code
        new_match = actual_match.replace(code, f'({code}', 1)
    elif issue_type == "missing_close":
        # (GXXXX → (GXXXX)
        # Add closing paren after the code
        new_match = actual_match.replace(code, f'{code})', 1)
    else:
        new_match = actual_match
    
    return text[:issue.start] + new_match + text[issue.end:]


def preview_balance_fixes(filepath: str) -> List[BalanceFixAction]:
    """Analyze a file and return all balance fix actions (preview, no changes)."""
    actions = []
    
    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)
    
    # Scan all text fields and check balance for each
    def _collect(obj, path_prefix: str = ""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                ctx_key = f"{path_prefix}.{k}" if path_prefix else k
                if isinstance(v, str):
                    # Check balance in this field
                    from shared_validation.balance_checker import check_balance
                    issues = check_balance(v)
                    for issue in issues:
                        # Determine the fix
                        actual_match = v[issue.start:issue.end]
                        
                        if issue.issue_type == "double_open":
                            new_match = actual_match.replace('((', '(', 1)
                        elif issue.issue_type == "double_close":
                            new_match = actual_match.replace('))', ')', 1)
                        elif issue.issue_type == "missing_open":
                            new_match = actual_match.replace(issue.code, f'({issue.code}', 1)
                        elif issue.issue_type == "missing_close":
                            new_match = actual_match.replace(issue.code, f'{issue.code})', 1)
                        else:
                            new_match = actual_match
                        
                        actions.append(BalanceFixAction(
                            filepath=filepath,
                            field_path=ctx_key,
                            code=issue.code,
                            old=actual_match,
                            new=new_match,
                            start=issue.start,
                            end=issue.end,
                            issue_type=issue.issue_type,
                        ))
                elif isinstance(v, (dict, list)):
                    _collect(v, ctx_key)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                _collect(item, f"{path_prefix}[{i}]")
    
    _collect(data)
    return actions


def apply_balance_fixes(filepath: str, actions: List[BalanceFixAction]) -> FixResult:
    """Apply balance fix actions to a file.

    Returns the full FixResult (applied AND failed counts) — see
    strong_fixer.apply_fixes for why `failed` must not be discarded.
    """
    if not actions:
        return FixResult(applied=0, failed=0, filepath=filepath)
    
    # Use the shared applier
    return apply_fixes(filepath, actions)


def validate_after_fix(filepath: str) -> tuple[bool, int]:
    """Validate a file after applying fixes.
    
    Returns:
        (is_clean, issue_count) - True if no balance issues remain
    """
    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)
    
    issues = []
    def _collect(obj, path_prefix: str = ""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                ctx_key = f"{path_prefix}.{k}" if path_prefix else k
                if isinstance(v, str):
                    issues.extend(check_balance(v))
                elif isinstance(v, (dict, list)):
                    _collect(v, ctx_key)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                _collect(item, f"{path_prefix}[{i}]")
    
    _collect(data)
    return (len(issues) == 0, len(issues))
