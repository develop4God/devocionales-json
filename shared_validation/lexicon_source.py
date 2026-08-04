"""lexicon_source.py — abstraction over "a dictionary that maps a native-script
lemma to its canonical transliteration and gloss".

lexicon_check.py depends only on the LexiconSource protocol, never on Strong's
specifically (Dependency Inversion). Swapping in Mounce's NT dictionary, BDB,
or a custom curated list later means writing one new class here — nothing in
lexicon_check.py changes.

Data files are the pre-cleaned, unified-schema JSON derived from
openscriptures/strongs (github.com/openscriptures/strongs, CC-BY-SA):
  greek/strongs-greek-dictionary.js  -> lexicon_data/strongs_greek.json
  hebrew/strongs-hebrew-dictionary.js -> lexicon_data/strongs_hebrew.json

Both files share one schema per entry, keyed by Strong's number:
    {"lemma": <native script>, "translit": <official transliteration>,
     "gloss": <short definition>}

The two source .js files did NOT share a schema natively (Greek used
"translit", Hebrew used "xlit"/"pron") — that inconsistency is resolved once,
at data-generation time, not at lookup time.
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import NamedTuple, Protocol


class LexiconEntry(NamedTuple):
    strongs_number: str
    lemma: str
    translit: str
    gloss: str


def _normalized_translit(word: str) -> str:
    """Strip diacritics and casefold, so a corpus transliteration written
    without Strong's own stress marks (e.g. 'anamnesis') still matches its
    headword ('anámnēsis', G364). Same tiny algorithm already duplicated in
    greek_hebrew_gloss.py and lexicon_fixer.py for the identical reason
    (comparing transliterations without treating case/accent as meaning) —
    not imported from either, since lexicon_source.py sits below both in
    the dependency graph (this module's own docstring) and importing from
    a caller would invert that. Kept in sync by hand; not worth a larger
    refactor to deduplicate for a 6-line function."""
    return "".join(
        char
        for char in unicodedata.normalize("NFD", word).casefold()
        if not unicodedata.combining(char)
    )


# native_script_ranges.json's per-language Unicode block ranges + writing
# direction — moved here (from greek_hebrew_gloss.py, which used to own a
# private copy of this exact loader) so both modules can share one loader
# without a circular import: greek_hebrew_gloss.py already imports from
# this module (resolve_lemma_entry), so this module cannot also import
# from greek_hebrew_gloss.py — the loader has to live on this, the lower,
# side of that dependency for both callers to reuse it. See that file's
# _phonetic_respelling_re_for_lang / _rtl_script_re_for_lang for how it's
# used there; find_nearby_strong_citation below is this module's own user
# of the same data.
_NATIVE_SCRIPT_RANGES_PATH = Path(__file__).parent / "native_script_ranges.json"
_native_script_ranges_cache: dict | None = None


def load_native_script_ranges() -> dict:
    global _native_script_ranges_cache
    if _native_script_ranges_cache is None:
        with open(_NATIVE_SCRIPT_RANGES_PATH, encoding="utf-8") as f:
            _native_script_ranges_cache = json.load(f)["ranges"]
    return _native_script_ranges_cache


class LexiconSource(Protocol):
    """Anything that can resolve a native-script lemma to its lexicon entry."""

    def lookup_by_lemma(self, word: str) -> list[LexiconEntry]:
        """Every headword entry matching `word` exactly, in Strong's-number
        order. Empty list if `word` is not a dictionary headword at all
        (e.g. it's an inflected surface form — callers decide what to do
        with that, this layer does not guess stems). More than one entry
        means `word` is genuinely ambiguous in this lexicon — see
        StrongsLexiconSource's docstring for why that's common (real data,
        not an edge case): callers that already have a candidate Strong's
        number (e.g. one already cited in the source text) should pass it to
        `lookup_by_lemma_and_number` to disambiguate; callers with no such
        hint must decide how to handle multiple candidates themselves."""
        ...

    def lookup_by_lemma_and_number(
        self, word: str, strongs_number: str
    ) -> LexiconEntry | None:
        """Exact lemma match narrowed to one specific Strong's number —
        disambiguates the list lookup_by_lemma returns when `word` collides
        across multiple headwords. Returns None if `word` has no entry under
        that specific number (either `word` isn't a headword at all, or it
        is one but not under this number)."""
        ...

    def lookup_by_number(self, strongs_number: str) -> LexiconEntry | None:
        """Direct lookup by Strong's number, e.g. 'G1096' or 'H1961'."""
        ...

    def lookup_by_translit(self, translit: str) -> list[LexiconEntry]:
        """Every headword entry whose OWN transliteration matches `translit`,
        diacritic/case-insensitively — e.g. 'anamnesis' matches G364's
        'anámnēsis'. Same list-return shape as lookup_by_lemma for the same
        reason: transliteration collisions are real (664 confirmed across
        the combined Greek+Hebrew data, e.g. 'ō' alone maps to 3 different
        Strong's numbers), so callers with no disambiguating hint must
        handle multiple candidates themselves. Empty list if `translit`
        matches no headword's transliteration at all — that is NOT proof
        the underlying word is fictional, only that this specific spelling
        isn't a Strong's headword transliteration (e.g. it could be an
        inflected surface form, same caveat as lookup_by_lemma)."""
        ...


class StrongsLexiconSource:
    """LexiconSource backed by the openscriptures/strongs JSON data files.

    Loads once at construction, held in memory for the life of the process —
    this is static 1890-vintage reference data, never fetched over the
    network and never re-read per lookup.

    Lemma collisions are real and common, not an edge case: 646 distinct
    Hebrew lemmas (out of ~7,900) map to 2+ Strong's numbers — e.g. עוּר is
    both H5782 ("to wake") and H5784 ("chaff"), two unrelated words that
    happen to share the same consonantal spelling (Hebrew's written form
    doesn't disambiguate the way vowel points/context do). Greek has a
    handful too (7 lemmas). A single {lemma: entry} dict silently drops all
    but the last-loaded entry for every collision — verified against the
    real data (not assumed) after lookup_by_lemma appeared to "correct" an
    already-right Strong's citation in hammer_of_god_001 to a different,
    also-plausible number for the same lemma. `_by_lemma` therefore maps to
    a list of every candidate; disambiguation is the caller's job via
    lookup_by_lemma_and_number, using whatever Strong's number (if any) the
    source text already cites as the hint.

    Case mismatch is a second, independent source of false "not a
    headword" misses, Greek-only (Hebrew has no case): the corpus quotes a
    word exactly as Greek grammar requires wherever it appears — capitalized
    at the start of a sentence/heading/title — while openscriptures stores
    every headword in plain dictionary-citation form, which is lowercase
    except for a handful of proper nouns. An exact-string dict lookup treats
    that capitalization difference as "different word," identical to a
    genuinely-absent inflected form, so 3 real words across 30 corpus
    occurrences (ᾍδης, Λογίζομαι, Δύναμις — discovery/saints_resurrected_001,
    discovery/union_with_christ_001, encounters/bleeding_woman_001) went
    unmatched and uncorrected through every fixer/checker run this session
    until caught by a dedicated corpus-wide casefold() scan. `_by_lemma_ci`
    mirrors `_by_lemma` casefold()-keyed (Unicode-correct case folding, not
    `.lower()` — handles final-sigma and every other multi-character case
    mapping) and is consulted only when the exact-case lookup misses, so it
    never changes behavior for the normal case-matching path. It is NOT a
    blanket "ignore case" policy: Strong's own data has 6 lowercase forms
    that collide across two truly distinct headwords under case-folding
    (e.g. Στέφανος "Stephen" vs στέφανος "crown") — casefold() naturally
    surfaces both as candidates in that case, same as any other lemma
    collision, so the existing lookup_by_lemma_and_number/
    resolve_lemma_entry disambiguation-by-nearby-Strong-code path handles
    it with no new logic; verified none of those 6 collision words are
    used anywhere in this corpus, so this fallback is unambiguous in
    every real case found so far.

    Combining-mark order is a third, independent source of false "not a
    headword" misses, Hebrew-only (niqqud are combining marks; Greek
    accents are precomposed): two strings can be visually identical and
    NFC/NFD-equal under unicodedata.normalize, yet still fail a raw `==`
    dict lookup because the corpus and Strong's data disagree on which
    combining mark comes first at the same base letter (e.g. tsere before
    dagesh vs. dagesh before tsere on the same הִנֵּה) — Python does not
    canonicalize combining-mark order for you outside of explicit NFC/NFD
    normalization. Found in zechariah_14_return_001 (all 10 languages):
    the corpus's הִנֵּה byte-differs from H2009's stored הִנֵּה though both
    are the same word. `_by_lemma`/`_by_lemma_ci` are keyed (and queried)
    NFC-normalized for this reason — same fix scripture_check.py's
    _normalize() already applies to verse text for the identical reason,
    see that function's docstring.
    """

    _DATA_DIR = Path(__file__).parent / "lexicon_data"

    def __init__(
        self, greek_path: Path | None = None, hebrew_path: Path | None = None
    ):
        greek_path = greek_path or self._DATA_DIR / "strongs_greek.json"
        hebrew_path = hebrew_path or self._DATA_DIR / "strongs_hebrew.json"

        self._by_number: dict[str, LexiconEntry] = {}
        self._by_lemma: dict[str, list[LexiconEntry]] = {}
        self._by_lemma_ci: dict[str, list[LexiconEntry]] = {}
        self._by_translit_norm: dict[str, list[LexiconEntry]] = {}

        for path in (greek_path, hebrew_path):
            with open(path, encoding="utf-8") as f:
                raw = json.load(f)
            for number, fields in raw.items():
                entry = LexiconEntry(
                    strongs_number=number,
                    lemma=fields["lemma"],
                    translit=fields["translit"],
                    gloss=fields["gloss"],
                )
                self._by_number[number] = entry
                if entry.lemma:
                    lemma_nfc = unicodedata.normalize("NFC", entry.lemma)
                    self._by_lemma.setdefault(lemma_nfc, []).append(entry)
                    self._by_lemma_ci.setdefault(lemma_nfc.casefold(), []).append(entry)
                if entry.translit:
                    self._by_translit_norm.setdefault(
                        _normalized_translit(entry.translit), []
                    ).append(entry)

        for index in (self._by_lemma, self._by_lemma_ci, self._by_translit_norm):
            for entries in index.values():
                entries.sort(key=lambda e: e.strongs_number)

    def lookup_by_lemma(self, word: str) -> list[LexiconEntry]:
        word_nfc = unicodedata.normalize("NFC", word)
        exact = self._by_lemma.get(word_nfc)
        if exact:
            return list(exact)
        return list(self._by_lemma_ci.get(word_nfc.casefold(), []))

    def lookup_by_translit(self, translit: str) -> list[LexiconEntry]:
        return list(self._by_translit_norm.get(_normalized_translit(translit), []))

    def lookup_by_lemma_and_number(
        self, word: str, strongs_number: str
    ) -> LexiconEntry | None:
        word_nfc = unicodedata.normalize("NFC", word)
        for entry in self._by_lemma.get(word_nfc, []):
            if entry.strongs_number == strongs_number:
                return entry
        for entry in self._by_lemma_ci.get(word_nfc.casefold(), []):
            if entry.strongs_number == strongs_number:
                return entry
        return None

    def lookup_by_number(self, strongs_number: str) -> LexiconEntry | None:
        return self._by_number.get(strongs_number)


# The single rule for locating an existing Strong's-code citation right
# after a gloss's own ", (translit)" tail: take the "token" immediately
# following the gloss — however it's shaped (bare "H4074)", full-width
# "（H4074）", dash-prefixed "-G728):", whatever) — and if it contains a
# Strong's-shaped code (letter + 2-5 digits) anywhere in it, that whole
# token is "the existing citation" to be replaced wholesale with the
# canonical "(STRONG)". No per-shape special-casing (bracketed vs bare vs
# dash vs colon) — one rule, applied uniformly, because this corpus turned
# out to have too many distinct malformed shapes to special-case correctly.
#
# What ends the token differs by script, which is why this needs the
# caller's own language's native-script character class (same data source
# greek_hebrew_gloss.py's phonetic-respelling/RTL checks already use,
# native_script_ranges.json):
#   - Latin-script languages (no native-script range — de/en/es/fil/fr/pt/...):
#     the token ends at the next whitespace, same as an ordinary word. A
#     sentence's own closing paren right after a bare code (e.g.
#     "(מָדַי, (Mâday) H4074) is..." — the ")" sits inside the token
#     "H4074)" together with the digits) gets replaced as part of that
#     token, same as the digits.
#   - Languages with their own native script and no spaces between words
#     (ja/zh) or where the citation is embedded directly against native
#     prose with no whitespace at all: whitespace can't mark the boundary
#     (there may be none), so the token instead ends at the first character
#     of the file's own native script — that's provably where the
#     surrounding sentence's real content resumes, since the citation
#     itself (Latin letters, digits, brackets) never overlaps with it.
#     ar/hi still have whitespace between words, so this falls back to the
#     whitespace rule for them in practice, but the native-script boundary
#     is checked first regardless (a defensive backstop, not the primary
#     mechanism, for RTL languages where a citation might not be
#     whitespace-separated from following native text).
_STRONG_IN_TOKEN_RE = re.compile(r"[GH]\d{2,5}")
_NEARBY_STRONG_WINDOW = 40


_native_script_class_cache: dict[str, str | None] = {}


def is_rtl_lang(lang: str) -> bool:
    """True if `lang`'s own script is marked "rtl" in
    native_script_ranges.json (currently only 'ar') — the same flag
    check_script_boundary_spacing already uses for the bidi glue-check.
    Used by find_nearby_strong_citation's caller to decide whether a
    Strong's-code citation might legitimately precede the gloss instead of
    following it: RTL authors typing a bulleted citation in their own
    reading order can produce "• H5221 נָכָה, (nākhāh): meaning" (code
    first), a real convention observed in the wild
    (balaam_humble_vision_001/ar), not noise or a formatting error."""
    entry = load_native_script_ranges().get(lang)
    return bool(entry and entry.get("direction") == "rtl")


def _native_script_class_for_lang(lang: str) -> str | None:
    """The regex character class for `lang`'s own native script (e.g.
    ja -> '぀-ヿ一-鿿'), read from native_script_ranges.json, or None for a
    Latin-script language (no entry there). Cached per language since the
    ranges file never changes at runtime — same caching pattern
    greek_hebrew_gloss.py's _phonetic_respelling_re_for_lang uses for the
    same underlying data."""
    if lang in _native_script_class_cache:
        return _native_script_class_cache[lang]
    entry = load_native_script_ranges().get(lang)
    result = "".join(entry["blocks"]) if entry else None
    _native_script_class_cache[lang] = result
    return result


def find_nearby_strong_citation(
    text: str, end: int, lang: str | None = None
) -> tuple[str | None, int]:
    """Look at the "token" immediately following `end` (a gloss span's end
    offset, skipping exactly one leading space if present) for a Strong's-
    shaped code. Returns (code, citation_end): code is the code found (or
    None if the token has no such code, or there's no token there at all —
    e.g. straight to a "would-be-empty" citation like ") = meaning...");
    citation_end is the absolute offset where that whole token ends (==
    `end` if no token/code found, so callers can always use it as a safe
    slice boundary).

    `lang` is the file's own language code (e.g. 'ja', 'ar', 'en') — used
    to look up that language's native-script class via
    native_script_ranges.json (None for a Latin-script language, meaning
    there's nothing but whitespace to bound the token on). When a native
    script class exists, the token ends at whichever comes first: the next
    whitespace, or the next character in that script — this is what lets
    ja/zh (no spaces between words) still find the right boundary. See the
    module comment above for the full rationale."""
    native_script_class = _native_script_class_for_lang(lang) if lang else None
    window = text[end : end + _NEARBY_STRONG_WINDOW]
    rest = window[1:] if window[:1] == " " else window
    offset = end + (1 if window[:1] == " " else 0)
    stop_pattern = r"\s" if not native_script_class else rf"\s|{native_script_class}"
    token_match = re.match(rf"(?:(?!{stop_pattern}).)+", rest)
    if not token_match:
        return None, end
    token = token_match.group(0)
    code_match = _STRONG_IN_TOKEN_RE.search(token)
    if not code_match:
        return None, end
    return code_match.group(0), offset + token_match.end()


def resolve_lemma_entry(
    lexicon: LexiconSource, word: str, text: str, end: int, lang: str | None = None
) -> tuple[LexiconEntry | None, tuple[LexiconEntry, ...]]:
    """Single shared resolution step for 'which Strong's entry does this
    gloss span mean' — used by every caller that needs a lemma resolved
    (the lexical-accuracy checker, the hard-gate transliteration check, and
    the fixer) so all three never disagree on how a collision is resolved.

    Returns (resolved_entry, all_candidates):
      - no candidates at all: (None, ())                    — word isn't a headword (e.g. inflected form)
      - exactly one candidate: (that entry, (that entry,))  — ordinary matched/mismatched case
      - 2+ candidates, a nearby Strong's-code hint picks one: (that entry, all candidates)
      - 2+ candidates, no hint (or hint matches none of them): (None, all candidates) — genuinely ambiguous

    `lang` is passed through to find_nearby_strong_citation so the
    disambiguation hint's token boundary is correct for CJK files (no
    whitespace between words) — see that function's docstring.
    """
    candidates = tuple(lexicon.lookup_by_lemma(word))
    if not candidates:
        return None, ()
    if len(candidates) == 1:
        return candidates[0], candidates
    hint, _ = find_nearby_strong_citation(text, end, lang)
    if hint:
        resolved = lexicon.lookup_by_lemma_and_number(word, hint)
        if resolved is not None:
            return resolved, candidates
    return None, candidates
