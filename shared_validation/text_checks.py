"""text_checks.py — text-field validation helpers shared by both pipelines:
quote-anomaly detection, string-tree iteration, cognate lookup, half-width
colon detection, and Latin-leak detection. The Greek/Hebrew inline gloss
hard gate lives in greek_hebrew_gloss.py; find_greek_hebrew_glosses is
imported from there since check_no_latin_leak also depends on it.

cognates.py was considered as a separate module and rejected as too small;
folded in here per the spike scope.
"""

import json
import re
from collections.abc import Iterator
from pathlib import Path

from .greek_hebrew_gloss import _strong_code_re, find_greek_hebrew_glosses
from .report import ReportLike

# Quote-like characters whose accidental back-to-back doubling indicates a
# stray-punctuation typo (e.g. »» , "" , '')
_DOUBLE_CHECK_CHARS = {'"', "'", "«", "»", "“", "”", "‘", "’"}

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
    "fr": {"courage", "grace", "grâce"},
    "pt": {"coragem", "graça"},
    "es": {"coraje", "gracia"},
    # 'Legion' is spelled identically in German (from Latin legio) and is the
    # word used in the LU17 Bible text itself (Mark 5:9) — not a missed translation.
    "de": {"legion"},
}


def is_cognate(value: str, lang: str) -> bool:
    """Return True if value is a known valid cognate word for lang."""
    return value.strip().lower() in _ROMANCE_COGNATES.get(lang, set())


def iter_strings(obj, path: str = "") -> Iterator[tuple[str, str]]:
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
    return bool(re.match(r"^[\s.!?,;:]*$", text[idx + 1 :]))


# Languages whose native typography uses a full-width colon (：) rather
# than the half-width ASCII ':' — checked in title fields only, since a
# half-width colon there is a generation/template artifact, not a stylistic
# choice (body text, greek_words, etc. legitimately mix both e.g. in inline
# Bible chapter:verse citations).
_FULLWIDTH_COLON_LANGS = {"ja", "zh"}


_TITLE_LIKE_KEYS = {"title", "subtitle"}


def check_halfwidth_colon_in_title(
    text: str, path: str, lang: str, ctx: str, report: ReportLike
) -> None:
    """Flag a half-width ':' in a title/subtitle field for ja/zh content.

    Skips colons immediately followed by a digit, since those are Bible
    chapter:verse references embedded in the title (e.g. "ヨハネ1:1",
    "诗篇22:16") and must stay half-width — scripture references are
    half-width everywhere else in the corpus.
    """
    if lang not in _FULLWIDTH_COLON_LANGS:
        return
    key = path.rsplit(".", 1)[-1].split("[")[0]
    if key not in _TITLE_LIKE_KEYS:
        return
    for i, c in enumerate(text):
        if c == ":" and not (i + 1 < len(text) and text[i + 1].isdigit()):
            report.E(f"{ctx}: half-width ':' in title should be full-width '：'")


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
            "languages": data["languages"],
            "skip_keys": set(data["skip_keys"]),
        }
    return _no_latin_languages_cache


_LATIN_LETTER_RE = re.compile(r"[A-Za-zÀ-ɏḀ-ỿ]+")
_LATIN_PUNCT_RE = re.compile(r'[,.!?"\']')


def check_no_latin_leak(
    text: str, path: str, lang: str, ctx: str, report: ReportLike
) -> None:
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

    A Strong's-code citation (G1242, H5782, "Strong G40", ...) is also
    carved out via greek_hebrew_gloss._strong_code_re — the same regex
    check_strong_code_native_script already uses to anchor on these citations
    elsewhere in the pipeline. Without this, the citation's own letter
    prefix (the bare 'G' in '(G1242)') gets matched by _LATIN_LETTER_RE and
    reported as a stray Latin leak, which it is not.
    """
    config = _load_no_latin_config()
    rules = config["languages"].get(lang)
    if rules is None:
        return
    key = path.rsplit(".", 1)[-1].split("[")[0]
    if key in config["skip_keys"]:
        return
    gloss_spans = find_greek_hebrew_glosses(text)
    strong_code_spans = [(m.start(), m.end()) for m in _strong_code_re().finditer(text)]

    def in_gloss(pos: int) -> bool:
        return any(
            start <= pos < end
            for start, end, _, _, well_formed in gloss_spans
            if well_formed
        ) or any(start <= pos < end for start, end in strong_code_spans)

    # A malformed gloss span covers only the native word itself (no ", (...)"
    # tail matched), so the stray Latin transliteration that was presumably
    # meant to follow it sits just after `end`, not inside the span. Treat a
    # Latin match starting within a few characters of a malformed span's end
    # as "near" it — this is what distinguishes a shape bug (real gloss,
    # broken punctuation) from a genuine untranslated leftover elsewhere in
    # the field, which check_greek_hebrew_transliteration's hard gate is
    # already responsible for flagging on its own.
    _NEAR_MALFORMED_GLOSS_WINDOW = 5

    def near_malformed_gloss(pos: int) -> bool:
        return any(
            0 <= pos - end <= _NEAR_MALFORMED_GLOSS_WINDOW
            for _, end, _, _, well_formed in gloss_spans
            if not well_formed
        )

    if rules.get("letters"):
        for m in _LATIN_LETTER_RE.finditer(text):
            if in_gloss(m.start()):
                continue
            if near_malformed_gloss(m.start()):
                report.W(
                    f"{ctx}: Latin text '{m.group(0)}' in {lang} field — "
                    "near a malformed Greek/Hebrew gloss, likely a shape "
                    "bug (see check_greek_hebrew_transliteration), not a "
                    "translation gap"
                )
            else:
                report.W(
                    f"{ctx}: Latin text '{m.group(0)}' in {lang} field — possible untranslated leftover"
                )

    if rules.get("punctuation"):
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
    oc, cc = text.count("«"), text.count("»")
    if oc != cc and not (oc + cc == 1 and is_verse_continuation_close(text, "«»")):
        report.W(f"{ctx}: unbalanced '«'/'»' — {oc} open vs {cc} close")

    # Straight double quotes should appear in pairs, with the same
    # verse-continuation exception as guillemets above.
    if text.count('"') % 2 != 0 and not (
        text.count('"') == 1 and is_verse_continuation_close(text, '"')
    ):
        report.W(
            f'{ctx}: odd number of straight double quotes (") — possible stray quote'
        )

    # Balanced parentheses, ASCII '()' and full-width '（）' counted as one
    # shared pair — ja/zh content legitimately opens with '（' and closes
    # with an ASCII ')' (or vice versa) within the same gloss/citation span,
    # so counting each bracket style separately produces false positives on
    # otherwise-correct content (see gold_silver_ashes_ja_001.json's
    # '金（χρυσίον, (chrysíon) (G5553))：' — one full-width opener, two
    # ASCII pairs, balanced overall). An imbalance after normalizing both
    # styles to ASCII means a real dropped/extra paren, most often a
    # Strong's-citation rewrite (see lexicon_fixer.py) that failed to close
    # the outer wrapper it was editing inside of.
    normalized = text.replace("（", "(").replace("）", ")")
    poc, pcc = normalized.count("("), normalized.count(")")
    if poc != pcc:
        report.E(
            f"{ctx}: unbalanced '('/')' — {poc} open vs {pcc} close — likely a dropped or extra parenthesis"
        )
