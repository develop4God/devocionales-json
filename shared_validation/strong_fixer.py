"""strong_fixer.py — Preview and fix Strong code patterns in corpus files.

The fix normalizes all Strong code formats to `(CODE)`:
  (Strong G3327) → (G3327)
  Strong G1568   → (G1568)
  - G728)        → (G728)
  G728           → (G728)

Usage:
    from shared_validation.strong_fixer import preview_file, apply_fixes

    # Preview what will change
    actions = preview_file('discovery/es/passed_from_death_es_001.json')
    for a in actions:
        print(f"  {a.old:20s} → {a.new}")

    # Apply the fixes
    apply_fixes('discovery/es/passed_from_death_es_001.json', actions)
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import List, NamedTuple, Optional

from shared_validation.strong_search import (
    find_strong_codes_in_file,
    is_correct_format,
)


class FixAction(NamedTuple):
    """A single fix: replace `old` with `new` at a position in a field."""

    filepath: str
    field_path: str  # e.g. "cards[0].content"
    code: str
    old: str  # the original matched text
    new: str  # the canonical replacement: (CODE)
    start: int
    end: int
    status: str  # "fix" or "skip"


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


def preview_file(filepath: str) -> List[FixAction]:
    """Analyze a file and return all fix actions (preview, no changes made)."""
    actions = []

    # Use the new search logic — scans ALL string fields in the file
    results = find_strong_codes_in_file(filepath, phase=3)

    for r in results:
        # Use the format checker from strong_format.json
        if is_correct_format(r):
            status = "skip"
        else:
            status = "fix"

        canonical = f"({r.code})"
        actions.append(FixAction(
            filepath=filepath,
            field_path=r.field_path if hasattr(r, 'field_path') else "",
            code=r.code,
            old=r.full_match.strip(),
            new=canonical,
            start=r.start,
            end=r.end,
            status=status,
        ))

    return actions


def preview_family(study_id: str, content_type: str = "discovery") -> dict:
    """Preview fixes across all files in a family (all language versions).

    Returns {lang: [FixAction, ...]} for each language that has fixes.
    """
    from shared_validation.family_resolver import (
        _resolve_discovery_family,
        _resolve_encounters_family,
    )

    resolver = {
        "discovery": _resolve_discovery_family,
        "encounters": _resolve_encounters_family,
    }.get(content_type)

    if not resolver:
        return {}

    family = resolver(study_id)
    if not family:
        return {}

    result = {}
    for lang, fp in sorted(family.items()):
        actions = preview_file(str(fp))
        fixes = [a for a in actions if a.status == "fix"]
        if fixes:
            result[lang] = fixes
    return result


def apply_fixes(filepath: str, actions: List[FixAction]) -> int:
    """Apply fix actions to a file. Returns number of fixes applied."""
    fixes = [a for a in actions if a.status == "fix" and a.filepath == filepath]
    if not fixes:
        return 0

    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)

    # Group fixes by field path, reverse order so positions don't shift
    from collections import defaultdict
    by_field = defaultdict(list)
    for a in fixes:
        by_field[a.field_path].append(a)

    count = 0
    for field_path, field_fixes in by_field.items():
        text = _get_field(data, field_path)
        # Sort in reverse position order so edits don't shift positions
        for a in sorted(field_fixes, key=lambda x: -x.start):
            if text[a.start:a.end] == a.old:
                text = text[:a.start] + a.new + text[a.end:]
                count += 1
        _set_field(data, field_path, text)

    # Write back
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return count