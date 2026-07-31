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
import unicodedata
from pathlib import Path

from .lexicon_source import (
    load_native_script_ranges,
    resolve_lemma_entry,
    find_nearby_strong_citation,
)
from .report import ReportLike

_GREEK_RE = re.compile(r"[Ͱ-Ͽἀ-῿]")
_HEBREW_RE = re.compile(r"[֐-׿]")
# A single native-script word: one run of Greek/Hebrew letters with no
# internal whitespace.
_NATIVE_WORD_RE = re.compile(r"[Ͱ-Ͽἀ-῿֐-׿][Ͱ-Ͽἀ-῿֐-׿֑-ׇ]*")
# A two-word native-script run: word, one ASCII space, word — used to try
# the two-word-phrase form before falling back to single-word (see
# find_greek_hebrew_glosses). The hard gate accepts 1 or 2 words only,
# never 3+ (that's a multi-word/sentence pairing, rejected by
# gloss_format.json).
_NATIVE_TWO_WORD_RE = re.compile(
    r"([Ͱ-Ͽἀ-῿֐-׿][Ͱ-Ͽἀ-῿֐-׿֑-ׇ]*) ([Ͱ-Ͽἀ-῿֐-׿][Ͱ-Ͽἀ-῿֐-׿֑-ׇ]*)"
)
# The one accepted gloss immediately following a native word/phrase: exactly
# ",<space>(<transliteration>)" — ASCII comma, exactly one ASCII space,
# ASCII parens. Captured separately so we can tell "correctly-glossed" apart
# from "native word with no gloss trailing it at all" vs. "native word with
# a malformed gloss attempt trailing it".
_STRICT_GLOSS_TAIL_RE = re.compile(r", \(([^()]*)\)")
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
_GLOSS_FORMAT_PATH = Path(__file__).parent / "gloss_format.json"
_gloss_format_cache = None
_phonetic_respelling_re_cache: dict = {}


def _load_gloss_format() -> dict:
    global _gloss_format_cache
    if _gloss_format_cache is None:
        with open(_GLOSS_FORMAT_PATH, encoding="utf-8") as f:
            _gloss_format_cache = json.load(f)
    return _gloss_format_cache


def _phonetic_respelling_re_for_lang(lang: str):
    """Return the compiled phonetic-respelling-tail regex for `lang`'s own
    native script, or None if `lang` is Latin-script (nothing to check —
    see module comment above). Cached per language since the ranges file
    never changes at runtime."""
    if lang in _phonetic_respelling_re_cache:
        return _phonetic_respelling_re_cache[lang]
    entry = load_native_script_ranges().get(lang)
    if not entry:
        _phonetic_respelling_re_cache[lang] = None
        return None
    script_class = "".join(entry["blocks"])
    pattern = re.compile(
        rf"(?:[,،、]\s*[(（]?|[(（])([{script_class}][{script_class}・ ]*)[)）]"
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
_STRONG_PREFIX_RE = re.compile(r"^(Strong\s+)?[GH]?\d+\s*[:\-]?\s*", re.IGNORECASE)
# How far to look around a Strong's-code citation for the word it's
# citing — generous enough to span "(كلمة — G1234)" or "G1234: كلمة"
# but not so wide it crosses into unrelated prose.
_STRONG_CODE_WINDOW = 30
_strong_code_re_cache = None


def _strong_code_re():
    """A citation-code as it appears inline in prose: "G4642", "H5782",
    "Strong G40", "Strong H3419". Always cites a real Hebrew or Greek word
    — used as the anchor for check_strong_code_native_script, since
    find_greek_hebrew_glosses can't anchor on a language's own script
    faking the word phonetically (see that function's docstring).

    The shape (single uppercase letter + 2-5 digits, optional "Strong "
    prefix) is read from gloss_format.json's "strong_code_prefixes" rather
    than hardcoded here. Deliberately not restricted to a specific letter
    set (e.g. just G/H) even though those are the only two seen in the
    corpus today — see that spec entry for why a broad letter-agnostic
    pattern is preferred over an enumerated list.
    """
    global _strong_code_re_cache
    if _strong_code_re_cache is None:
        _strong_code_re_cache = re.compile(r"(?:Strong\s+)?([A-Z])\d{1,5}")
    return _strong_code_re_cache


_SKIP_KEYS = {"word"}
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
                spans.append(
                    (
                        m2.start(),
                        tail_match.end(),
                        two_word,
                        tail_match.group(1).strip(),
                        True,
                    )
                )
                pos = tail_match.end()
                continue
        word = m1.group(0)
        tail_match = _STRICT_GLOSS_TAIL_RE.match(text, m1.end())
        if tail_match:
            spans.append(
                (m1.start(), tail_match.end(), word, tail_match.group(1).strip(), True)
            )
            pos = tail_match.end()
        else:
            spans.append((m1.start(), m1.end(), word, None, False))
            pos = m1.end()
    return spans


def check_greek_hebrew_transliteration(
    text: str, path: str, lang: str, ctx: str, report: ReportLike, lexicon=None
) -> None:
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

    `lexicon` (optional, a shared_validation.lexicon_source.LexiconSource):
    when the gloss's word is a real Strong's headword, the transliteration
    is checked against Strong's own spelling instead of the ASCII/diacritic
    charset regex below. This matters because the regex was built by
    scanning the corpus's own (sometimes wrong) content — it rejects
    correct scholarly marks the corpus hadn't used yet (e.g. Hebrew's
    circumflex â/û or the ayin glyph ʻ, both real characters in Strong's own
    transliterations like 'rûwach', 'ʻûwr') and would just as happily accept
    a plausible-looking but factually wrong spelling. A real dictionary
    lookup is strictly more accurate than a guessed character class, so it
    takes priority whenever a lemma match exists; the regex is now only a
    fallback for words Strong's doesn't recognize (inflected surface forms
    with no headword to check against — see lexicon_check.py's
    INFLECTED_NO_LEMMA_MATCH). `lexicon=None` (the default) preserves the
    old regex-only behavior for callers that haven't wired a lexicon in yet.
    """
    key = path.rsplit(".", 1)[-1].split("[")[0]
    if key in _SKIP_KEYS:
        return
    if not (_GREEK_RE.search(text) or _HEBREW_RE.search(text)):
        return
    phonetic_re = _phonetic_respelling_re_for_lang(lang)
    for start, end, word, inner, well_formed in find_greek_hebrew_glosses(text):
        if not well_formed:
            phonetic_match = phonetic_re.match(text, end) if phonetic_re else None
            if phonetic_match:
                report.E(
                    f"{ctx}: '{word}' gloss uses a phonetic respelling in a non-Latin script ('{phonetic_match.group(1)}') instead of the required Latin transliteration (required format: '{word}, (translit)', see gloss_format.json)"
                )
                continue
            lookahead = text[end : end + _MALFORMED_LOOKAHEAD]
            report.E(
                f"{ctx}: '{word}' is not followed by the required ', (transliteration)' gloss (required format: '{word}, (translit)', see gloss_format.json) — found: '{word}{lookahead}'"
            )
            continue
        stripped = _STRONG_PREFIX_RE.sub("", inner).strip()
        if not stripped:
            report.E(f"{ctx}: gloss '{word}, ({inner})' — empty transliteration")
            continue
        if _GREEK_RE.search(stripped) or _HEBREW_RE.search(stripped):
            report.E(
                f"{ctx}: gloss '{word}, ({inner})' — parenthetical repeats original script instead of giving a Latin transliteration"
            )
            continue
        entry, candidates = (
            resolve_lemma_entry(lexicon, word, text, end, lang)
            if lexicon
            else (None, ())
        )
        if entry is not None:
            given_norm = stripped.lower().strip()
            official_norm = entry.translit.lower().strip()
            if given_norm != official_norm:
                report.E(
                    f"{ctx}: gloss '{word}, ({inner})' — {entry.strongs_number} gives "
                    f"'{entry.translit}', not '{stripped}' — check spelling"
                )
            continue  # lexicon match settles it either way; regex charset guess not needed
        if candidates:
            # 2+ Strong's headwords share this lemma and no nearby citation
            # disambiguates which one is meant — the regex charset guess
            # below can't help here either way, so this is left to the
            # dedicated lexical-accuracy checker (lexicon_check.py reports
            # AMBIGUOUS_LEMMA); the hard gate only cares about well-formed
            # shape, which this span already has.
            continue
        if not _LATIN_TRANSLIT_RE.match(stripped):
            report.E(
                f"{ctx}: gloss '{word}, ({inner})' — parenthetical is not Latin-alphabet (looks like a phonetic respelling into the target script)"
            )


def check_bare_transliteration_reuse(
    text: str, path: str, ctx: str, report: ReportLike
) -> None:
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
    key = path.rsplit(".", 1)[-1].split("[")[0]
    if key in _SKIP_KEYS:
        return
    glosses = find_greek_hebrew_glosses(text)
    wellformed_spans = [(s, e) for s, e, _, i2, wf in glosses if wf and i2]
    for _, end, _, inner, well_formed in glosses:
        if not (well_formed and inner):
            continue
        for m in re.finditer(rf"\b{re.escape(inner)}\b", text[end:]):
            m_start, m_end = end + m.start(), end + m.end()
            if any(s <= m_start and m_end <= e for s, e in wellformed_spans):
                continue
            report.E(
                f"{ctx}: '{inner}' reused as bare Latin text later in this field with no accompanying native-script gloss (every occurrence needs its own '<word>, ({inner})', see gloss_format.json 'Bare reuse without a gloss')"
            )
            break


def _rtl_script_re_for_lang(lang: str):
    """Return the compiled character-class regex for `lang`'s own native
    script, or None if `lang` isn't a known language, or its script isn't
    marked "rtl" in native_script_ranges.json's `direction` field. No
    hardcoded language list here — RTL-ness is data in that file (same
    file and loader _phonetic_respelling_re_for_lang uses), not a second
    copy of it in Python. hi/ja/zh are also in that file but marked
    "ltr", since gluing them to a Greek/Hebrew gloss with no space
    doesn't produce the bidi/visual-order bug this check exists for."""
    entry = load_native_script_ranges().get(lang)
    if not entry or entry.get("direction") != "rtl":
        return None
    return re.compile(f"[{''.join(entry['blocks'])}]")


def check_script_boundary_spacing(
    text: str, path: str, lang: str, ctx: str, report: ReportLike
) -> None:
    """HARD GATE: an RTL language's own native script must never sit
    directly adjacent to a Greek/Hebrew gloss character with no
    whitespace between them. Catches glued-prefix bugs like 'بِـσῴζω'
    (should be 'بِـ σῴζω') that format-only checks on the gloss itself
    can't see, since the gloss span is well-formed — the bug is in what
    touches it from the RTL side.

    Deliberately narrow to Greek/Hebrew (the _GREEK_RE / _HEBREW_RE
    ranges used for glosses elsewhere in this module), NOT general Latin
    — RTL prose legitimately sits with zero space against ASCII
    punctuation (سؤال!, نعم.) and Latin loanwords are sometimes
    intentionally unspaced. Flagging any RTL-adjacent-to-Latin pair is
    far too broad and fires on normal prose; the actual bug class is
    specifically RTL script glued to a Greek/Hebrew gloss term.
    """
    key = path.rsplit(".", 1)[-1].split("[")[0]
    if key in _SKIP_KEYS:
        return
    rtl_re = _rtl_script_re_for_lang(lang)
    if rtl_re is None or not rtl_re.search(text):
        return
    foreign_re = re.compile(f"{_GREEK_RE.pattern}|{_HEBREW_RE.pattern}")
    for i in range(len(text) - 1):
        a, b = text[i], text[i + 1]
        rtl_then_foreign = rtl_re.match(a) and foreign_re.match(b)
        foreign_then_rtl = foreign_re.match(a) and rtl_re.match(b)
        if rtl_then_foreign or foreign_then_rtl:
            snippet = text[max(0, i - 10) : i + 12]
            report.E(
                f"{ctx}: {lang} native script glued directly to a Greek/Hebrew gloss with no space — '{snippet}' (RTL/LTR script-boundary bug, insert a space)"
            )


def _native_script_re_for_lang(lang: str):
    """Return the compiled character-class regex for `lang`'s own native
    script, or None if `lang` isn't in native_script_ranges.json (i.e. its
    own script is already Latin — nothing to check). Unlike
    _rtl_script_re_for_lang, this ignores `direction`: it's used to detect
    the language's own script standing in for a missing gloss, which can
    happen regardless of writing direction."""
    entry = load_native_script_ranges().get(lang)
    if not entry:
        return None
    return re.compile(f"[{''.join(entry['blocks'])}]")


def check_strong_code_native_script(
    text: str, path: str, lang: str, ctx: str, report: ReportLike
) -> None:
    """HARD GATE: a Strong's-code citation (G1234, H5678, "Strong G40", ...)
    always cites a real Hebrew or Greek word. If the text around it contains
    the file's own native script (Arabic, Devanagari, ...) but no genuine
    Hebrew/Greek character, the citation is dangling — the actual word was
    replaced by a phonetic respelling into the target script, or dropped
    entirely, and the Strong code is the only surviving evidence a gloss
    was ever meant to be here.

    This closes a real gap in find_greek_hebrew_glosses: that function (and
    everything built on it — check_greek_hebrew_transliteration's phonetic-
    respelling detector, check_bare_transliteration_reuse) only fires once
    it finds an actual Hebrew/Greek Unicode character to anchor on. A
    string like Arabic 'سْكليروس (G4642)' has no such character anywhere —
    سْكليروس is Arabic letters arranged to sound like Greek σκληρός, not
    σκληρός itself — so the whole detection pipeline stays silent even
    though this is the same "phonetic respelling instead of Latin
    transliteration" bug gloss_format.json already documents for AR/HI/JA/ZH
    (see its 'violations_not_accepted'). The Strong code is what makes this
    case detectable at all: a citation with nothing genuine nearby is
    itself the signal, independent of which script filled the gap.

    Latin-script languages (de, en, es, fil, fr, pt, ...) have no entry in
    native_script_ranges.json and skip this check entirely — a Strong code
    embedded in Latin-script prose is unremarkable (the language's own
    script can't be mistaken for the missing word).
    """
    key = path.rsplit(".", 1)[-1].split("[")[0]
    if key in _SKIP_KEYS:
        return
    native_re = _native_script_re_for_lang(lang)
    if native_re is None:
        return
    foreign_re = re.compile(f"{_GREEK_RE.pattern}|{_HEBREW_RE.pattern}")
    for m in _strong_code_re().finditer(text):
        start = max(0, m.start() - _STRONG_CODE_WINDOW)
        end = min(len(text), m.end() + _STRONG_CODE_WINDOW)
        window = text[start:end]
        if native_re.search(window) and not foreign_re.search(window):
            snippet = text[start:end].replace("\n", " ")
            report.E(
                f"{ctx}: Strong code '{m.group(0)}' has no real Hebrew/Greek word nearby — only {lang} native script, which is likely a phonetic respelling standing in for the missing gloss (found: '...{snippet}...', see gloss_format.json 'Phonetic respelling into the target script instead of Latin')"
            )


# A native-script word run immediately (zero space, no comma) followed by
# a bare Latin transliteration in parentheses — e.g. Chinese '道(Logos)' or
# '拯救者(Amnos)'. Confirmed in the wild 2026-07-28: 52 occurrences across
# the whole zh discovery+encounters corpus (logos_creation, morning_star,
# restoration_by_fire, new_covenant_cup, and others), zero false positives
# — every parenthetical word sampled was a genuine Greek/Hebrew
# transliteration (Logos, Amnos, AGAPAS, YHWH, kippur, ...), never an
# ordinary English gloss/acronym. Zero hits in ja/hi/ar, which either
# space the parenthetical differently or haven't picked up this habit —
# For Latin-script locales, the equivalent anchor is the complete word before
# the parenthesis: it is an error only when that word is *not* the same
# transliteration (e.g. ``love(agape)``). ``agape(agape)`` is ordinary prose,
# not a substituted translation-word.
_native_bare_translit_re_cache = None


def _native_bare_translit_re():
    """Compiled from gloss_format.json's native_script_bare_transliteration_gate
    min/max length rather than hardcoded here — same _load_gloss_format()
    reuse pattern as _translit_diacritic_re()."""
    global _native_bare_translit_re_cache
    if _native_bare_translit_re_cache is None:
        gate = _load_gloss_format()["native_script_bare_transliteration_gate"]
        lo, hi = gate["min_translit_length"], gate["max_translit_length"]
        _native_bare_translit_re_cache = re.compile(
            rf"[^\s(]\(([A-Za-zÁÉÍÓÚÝáéíóúýĀāĒēĪīŌōŪūḖḗṒṓ]{{{lo},{hi}}})\)"
        )
    return _native_bare_translit_re_cache


_LATIN_WORD_AT_END_RE = re.compile(r"[A-Za-zÁÉÍÓÚÝáéíóúýĀāĒēĪīŌōŪūḖḗṒṓ]+$")


def _normalized_translit(word: str) -> str:
    """Compare transliterations without treating case/diacritics as meaning.

    Corpus prose may write ``AGAPAS`` beside ``agapās``; that is still the
    same transliteration, whereas ``love(agape)`` is the malformed shape this
    gate is intended to expose in Latin-script locales.
    """
    return "".join(
        char
        for char in unicodedata.normalize("NFD", word).casefold()
        if not unicodedata.combining(char)
    )


def check_native_script_bare_transliteration(
    text: str, path: str, lang: str, ctx: str, report: ReportLike, lexicon=None
) -> None:
    """HARD GATE: `lang`'s own native script glued directly (no space, no
    comma) to a bare Latin transliteration in parentheses — e.g. Chinese
    '道(Logos)' — means the real Greek/Hebrew word was never given at all,
    only a Chinese gloss/translation standing next to the transliteration
    that was meant to accompany it (required form: '<Greek/Hebrew word>,
    (translit)', see gloss_format.json). Distinct from
    check_word_study_bare_transliteration (which needs the whole field to
    have zero Greek/Hebrew characters anywhere and a macron diacritic as
    its trigger): this fires per-occurrence, anchored on the native-script
    letter immediately before the parenthesis, so it still catches this
    bug even in a field that also contains a separate, correctly-formed
    gloss elsewhere.

    `lexicon` (optional, a shared_validation.lexicon_source.LexiconSource):
    when a Strong's-code citation (see find_nearby_strong_citation) sits
    right after the bare transliteration — e.g. '道(Logos G3056)' — the
    real headword is knowable even though it was never written out, so
    this checks the given transliteration against Strong's own spelling
    for that code and reports a spelling mismatch instead of the generic
    missing-word error. No corpus example of this shape exists yet (all
    52 occurrences found 2026-07-28 have no nearby Strong's code); this
    branch is forward-looking, same reuse (find_nearby_strong_citation +
    lookup_by_number) as check_strong_code_native_script already uses
    elsewhere in this module. `lexicon=None` (the default) skips this
    branch entirely and always falls back to the shape-only error below.

    In Latin-script languages (de, en, es, fil, fr, pt, ...), the same shape
    is only an error when the full Latin word immediately before the paren is
    different from the transliteration. This catches a translated meaning
    word substituted for the missing Greek/Hebrew word (``love(agape)``),
    while allowing an ordinary repeated transliteration (``agape(agape)``).
    """
    key = path.rsplit(".", 1)[-1].split("[")[0]
    if key in _SKIP_KEYS:
        return
    native_re = _native_script_re_for_lang(lang)
    for m in _native_bare_translit_re().finditer(text):
        translit = m.group(1)
        if not _LATIN_TRANSLIT_RE.match(translit):
            continue
        if native_re is not None:
            if not native_re.match(text[m.start()]):
                continue
        else:
            preceding = _LATIN_WORD_AT_END_RE.search(text[: m.start() + 1])
            normalized_translit = _normalized_translit(translit)
            if (
                preceding is None
                or _normalized_translit(preceding.group(0))
                == normalized_translit
                # Romance-language inclusive forms such as ``tel(le)`` and
                # ``ami(e)`` are not transliterations.  The gate's two-letter
                # minimum is necessary for non-Latin scripts (e.g. ``ēn``),
                # but would otherwise mistake this ordinary suffix notation
                # for a Latin-language gloss.
                or (
                    len(normalized_translit) <= 2
                    and (
                        _normalized_translit(preceding.group(0)).endswith(
                            normalized_translit
                        )
                        # ``tel(le)`` overlaps its final ``l`` with the
                        # optional feminine suffix; it is likewise ordinary
                        # inclusive-language notation.
                        or _normalized_translit(preceding.group(0))[-1:]
                        == normalized_translit[:1]
                    )
                )
            ):
                continue
        if lexicon is not None:
            code, citation_end = find_nearby_strong_citation(text, m.end(), lang)
            if code:
                entry = lexicon.lookup_by_number(code)
                if entry is not None:
                    if translit.lower().strip() != entry.translit.lower().strip():
                        report.E(
                            f"{ctx}: '{translit}' near Strong's code '{code}' — {entry.strongs_number} gives '{entry.translit}', not '{translit}' — check spelling (native-script word is still missing, required format: '<word>, ({entry.translit})', see gloss_format.json)"
                        )
                    else:
                        report.E(
                            f"{ctx}: '{translit}' ({code}) is a bare transliteration standing next to a Strong's code with no native-script word given anywhere (required format: '<word>, ({translit})' with the native-script word present, see gloss_format.json)"
                        )
                    continue
        anchor = (
            f"{lang} native script"
            if native_re is not None
            else f"the Latin meaning-word '{preceding.group(0)}'"
        )
        report.E(
            f"{ctx}: '{translit}' in parentheses is glued directly to {anchor} with no comma — the real Greek/Hebrew word was never given, only its transliteration next to a gloss (required format: '<word>, ({translit})' with the Greek/Hebrew word present, see gloss_format.json)"
        )


# An ALL-CAPS (optionally macron/acute-accented) Latin word immediately
# followed by a Strong's-code citation in parentheses — e.g. "DIATHĒKĒ
# (Strong G1242)" or "ESTIN (G1510)". This is the Latin-script twin of the
# bug check_strong_code_native_script catches for non-Latin languages: the
# Strong code always cites a real Hebrew/Greek word, but here the only
# thing standing in for it is the word's own transliteration in full caps
# — the native-script word was never given at all. Confirmed in the wild
# 2026-07-27 across every Latin-script language (de/en/es/fil/fr/pt) in
# new_covenant_cup, gethsemane_agony, cup_of_wrath, passed_from_death, and
# saints_resurrected — zero false positives against the full corpus scan.
_ALLCAPS_STRONG_CODE_RE = re.compile(
    r"\b([A-ZĀĒĪŌŪÁÉÍÓÚḔṌ][A-ZĀĒĪŌŪÁÉÍÓÚḔṌ]{1,20})\s*\((?:Strong\s+)?([A-Z]\d{1,5})\)"
)


def check_strong_code_bare_transliteration(
    text: str, path: str, ctx: str, report: ReportLike
) -> None:
    """HARD GATE: in Latin-script prose, an ALL-CAPS word immediately
    before a Strong's-code citation — "DIATHĒKĒ (Strong G1242)" — is the
    same dangling-citation bug check_strong_code_native_script catches for
    non-Latin languages, just with the target script already being Latin.
    check_strong_code_native_script skips Latin-script languages entirely
    on the assumption that "a Strong code embedded in Latin-script prose is
    unremarkable" — true in general, but not when the word right next to
    the code is itself a bare transliteration standing in for the missing
    native-script word. No native-script anchor is needed to see this one:
    the ALL-CAPS shape directly adjacent to the citation is the signal.
    """
    key = path.rsplit(".", 1)[-1].split("[")[0]
    if key in _SKIP_KEYS:
        return
    if _GREEK_RE.search(text) or _HEBREW_RE.search(text):
        return
    for m in _ALLCAPS_STRONG_CODE_RE.finditer(text):
        report.E(
            f"{ctx}: '{m.group(1)}' is a bare transliteration standing next to Strong code '{m.group(2)}' with no real Hebrew/Greek word given anywhere (required format: '<word>, ({m.group(1).lower()})' with the native-script word present, see gloss_format.json)"
        )


# 'word' (word) — a quoted word immediately followed by a parenthetical
# word, both short enough to be a single term rather than a clause. This is
# the shape a bare transliteration takes when it was never given a real
# Greek/Hebrew anchor anywhere — e.g. "'mujer' (gynai)" or "'Skēnē'
# (tienda)" — but the same shape is also completely ordinary prose (e.g.
# "'esclerosis' (endurecimiento)"), so this regex alone is not a signal;
# see check_word_study_bare_transliteration for the diacritic filter that
# separates the two.
_QUOTED_PAREN_PAIR_RE = re.compile(
    r"['‘’\"]([^'‘’\"()]{2,30})['‘’\"]\s*\(([^()]{2,30})\)"
)
_translit_diacritic_re_cache = None


def _translit_diacritic_re():
    """Character class of gloss_format.json's macron_only_diacritics (ā, ē,
    ī, ō, ū, ḗ, ṓ) — deliberately the macron-only subset of
    transliteration_charset.diacritics_in_use, not the full list. The full
    list also includes plain acutes (á é í ó ú), which are ordinary
    Spanish/Portuguese/French orthography ('está', 'é', 'cántaros') and
    produced dozens of false positives when first tried as the trigger
    here (2026-07-27) — macrons never occur in Romance-language prose, so
    they're the low-noise signal. Read from that file rather than
    hardcoded here, same as every other charset in this module. A
    plain-ASCII transliteration (e.g. "gynai") or one using only an acute
    and no macron (e.g. "ktémata") is indistinguishable from an ordinary
    word by shape alone and is not caught here; see
    check_word_study_bare_transliteration's docstring."""
    global _translit_diacritic_re_cache
    if _translit_diacritic_re_cache is None:
        diacritics = _load_gloss_format()["transliteration_charset"][
            "macron_only_diacritics"
        ]["marks"]
        _translit_diacritic_re_cache = re.compile(f"[{''.join(diacritics)}]")
    return _translit_diacritic_re_cache


def check_word_study_bare_transliteration(
    text: str, path: str, ctx: str, report: ReportLike
) -> None:
    """WARNING: a quoted word immediately followed by a parenthetical word
    (either order — "'mujer' (gynai)" or "'Skēnē' (tienda)") where one side
    carries this corpus's own scholarly-transliteration diacritics (ā, ē,
    ī, ō, ū, ...) but the whole string has no real Hebrew/Greek character
    anywhere. That combination means a Greek/Hebrew word is being discussed
    by its transliteration only, with the actual native-script word never
    given at all — not even a malformed attempt, just entirely absent.

    Confirmed in the wild 2026-07-27: cana_wedding's "'mujer' (gynai)" and
    morning_star's "'Skēnē' (tienda)" / "'tienda de carne' (sarx)" — none
    of these ever cite the real Greek word or a Strong's code anywhere in
    the file, so neither find_greek_hebrew_glosses (needs a real
    Hebrew/Greek character to anchor on) nor check_strong_code_native_script
    (needs an explicit citation code to anchor on) can see them.

    The diacritic requirement is what keeps this from false-positiving on
    completely ordinary prose of the identical shape — "'esclerosis'
    (endurecimiento)" is a quoted word with its own gloss in parens, and
    "it IS a real Spanish word" is the only difference from "'Skēnē'
    (tienda)", which isn't a distinction this check (or any regex) can
    make. It can only fire when one side of the pair looks like scholarly
    romanization, which ordinary vocabulary essentially never does. A
    plain-ASCII transliteration with no diacritic at all (e.g. "gynai"
    itself, or "ti emoi kai soi") is NOT caught by this check for the same
    reason — there is no shape left to distinguish it from a real word,
    and it stays a manual reverse-read item, same as the already-documented
    ja duplicate-gloss case.
    """
    key = path.rsplit(".", 1)[-1].split("[")[0]
    if key in _SKIP_KEYS:
        return
    if _GREEK_RE.search(text) or _HEBREW_RE.search(text):
        return
    diacritic_re = _translit_diacritic_re()
    for m in _QUOTED_PAREN_PAIR_RE.finditer(text):
        quoted, parenthetical = m.group(1), m.group(2)
        if diacritic_re.search(quoted) or diacritic_re.search(parenthetical):
            report.W(
                f"{ctx}: '{quoted}' ({parenthetical}) has the shape of a bare Greek/Hebrew transliteration (scholarly diacritic present) but the field has no real Hebrew/Greek character anywhere — likely discussing a word by its transliteration only, with the actual native-script word never given (see gloss_format.json 'transliteration_charset')"
            )


# Languages confirmed 2026-07-31 to carry the whole-clause bare-
# transliteration/respelling bug (logos_creation_{zh,ar,ja,hi}_001.json,
# all quoting John 1:1's three Greek clauses this way in cards[1].content).
# Deliberately an explicit enum, NOT driven by native_script_ranges.json
# membership: that file groups zh with ja/hi (all three have a `blocks`
# entry), but zh's real bug is bare-LATIN transliteration (no Chinese
# characters in the parenthetical at all, same shape as ar), while ja/hi's
# bug is phonetic respelling INTO their own native script — two different
# checks below, and native_script_ranges.json's grouping doesn't line up
# with which check each language needs. Latin-script languages
# (en/es/pt/de/fil/...) are never in scope for either variant: an ALL-CAPS
# scripture quote followed by a transliteration in a Latin-script field
# (e.g. en 'IN THE BEGINNING WAS THE WORD' (Ēn archē ēn ho Logos)) is not
# a bug — the reader's own language already IS the target script, there is
# nothing being "respelled into" or substituted for.
_CLAUSE_BUG_LATIN_TRANSLIT_LANGS = {"zh", "ar"}
_CLAUSE_BUG_PHONETIC_RESPELLING_LANGS = {"ja", "hi"}

# A quoted native-language translation immediately followed by a
# parenthetical clause — 3+ space/interpunct-separated tokens. Interpunct
# '・' is included in the token-splitting class since JA renders each
# transliterated syllable as its own katakana run joined by '・', not by
# whitespace. Length caps come from gloss_format.json's
# word_study_bare_clause_transliteration_gate (the exact longest confirmed
# real instance, not a round-number guess) — see _quoted_paren_clause_re()
# below, same _load_gloss_format() reuse pattern as _native_bare_translit_re().
_quoted_paren_clause_re_cache = None


def _quoted_paren_clause_re():
    global _quoted_paren_clause_re_cache
    if _quoted_paren_clause_re_cache is None:
        gate = _load_gloss_format()["word_study_bare_clause_transliteration_gate"]
        q_hi = gate["max_quoted_length"]
        p_hi = gate["max_parenthetical_length"]
        _quoted_paren_clause_re_cache = re.compile(
            rf"['‘’\"「]([^'‘’\"「」()（）]{{2,{q_hi}}})['‘’\"」]\s*[\(（]([^()（）]{{2,{p_hi}}})[\)）]"
        )
    return _quoted_paren_clause_re_cache


# Whole-parenthetical purity test for the Latin-transliteration variant
# (zh, ar): every token must itself be a well-formed transliteration word
# (same charset _LATIN_TRANSLIT_RE already validates for single-word
# glosses — ASCII + scholarly diacritics, nothing else), and at least one
# token must carry a macron (the low-noise scholarly-romanization signal
# _translit_diacritic_re already uses — see check_word_study_bare_
# transliteration's docstring for why acutes alone are too noisy). This is
# what rejects ordinary explanatory asides that happen to contain a Latin
# loanword (e.g. ar 'قوة' (dynamis = قوة جسدية) — 'dynamis' has no macron
# and the rest of the parenthetical isn't Latin transliteration at all, so
# it correctly fails the "every token is transliteration" test).
def _is_bare_latin_clause(tokens: list) -> bool:
    if not any(_translit_diacritic_re().search(t) for t in tokens):
        return False
    return all(_LATIN_TRANSLIT_RE.match(t) for t in tokens)


# Whole-parenthetical purity test for the phonetic-respelling variant (ja,
# hi): every character in the parenthetical must be in the language's own
# native-script Unicode block, plus only the '・' interpunct and
# whitespace as separators — reusing _phonetic_respelling_re_for_lang's
# script_class construction so this stays in sync with the same source
# language definitions rather than re-deriving script ranges here. This is
# what rejects ordinary Hindi/Arabic sentences that merely contain 3+
# words of native script: e.g. hi 'फिर से' (एक बार और, दूसरी बार) — plain
# synonym elaboration — fails purity because of its comma (ordinary prose
# punctuation, not a transliteration-run separator), while the real bug hi
# 'आदि में वचन था' (एन आर्के एन हो लोगॉस) is pure Devanagari + spaces and
# correctly matches.
#
# KNOWN PRECISION GAP (hi specifically, confirmed 2026-07-31): an ordinary
# Hindi contrastive-paraphrase aside with zero internal punctuation and 3+
# words — e.g. 'जीवित प्राणी' (केवल प्राप्त करते हुए) "'living being'
# (merely receiving)" — is indistinguishable from the real bug by script
# purity alone and WILL false-positive. This is a real, accepted
# limitation, not an oversight: there is no regex-only signal left to
# separate "ordinary Devanagari paraphrase" from "Devanagari phonetic
# respelling of a Greek clause" (unlike the zh/ar bare-Latin variant,
# where the macron-diacritic trigger makes ordinary prose essentially
# impossible to false-positive on). ja is unaffected — katakana is used
# almost exclusively for loanwords/transliteration in this corpus, so
# pure-katakana asides are reliably the real bug. Every hi hit from this
# check needs a human read before acting on it; do not auto-fix based on
# this warning alone for hi. A lexicon-backed check (verifying the
# parenthetical against Strong's own transliteration, same pattern
# check_native_script_bare_transliteration uses via `lexicon` for the
# single-word case) would fix this properly but was out of scope here.
def _is_pure_native_script_clause(parenthetical: str, lang: str) -> bool:
    entry = load_native_script_ranges().get(lang)
    if not entry:
        return False
    script_class = "".join(entry["blocks"])
    pure_re = re.compile(rf"^[{script_class}・\s]+$")
    return bool(pure_re.match(parenthetical))


def check_word_study_bare_clause_transliteration(
    text: str, path: str, lang: str, ctx: str, report: ReportLike
) -> None:
    """WARNING: a quoted native-language translation immediately followed by
    a parenthetical multi-word clause transliteration/respelling of the
    underlying Greek — e.g. zh '"太初有道"(Ēn archē ēn ho Logos)', ar
    "'فِي الْبَدْءِ...' (Ēn archē ēn ho Logos)", ja
    '「初めに、ことばがあった」（エーン・アルケー・エーン・ホ・ロゴス）', hi
    "'आदि में वचन था' (एन आर्के एन हो लोगॉस)" — where the field has no real
    Hebrew/Greek character anywhere. The whole clause is being discussed by
    its transliteration (bare Latin in zh/ar) or a phonetic respelling into
    the reader's own script (katakana in ja, Devanagari in hi) with the
    actual Greek clause never given at all, same root bug
    check_word_study_bare_transliteration catches for a single word — see
    that function's docstring and gloss_format.json's
    'Three-or-more-word phrase ... instead of a 1-or-2-word gloss'
    violation.

    Scoped to exactly _CLAUSE_BUG_LATIN_TRANSLIT_LANGS |
    _CLAUSE_BUG_PHONETIC_RESPELLING_LANGS (zh/ar/ja/hi) — the confirmed
    family, not every non-Latin-script language and never a Latin-script
    one (see that set's own comment for why native_script_ranges.json
    membership alone is the wrong scoping signal here).

    Requires 3+ tokens in the parenthetical (an ordinary 1-2-word gloss
    pair is already check_word_study_bare_transliteration's job), AND the
    parenthetical must pass a whole-content purity test — every token is
    itself transliteration-shaped (zh/ar) or every character is the
    language's own native script (ja/hi) — not just "contains a native
    character/diacritic somewhere". The first draft of this check used a
    'contains' test and produced dozens of false positives on ordinary
    prose asides (2026-07-31); the purity test is what actually
    distinguishes "the whole parenthetical IS a transliterated/respelled
    clause" from "this sentence happens to touch the target script or a
    Latin loanword".

    KNOWN PRECISION GAP — hi specifically: confirmed clean (zero false
    positives) for zh/ar/ja; hi still produces false positives on ordinary
    punctuation-free Devanagari prose asides that happen to have 3+ words
    (e.g. "'living being' (merely receiving)"), because script purity
    alone can't distinguish that from a real phonetic-respelled clause —
    see _is_pure_native_script_clause's comment for the full explanation
    and why this is a deliberate, accepted tradeoff rather than a bug.
    Every hi hit from this check needs a human read before acting on it.
    """
    if lang not in (
        _CLAUSE_BUG_LATIN_TRANSLIT_LANGS | _CLAUSE_BUG_PHONETIC_RESPELLING_LANGS
    ):
        return
    key = path.rsplit(".", 1)[-1].split("[")[0]
    if key in _SKIP_KEYS:
        return
    if _GREEK_RE.search(text) or _HEBREW_RE.search(text):
        return
    for m in _quoted_paren_clause_re().finditer(text):
        quoted, parenthetical = m.group(1), m.group(2)
        tokens = [t for t in re.split(r"[\s・]+", parenthetical.strip()) if t]
        if len(tokens) < 3:
            continue
        if lang in _CLAUSE_BUG_LATIN_TRANSLIT_LANGS:
            matched = _is_bare_latin_clause(tokens)
        else:
            matched = _is_pure_native_script_clause(parenthetical, lang)
        if not matched:
            continue
        report.W(
            f"{ctx}: '{quoted}' ({parenthetical}) has the shape of a bare Greek clause transliteration/respelling (3+ tokens) but the field has no real Hebrew/Greek character anywhere — likely discussing a whole clause by its transliteration only, with the actual Greek text never given (see gloss_format.json 'Three-or-more-word phrase ... instead of a 1-or-2-word gloss')"
        )
