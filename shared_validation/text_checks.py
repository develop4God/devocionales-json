"""text_checks.py — text-field validation helpers shared by both pipelines:
quote-anomaly detection, string-tree iteration, and cognate lookup.

cognates.py was considered as a separate module and rejected as too small;
folded in here per the spike scope.
"""

import json
import re
from pathlib import Path
from typing import Iterator, Tuple

from .report import ReportLike

# Quote-like characters whose accidental back-to-back doubling indicates a
# stray-punctuation typo (e.g. »» , "" , '')
_DOUBLE_CHECK_CHARS = {'"', "'", '«', '»', '“', '”', '‘', '’'}

# Paired quote characters that should appear in balanced counts within a field.
# Note: curly double quotes (“ ” „) are intentionally NOT balance-checked here —
# this corpus mixes „...“ and „...” conventions across different German
# encounters/studies, so a fixed pair produces false positives. Guillemets « »
# are checked for all languages (used in AR/FR/etc.) since their usage is
# consistent.

# Words identical (or near-identical) across English and Romance languages —
# valid cognate translations, not untranslated leftovers. Per translator skill
# § "Cognates (FR, PT, ES)": these are correct and should not be flagged.
# Union of both pipelines' tables — encounters has an extra 'de': {'legion'}
# entry discovery doesn't have; kept, it's harmless for discovery (which
# never actually calls is_cognate('legion', 'de') in its current form).
_ROMANCE_COGNATES = {
    'fr': {'courage', 'grace', 'grâce'},
    'pt': {'coragem', 'graça'},
    'es': {'coraje', 'gracia'},
    # 'Legion' is spelled identically in German (from Latin legio) and is the
    # word used in the LU17 Bible text itself (Mark 5:9) — not a missed translation.
    'de': {'legion'},
}


def is_cognate(value: str, lang: str) -> bool:
    """Return True if value is a known valid cognate word for lang."""
    return value.strip().lower() in _ROMANCE_COGNATES.get(lang, set())


def iter_strings(obj, path: str = "") -> Iterator[Tuple[str, str]]:
    """Recursively yield (path, value) for every string leaf in obj."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from iter_strings(v, f"{path}.{k}" if path else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from iter_strings(v, f"{path}[{i}]")
    elif isinstance(obj, str):
        yield path, obj


def is_verse_continuation_close(text: str, mark_chars: str) -> bool:
    """True if `text` looks like the tail fragment of a multi-verse quotation:
    it carries exactly one quote-like mark from `mark_chars`, sitting at the
    very end of the field (only trailing punctuation/whitespace after it).
    This corpus stores consecutive Bible verses as separate string fields, so
    a quotation that began in an earlier verse legitimately closes here with
    no opener of its own — not a stray-punctuation typo.
    """
    positions = [i for i, c in enumerate(text) if c in mark_chars]
    if len(positions) != 1:
        return False
    idx = positions[0]
    return bool(re.match(r'^[\s.!?,;:]*$', text[idx + 1:]))


# Languages whose native typography uses a full-width colon (：) rather
# than the half-width ASCII ':' — checked in title fields only, since a
# half-width colon there is a generation/template artifact, not a stylistic
# choice (body text, greek_words, etc. legitimately mix both e.g. in inline
# Bible chapter:verse citations).
_FULLWIDTH_COLON_LANGS = {'ja', 'zh'}


_TITLE_LIKE_KEYS = {'title', 'subtitle'}


def check_halfwidth_colon_in_title(text: str, path: str, lang: str, ctx: str, report: ReportLike) -> None:
    """Flag a half-width ':' in a title/subtitle field for ja/zh content.

    Skips colons immediately followed by a digit, since those are Bible
    chapter:verse references embedded in the title (e.g. "ヨハネ1:1",
    "诗篇22:16") and must stay half-width — scripture references are
    half-width everywhere else in the corpus.
    """
    if lang not in _FULLWIDTH_COLON_LANGS:
        return
    key = path.rsplit('.', 1)[-1].split('[')[0]
    if key not in _TITLE_LIKE_KEYS:
        return
    for i, c in enumerate(text):
        if c == ':' and not (i + 1 < len(text) and text[i + 1].isdigit()):
            report.E(f"{ctx}: half-width ':' in title should be full-width '：'")


# HARD GATE — Greek/Hebrew inline word-study glosses. Skip the `word` field
# itself (holds the original-script term by design) and `transliteration`
# (checked separately by validate_family.py's word-block validation, for
# Discovery) — this check is for inline prose glosses like "θεός, (theos)"
# in content/reflection/narrative/question/etc. The canonical format is
# specified in gloss_format.json (single source of truth, not hardcoded
# here) — read that file for the full rule and rationale. Exactly two
# accepted forms, no alternate conventions, no exceptions:
# <word>,<space>(<transliteration>) or <word> <word>,<space>(<transliteration>).
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
# Extended-Latin transliteration charset: ASCII + Latin-1/Extended-A/B +
# combining diacritics used for scholarly romanization (ā, ṓ, ḥ, ʿ, etc.)
_LATIN_TRANSLIT_RE = re.compile(r"^[A-Za-zÀ-ɏḀ-ỿ\s\-'’.:0-9]+$")
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
    check_no_latin_leak (treats each well-formed span's transliteration as
    the one accepted exception before flagging stray Latin elsewhere in
    the field).
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


def check_greek_hebrew_transliteration(text: str, path: str, ctx: str, report: ReportLike) -> None:
    """HARD GATE: every Greek/Hebrew word or two-word phrase must be
    immediately followed by ", (<Latin transliteration>)" — nothing else is
    accepted.

    Convention (see gloss_format.json, the single source of truth): each
    native-script word or two-word phrase is glossed as "<word(s)>, (<translit>)",
    e.g. "θεός, (theos)" or "τὸ γεγονός, (to gegonos)". No space-only
    variant, no full-width punctuation, no comma-inside-one-parenthetical,
    no bare reuse without a gloss, no 3+-word/sentence pairing. Every
    occurrence gets its own gloss.
    """
    key = path.rsplit('.', 1)[-1].split('[')[0]
    if key in _SKIP_KEYS:
        return
    if not (_GREEK_RE.search(text) or _HEBREW_RE.search(text)):
        return
    for start, end, word, inner, well_formed in find_greek_hebrew_glosses(text):
        if not well_formed:
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


# Per-language rules for check_no_latin_leak, see that file's own _comment
# for what 'letters'/'punctuation' mean and when to add a language.
_NO_LATIN_LANGUAGES_PATH = Path(__file__).parent / "no_latin_languages.json"
_no_latin_languages_cache = None


def _load_no_latin_config() -> dict:
    global _no_latin_languages_cache
    if _no_latin_languages_cache is None:
        with open(_NO_LATIN_LANGUAGES_PATH, encoding="utf-8") as f:
            data = json.load(f)
        _no_latin_languages_cache = {
            'languages': data['languages'],
            'skip_keys': set(data['skip_keys']),
        }
    return _no_latin_languages_cache


_LATIN_LETTER_RE = re.compile(r"[A-Za-zÀ-ɏḀ-ỿ]+")
_LATIN_PUNCT_RE = re.compile(r'[,.!?"\']')


def check_no_latin_leak(text: str, path: str, lang: str, ctx: str, report: ReportLike) -> None:
    """Flag Latin letters/punctuation leaking into a non-Latin-script
    language's text field — e.g. a stray untranslated English word or
    phrase mixed into otherwise-translated zh content.

    Which languages are checked, whether punctuation is included, and which
    field keys are structural (skipped — never prose) are all configured in
    no_latin_languages.json rather than hardcoded here, so adding a language
    or a new structural field doesn't require a code change (see that
    file's _comment / _skip_keys_comment). The one accepted content
    exception is the Latin transliteration inside a well-formed Greek/Hebrew
    gloss, e.g. 'θεός, (theos)' — those spans are carved out via
    find_greek_hebrew_glosses before scanning for stray Latin. A
    malformed/incomplete gloss attempt is NOT carved out here — it is a
    hard-gate error from check_greek_hebrew_transliteration in its own
    right, and any Latin text near it is still fair game for this check.
    """
    config = _load_no_latin_config()
    rules = config['languages'].get(lang)
    if rules is None:
        return
    key = path.rsplit('.', 1)[-1].split('[')[0]
    if key in config['skip_keys']:
        return
    gloss_spans = find_greek_hebrew_glosses(text)

    def in_gloss(pos: int) -> bool:
        return any(start <= pos < end for start, end, _, _, well_formed in gloss_spans if well_formed)

    if rules.get('letters'):
        for m in _LATIN_LETTER_RE.finditer(text):
            if not in_gloss(m.start()):
                report.W(f"{ctx}: Latin text '{m.group(0)}' in {lang} field — possible untranslated leftover")

    if rules.get('punctuation'):
        for m in _LATIN_PUNCT_RE.finditer(text):
            if not in_gloss(m.start()):
                report.W(f"{ctx}: Latin punctuation '{m.group(0)}' in {lang} field")


def check_quote_anomalies(text: str, ctx: str, report: ReportLike) -> None:
    """Flag stray/duplicated/unbalanced quote-like punctuation in a text field.

    Note: the `lang` parameter present in both original _check_quote_anomalies
    functions is unused by either implementation's body — dropped here since
    it carries no behavior.
    """
    # Doubled identical quote-like characters back-to-back (e.g. »», "", '')
    for i in range(len(text) - 1):
        c = text[i]
        if c in _DOUBLE_CHECK_CHARS and text[i + 1] == c:
            report.E(f"{ctx}: contains doubled '{c}{c}' — likely stray punctuation")

    # Balanced guillemets (used in AR/FR/etc.). Skip fields that are the
    # trailing fragment of a quotation opened in a preceding verse — see
    # is_verse_continuation_close.
    oc, cc = text.count('«'), text.count('»')
    if oc != cc and not (oc + cc == 1 and is_verse_continuation_close(text, '«»')):
        report.W(f"{ctx}: unbalanced '«'/'»' — {oc} open vs {cc} close")

    # Straight double quotes should appear in pairs, with the same
    # verse-continuation exception as guillemets above.
    if text.count('"') % 2 != 0 and not (text.count('"') == 1 and is_verse_continuation_close(text, '"')):
        report.W(f"{ctx}: odd number of straight double quotes (\") — possible stray quote")
