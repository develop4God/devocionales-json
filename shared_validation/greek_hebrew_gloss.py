"""greek_hebrew_gloss.py — HARD GATE for inline Greek/Hebrew word-study
glosses in Discovery/Encounters prose (content/reflection/narrative/
question/etc. fields).

Canonical format is specified in gloss_format.json (single source of
truth, not hardcoded here) — read that file for the full rule and
rationale. Exactly two accepted forms, no alternate conventions, no
exceptions: <word>,<space>(<transliteration>) or
<word> <word>,<space>(<transliteration>).

find_greek_hebrew_glosses is also consumed by text_checks.py's
check_no_latin_leak, which treats each well-formed span's
transliteration as the one accepted exception before flagging stray
Latin elsewhere in a non-Latin-script field.
"""

import json
import re
from pathlib import Path

from .report import ReportLike

_GREEK_RE = re.compile(r'[Ͱ-Ͽἀ-῿]')
_HEBREW_RE = re.compile(r'[֐-׿]')
# A single native-script word: one run of Greek/Hebrew letters with no
# internal whitespace.
_NATIVE_WORD_RE = re.compile(r'[Ͱ-Ͽἀ-῿֐-׿][Ͱ-Ͽἀ-῿֐-׿֑-ׇ]*')
# A two-word native-script run: word, one ASCII space, word — used to try
# the two-word-phrase form before falling back to single-word (see
# find_greek_hebrew_glosses). The hard gate accepts 1 or 2 words only,
# never 3+ (that's a multi-word/sentence pairing, rejected by
# gloss_format.json).
_NATIVE_TWO_WORD_RE = re.compile(
    r'([Ͱ-Ͽἀ-῿֐-׿][Ͱ-Ͽἀ-῿֐-׿֑-ׇ]*) ([Ͱ-Ͽἀ-῿֐-׿][Ͱ-Ͽἀ-῿֐-׿֑-ׇ]*)'
)
# The one accepted gloss immediately following a native word/phrase: exactly
# ",<space>(<transliteration>)" — ASCII comma, exactly one ASCII space,
# ASCII parens. Captured separately so we can tell "correctly-glossed" apart
# from "native word with no gloss trailing it at all" vs. "native word with
# a malformed gloss attempt trailing it".
_STRICT_GLOSS_TAIL_RE = re.compile(r', \(([^()]*)\)')
# A malformed gloss attempt whose transliteration slot was filled with a
# phonetic respelling in a non-Latin script instead of Latin — e.g.
# "κατέγραφεν, कतेग्राफेन)" (Devanagari, ASCII comma), "παρακαλέω،
# باراكاليو)" (Arabic script + Arabic comma), "κράσπεδον（クラスペドン）"
# (Katakana, full-width parens, no comma at all — the systemic ja
# convention). Distinct from a plain missing-gloss case: this pattern has
# non-Latin-script content sitting immediately after the word (optionally
# preceded by a comma/native-comma, optionally wrapped in ASCII or
# full-width parens), which is specifically diagnostic of the phonetic-
# respelling bug (see gloss_format.json "Phonetic respelling into the
# target script instead of Latin"), not just "no gloss was attempted at
# all". Matched separately so check_greek_hebrew_transliteration can name
# the real problem instead of the generic "not followed by the required
# gloss" message.
#
# The specific script range checked is per-language (see
# native_script_ranges.json / _phonetic_respelling_re_for_lang below) —
# a Hindi file is only tested against Devanagari, a Japanese file only
# against Katakana/Han, etc. There is no reason to test a German file
# against Devanagari, or a Hindi file against Katakana: each language can
# only phonetically misspell into its OWN native script, never another
# language's. Latin-script languages (de, en, es, fil, fr, pt, ...) have
# no range at all and skip this check entirely — the bug can't occur when
# the target language's own script already IS Latin.
_NATIVE_SCRIPT_RANGES_PATH = Path(__file__).parent / "native_script_ranges.json"
_native_script_ranges_cache = None
_phonetic_respelling_re_cache: dict = {}


def _load_native_script_ranges() -> dict:
    global _native_script_ranges_cache
    if _native_script_ranges_cache is None:
        with open(_NATIVE_SCRIPT_RANGES_PATH, encoding="utf-8") as f:
            _native_script_ranges_cache = json.load(f)["ranges"]
    return _native_script_ranges_cache


def _phonetic_respelling_re_for_lang(lang: str):
    """Return the compiled phonetic-respelling-tail regex for `lang`'s own
    native script, or None if `lang` is Latin-script (nothing to check —
    see module comment above). Cached per language since the ranges file
    never changes at runtime."""
    if lang in _phonetic_respelling_re_cache:
        return _phonetic_respelling_re_cache[lang]
    ranges = _load_native_script_ranges().get(lang)
    if not ranges:
        _phonetic_respelling_re_cache[lang] = None
        return None
    script_class = ''.join(ranges)
    pattern = re.compile(
        rf'(?:[,،、]\s*[(（]?|[(（])([{script_class}][{script_class}・ ]*)[)）]'
    )
    _phonetic_respelling_re_cache[lang] = pattern
    return pattern
# Extended-Latin transliteration charset: ASCII + Latin-1/Extended-A/B +
# combining diacritics used for scholarly romanization (ā, ṓ, ḥ, ʿ, etc.)
# The specific diacritic set this corpus's transliteration convention
# actually uses (see gloss_format.json "transliteration_charset" — derived
# empirically from every well-formed gloss in the corpus, not the full SBL
# academic Hebrew table). A Latin letter outside this set is either a typo,
# an accidental other-language character, or a not-yet-adopted style —
# either way, worth flagging rather than silently accepting any Latin script.
_LATIN_TRANSLIT_RE = re.compile(r"^[A-Za-zÁÉÍÓÚÝáéíóúýĀāĒēĪīŌōŪūḖḗṒṓ\s\-'’.:0-9]+$")
_STRONG_PREFIX_RE = re.compile(r'^(Strong\s+)?[GH]?\d+\s*[:\-]?\s*', re.IGNORECASE)
_SKIP_KEYS = {'word'}
# How far past the end of a native word we look for a malformed gloss
# attempt, so the error message can show what's actually there instead of
# just "no gloss found".
_MALFORMED_LOOKAHEAD = 40


def find_greek_hebrew_glosses(text: str) -> list:
    """Find every native-script (Greek/Hebrew) word or two-word phrase in
    text and whether it is followed by a correctly-formed gloss.

    Returns a list of (start, end, word, inner, well_formed) tuples:
    start/end are the character offsets of the whole span (the native
    word/phrase plus its gloss tail, if any correctly-formed one follows)
    in `text`; word is the matched native-script text (a single word, or a
    two-word run — the hard gate accepts 1 or 2 words only, never 3+); inner
    is the raw transliteration content when a well-formed ", (...)" tail
    follows, else None; well_formed is True only when the word/phrase is
    immediately followed by exactly ", (<content>)" — ASCII comma, one
    ASCII space, ASCII parens (see gloss_format.json). Any other trailing
    punctuation (or none) means well_formed=False and inner=None — a HARD
    GATE violation, full stop. There is no reuse exception, no sentence-
    pair exception, no comma-inside-parens exception, no 3+-word exception:
    every occurrence of every native-script word or two-word phrase must
    carry its own gloss, every time.

    Two-word phrases are tried first at each position (greedy — a
    correctly-glossed two-word phrase must not be mistaken for a
    single-word gloss followed by stray text), falling back to single-word
    if the two-word form isn't immediately followed by a well-formed tail.
    Once a span is consumed (as either form), scanning resumes after it —
    a two-word phrase's second word is not re-matched as its own word.

    Shared span-finder consumed by check_greek_hebrew_transliteration
    (validates what's inside the parens once well_formed) and
    text_checks.check_no_latin_leak (treats each well-formed span's
    transliteration as the one accepted exception before flagging stray
    Latin elsewhere in the field).
    """
    spans = []
    pos = 0
    n = len(text)
    while pos < n:
        m1 = _NATIVE_WORD_RE.match(text, pos)
        if not m1:
            pos += 1
            continue
        m2 = _NATIVE_TWO_WORD_RE.match(text, pos)
        if m2:
            two_word = f"{m2.group(1)} {m2.group(2)}"
            tail_match = _STRICT_GLOSS_TAIL_RE.match(text, m2.end())
            if tail_match:
                spans.append((m2.start(), tail_match.end(), two_word, tail_match.group(1).strip(), True))
                pos = tail_match.end()
                continue
        word = m1.group(0)
        tail_match = _STRICT_GLOSS_TAIL_RE.match(text, m1.end())
        if tail_match:
            spans.append((m1.start(), tail_match.end(), word, tail_match.group(1).strip(), True))
            pos = tail_match.end()
        else:
            spans.append((m1.start(), m1.end(), word, None, False))
            pos = m1.end()
    return spans


def check_greek_hebrew_transliteration(text: str, path: str, lang: str, ctx: str, report: ReportLike) -> None:
    """HARD GATE: every Greek/Hebrew word or two-word phrase must be
    immediately followed by ", (<Latin transliteration>)" — nothing else is
    accepted.

    Convention (see gloss_format.json, the single source of truth): each
    native-script word or two-word phrase is glossed as "<word(s)>, (<translit>)",
    e.g. "θεός, (theos)" or "τὸ γεγονός, (to gegonos)". No space-only
    variant, no full-width punctuation, no comma-inside-one-parenthetical,
    no bare reuse without a gloss, no 3+-word/sentence pairing. Every
    occurrence gets its own gloss.

    `lang` selects which native-script range (if any) is checked for the
    phonetic-respelling sub-case — see native_script_ranges.json /
    _phonetic_respelling_re_for_lang. Latin-script languages skip that
    sub-check entirely (nothing to check: their own language is already
    Latin script, so a Devanagari/Katakana/etc. respelling can't occur).
    """
    key = path.rsplit('.', 1)[-1].split('[')[0]
    if key in _SKIP_KEYS:
        return
    if not (_GREEK_RE.search(text) or _HEBREW_RE.search(text)):
        return
    phonetic_re = _phonetic_respelling_re_for_lang(lang)
    for start, end, word, inner, well_formed in find_greek_hebrew_glosses(text):
        if not well_formed:
            phonetic_match = phonetic_re.match(text, end) if phonetic_re else None
            if phonetic_match:
                report.E(f"{ctx}: '{word}' gloss uses a phonetic respelling in a non-Latin script ('{phonetic_match.group(1)}') instead of the required Latin transliteration (required format: '{word}, (translit)', see gloss_format.json)")
                continue
            lookahead = text[end:end + _MALFORMED_LOOKAHEAD]
            report.E(f"{ctx}: '{word}' is not followed by the required ', (transliteration)' gloss (required format: '{word}, (translit)', see gloss_format.json) — found: '{word}{lookahead}'")
            continue
        stripped = _STRONG_PREFIX_RE.sub('', inner).strip()
        if not stripped:
            report.E(f"{ctx}: gloss '{word}, ({inner})' — empty transliteration")
            continue
        if _GREEK_RE.search(stripped) or _HEBREW_RE.search(stripped):
            report.E(f"{ctx}: gloss '{word}, ({inner})' — parenthetical repeats original script instead of giving a Latin transliteration")
        elif not _LATIN_TRANSLIT_RE.match(stripped):
            report.E(f"{ctx}: gloss '{word}, ({inner})' — parenthetical is not Latin-alphabet (looks like a phonetic respelling into the target script)")


def check_bare_transliteration_reuse(text: str, path: str, ctx: str, report: ReportLike) -> None:
    """HARD GATE: a transliteration introduced by one well-formed gloss in
    this field must never appear again later in the same field as bare
    Latin text with no accompanying native-script word — see
    gloss_format.json "Bare reuse without a gloss: introducing 'θεός,
    (theos)' once and later writing bare 'theos' with no gloss". No
    exception for any language: every occurrence gets its own
    '<word>, (<translit>)' gloss, full stop — a lone Latin loanword
    reading as unremarkable in English/German/etc. prose doesn't matter.

    find_greek_hebrew_glosses only looks for native-script characters, so
    it can't see this case (a bare Latin word has no native-script word to
    anchor on). Simple approach: collect each well-formed gloss's
    transliteration and end position, then \\b-search the text AFTER that
    point for the same word reappearing bare — but a match that falls
    inside another well-formed gloss's own parenthetical (i.e. the word
    was re-glossed again, correctly, later in the field) is not bare reuse
    and must be excluded, or every correctly-repeated gloss of the same
    word would falsely trip this check on its own transliteration text.
    """
    key = path.rsplit('.', 1)[-1].split('[')[0]
    if key in _SKIP_KEYS:
        return
    glosses = find_greek_hebrew_glosses(text)
    wellformed_spans = [(s, e) for s, e, _, i2, wf in glosses if wf and i2]
    for _, end, _, inner, well_formed in glosses:
        if not (well_formed and inner):
            continue
        for m in re.finditer(rf'\b{re.escape(inner)}\b', text[end:]):
            m_start, m_end = end + m.start(), end + m.end()
            if any(s <= m_start and m_end <= e for s, e in wellformed_spans):
                continue
            report.E(f"{ctx}: '{inner}' reused as bare Latin text later in this field with no accompanying native-script gloss (every occurrence needs its own '<word>, ({inner})', see gloss_format.json 'Bare reuse without a gloss')")
            break
