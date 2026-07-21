"""scripture_check.py — validates that a stored Bible reference is a real,
resolvable citation and that its stored verse text matches what that
reference actually points to.

Reuses devocionales_scripts/verse_resolver.py (VerseResolver, parse_en_ref,
fetch_text), which is already trusted at generation time — this module
never re-implements reference parsing or verse lookup, only wires those
existing pieces into the validation pipelines.

Four single-purpose pieces:
  - find_scripture_pairs()      — pure extraction (recursive walk, no I/O)
  - ScriptureValidator          — owns/caches one VerseResolver per (lang, bible_version)
  - validate_pair()             — EN file: resolve + fuzzy match
  - validate_translated_pair()  — non-EN file: resolve via its EN sibling, fuzzy match

Note on scope: every encounter/discovery file has an EN version plus 9
translated siblings, each storing the SAME verse per card (see
validate_cross_translation's card-count/order/type parity gate — cards
across languages are already guaranteed to align by position). So a
translated card's reference never needs to be parsed as native-language
text at all: resolve the *EN sibling's* reference (parse_en_ref + the EN
bible_books.json SOT — the exact mechanism VerseResolver.resolve() already
uses), then fetch that same book/chapter/verse from the *target-language*
DB via fetch_text(). This avoids reverse-parsing native book names in 9
different scripts/orthographies, which is a fundamentally harder, more
error-prone problem than reusing the citation the corpus already has in
English.
"""

import json
import os
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from devocionales_scripts.verse_resolver import VerseResolver, fetch_text, parse_en_ref

# ─────────────────────────────────────────────────────────────────────────────
# CI GATING
# ─────────────────────────────────────────────────────────────────────────────
#
# Phase D scans every scripture reference in the ENTIRE corpus (2000+ pairs
# across 10 languages) on every run — a full-corpus audit appropriate for a
# CI gate, not a fast per-file feedback loop for daily content editing.
# Callers should skip this phase locally and only run it where CI=true is
# set, which GitHub Actions (and most other CI providers) already set
# automatically with no workflow-file changes needed.

def scripture_validation_enabled() -> bool:
    """True only when running in CI (CI env var set, as GitHub Actions and
    most CI providers do automatically). Callers use this to skip Phase D
    during local/daily-work validator runs."""
    return os.environ.get("CI", "").lower() in ("1", "true", "yes")


# ─────────────────────────────────────────────────────────────────────────────
# VERSIFICATION EXCEPTIONS
# ─────────────────────────────────────────────────────────────────────────────

_VERSIFICATION_EXCEPTIONS_PATH = Path(__file__).parent / "versification_exceptions.json"
_versification_exceptions_cache: Optional[dict] = None


def _load_versification_exceptions() -> dict:
    """Load and cache versification_exceptions.json: a small, hand-verified
    list of known cross-edition chapter/verse shifts (see that file's own
    _comment for what belongs in it and what doesn't). Loaded once per
    process; callers never mutate the returned dict."""
    global _versification_exceptions_cache
    if _versification_exceptions_cache is None:
        with open(_VERSIFICATION_EXCEPTIONS_PATH, encoding="utf-8") as f:
            data = json.load(f)
        _versification_exceptions_cache = {
            (e["en_reference"], e["bible_version"]): e for e in data["exceptions"]
        }
    return _versification_exceptions_cache


def _find_versification_exception(en_reference: str, bible_version: str) -> Optional[dict]:
    return _load_versification_exceptions().get((en_reference, bible_version))


# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────

# Jaccard token-overlap ratio below which stored verse_text is flagged as a
# possible mismatch against the resolved DB text. Tunable — see the issue's
# "Rollout" section: start permissive, tighten once real-corpus noise is
# reviewed. Merged consecutive-verse blocks (this project's own editorial
# convention) still share the large majority of their tokens with the sum
# of the individual verses, so 0.7 comfortably separates "legitimately the
# same verse(s), reformatted" from "wrong verse entirely."
FUZZY_MATCH_THRESHOLD = 0.7

# {reference-field-name: verse-text-field-name} pairs this module looks for
# on any dict encountered during the walk. Covers scripture_moment cards
# (verse_reference/verse_text) and every other reference+text shape used
# elsewhere in the corpus (key_verse, completion_verse, scripture_anchor,
# scripture_connections, scripture_passage entries) — all of which use
# reference/text.
_PAIR_FIELD_NAMES = (
    ("reference", "verse_text"),
    ("verse_reference", "verse_text"),
    ("reference", "text"),
)

_WHITESPACE_RE = re.compile(r"\s+")
_SMART_QUOTES = str.maketrans({
    "“": '"', "”": '"',  # “ ”
    "‘": "'", "’": "'",  # ‘ ’
})


# ─────────────────────────────────────────────────────────────────────────────
# EXTRACTION
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ScriptureRef:
    """One {reference, verse_text} pair found in a parsed card/file dict."""
    reference: str
    verse_text: str
    path: str  # e.g. "cards[2].scripture_moment.reference"


def find_scripture_pairs(data: dict) -> list[ScriptureRef]:
    """Recursively walk a parsed card/file dict, collecting every
    {reference, verse_text} or {verse_reference, verse_text} pair (and the
    reference/text shape used by key_verse, scripture_connections, etc.),
    each with a path string for reporting.

    Mirrors the recursive-walk pattern of discovery's _check_key_parity
    (validate_discovery.py) for style consistency across shared_validation.
    Pure extraction only — no resolving, no I/O.
    """
    pairs: list[ScriptureRef] = []
    _walk(data, "", pairs)
    return pairs


def _walk(obj, path: str, pairs: list) -> None:
    if isinstance(obj, dict):
        for ref_key, text_key in _PAIR_FIELD_NAMES:
            ref_val = obj.get(ref_key)
            text_val = obj.get(text_key)
            if isinstance(ref_val, str) and ref_val.strip() and \
               isinstance(text_val, str) and text_val.strip():
                ref_path = f"{path}.{ref_key}" if path else ref_key
                pairs.append(ScriptureRef(reference=ref_val, verse_text=text_val, path=ref_path))
                break  # a dict matches at most one pair-shape; don't double-count
        for k, v in obj.items():
            _walk(v, f"{path}.{k}" if path else k, pairs)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _walk(v, f"{path}[{i}]", pairs)


# ─────────────────────────────────────────────────────────────────────────────
# MATCHING
# ─────────────────────────────────────────────────────────────────────────────

def _normalize(text: str) -> str:
    """Strip punctuation-adjacent whitespace, collapse internal whitespace,
    unify smart/straight quotes, and apply Unicode NFC normalization —
    two visually-identical Arabic words can encode the same combining
    diacritics (fatha/shadda) in a different codepoint order, which
    compares as unequal without this (found via nicodemus_ar_001.json:
    stored 'لأَنَّهُ' vs. resolved 'لأَنَّهُ' rendered identically but
    NFC-normalized to different byte sequences pre-fix) — so formatting
    differences, not content differences, never affect the token-overlap
    ratio."""
    text = unicodedata.normalize("NFC", text)
    text = text.translate(_SMART_QUOTES)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text


# CJK Unified Ideographs (+ Ext-A) and Hiragana/Katakana — scripts written
# without whitespace between words, where a whitespace .split() collapses
# an entire verse into one token and always compares as 0% overlap
# regardless of content (found via peter_water_zh_001.json / _ja_001.json:
# stored and resolved text were the same verse, differing only by quote
# marks, yet scored 0%). Any text containing one of these characters is
# tokenized by individual character instead of by whitespace-split word.
_CJK_RE = re.compile(r"[぀-ヿ㐀-䶿一-鿿]")


def _tokenize(text: str) -> set[str]:
    normalized = _normalize(text)
    if _CJK_RE.search(normalized):
        return set(normalized.replace(" ", ""))
    return set(normalized.lower().split())


def jaccard_similarity(a: str, b: str) -> float:
    """Token-overlap ratio of two strings' whitespace-split token sets.
    1.0 = identical token sets, 0.0 = no overlap. Two empty strings are
    treated as a perfect match (nothing to compare); one empty and one
    non-empty is a total mismatch."""
    tokens_a, tokens_b = _tokenize(a), _tokenize(b)
    if not tokens_a and not tokens_b:
        return 1.0
    if not tokens_a or not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / len(tokens_a | tokens_b)


# ─────────────────────────────────────────────────────────────────────────────
# FINDING
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Finding:
    """One validation result for a ScriptureRef. kind distinguishes the two
    failure modes the issue calls out — both WARNING-only in this initial
    rollout (see module docstring / issue Rollout section)."""
    kind: str  # "resolution_failed" | "text_mismatch"
    ref: ScriptureRef
    message: str


def validate_pair(ref: ScriptureRef, resolver: VerseResolver) -> Optional[Finding]:
    """Resolve `ref.reference` (must be an English reference) via `resolver`
    and compare against `ref.verse_text`. Returns a Finding describing
    what's wrong, or None if the pair is clean (resolves, and text
    fuzzy-matches above threshold). Use this for EN files; use
    validate_translated_pair() for non-EN files.

    Never auto-fails on a fuzzy mismatch alone — the caller decides how to
    report it (this module always returns WARNING-severity findings for
    both failure kinds, per the issue's initial-rollout scope).
    """
    cita, texto, error = resolver.resolve(ref.reference)

    if error is not None:
        return Finding(
            kind="resolution_failed",
            ref=ref,
            message=f"'{ref.path}': could not resolve reference '{ref.reference}' — {error}",
        )

    return _compare_text(ref, texto)


def validate_translated_pair(
    en_ref: ScriptureRef, native_ref: ScriptureRef, native_resolver: VerseResolver,
    bible_version: Optional[str] = None,
) -> Optional[Finding]:
    """Validate a translated card's stored verse_text against its EN
    sibling card's reference — the corpus guarantees cards align 1:1 by
    position across languages (see validate_cross_translation's parity
    gate), so `en_ref` and `native_ref` are always the same verse.

    Resolves `en_ref.reference` the same way VerseResolver.resolve() does
    internally (parse_en_ref + the EN books SOT via native_resolver.books_sot,
    which is loaded from the same shared SOT regardless of which DB the
    resolver wraps), then fetches that book/chapter/verse from
    `native_resolver`'s own DB — i.e. the target language's Bible, not
    English. This never parses `native_ref.reference` itself; it's treated
    as a citation label only, not a lookup key.

    If `bible_version` has a registered VERSIFICATION_EXCEPTIONS entry for
    this en_reference, that entry's target chapter/verse is used from the
    start rather than the EN-parsed address — covers both cases where a
    target edition splits chapters/verses differently at this exact verse:
    the EN address doesn't exist at all in the target (e.g. KJV Jonah 1:17
    == LSG1910 Jonas 2:1, since LSG1910's chapter 1 ends at verse 16), and
    the subtler case where the EN address DOES exist in the target but
    holds different content because the shift happens mid-chapter (e.g.
    KJV Psalm 18:16 == LSG1910/LU17 Psalm 18:17 — both editions have a
    verse 16, just not the same one, so a plain "did the lookup fail"
    check would silently compare against the wrong verse instead of
    catching the mismatch). Every entry there was hand-verified against
    its DB; this never guesses a shift. Falls back to the EN-parsed
    address when no exception is registered, or reports a resolution
    failure if that address doesn't exist either.
    """
    parsed = parse_en_ref(en_ref.reference)
    if parsed is None:
        return Finding(
            kind="resolution_failed",
            ref=native_ref,
            message=f"'{native_ref.path}': EN sibling reference '{en_ref.reference}' could not be parsed",
        )

    book_en, chapter, v_start, v_end = parsed
    book_number = native_resolver.books_sot.get(book_en)
    if book_number is None:
        return Finding(
            kind="resolution_failed",
            ref=native_ref,
            message=f"'{native_ref.path}': EN sibling book '{book_en}' unknown in bible_books.json SOT",
        )

    exception = _find_versification_exception(en_ref.reference, bible_version) if bible_version else None
    if exception is not None:
        chapter, v_start, v_end = (
            exception["target_chapter"], exception["target_verse_start"], exception["target_verse_end"],
        )

    texto = fetch_text(native_resolver.cursor, book_number, chapter, v_start, v_end)

    if texto is None:
        return Finding(
            kind="resolution_failed",
            ref=native_ref,
            message=(
                f"'{native_ref.path}': verse not found for '{en_ref.reference}' "
                f"in this file's Bible version"
            ),
        )

    return _compare_text(native_ref, texto)


def _compare_text(ref: ScriptureRef, resolved_text: str) -> Optional[Finding]:
    """Shared fuzzy-match step for both validate_pair() and
    validate_translated_pair() — same threshold, same Finding shape."""
    similarity = jaccard_similarity(ref.verse_text, resolved_text)
    if similarity < FUZZY_MATCH_THRESHOLD:
        return Finding(
            kind="text_mismatch",
            ref=ref,
            message=(
                f"'{ref.path}': stored verse_text only "
                f"{similarity:.0%} token-overlaps the resolved text (threshold "
                f"{FUZZY_MATCH_THRESHOLD:.0%}).\n"
                f"      stored:   {ref.verse_text}\n"
                f"      resolved: {resolved_text}"
            ),
        )

    return None


# ─────────────────────────────────────────────────────────────────────────────
# RESOLVER LIFECYCLE
# ─────────────────────────────────────────────────────────────────────────────

class ScriptureValidator:
    """Owns one open VerseResolver per (language, bible_version) seen in a
    run, so a corpus scan across many files/languages opens each SQLite DB
    once instead of once per card. Cached by (lang, version) rather than
    version alone because a version code is not always unique to one
    language — e.g. 'NVI' names both bible_database/NVI_es.SQLite3.gz
    (Spanish) and NVI_pt.SQLite3.gz (Portuguese), two different DBs with
    different verse text. Does not extract pairs or perform comparisons
    itself — that's find_scripture_pairs()'s and validate_pair()'s job
    respectively; this class only manages resolver lifecycle/caching.
    """

    def __init__(self, bible_database_dir: Path, books_sot_path: Optional[str] = None):
        self._bible_database_dir = Path(bible_database_dir)
        self._books_sot_path = books_sot_path
        self._resolvers: dict[tuple[str, str], VerseResolver] = {}

    def get_resolver(self, bible_version: str, lang: str) -> Optional[VerseResolver]:
        """Return the open VerseResolver for (bible_version, lang), opening
        and caching it on first use. Returns None if no matching DB file
        exists under bible_database_dir — callers should treat that as
        "cannot validate this version," not crash the run."""
        cache_key = (lang, bible_version)
        if cache_key in self._resolvers:
            return self._resolvers[cache_key]

        db_path = self._bible_database_dir / f"{bible_version}_{lang}.SQLite3.gz"
        if not db_path.exists():
            return None

        resolver = VerseResolver(str(db_path), books_sot_path=self._books_sot_path)
        self._resolvers[cache_key] = resolver
        return resolver

    def close(self) -> None:
        """Close every resolver opened by this validator."""
        for resolver in self._resolvers.values():
            resolver.close()
        self._resolvers.clear()

    def __enter__(self) -> "ScriptureValidator":
        return self

    def __exit__(self, *_) -> None:
        self.close()
