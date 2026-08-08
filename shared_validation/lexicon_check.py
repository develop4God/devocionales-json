"""lexicon_check.py — lexical-accuracy check for inline Greek/Hebrew glosses.

This is deliberately separate from greek_hebrew_gloss.py's hard gate.
greek_hebrew_gloss.py answers "is this gloss well-formed?" (structure only —
comma placement, script boundaries, Latin-leak detection). This module
answers a different question: "does this well-formed gloss say something
true?" — is <word> a real Greek/Hebrew headword, and does <transliteration>
match what Strong's records for it?

Reusing find_greek_hebrew_glosses means this module never re-implements span
extraction — if the format rules in gloss_format.json change, this file
doesn't need to change with them.

Four possible outcomes per gloss span, not a pass/fail binary:
  MATCHED                  — lemma found, transliteration agrees (after
                              diacritic normalization)
  INFLECTED_NO_LEMMA_MATCH — native word isn't a dictionary headword (it's a
                              declined/conjugated surface form, e.g. λίθοι vs
                              lemma λίθος). Expected for ~half of exegesis
                              content. Flagged for human review, not an error.
  TRANSLIT_MISMATCH        — the word IS a recognized headword, but the given
                              transliteration doesn't match Strong's for it.
                              This is the actual error case the gate exists
                              to catch.
  AMBIGUOUS_LEMMA          — the word matches 2+ Strong's headwords (common in
                              Hebrew: 646 lemmas collide, e.g. עוּר is both
                              H5782 "to wake" and H5784 "chaff" — genuinely
                              different words sharing one consonantal
                              spelling) and no Strong's code already cited
                              near the gloss disambiguates which one is
                              meant. Reported, not silently resolved by
                              picking a candidate — see
                              LexiconSource.lookup_by_lemma's docstring.

Deliberately no stemming/lemmatization heuristics (YAGNI): guessing Greek/
Hebrew inflectional endings well enough to avoid false positives is a
non-trivial NLP problem on its own. INFLECTED_NO_LEMMA_MATCH is an honest,
deterministic outcome — a human confirms it in seconds, whereas a wrong
guess would need to be un-learned. If this becomes a bottleneck, add a
MatchStrategy the same way LexiconSource is added: as a new interchangeable
piece, not a rewrite of this module (Open/Closed).
"""

from __future__ import annotations

from enum import Enum
from typing import NamedTuple

from .greek_hebrew_gloss import find_greek_hebrew_glosses
from .lexicon_source import LexiconSource, resolve_lemma_entry
from .report import ReportLike


class LexicalStatus(Enum):
    MATCHED = "matched"
    INFLECTED_NO_LEMMA_MATCH = "inflected_no_lemma_match"
    TRANSLIT_MISMATCH = "translit_mismatch"
    AMBIGUOUS_LEMMA = "ambiguous_lemma"


class LexicalCheckResult(NamedTuple):
    word: str
    given_translit: str
    status: LexicalStatus
    strongs_number: str | None = None
    expected_translit: str | None = None
    candidates: tuple[str, ...] = ()


def _translit_matches(given: str, official: str) -> bool:
    """Exact match required (case-insensitive) — no diacritic-stripping.

    An earlier version stripped combining marks from both sides before
    comparing, meant to tolerate this corpus's occasional bare-ASCII house
    style (e.g. 'ginomai' for 'gínomai') without flagging it as wrong. That
    silently accepted a real mismatch too: stripping marks from BOTH sides
    makes 'anthrakia' (missing its required accent) indistinguishable from
    'ginomai' (deliberately plain ASCII) — both reduce to the same
    stripped form, so a wrong transliteration that happened to differ from
    Strong's by only an accent passed as MATCHED (found 2026-07-28,
    peter_restoration_001: anthrakia/lambano/bosko/poimaino all silently
    accepted against Strong's anthrakiá/lambánō/bóskō/poimaínō). Strong's
    own spelling — diacritics included — is this corpus's source of truth
    (see lexicon_fixer.py's module docstring); an exact match is the only
    comparison that can't hide this class of error, and it's the same
    comparison lexicon_fixer.py already uses to decide what to rewrite.
    """
    return given.lower().strip() == official.lower().strip()


def _grade_word_translit(
    word: str,
    given_translit: str,
    entry,
    candidates: tuple,
    path: str,
    lang: str,
    ctx: str,
    report: ReportLike,
    debug: bool = False,
) -> LexicalCheckResult:
    """Core grading step shared by every caller that has already resolved
    (or failed to resolve) a word against the lexicon — one word/translit
    pair in, one graded LexicalCheckResult out, with the matching report
    call. Used by check_lexical_accuracy (inline ", (translit)" prose
    spans) and check_structured_word_study_accuracy (greek_words/
    hebrew_words array entries) so both shapes are graded identically and
    this logic exists exactly once.

    `debug`, when True, prints the exact given-vs-official comparison for
    EVERY span, including a clean MATCHED — a plain corpus scan only ever
    reports errors/ambiguous cases, so a comparison that wrongly resolves
    to MATCHED (as _translit_matches's old diacritic-stripping did, see
    its docstring) produces no output at all in a normal run. --debug
    makes that decision visible on demand without adding noise by default."""
    if debug:
        print(
            f"[debug] {ctx}: '{word}' given={given_translit!r} "
            f"entry={entry.strongs_number if entry else None!r} "
            f"official={entry.translit if entry else None!r} "
            f"candidates={tuple(c.strongs_number for c in candidates)}"
        )
    if not candidates:
        report.I(
            f"{path} [{lang}] {ctx}: '{word}' ({given_translit}) is not a "
            f"Strong's headword — likely an inflected form; confirm lemma manually."
        )
        return LexicalCheckResult(
            word=word,
            given_translit=given_translit,
            status=LexicalStatus.INFLECTED_NO_LEMMA_MATCH,
        )

    if entry is None:
        candidate_codes = tuple(c.strongs_number for c in candidates)
        report.I(
            f"{path} [{lang}] {ctx}: '{word}' ({given_translit}) matches "
            f"{len(candidates)} distinct Strong's headwords {candidate_codes} with no "
            f"citation nearby to disambiguate — confirm which one manually and cite it."
        )
        return LexicalCheckResult(
            word=word,
            given_translit=given_translit,
            status=LexicalStatus.AMBIGUOUS_LEMMA,
            candidates=candidate_codes,
        )

    exact_match = _translit_matches(given_translit, entry.translit)
    if debug:
        print(f"[debug]   -> exact_match={exact_match}")
    if exact_match:
        return LexicalCheckResult(
            word=word,
            given_translit=given_translit,
            status=LexicalStatus.MATCHED,
            strongs_number=entry.strongs_number,
            expected_translit=entry.translit,
        )

    report.E(
        f"{path} [{lang}] {ctx}: '{word}' glossed as '({given_translit})' but "
        f"{entry.strongs_number} gives '{entry.translit}' — check spelling."
    )
    return LexicalCheckResult(
        word=word,
        given_translit=given_translit,
        status=LexicalStatus.TRANSLIT_MISMATCH,
        strongs_number=entry.strongs_number,
        expected_translit=entry.translit,
    )


def check_lexical_accuracy(
    text: str,
    lexicon: LexiconSource,
    path: str,
    lang: str,
    ctx: str,
    report: ReportLike,
    debug: bool = False,
) -> list[LexicalCheckResult]:
    """Runs lexical validation over every well-formed gloss span in `text`.

    Only well-formed spans (well_formed=True, inner is not None) are
    checked — a span that fails the structural hard gate is greek_hebrew_
    gloss.py's problem to report, not this module's; checking a malformed
    span for lexical accuracy would be reporting on data we don't trust yet.
    """
    results: list[LexicalCheckResult] = []

    for _start, end, word, inner, well_formed in find_greek_hebrew_glosses(text):
        if not well_formed:
            continue  # structural hard gate's problem, not this module's

        entry, candidates = resolve_lemma_entry(lexicon, word, text, end, lang)
        results.append(
            _grade_word_translit(
                word, inner, entry, candidates, path, lang, ctx, report, debug
            )
        )

    return results


def check_structured_word_study_accuracy(
    word: str,
    transliteration: str,
    lexicon: LexiconSource,
    path: str,
    lang: str,
    ctx: str,
    report: ReportLike,
    debug: bool = False,
    strongs_hint: str | None = None,
) -> LexicalCheckResult:
    """Same lexical grading as check_lexical_accuracy, for the OTHER shape
    this corpus uses to cite a Greek/Hebrew word study: the structured
    greek_words/hebrew_words array, where the native word and its
    transliteration are separate JSON keys ({"word": "δόλος",
    "transliteration": "Dolos"}) rather than one inline ", (translit)"
    prose string. find_greek_hebrew_glosses can't see this shape at all —
    it only matches native-script text immediately followed by its own
    inline gloss tail in the SAME string — so this array was invisible to
    every Strong's check until now, verified while reviewing
    natanael_fig_tree_001 (its greek_words entries had never been checked
    against Strong's at all, passing every existing validator only because
    nothing looked at them).

    A structured array entry has no "nearby citation" text to hunt for a
    disambiguation hint in (unlike inline prose, there's no surrounding
    sentence here) — so when `word` is ambiguous across multiple Strong's
    headwords, this reports AMBIGUOUS_LEMMA unless the caller passes
    `strongs_hint` (from the entry's own optional "strong" JSON field —
    the same key breath_new_adam/hammer_of_god/jesus_troubled_himself/
    restoration_by_fire/road_to_emmaus already use), in which case that
    code is tried directly via resolve_lemma_entry's explicit_hint path.

    Multi-word phrases (e.g. "ὁ υἱὸς τοῦ ἀνθρώπου", a title, not a single
    lexical term) are deliberately NOT split into per-word checks here —
    lookup_by_lemma on the full phrase string will simply find no match
    (INFLECTED_NO_LEMMA_MATCH), which is the correct, harmless outcome for
    a phrase this check was never meant to grade word-by-word.
    """
    entry, candidates = resolve_lemma_entry(
        lexicon, word, "", 0, lang, explicit_hint=strongs_hint
    )
    return _grade_word_translit(
        word, transliteration, entry, candidates, path, lang, ctx, report, debug
    )
