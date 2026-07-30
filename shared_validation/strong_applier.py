"""applier.py — Shared fix application logic for all fixers.

This is the SINGLE SOURCE OF TRUTH for applying fixes to JSON files.
Both strong_fixer and balance_fixer use this to eliminate duplication.

Usage:
    from shared_validation.strong_applier import apply_fixes, FixResult

    result = apply_fixes(filepath, actions)
    print(f"Applied {result.applied} fixes")
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List, NamedTuple, Dict, Tuple


class FixResult(NamedTuple):
    """Result of applying fixes to a file.
    
    Attributes:
        applied: Number of fixes successfully applied
        failed: Number of fixes that failed (text didn't match)
        filepath: Path to the file that was modified
    """
    applied: int
    failed: int
    filepath: str


def _get_field(data, field_path: str):
    """Navigate a dotted path like 'cards[0].content' to get the value."""
    parts = re.split(r'[.\[\]]+', field_path)
    parts = [p for p in parts if p]
    current = data
    for part in parts:
        if isinstance(current, dict):
            current = current[part]
        elif isinstance(current, list):
            current = current[int(part)]
    return current


def _set_field(data, field_path: str, value):
    """Set a value at a dotted path like 'cards[0].content'."""
    parts = re.split(r'[.\[\]]+', field_path)
    parts = [p for p in parts if p]
    current = data
    for i, part in enumerate(parts[:-1]):
        if isinstance(current, dict):
            current = current[part]
        elif isinstance(current, list):
            current = current[int(part)]
    last = parts[-1]
    if isinstance(current, dict):
        current[last] = value
    elif isinstance(current, list):
        current[int(last)] = value


def apply_fixes(filepath: str, actions: List[NamedTuple]) -> FixResult:
    """Apply fix actions to a file.
    
    This is the SINGLE IMPLEMENTATION for applying fixes.
    Both strong_fixer and balance_fixer should use this.
    
    Args:
        filepath: Path to the JSON file to modify
        actions: List of fix actions (FixAction or BalanceFixAction)
        
    Returns:
        FixResult with counts of applied/failed fixes
    """
    if not actions:
        return FixResult(applied=0, failed=0, filepath=filepath)
    
    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)
    
    # Group fixes by field path, reverse order so positions don't shift
    from collections import defaultdict
    by_field: Dict[str, List] = defaultdict(list)
    for a in actions:
        by_field[a.field_path].append(a)
    
    applied = 0
    failed = 0
    
    for field_path, field_fixes in by_field.items():
        text = _get_field(data, field_path)
        # Sort in reverse position order so edits don't shift positions
        for a in sorted(field_fixes, key=lambda x: -x.start):
            if text[a.start:a.end] == a.old:
                text = text[:a.start] + a.new + text[a.end:]
                applied += 1
            else:
                failed += 1
        _set_field(data, field_path, text)
    
    # Write back
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return FixResult(
        applied=applied,
        failed=failed,
        filepath=filepath
    )


def apply_fixes_to_text(text: str, actions: List[NamedTuple], inplace: bool = False) -> Tuple[str, int, int]:
    """Apply fixes to a text string (without touching the file).
    
    Useful for testing or when you need to modify text before writing.
    
    Args:
        text: The text to modify
        actions: List of fix actions
        inplace: If True, modify text in place (default: False, return new text)
        
    Returns:
        Tuple of (modified_text, applied_count, failed_count)
    """
    if not actions:
        return (text, 0, 0)
    
    # Sort in reverse position order so edits don't shift positions
    sorted_actions = sorted(actions, key=lambda x: -x.start)
    
    applied = 0
    failed = 0
    
    for a in sorted_actions:
        if text[a.start:a.end] == a.old:
            text = text[:a.start] + a.new + text[a.end:]
            applied += 1
        else:
            failed += 1
    
    return (text, applied, failed)
