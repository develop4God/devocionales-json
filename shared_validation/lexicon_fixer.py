#!/usr/bin/env python3
"""
lexicon_fixer.py — rewrites inline Greek/Hebrew glosses to match Strong's
Concordance exactly: fixes a wrong transliteration AND inserts/corrects the
trailing Strong's-code citation, producing the single canonical shape
"WORD, (translit) (STRONG)" for every well-formed gloss with a real Strong's
lemma match.

Strong's is the single source of truth (SOT) for this corrective pass — see
lexicon_family_check.py's module docstring for why: a wrong transliteration
(or a wrong/missing/malformed Strong's code) that was copy-pasted identically
into every language file can't be caught or fixed by comparing files to each
other (every file agrees with every other file), only by checking each one
independently against a fixed external authority. This script is the write
side of that same check: whatever Strong's records for a lemma is written
exactly as Strong's gives it — diacritics, circumflexes, ayin/aleph glyphs
and all — with no attempt to "normalize" it back into whatever casing/
diacritic convention the corpus happened to use before. The corpus conforms
to Strong's, not the reverse.

Two independent corrections are made per well-formed gloss with a real
Strong's lemma match, either or both as needed:
    1. Transliteration spelling — replaced with entry.translit verbatim if
       it doesn't match (case/diacritic-insensitive comparison decides
       whether a fix is needed; the replacement itself is exact).
    2. Strong's-code citation — inserted as " (STRONG)" immediately after
       the gloss if missing, or corrected if the wrong code is already
       present. Any existing citation is detected regardless of its shape
       (bare "H4074)" swallowed by the gloss's own outer paren, full-width
       "（H4074）", dash/colon-separated, or already-canonical) and replaced
       wholesale — never left behind as leftover duplicate text.

It never touches:
    - malformed spans (greek_hebrew_gloss.py's hard gate is what flags
      those; a malformed span isn't trustworthy input for this rewrite)
    - INFLECTED_NO_LEMMA_MATCH spans (the word isn't a dictionary headword —
      there's nothing in Strong's to replace it with; these stay a manual/
      human-confirmation item, same as lexicon_family_check.py's INFO output)

Editing strategy: operates on the file's raw text (not a re-serialized
`json.dumps` of the parsed object), replacing only the exact gloss-plus-
citation substring at each flagged span's offset. This preserves the file's
existing formatting (key order, indentation, unrelated escaping) byte-for-
byte outside the fixed span — re-serializing the whole parsed JSON object
risks silently reordering keys or changing quote/escape style elsewhere in
the file, which is not this script's job to do.

Usage:
    # dry run (default) — show what would change, write nothing
    python3 shared_validation/lexicon_fixer.py --type discovery --id gold_silver_ashes_001

    # actually write the fixes
    python3 shared_validation/lexicon_fixer.py --type discovery --id gold_silver_ashes_001 --apply

    # one folder / whole corpus, same --type/--id/--all scope as lexicon_family_check.py
    python3 shared_validation/lexicon_fixer.py --type discovery --apply
    python3 shared_validation/lexicon_fixer.py --all --apply

Exit code: 0 always on a dry run; on --apply, 0 if every flagged mismatch in
scope was successfully rewritten, 1 if any file failed to load/write.
"""

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from shared_validation.family_resolver import ID_LISTERS, RESOLVERS
from shared_validation.greek_hebrew_gloss import find_greek_hebrew_glosses
from shared_validation.lexicon_source import (
    StrongsLexiconSource,
    is_rtl_lang,
    load_native_script_ranges,
    resolve_lemma_entry,
)


# A single JSON string field, e.g. "transliteration": "Nakaj" — captures the
# quoted value so it can be replaced in place without disturbing anything
# else in the file (indentation, key order, neighboring fields). Built per
# call from the exact key name and old value, not a generic pattern, so it
# can only ever match the one field intended.
def _json_string_field_re(key: str, value: str) -> re.Pattern:
    return re.compile(rf'("{re.escape(key)}"\s*:\s*)"{re.escape(value)}"')


# A Strong's-shaped code, wherever it appears (used bounded by the next
# occurrence's start — see _fix_file_text). Matches gloss_format.json's
# strong_code_prefixes spec: a single uppercase Latin letter + 2-5 digits.
_STRONG_CODE_RE = re.compile(r"[GH]\d{2,5}")
# Hard cap on how far past a gloss's end this fixer will look for that
# gloss's OWN Strong's-code citation, applied together with (never wider
# than) the next-occurrence boundary. Needed because a missing citation
# can't be told apart from "still searching" by the next-occurrence
# boundary alone when the next real occurrence is an entire card away —
# see the comment at its use site for the corruption this prevents.
_SEARCH_WINDOW = 40
_BARE_LATIN_CANDIDATE_RE = re.compile(
    r"(?P<meaning>\S+)\s+\((?P<translit>[^()]{2,30})\)"
)

RED, YLW, GRN, CYN, RST = "\033[91m", "\033[93m", "\033[92m", "\033[96m", "\033[0m"
DBG = "\033[95m"


def _normalized_translit(word: str) -> str:
    return "".join(
        char
        for char in unicodedata.normalize("NFD", word).casefold()
        if not unicodedata.combining(char)
    )


def triage_bare_latin_glosses(
    raw_text: str, lexicon: StrongsLexiconSource, lang: str
) -> list[str]:
    """Report, without editing, Latin ``meaning (translit)`` substitutions.

    This deliberately complements the normal fixer rather than sharing its
    write path: the Greek/Hebrew lemma is absent, so a reverse Strong's lookup
    can propose a replacement but must not silently apply it.  Canonical
    ``lemma, (translit)`` spans are excluded using the existing gloss parser.
    """
    if lang in load_native_script_ranges():
        return []
    by_translit: dict[str, list] = {}
    for entry in lexicon._by_number.values():
        by_translit.setdefault(_normalized_translit(entry.translit), []).append(entry)
    canonical_ends = {
        end
        for _, end, _, _, well_formed in find_greek_hebrew_glosses(raw_text)
        if well_formed
    }
    findings = []
    for match in _BARE_LATIN_CANDIDATE_RE.finditer(raw_text):
        if match.end() in canonical_ends:
            continue
        translit = match.group("translit").strip()
        entries = by_translit.get(_normalized_translit(translit), [])
        if not entries:
            continue
        meaning = match.group("meaning")
        if len(entries) != 1:
            codes = ", ".join(entry.strongs_number for entry in entries)
            findings.append(
                f"'{meaning} ({translit})': REVIEW — ambiguous transliteration; candidates {codes}"
            )
            continue
        entry = entries[0]
        findings.append(
            f"'{meaning} ({translit})' -> '{entry.lemma}, ({entry.translit}) ({entry.strongs_number})'"
        )
    return findings


def fix_bare_latin_glosses(
    raw_text: str, lexicon: StrongsLexiconSource, lang: str
) -> tuple[str, list[str]]:
    """Apply only uniquely resolved bare-Latin replacements; keep REVIEW items."""
    if lang in load_native_script_ranges():
        return raw_text, []
    by_translit: dict[str, list] = {}
    for entry in lexicon._by_number.values():
        by_translit.setdefault(_normalized_translit(entry.translit), []).append(entry)
    canonical_ends = {
        end
        for _, end, _, _, well_formed in find_greek_hebrew_glosses(raw_text)
        if well_formed
    }
    replacements = []
    changes = []
    for match in _BARE_LATIN_CANDIDATE_RE.finditer(raw_text):
        if match.end() in canonical_ends:
            continue
        translit = match.group("translit").strip()
        entries = by_translit.get(_normalized_translit(translit), [])
        if len(entries) != 1:
            continue
        entry = entries[0]
        # Only replace the transliteration part, preserving the original
        # meaning word — the regex match spans "meaning (translit)" but we
        # must not delete the meaning (e.g. "Christ (Bema)" should become
        # "Christ (βῆμα, (bēma) (G968))", not "βῆμα, (bēma) (G968)").
        translit_start = match.start("translit")
        translit_end = match.end("translit")
        replacement = f"{entry.lemma}, ({entry.translit}) ({entry.strongs_number})"
        replacements.append((translit_start, translit_end, replacement))
        changes.append(
            f"'{match.group(0)}' -> '{match.group('meaning')} ({replacement})'"
        )
    for start, end, replacement in reversed(replacements):
        raw_text = raw_text[:start] + replacement + raw_text[end:]
    return raw_text, changes


def _fix_file_text(
    raw_text: str, lexicon: StrongsLexiconSource, lang: str, debug: bool = False
) -> tuple[str, list[str]]:
    """Scan every JSON string value's worth of text in `raw_text` isn't
    attempted here — glosses only ever occur inside string values, and
    `find_greek_hebrew_glosses` matches on the same raw file text a JSON
    string's escaped content would produce for plain-Greek/Hebrew/Latin
    characters (none of which need backslash-escaping in JSON), so scanning
    the whole file's raw text directly finds the same spans as scanning each
    decoded string field would, without needing to re-locate each field's
    span back in the original text after decoding. Returns (new_text,
    change_descriptions)."""
    changes: list[str] = []
    # Computed once against the ORIGINAL text, in forward (text) order —
    # next_starts[i] is where the i+1'th occurrence begins, the boundary
    # that keeps this occurrence's Strong-code search from crossing into
    # the next occurrence's own citation (see the search below). None for
    # the last occurrence (search runs to end of text).
    orig_spans = [s for s in find_greek_hebrew_glosses(raw_text) if s[4] and s[3]]
    next_starts = [s[0] for s in orig_spans[1:]] + [None]
    # Backward boundary for the RTL preceding-code search (see below) — the
    # previous occurrence's own end, so that search can never reach back
    # into a DIFFERENT occurrence's gloss/citation. None for the first
    # occurrence (nothing before it to bound against; search runs to start
    # of text).
    prev_ends = [None] + [s[1] for s in orig_spans[:-1]]

    # Processed LEFT-TO-RIGHT (unlike a simple offset-preserving right-to-
    # left walk) because next_starts is computed once against the original
    # text and must be corrected by how much earlier replacements in this
    # same pass have already shifted the text — that correction (`shift`)
    # only makes sense accumulating forward.
    shift = 0
    for (start, end, word, inner, well_formed), next_start_orig, prev_end_orig in zip(
        orig_spans, next_starts, prev_ends
    ):
        start, end = start + shift, end + shift
        next_start = next_start_orig + shift if next_start_orig is not None else None
        prev_end = prev_end_orig + shift if prev_end_orig is not None else None
        if debug:
            print(
                f"{DBG}[debug] word={word!r} start={start} end={end} "
                f"inner={inner!r} context={raw_text[max(0, start - 15) : end + 25]!r}{RST}"
            )
        entry, candidates = resolve_lemma_entry(lexicon, word, raw_text, end, lang)
        if debug:
            print(
                f"{DBG}[debug]   resolve_lemma_entry -> entry="
                f"{entry.strongs_number if entry else None!r} "
                f"candidates={[c.strongs_number for c in candidates]}{RST}"
            )
        if entry is None:
            if candidates:
                # 2+ Strong's headwords share this lemma and no nearby
                # citation disambiguates which one is meant (e.g. עוּר is
                # both H5782 "to wake" and H5784 "chaff") — guessing which
                # one the author meant is exactly the kind of silent, hard-
                # to-undo mistake this fixer must not make. Left for a human
                # to confirm and cite explicitly; see lexicon_check.py's
                # AMBIGUOUS_LEMMA for the read-only report of the same case.
                changes.append(
                    f"'{word}': SKIPPED — ambiguous lemma, {len(candidates)} "
                    f"Strong's headwords match {tuple(c.strongs_number for c in candidates)} "
                    "and no citation nearby disambiguates; confirm manually"
                )
            continue  # no candidates at all: INFLECTED_NO_LEMMA_MATCH — nothing to replace with

        given_norm = inner.lower().strip()
        official_norm = entry.translit.lower().strip()
        translit_fixed = given_norm != official_norm
        new_translit = entry.translit if translit_fixed else inner

        # The simplified rule: find THIS occurrence's own Strong's code (if
        # any) by searching forward from the gloss's end, but never search
        # past where the NEXT native-script word/phrase begins — that
        # boundary is what keeps two nearby occurrences (e.g. עוּר ... H5782
        # ... רוּחַ ... H7307 in one sentence) from bleeding into each
        # other's citation. Whatever sits between the gloss and that code
        # (space, dash, wrapping paren, stray extra-language debris — no
        # matter what) is simply replaced along with it; no attempt to
        # detect/preserve/rebalance a wrapping parenthesis separately, which
        # is what previously corrupted content by scanning too far.
        #
        # The next-occurrence boundary alone is NOT enough: an occurrence
        # can have no Strong code cited nearby at all (e.g. a lone
        # hebrew_words entry with the code never given), and the next real
        # occurrence can be an entire card away — thousands of characters
        # of unrelated prose, another card's title/content/hebrew_words
        # array, all silently swallowed as "the citation" if the search
        # window were only bounded by that far-off next occurrence. Verified
        # in the wild (balaam_humble_vision_001/ar: חָבַשׁ's search walked
        # past its own card's end into a completely different card's
        # content before finding an unrelated H5221 four hundred characters
        # later). A short, fixed local window (same size the original,
        # narrower citation-detection used) is always applied ON TOP OF the
        # next-occurrence boundary — whichever limit is smaller wins — so a
        # missing citation is recognized as missing quickly, not treated as
        # "still searching."
        search_limit = min(
            next_start if next_start is not None else len(raw_text),
            end + _SEARCH_WINDOW,
        )
        code_match = _STRONG_CODE_RE.search(raw_text, end, search_limit)
        canonical_citation_text = f" ({entry.strongs_number})"
        leading_code_start = None  # set only when the RTL backward path fires

        if code_match:
            existing_code = code_match.group(0)
            citation_end = code_match.end()
            # If the code is immediately followed by its own closing paren
            # (already-canonical shape, e.g. "H4074)"), consume that paren
            # too — otherwise comparing existing_text against
            # canonical_citation_text (which always includes both parens)
            # would report a false mismatch on content that's already
            # perfectly correct, since existing_text would never have a
            # trailing ")" to match against. Must check the full-width CJK
            # "）" as well as ASCII ")" — a citation wrapped in full-width
            # parens (e.g. ja/zh "（Strong G772）") has its closing paren in
            # that form, and missing it here leaves the untouched "）"
            # sitting right after the newly-inserted canonical "(G772)",
            # corrupting the text (verified in the wild:
            # discovery/ja/gethsemane_agony_ja_001.json produced
            # "(asthenḗs) (G772)）" before this fix).
            if raw_text[citation_end : citation_end + 1] in (")", "）"):
                citation_end += 1
            existing_text = raw_text[end:citation_end]
        elif is_rtl_lang(lang):
            # RTL languages can cite the Strong code BEFORE the gloss
            # instead of after — e.g. Arabic "• H5221 נָכָה, (nākhāh):
            # meaning", the author typing the citation in their own reading
            # order. Verified in the wild (balaam_humble_vision_001/ar); no
            # such case has been seen in any LTR language, so this backward
            # search only runs for RTL and only as a fallback once the
            # normal forward search finds nothing — never instead of it,
            # so an RTL language's ordinary forward citation (also seen in
            # this same file, e.g. עוּר, (ur) H5782) is never disturbed.
            # Bounded backward by prev_end (the previous occurrence's own
            # end) so this can never reach into a different occurrence's
            # own gloss or citation, same principle as the forward
            # next-occurrence bound.
            backward_limit = max(
                prev_end if prev_end is not None else 0, start - _SEARCH_WINDOW
            )
            leading_text = raw_text[backward_limit:start]
            leading_matches = list(_STRONG_CODE_RE.finditer(leading_text))
            if leading_matches:
                m = leading_matches[
                    -1
                ]  # nearest to `start`, not the first in the window
                existing_code = m.group(0)
                leading_code_start = backward_limit + m.start()
                citation_end = end
                existing_text = raw_text[leading_code_start:end]
            else:
                existing_code = None
                citation_end = end
                existing_text = ""
        else:
            existing_code = None
            citation_end = end
            existing_text = ""

        if debug:
            print(
                f"{DBG}[debug]   search bounded [{end}:{search_limit}] -> "
                f"code_match={existing_code!r} citation_end={citation_end} "
                f"leading_code_start={leading_code_start} "
                f"text_to_replace={existing_text!r}{RST}"
            )

        if leading_code_start is not None:
            # A leading code is always wrong shape (canonical target always
            # has the code AFTER the word) even when its VALUE already
            # matches — the position itself must move either way.
            code_fixed = True
            span_start = leading_code_start
        else:
            code_fixed = existing_text != canonical_citation_text
            span_start = start

        if not translit_fixed and not code_fixed:
            if debug:
                print(f"{DBG}[debug]   -> SKIP (nothing to fix){RST}")
            continue  # already fully correct — gloss and Strong's citation both match

        # When the code was leading, replace from before the word (removing
        # the leading code entirely) through the word/gloss to citation_end;
        # otherwise replace from the word's own start, same as always.
        new_span_text = f"{word}, ({new_translit}){canonical_citation_text}"
        if debug:
            print(
                f"{DBG}[debug]   REPLACE raw_text[{span_start}:{citation_end}]="
                f"{raw_text[span_start:citation_end]!r} -> {new_span_text!r}{RST}"
            )
        raw_text = raw_text[:span_start] + new_span_text + raw_text[citation_end:]
        shift += len(new_span_text) - (citation_end - span_start)

        parts = []
        if translit_fixed:
            parts.append(f"translit '{inner}' -> '{new_translit}'")
        if code_fixed:
            if existing_code is None:
                parts.append(f"strong (none) -> '{entry.strongs_number}' (inserted)")
            elif existing_code != entry.strongs_number:
                parts.append(f"strong '{existing_code}' -> '{entry.strongs_number}'")
            else:
                parts.append(
                    f"strong '{existing_code}' reformatted to canonical shape "
                    f"'{canonical_citation_text.strip()}'"
                )
        changes.append(f"'{word}': {', '.join(parts)}")
    return raw_text, changes


def _fix_structured_word_studies(
    raw_text: str, lexicon: StrongsLexiconSource, lang: str, debug: bool = False
) -> tuple[str, list[str]]:
    """Fix the OTHER shape this corpus uses for a word study: the
    greek_words/hebrew_words array, where word + transliteration are
    separate JSON keys ({"word": "נָכָה", "transliteration": "Nakaj"})
    rather than one inline ", (translit)" prose string. This is a much
    simpler and safer edit than _fix_file_text's raw-text span surgery: the
    parsed JSON structure gives an unambiguous word/transliteration pair
    with no boundary-detection needed at all (no wrapping parens, no
    nearby-debris, no RTL code-before-word convention — those are all
    inline-prose-only concerns), so only the transliteration VALUE is
    rewritten, in place, via a targeted string replacement in the raw text
    (same "preserve everything else byte-for-byte" approach _fix_file_text
    uses, for the same reason: no risk of a json.dumps reformatting the
    whole file).

    Does not touch the Strong's-code citation at all — this array shape
    doesn't have inline citation text to correct; if a "reference" field
    citing a Strong's number ever needs correcting that would be a separate,
    later addition, not assumed here.
    """
    changes: list[str] = []
    data = json.loads(raw_text)
    for i, card in enumerate(data.get("cards", []) or []):
        for key in ("greek_words", "hebrew_words"):
            for j, w in enumerate(card.get(key) or []):
                word, translit = w.get("word"), w.get("transliteration")
                if not word or not translit:
                    continue  # discovery_schema_checks.py's job to flag, not this one's
                entry, _candidates = resolve_lemma_entry(lexicon, word, "", 0, lang)
                if entry is None:
                    continue  # no single confirmed match — INFLECTED_NO_LEMMA_MATCH or AMBIGUOUS_LEMMA, same as the checker
                given_norm = translit.lower().strip()
                official_norm = entry.translit.lower().strip()
                if given_norm == official_norm:
                    continue  # already correct
                field_re = _json_string_field_re("transliteration", translit)
                new_raw_text, n = field_re.subn(
                    rf'\g<1>"{entry.translit}"', raw_text, count=1
                )
                if n == 0:
                    if debug:
                        print(
                            f"{DBG}[debug]   structured cards[{i}].{key}[{j}] "
                            f"'{word}': COULD NOT LOCATE transliteration field "
                            f"{translit!r} in raw text — skipped{RST}"
                        )
                    continue
                raw_text = new_raw_text
                changes.append(
                    f"'{word}' (cards[{i}].{key}[{j}]): translit '{translit}' -> "
                    f"'{entry.translit}'"
                )
                if debug:
                    print(
                        f"{DBG}[debug]   structured cards[{i}].{key}[{j}] "
                        f"'{word}': '{translit}' -> '{entry.translit}'{RST}"
                    )
    return raw_text, changes


def fix_file(
    path: Path,
    lexicon: StrongsLexiconSource,
    apply: bool,
    lang: str,
    debug: bool = False,
) -> list[str]:
    """Fix one file. Returns the list of change descriptions (empty if none).
    Only writes to disk when `apply` is True; a dry run always leaves the
    file untouched. `lang` is the language code this file is written in
    (e.g. the parent directory name, same as every other caller in this
    package derives it) — needed so the Strong's-citation token boundary is
    correct for CJK languages with no whitespace between words."""
    raw_text = path.read_text(encoding="utf-8")
    new_text, changes = _fix_file_text(raw_text, lexicon, lang, debug)
    new_text, structured_changes = _fix_structured_word_studies(
        new_text, lexicon, lang, debug
    )
    changes = changes + structured_changes
    if not changes:
        return []
    if apply:
        json.loads(
            new_text
        )  # fail loudly before writing if the edit broke JSON validity
        path.write_text(new_text, encoding="utf-8")
    return changes


def run_for_family(
    content_type: str,
    content_id: str,
    lexicon: StrongsLexiconSource,
    apply: bool,
    debug: bool = False,
) -> int:
    """Fix every language file of one content item. Returns the number of
    files that failed to load/write (0 on full success)."""
    family = RESOLVERS[content_type](content_id)
    if not family:
        print(f"No {content_type} item with id '{content_id}' found in index.json")
        return 1

    failures = 0
    for lang, path in sorted(family.items()):
        if not path.exists():
            continue
        if debug:
            print(f"{DBG}[debug] === {lang}:{path.name} ==={RST}")
        try:
            changes = fix_file(path, lexicon, apply, lang, debug)
        except (json.JSONDecodeError, OSError) as e:
            print(f"  {RED}❌ {lang}: failed to fix {path.name}: {e}{RST}")
            failures += 1
            continue
        if not changes:
            continue
        verb = "Fixed" if apply else "Would fix"
        print(f"  {YLW}{verb} {lang}:{path.name}{RST}")
        for change in changes:
            print(f"    {change}")
    return failures


def run_for_type(
    content_type: str, lexicon: StrongsLexiconSource, apply: bool, debug: bool = False
) -> int:
    total_failures = 0
    for content_id in ID_LISTERS[content_type]():
        total_failures += run_for_family(
            content_type, content_id, lexicon, apply, debug
        )
    return total_failures


def run_all(lexicon: StrongsLexiconSource, apply: bool, debug: bool = False) -> int:
    total_failures = 0
    for content_type in RESOLVERS:
        total_failures += run_for_type(content_type, lexicon, apply, debug)
    return total_failures


def run_bare_latin_triage(
    content_type: str | None,
    content_id: str | None,
    all_types: bool,
    lexicon: StrongsLexiconSource,
) -> int:
    """Print proposed fixes for the spaced Latin bug shape; never writes."""
    types = list(RESOLVERS) if all_types else [content_type]
    for selected_type in types:
        ids = [content_id] if content_id else ID_LISTERS[selected_type]()
        for selected_id in ids:
            family = RESOLVERS[selected_type](selected_id)
            if not family:
                print(
                    f"No {selected_type} item with id '{selected_id}' found in index.json"
                )
                return 1
            for lang, path in sorted(family.items()):
                if not path.exists():
                    continue
                try:
                    findings = triage_bare_latin_glosses(
                        path.read_text(encoding="utf-8"), lexicon, lang
                    )
                except (OSError, json.JSONDecodeError) as e:
                    print(f"  {RED}❌ {lang}: failed to triage {path.name}: {e}{RST}")
                    return 1
                if findings:
                    print(f"  {YLW}Review {lang}:{path.name}{RST}")
                    for finding in findings:
                        print(f"    {finding}")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Rewrite Greek/Hebrew gloss transliterations flagged as "
        "TRANSLIT_MISMATCH to match Strong's Concordance exactly."
    )
    parser.add_argument("--type", choices=sorted(RESOLVERS))
    parser.add_argument(
        "--id", help="A single content id (family scope). Requires --type."
    )
    parser.add_argument(
        "--all", action="store_true", help="Whole corpus, both content types."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write changes to disk. Without this flag, only prints what would change.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print every span-by-span decision (resolved entry, citation "
        "detection, wrapper handling, exact text about to be replaced) as "
        "the fixer walks each file. Verbose — use with --id for one family.",
    )
    parser.add_argument(
        "--triage-bare-latin",
        action="store_true",
        help="Read-only report of Latin 'meaning (translit)' substitutions; never writes.",
    )
    args = parser.parse_args()

    if args.triage_bare_latin and args.apply:
        parser.error(
            "--triage-bare-latin is read-only and cannot be combined with --apply"
        )
    if args.triage_bare_latin and not (args.all or args.type):
        parser.error("--triage-bare-latin requires --type or --all")
    if args.triage_bare_latin and args.id and not args.type:
        parser.error("--id requires --type")

    lexicon = StrongsLexiconSource()

    if not args.apply:
        print(
            f"{CYN}DRY RUN — no files will be modified. Pass --apply to write changes.{RST}\n"
        )

    if args.triage_bare_latin:
        failures = run_bare_latin_triage(args.type, args.id, args.all, lexicon)
    elif args.all:
        failures = run_all(lexicon, args.apply, args.debug)
    elif args.id:
        if not args.type:
            parser.error("--id requires --type")
        failures = run_for_family(args.type, args.id, lexicon, args.apply, args.debug)
    elif args.type:
        failures = run_for_type(args.type, lexicon, args.apply, args.debug)
    else:
        parser.error("pass --id/--type, --type alone, or --all")

    print(f"\n{'=' * 60}")
    if failures == 0:
        print(f"{GRN}✅ done, 0 file failures{RST}")
    else:
        print(f"{RED}❌ {failures} file(s) failed to fix{RST}")
    print(f"{'=' * 60}")

    sys.exit(0 if failures == 0 else 1)


if __name__ == "__main__":
    main()
