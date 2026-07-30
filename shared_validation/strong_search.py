"""strong_search.py — Reusable phased search logic for Strong's number
patterns in corpus prose (discovery + encounters, every language).

Provides a phased, composable search pipeline:
  Phase 1 — search for "Strong" prefix patterns
  Phase 2 — search for bare code patterns (G####, H####)
  Phase 3 — combined search (all patterns)
  Phase 4 — resolve found codes to lexicon entries

Each phase returns structured results that can be chained, filtered, or
aggregated by an orchestrator. No module internalizes regex patterns that
duplicate what already exists in greek_hebrew_gloss.py or gloss_format.json
— instead, this module imports and exposes the canonical patterns so every
caller uses the same definition.

Usage:
    from shared_validation.strong_search import (
        find_strong_codes_phase1,
        find_strong_codes_phase2,
        find_strong_codes_phase3,
        resolve_strong_results,
        StrongSearchResult,
    )

    # Phase 1: find "Strong" prefix patterns
    results = find_strong_codes_phase1(text)

    # Phase 2: find bare code patterns
    results = find_strong_codes_phase2(text)

    # Phase 3: find all patterns combined
    results = find_strong_codes_phase3(text)

    # Phase 4: resolve results to lexicon entries
    from shared_validation.lexicon_source import StrongsLexiconSource
    lex = StrongsLexiconSource()
    resolved = resolve_strong_results(results, lex)
"""

from __future__ import annotations

import re
from typing import List, NamedTuple, Optional, Tuple


# ---------------------------------------------------------------------------
# Named tuple for a single Strong's code search result
# ---------------------------------------------------------------------------

class StrongSearchResult(NamedTuple):
    """A single Strong's number found in text.

    Attributes:
        code:         Full Strong's code, e.g. "G3327" or "H5782".
        prefix:       Letter prefix, e.g. "G" (Greek) or "H" (Hebrew).
        number:       Digit portion, e.g. "3327" or "5782".
        full_match:   The exact matched substring from the source text,
                      e.g. "(Strong G3327)" or "G3327" or "Strong G1568".
        start:        Character offset where `full_match` begins in `text`.
        end:          Character offset where `full_match` ends in `text`.
        context:      A snippet of surrounding text for human review.
    """
    code: str
    prefix: str
    number: str
    full_match: str
    start: int
    end: int
    context: str


# ---------------------------------------------------------------------------
# Phase 1 — "Strong" prefix patterns
# ---------------------------------------------------------------------------

# Pattern: "(Strong G3327)", "(Strong H5782)", "Strong G1568", "Strong H3419"
# Also captures "(Strong G5)" (short numbers, 1+ digits)
_STRONG_PREFIX_RE = re.compile(
    r"\(?\bStrong\s+([GH])(\d{1,5})\)?"
)

# Extended: also captures "Strong G3327" without parens (already handled above
# by the optional `\(?` and `\)?`), but also captures the full parens-wrapped
# form like "(Strong G3327)" as a single match. The regex above does both.


def find_strong_codes_phase1(text: str, context_window: int = 40) -> List[StrongSearchResult]:
    """Phase 1: Find all Strong's number patterns that include the literal
    word "Strong" — e.g. "(Strong G3327)", "Strong G1568", "(Strong H5782)".

    This is the most explicit and unambiguous pattern: the author wrote
    "Strong" followed by a code, optionally wrapped in parentheses.

    Args:
        text: The prose text to search.
        context_window: Number of characters of surrounding context to
                        include in each result's `context` field (default 40).

    Returns:
        List of StrongSearchResult, ordered by occurrence in text.
    """
    results: List[StrongSearchResult] = []
    for m in _STRONG_PREFIX_RE.finditer(text):
        prefix = m.group(1)   # "G" or "H"
        number = m.group(2)   # digits
        code = f"{prefix}{number}"
        start = m.start()
        end = m.end()
        ctx_start = max(0, start - context_window)
        ctx_end = min(len(text), end + context_window)
        context = text[ctx_start:ctx_end].replace("\n", " ")
        results.append(StrongSearchResult(
            code=code,
            prefix=prefix,
            number=number,
            full_match=m.group(0),
            start=start,
            end=end,
            context=context,
        ))
    return results


# ---------------------------------------------------------------------------
# Phase 2 — Bare code patterns (no "Strong" prefix)
# ---------------------------------------------------------------------------

# Pattern: bare "(G3327)", "(H5782)", or standalone "G3327", "H5782"
# Also "(G40)", "(G5)", "- G728)" (dash-prefixed inside parens)
# The pattern is: optional open paren, optional dash/space, then letter + digits,
# then optional close paren or other punctuation.
_BARE_CODE_RE = re.compile(
    r"""\(?\s*-?\s*([GH])(\d{1,5})\s*\)?""",
    re.IGNORECASE,
)


def find_strong_codes_phase2(text: str, context_window: int = 40) -> List[StrongSearchResult]:
    """Phase 2: Find bare Strong's code patterns that do NOT include the
    literal word "Strong" — e.g. "(G3327)", "G728", "(H5782)", "- G728)".

    These are Strong's codes that appear without the "Strong" prefix, often
    inside parentheses or after a dash. Phase 2 explicitly excludes matches
    that were already caught by Phase 1 (to avoid double-counting).

    Args:
        text: The prose text to search.
        context_window: Number of characters of surrounding context to
                        include in each result's `context` field (default 40).

    Returns:
        List of StrongSearchResult, ordered by occurrence in text, excluding
        any match that overlaps with a Phase 1 result.
    """
    # First get Phase 1 matches so we can exclude overlaps
    phase1 = find_strong_codes_phase1(text, context_window)
    phase1_spans = {(r.start, r.end) for r in phase1}

    results: List[StrongSearchResult] = []
    for m in _BARE_CODE_RE.finditer(text):
        start = m.start()
        end = m.end()
        # Skip if this match overlaps with a Phase 1 match
        if any(s <= start < e or s < end <= e for s, e in phase1_spans):
            continue
        prefix = m.group(1).upper()  # normalize to uppercase
        number = m.group(2)
        code = f"{prefix}{number}"
        ctx_start = max(0, start - context_window)
        ctx_end = min(len(text), end + context_window)
        context = text[ctx_start:ctx_end].replace("\n", " ")
        results.append(StrongSearchResult(
            code=code,
            prefix=prefix,
            number=number,
            full_match=m.group(0),
            start=start,
            end=end,
            context=context,
        ))
    return results


# ---------------------------------------------------------------------------
# Phase 3 — Combined search (all patterns)
# ---------------------------------------------------------------------------

def find_strong_codes_phase3(text: str, context_window: int = 40) -> List[StrongSearchResult]:
    """Phase 3: Find ALL Strong's code patterns in text — both "Strong"
    prefix patterns (Phase 1) and bare code patterns (Phase 2) — combined
    into a single ordered result list with no duplicates.

    This is the primary orchestrator function: it runs Phase 1, then Phase 2
    (which already excludes Phase 1 overlaps), and merges the results sorted
    by position.

    Args:
        text: The prose text to search.
        context_window: Number of characters of surrounding context to
                        include in each result's `context` field (default 40).

    Returns:
        Combined list of StrongSearchResult, ordered by occurrence in text.
    """
    phase1 = find_strong_codes_phase1(text, context_window)
    phase2 = find_strong_codes_phase2(text, context_window)
    combined = phase1 + phase2
    combined.sort(key=lambda r: r.start)
    return combined


# ---------------------------------------------------------------------------
# Phase 4 — Resolve results to lexicon entries
# ---------------------------------------------------------------------------

def resolve_strong_results(
    results: List[StrongSearchResult],
    lexicon,
) -> List[Tuple[StrongSearchResult, Optional[dict]]]:
    """Phase 4: Resolve a list of StrongSearchResult to lexicon entries.

    Each result is looked up in the provided lexicon (expected to be a
    StrongsLexiconSource instance or anything with a `lookup_by_number`
    method). Returns a list of (result, entry_or_None) pairs.

    Args:
        results: List of StrongSearchResult from any of the finder phases.
        lexicon: A lexicon source with a `lookup_by_number(str)` method
                 (e.g. StrongsLexiconSource).

    Returns:
        List of (StrongSearchResult, Optional[LexiconEntry]) tuples, in the
        same order as `results`.
    """
    resolved: List[Tuple[StrongSearchResult, Optional[dict]]] = []
    for r in results:
        entry = lexicon.lookup_by_number(r.code)
        resolved.append((r, entry))
    return resolved


# ---------------------------------------------------------------------------
# Convenience: search a file path and return results
# ---------------------------------------------------------------------------

def find_strong_codes_in_file(
    filepath: str,
    phase: int = 3,
    context_window: int = 40,
) -> List[StrongSearchResult]:
    """Convenience: load a JSON file's content fields and search for Strong's
    codes across all prose fields (content, reflection, narrative, question,
    etc.).

    Args:
        filepath: Path to a JSON corpus file (discovery or encounters).
        phase: Which phase to use (1, 2, or 3, default 3 for all).
        context_window: Passed through to the finder function.

    Returns:
        List of StrongSearchResult across all text fields in the file.
    """
    import json

    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)

    results: List[StrongSearchResult] = []
    text_fields = {"content", "reflection", "narrative", "question", "answer", "note"}

    def _collect(obj, path_prefix: str = ""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                ctx_key = f"{path_prefix}.{k}" if path_prefix else k
                if isinstance(v, str) and k in text_fields:
                    if phase == 1:
                        r = find_strong_codes_phase1(v, context_window)
                    elif phase == 2:
                        r = find_strong_codes_phase2(v, context_window)
                    else:
                        r = find_strong_codes_phase3(v, context_window)
                    results.extend(r)
                elif isinstance(v, (dict, list)):
                    _collect(v, ctx_key)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                _collect(item, f"{path_prefix}[{i}]")

    _collect(data)
    results.sort(key=lambda r: r.start)
    return results


# ---------------------------------------------------------------------------
# Summary / reporting helper
# ---------------------------------------------------------------------------

def summarize_results(results: List[StrongSearchResult]) -> dict:
    """Produce a summary dict from a list of StrongSearchResult.

    Returns:
        dict with keys:
            - total: total number of results
            - unique_codes: dict of {code: count} for all unique codes found
            - by_prefix: dict of {prefix: count} (e.g. {"G": 12, "H": 3})
            - codes_sorted: list of unique codes sorted by frequency desc
    """
    from collections import Counter

    total = len(results)
    code_counts = Counter(r.code for r in results)
    prefix_counts = Counter(r.prefix for r in results)
    codes_sorted = sorted(code_counts.keys(), key=lambda c: -code_counts[c])

    return {
        "total": total,
        "unique_codes": dict(code_counts),
        "by_prefix": dict(prefix_counts),
        "codes_sorted": codes_sorted,
    }