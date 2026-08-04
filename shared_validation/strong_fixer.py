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
from typing import NamedTuple

from shared_validation.strong_applier import (
    FixResult,
    _get_field,
)
from shared_validation.strong_applier import (
    apply_fixes as _apply_fixes_shared,
)
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


def _consumes_an_outer_wrapper_close(
    field_text: str, match_start: int, match_end: int
) -> bool:
    """Check whether the ')' this match ends on actually belongs to an
    OUTER paren opened earlier in the field, before `match_start` — rather
    than to the match's own code citation.

    Real corpus shape: ``(Word - Strong G4977)`` or ``(Word - G4977)`` — a
    single wrapper opened before the word, dash-separated from the code,
    with only one closing paren shared by both the word and the code. The
    broad regex's match (e.g. ``- Strong G4977)`` or ``G4977)``) starts
    AFTER that opening '(', so naively replacing the whole match with
    ``(G4977)`` inserts a second, unrelated opening paren while reusing the
    file's only closing paren for it — leaving the original wrapper's own
    '(' permanently unclosed. Detected via the same stack-based balance
    scan used by strong_balance_fixer: if position `match_end - 1` (the
    match's own trailing ')') is the position the stack scan resolves as
    closing a '(' that occurs BEFORE `match_start`, this match must not
    consume that ')' — the caller should insert ``(CODE)`` immediately
    before it instead, leaving the outer wrapper's closer in place.
    """
    if not field_text[match_start:match_end].endswith(")"):
        return False
    close_pos = match_end - 1
    stack: list[int] = []
    for i, ch in enumerate(field_text):
        if i >= close_pos:
            break
        if ch == "(":
            stack.append(i)
        elif ch == ")" and stack:
            stack.pop()
    # Stopped scanning just before the match's own trailing ')'. Any
    # position left on the stack is a '(' still unclosed at that point —
    # i.e. the one `close_pos` is actually about to close. If it opened
    # before match_start, it belongs to an outer wrapper, not this match.
    return bool(stack) and stack[-1] < match_start


def preview_file(filepath: str) -> list[FixAction]:
    """Analyze a file and return all fix actions (preview, no changes made)."""
    actions = []

    # Use the new search logic — scans ALL string fields in the file
    results = find_strong_codes_in_file(filepath, phase=3)

    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)

    field_text_cache: dict = {}

    for r in results:
        # Use the format checker from strong_format.json
        if is_correct_format(r):
            status = "skip"
        else:
            status = "fix"

        # r.full_match includes leading/trailing whitespace captured by the
        # broad regex (see strong_search._BROAD_RE), and r.start/r.end are
        # offsets for that full (unstripped) match. FixAction.old must stay
        # in sync with whichever span start/end point at, or the applier's
        # `text[start:end] == old` check silently fails and no fix lands.
        # Strip the match but shrink the offsets by the same trimmed amount
        # so start/end keep pointing at exactly `old`.
        stripped = r.full_match.strip()
        left_trim = r.full_match.find(stripped)
        fixed_start = r.start + left_trim
        fixed_end = fixed_start + len(stripped)

        canonical = f"({r.code})"

        if status == "fix" and r.field_path not in field_text_cache:
            field_text_cache[r.field_path] = _get_field(data, r.field_path)
        field_text = field_text_cache.get(r.field_path)

        if (
            status == "fix"
            and field_text is not None
            and _consumes_an_outer_wrapper_close(field_text, fixed_start, fixed_end)
        ):
            # Don't consume the outer wrapper's own closing paren — insert
            # the canonical citation immediately before it instead, so that
            # paren survives to close the wrapper it always belonged to.
            old = field_text[fixed_start : fixed_end - 1]
            new = f"{canonical}"
            actions.append(
                FixAction(
                    filepath=filepath,
                    field_path=r.field_path if hasattr(r, "field_path") else "",
                    code=r.code,
                    old=old,
                    new=new,
                    start=fixed_start,
                    end=fixed_end - 1,
                    status=status,
                )
            )
            continue

        actions.append(
            FixAction(
                filepath=filepath,
                field_path=r.field_path if hasattr(r, "field_path") else "",
                code=r.code,
                old=stripped,
                new=canonical,
                start=fixed_start,
                end=fixed_end,
                status=status,
            )
        )

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


def apply_fixes(filepath: str, actions: list[FixAction]) -> FixResult:
    """Apply fix actions to a file.

    Returns the full FixResult (applied AND failed counts) — callers must
    not discard `failed`. A fix that fails to apply (its recorded `old`
    text no longer matches the file, e.g. from a stale scan or a
    conflicting concurrent edit) is a silent data-loss risk if the
    failure count isn't surfaced somewhere a human can see it.
    """
    fixes = [a for a in actions if a.status == "fix" and a.filepath == filepath]
    if not fixes:
        return FixResult(applied=0, failed=0, filepath=filepath)

    # Use the shared applier
    return _apply_fixes_shared(filepath, fixes)
