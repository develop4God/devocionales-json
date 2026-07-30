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
from shared_validation.strong_scanner import scan_file, get_field_text
from shared_validation.strong_applier import apply_fixes as _apply_fixes_shared


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
    
    # Use the shared applier
    result = _apply_fixes_shared(filepath, fixes)
    return result.applied
