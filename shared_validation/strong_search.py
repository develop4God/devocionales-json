"""strong_search.py — Reusable phased search logic for Strong's number
patterns in corpus prose (discovery + encounters, every language).

Architecture: broadest search first, then filter layers to condense.

  Phase 0 — BROADEST search: catch ALL G/H + digits patterns
  Phase 1 — filter Phase 0 to only "Strong" prefix patterns
  Phase 2 — filter Phase 0 to bare codes (no "Strong" word)
  Phase 3 — all Phase 0 results (combined, no filtering)
  Phase 4 — resolve found codes to lexicon entries

The broad regex is the foundation — it catches everything. The phases are
FILTERS on top of Phase 0, not separate regexes. This way nothing is missed.

Usage:
    from shared_validation.strong_search import (
        find_strong_codes_phase0,
        find_strong_codes_phase1,
        find_strong_codes_phase2,
        find_strong_codes_phase3,
        resolve_strong_results,
        StrongSearchResult,
    )

    # Phase 0: broadest search (catches everything)
    results = find_strong_codes_phase0(text)

    # Phase 1: only "Strong" prefix patterns
    results = find_strong_codes_phase1(text)

    # Phase 2: only bare codes (no "Strong")
    results = find_strong_codes_phase2(text)

    # Phase 3: all results combined
    results = find_strong_codes_phase3(text)

    # Phase 4: resolve to lexicon entries
    from shared_validation.lexicon_source import StrongsLexiconSource
    lex = StrongsLexiconSource()
    resolved = resolve_strong_results(results, lex)
"""

from __future__ import annotations

import json
import re
from pathlib import Path
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
                      e.g. "(Strong G3327)" or "G3327" or "- G728)".
        start:        Character offset where `full_match` begins in `text`.
        end:          Character offset where `full_match` ends in `text`.
        context:      A snippet of surrounding text for human review.
        has_strong:   True if the match includes the word "Strong" (any case).
        field_path:   Dotted path to the field in the JSON, e.g. "cards[0].content".
    """
    code: str
    prefix: str
    number: str
    full_match: str
    start: int
    end: int
    context: str
    has_strong: bool
    field_path: str = ""


# ---------------------------------------------------------------------------
# Format config (strong_format.json) — single source of truth
# ---------------------------------------------------------------------------

_FORMAT_PATH = Path(__file__).parent / "strong_format.json"
_format_cache: Optional[dict] = None

# ---------------------------------------------------------------------------
# Whitelist config (strong_whitelist.json) — false positive exclusions
# ---------------------------------------------------------------------------

_WHITELIST_PATH = Path(__file__).parent / "strong_whitelist.json"
_whitelist_cache: Optional[dict] = None


def load_strong_format() -> dict:
    """Load the canonical Strong code format spec from strong_format.json.
    Cached after first load — the file never changes at runtime."""
    global _format_cache
    if _format_cache is None:
        with open(_FORMAT_PATH, encoding="utf-8") as f:
            _format_cache = json.load(f)
    return _format_cache


def load_whitelist() -> dict:
    """Load the whitelist of false positive patterns from strong_whitelist.json.
    Cached after first load — the file never changes at runtime."""
    global _whitelist_cache
    if _whitelist_cache is None:
        with open(_WHITELIST_PATH, encoding="utf-8") as f:
            _whitelist_cache = json.load(f)
    return _whitelist_cache


def is_excluded(result: StrongSearchResult) -> bool:
    """Check if a StrongSearchResult should be excluded as a false positive.
    
    Reads exclusion rules from strong_whitelist.json:
    - Exact codes to exclude (e.g., G1910 when it's part of LSG1910)
    - Pattern-based exclusions (e.g., LSG\\d{4} for Bible version codes)
    
    Args:
        result: A StrongSearchResult to check.
    
    Returns:
        True if the result should be excluded (is a false positive).
    """
    whitelist = load_whitelist()
    
    # Check exact code exclusions
    for exclusion in whitelist.get("exact_codes_to_exclude", []):
        if result.code == exclusion["code"]:
            return True
    
    # Check pattern-based exclusions
    for pattern_exclusion in whitelist.get("excluded_patterns", []):
        pattern = pattern_exclusion["pattern"]
        if re.search(pattern, result.full_match, re.IGNORECASE):
            return True
    
    return False


def is_correct_format(result: StrongSearchResult) -> bool:
    """Check if a StrongSearchResult is already in the canonical (NXXXX) format.

    Reads the rules from strong_format.json:
    - Prefix must be uppercase G or H
    - 1-5 digits (no zeros like H00)
    - Wrapped in parentheses: (GXXXX)
    - No "Strong" word
    """
    fmt = load_strong_format()
    # Check prefix is uppercase
    if fmt["case_sensitivity"]["prefix_must_be_uppercase"]:
        if result.prefix not in ("G", "H"):
            return False
    # Check digit range
    digit_count = len(result.number)
    if digit_count < fmt["digit_range"]["min"] or digit_count > fmt["digit_range"]["max"]:
        return False
    # Check no "Strong" word
    if result.has_strong:
        return False
    # Check wrapped in parens: the match must contain (CODE) as a substring
    # (trailing punctuation like (G3327). or (G3327): is OK — the code itself
    # is correctly wrapped, the punctuation belongs to the sentence)
    canonical = f"({result.code})"
    return canonical in result.full_match


# ---------------------------------------------------------------------------
# Phase 0 — BROADEST search: catch ALL G/H + digits patterns
# ---------------------------------------------------------------------------

# The broadest possible regex: any G/H (case insensitive) followed by 1-5 digits,
# with optional surrounding punctuation (parens, brackets, dashes, colons, spaces).
# This is the foundation — it catches EVERYTHING. The phases above filter it.
#
# Pattern breakdown:
#   [\s\(\[-]*           — optional leading whitespace, open parens, brackets, dashes
#   (?:Strong\s+)?       — optional "Strong" word (case insensitive)
#   ([GHgh])             — the letter prefix (G=Greek, H=Hebrew)
#   (\d{1,5})            — 1-5 digits
#   [\s\)\]:.\-]*        — optional trailing whitespace, close parens, brackets, colons, dots, dashes
_BROAD_RE = re.compile(
    r"[\s\(\[-]*(?:Strong\s+)?([GHgh])(\d{1,5})[\s\)\]:.\-]*",
    re.IGNORECASE,
)


def find_strong_codes_phase0(text: str, context_window: int = 40) -> List[StrongSearchResult]:
    """Phase 0: BROADEST search — catch ALL G/H + digits patterns in text.

    This is the foundation. It catches every possible Strong code pattern:
    - (Strong G3327), Strong G1568, (G3327), - G728), G728, (G3327)., etc.
    - Case insensitive: STRONG, Strong, strong, G, g, H, h

    Filters out false positives using strong_whitelist.json (e.g., LSG1910).

    Args:
        text: The prose text to search.
        context_window: Characters of surrounding context (default 40).

    Returns:
        List of StrongSearchResult, ordered by occurrence in text.
    """
    results: List[StrongSearchResult] = []
    for m in _BROAD_RE.finditer(text):
        prefix = m.group(1).upper()  # normalize to uppercase
        number = m.group(2)
        code = f"{prefix}{number}"
        start = m.start()
        end = m.end()
        ctx_start = max(0, start - context_window)
        ctx_end = min(len(text), end + context_window)
        context = text[ctx_start:ctx_end].replace("\n", " ")
        full_match = m.group(0)
        has_strong = "strong" in full_match.lower()
        result = StrongSearchResult(
            code=code,
            prefix=prefix,
            number=number,
            full_match=full_match,
            start=start,
            end=end,
            context=context,
            has_strong=has_strong,
        )
        # Filter out false positives using whitelist
        if not is_excluded(result):
            results.append(result)
    return results


# ---------------------------------------------------------------------------
# Phase 1 — Filter Phase 0 to only "Strong" prefix patterns
# ---------------------------------------------------------------------------

def find_strong_codes_phase1(text: str, context_window: int = 40) -> List[StrongSearchResult]:
    """Phase 1: Filter Phase 0 results to only matches that include the
    word "Strong" (any case) — e.g. "(Strong G3327)", "Strong G1568".

    Args:
        text: The prose text to search.
        context_window: Characters of surrounding context (default 40).

    Returns:
        List of StrongSearchResult where has_strong=True.
    """
    return [r for r in find_strong_codes_phase0(text, context_window) if r.has_strong]


# ---------------------------------------------------------------------------
# Phase 2 — Filter Phase 0 to bare codes (no "Strong" word)
# ---------------------------------------------------------------------------

def find_strong_codes_phase2(text: str, context_window: int = 40) -> List[StrongSearchResult]:
    """Phase 2: Filter Phase 0 results to only matches that do NOT include
    the word "Strong" — e.g. "(G3327)", "G728", "- G728)".

    Args:
        text: The prose text to search.
        context_window: Characters of surrounding context (default 40).

    Returns:
        List of StrongSearchResult where has_strong=False.
    """
    return [r for r in find_strong_codes_phase0(text, context_window) if not r.has_strong]


# ---------------------------------------------------------------------------
# Phase 3 — All results combined (same as Phase 0)
# ---------------------------------------------------------------------------

def find_strong_codes_phase3(text: str, context_window: int = 40) -> List[StrongSearchResult]:
    """Phase 3: All Strong code patterns in text — both "Strong" prefix
    patterns (Phase 1) and bare code patterns (Phase 2) — combined.

    This is the same as Phase 0 (the broadest search). Provided as a
    convenience alias for callers that want "everything".

    Args:
        text: The prose text to search.
        context_window: Characters of surrounding context (default 40).

    Returns:
        Combined list of StrongSearchResult, ordered by occurrence in text.
    """
    return find_strong_codes_phase0(text, context_window)


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
        phase: Which phase to use (0, 1, 2, or 3, default 3 for all).
        context_window: Passed through to the finder function.

    Returns:
        List of StrongSearchResult across all text fields in the file.
    """
    import json

    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)

    results: List[StrongSearchResult] = []
    # Scan ALL string fields in the file, not just prose fields.
    # This catches Strong codes in subtitles, greek_words, hebrew_words,
    # revelation_key, and any other field that might contain a code.
    text_fields = None  # None = scan all string fields

    def _collect(obj, path_prefix: str = ""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                ctx_key = f"{path_prefix}.{k}" if path_prefix else k
                if isinstance(v, str):
                    if phase == 0:
                        r = find_strong_codes_phase0(v, context_window)
                    elif phase == 1:
                        r = find_strong_codes_phase1(v, context_window)
                    elif phase == 2:
                        r = find_strong_codes_phase2(v, context_window)
                    else:
                        r = find_strong_codes_phase3(v, context_window)
                    # Attach field_path to each result
                    for result in r:
                        results.append(StrongSearchResult(
                            code=result.code,
                            prefix=result.prefix,
                            number=result.number,
                            full_match=result.full_match,
                            start=result.start,
                            end=result.end,
                            context=result.context,
                            has_strong=result.has_strong,
                            field_path=ctx_key,
                        ))
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
            - with_strong: count of matches that include "Strong"
            - without_strong: count of bare code matches
    """
    from collections import Counter

    total = len(results)
    code_counts = Counter(r.code for r in results)
    prefix_counts = Counter(r.prefix for r in results)
    codes_sorted = sorted(code_counts.keys(), key=lambda c: -code_counts[c])
    with_strong = sum(1 for r in results if r.has_strong)
    without_strong = total - with_strong

    return {
        "total": total,
        "unique_codes": dict(code_counts),
        "by_prefix": dict(prefix_counts),
        "codes_sorted": codes_sorted,
        "with_strong": with_strong,
        "without_strong": without_strong,
    }