#!/usr/bin/env python3
"""
lexicon_family_check.py — standalone lexical-accuracy scanner for inline
Greek/Hebrew glosses, checked against Strong's Concordance instead of
cross-file majority vote.

Why this exists (and why greek_family_pattern_check.py's majority vote is
not enough): a majority-vote check can only ever detect DISAGREEMENT between
languages. If the same wrong transliteration was copy-pasted into most or all
language files, every file agrees with every other file — majority vote sees
perfect consensus and reports nothing, even though the shared value is
factually wrong. This module sidesteps that failure mode entirely: it never
compares one language file to another. Every gloss in every file is checked,
independently, against one fixed external authority (Strong's Concordance),
so a spec violation that spread identically into all 10 languages is caught
exactly the same way a violation in just one language would be.

Reuses, never reimplements:
    - shared_validation.lexicon_source.StrongsLexiconSource (the Strong's data)
    - shared_validation.lexicon_check.check_lexical_accuracy (the per-span check)
    - shared_validation.greek_hebrew_gloss.find_greek_hebrew_glosses (span extraction,
      via check_lexical_accuracy — not called directly here)
    - shared_validation.text_checks.iter_strings (walking every text field of a file)
    - shared_validation.family_resolver (index.json -> {lang: path} resolution)

This module only owns the reporting shell (loading files, walking fields,
tallying MATCHED/INFLECTED_NO_LEMMA_MATCH/TRANSLIT_MISMATCH per file, CLI
scope). It is READ-ONLY — it never rewrites content.

Usage:
    # one family (a single study or encounter id)
    python3 shared_validation/lexicon_family_check.py --type discovery --id gold_silver_ashes_001
    python3 shared_validation/lexicon_family_check.py --type encounters --id peter_water_001

    # one folder (every id of one content type)
    python3 shared_validation/lexicon_family_check.py --type discovery
    python3 shared_validation/lexicon_family_check.py --type encounters

    # whole corpus (both content types, every id)
    python3 shared_validation/lexicon_family_check.py --all

Exit code: 0 only if nothing was flagged anywhere scanned — no
TRANSLIT_MISMATCH, no citation-balance warning, no info. Any finding of any
severity fails the run (per-user directive 2026-08-15: no silent passing).
"""

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent

from shared_validation.checks.family_resolver import ID_LISTERS, RESOLVERS
from shared_validation.checks.lexicon_check import (
    LexicalStatus,
    check_lexical_accuracy,
    check_structured_word_study_accuracy,
)
from shared_validation.checks.lexicon_source import StrongsLexiconSource
from shared_validation.checks.text_checks import iter_strings
from shared_validation.report import ReportLike

RED, YLW, GRN, CYN, RST = "\033[91m", "\033[93m", "\033[92m", "\033[96m", "\033[0m"


class _ReportAdapter:
    """Adapts report.py's ReportLike (E/W/I) contract onto the counters this
    runner's summary needs, and prints each finding as it arrives. A separate
    small class rather than reusing family_check.Reporter (which speaks a
    different method contract: ok/warn/err/info) or report.py's Report
    (which buffers per-phase rather than printing inline, and isn't scoped
    per-family the way this runner's per-id output is) — see gloss_format.json
    for why a single canonical spec, not either existing reporter shape, is
    what both checks in this repo now share."""

    def __init__(self):
        self.errors = 0
        self.warnings = 0
        self.infos = 0

    def E(self, msg):
        print(f"  {RED}❌ {msg}{RST}")
        self.errors += 1

    def W(self, msg):
        print(f"  {YLW}⚠️  {msg}{RST}")
        self.warnings += 1

    def I(self, msg):  # noqa: E743
        print(f"  {CYN}ℹ️  {msg}{RST}")
        self.infos += 1


def check_family_citation_balance(
    counts_by_lang: dict[str, dict[str, int]],
    report: ReportLike,
) -> None:
    """Warn when a Strong's code's citation COUNT diverges across a family's
    languages, even though every individual citation is independently
    well-formed and lexically correct (i.e. check_lexical_accuracy already
    passed on all of them).

    Why this exists: check_lexical_accuracy grades one gloss span at a time
    and has no notion of "how many times should this word appear in THIS
    language, given how many times it appears in its 9 siblings" — a
    citation can be individually perfect and still be missing three more
    times where a sibling language cited the same underlying word. Found
    2026-08-10 (restoration_by_fire): a phonetic respelling or a dropped
    bracket in one language's dialogue-quote/discovery_question is
    invisible to every shape-based check (no bare Latin, no malformed
    gloss) but shows up immediately as a per-language count that doesn't
    match its siblings'.

    `counts_by_lang` is `{lang: {strongs_number: count}}`, built by the
    caller from the SAME LexicalCheckResult stream check_lexical_accuracy /
    check_structured_word_study_accuracy already produce — no new
    traversal or detection regex, this is a comparison over already-graded
    results.

    For each Strong's code that appears in at least 2 languages, the most
    common count across all languages (mode; ties broken toward the
    smallest count, since under-citing is more common than over-citing in
    this corpus's edit history) is treated as the family's baseline. Every
    language whose count differs — including a language that never cites
    the word at all — gets a warning. This can be a false positive for a
    family where one language's prose genuinely never needed a word its
    siblings used (Gate 11/12 in the project's Discovery gloss master
    plan cover how to tell the two apart by reading the actual text) —
    same tier as this module's other WARNING-level findings, not a hard
    gate.
    """
    all_codes = {code for counts in counts_by_lang.values() for code in counts}
    for code in sorted(all_codes):
        per_lang = {
            lang: counts.get(code, 0) for lang, counts in counts_by_lang.items()
        }
        if len(set(per_lang.values())) <= 1:
            continue  # every language agrees, nothing to report
        counted_langs = [lang for lang, n in per_lang.items() if n > 0]
        if len(counted_langs) < 2:
            continue  # only one language cites this code at all — not a cross-family imbalance
        tally: dict[int, int] = {}
        for n in per_lang.values():
            tally[n] = tally.get(n, 0) + 1
        baseline = min(tally, key=lambda n: (-tally[n], n))
        for lang in sorted(per_lang):
            n = per_lang[lang]
            if n != baseline:
                report.W(
                    f"{lang}: Strong's {code} cited {n} time(s), but {baseline} "
                    f"is the family's common count across its sibling languages — "
                    "possible missing/extra citation (verify by reading the text; "
                    "a language's own prose can legitimately differ)"
                )


def run_for_family(
    content_type: str,
    content_id: str,
    lexicon: StrongsLexiconSource,
    debug: bool = False,
) -> tuple[int, int]:
    """Run the lexical-accuracy check for every language file of one content
    item. Returns (errors, warnings): TRANSLIT_MISMATCH count (the only
    outcome that fails the gate) and citation-balance warning count from
    check_family_citation_balance (advisory, never gates)."""
    family = RESOLVERS[content_type](content_id)
    if not family:
        print(f"No {content_type} item with id '{content_id}' found in index.json")
        return 1, 0

    report = _ReportAdapter()
    print(f"\n── {content_type}/{content_id} ──")
    matched = 0
    counts_by_lang: dict[str, dict[str, int]] = {}
    for lang, path in sorted(family.items()):
        if not path.exists():
            report.W(f"{lang}: file listed in index but not found at {path}")
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            report.E(f"{lang}: invalid JSON in {path.name}: {e}")
            continue
        lang_counts = counts_by_lang.setdefault(lang, {})
        for field_path, text in iter_strings(data):
            ctx = f"{lang}:{field_path}"
            results = check_lexical_accuracy(
                text=text,
                lexicon=lexicon,
                path=str(path),
                lang=lang,
                ctx=ctx,
                report=report,
                debug=debug,
            )
            for r in results:
                if r.status == LexicalStatus.MATCHED:
                    matched += 1
                    lang_counts[r.strongs_number] = (
                        lang_counts.get(r.strongs_number, 0) + 1
                    )

        # The structured greek_words/hebrew_words array (word +
        # transliteration as separate JSON keys) is a distinct shape from
        # inline ", (translit)" prose — iter_strings/check_lexical_accuracy
        # above never sees it as a gloss (find_greek_hebrew_glosses needs
        # both parts in the SAME string). Same traversal shape
        # discovery_schema_checks.py's presence-check already uses for this
        # array, extended here to grade lexical accuracy instead of just
        # checking the fields are non-empty.
        for i, card in enumerate(data.get("cards", []) or []):
            for key in ("greek_words", "hebrew_words"):
                for j, w in enumerate(card.get(key) or []):
                    word, translit = w.get("word"), w.get("transliteration")
                    if not word or not translit:
                        continue  # discovery_schema_checks.py's job to flag, not this one's
                    ctx = f"{lang}:cards[{i}].{key}[{j}]"
                    result = check_structured_word_study_accuracy(
                        word=word,
                        transliteration=translit,
                        lexicon=lexicon,
                        path=str(path),
                        lang=lang,
                        ctx=ctx,
                        report=report,
                        debug=debug,
                        strongs_hint=w.get("strong"),
                    )
                    if result.status == LexicalStatus.MATCHED:
                        matched += 1
                        lang_counts[result.strongs_number] = (
                            lang_counts.get(result.strongs_number, 0) + 1
                        )

    check_family_citation_balance(counts_by_lang, report)

    if report.errors == 0 and report.warnings == 0 and report.infos == 0:
        print(
            f"  {GRN}✅ no lexical mismatches ({matched} gloss(es) matched Strong's){RST}"
        )
    return report.errors, report.warnings + report.infos


def run_for_type(
    content_type: str, lexicon: StrongsLexiconSource, debug: bool = False
) -> tuple[int, int]:
    """Run the check for every id of one content type. Returns (errors,
    warnings) totals across all ids."""
    total_errors = 0
    total_warnings = 0
    for content_id in ID_LISTERS[content_type]():
        errors, warnings = run_for_family(content_type, content_id, lexicon, debug)
        total_errors += errors
        total_warnings += warnings
    return total_errors, total_warnings


def run_all(lexicon: StrongsLexiconSource, debug: bool = False) -> tuple[int, int]:
    """Run the check across the whole corpus (both content types)."""
    total_errors = 0
    total_warnings = 0
    for content_type in RESOLVERS:
        errors, warnings = run_for_type(content_type, lexicon, debug)
        total_errors += errors
        total_warnings += warnings
    return total_errors, total_warnings


def main():
    parser = argparse.ArgumentParser(
        description="Lexical-accuracy scanner for inline Greek/Hebrew glosses, "
        "checked against Strong's Concordance (not cross-file majority vote)."
    )
    parser.add_argument(
        "--type",
        choices=sorted(RESOLVERS),
        help="Content type to scan (discovery or encounters). Required unless --all is passed.",
    )
    parser.add_argument(
        "--id",
        help="A single content id to scan (family scope). Requires --type. "
        "Omit to scan every id of --type (folder scope).",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Scan every id of every content type (whole-corpus scope). Ignores --type/--id.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print every gloss span's resolution decision (given vs Strong's "
        "official transliteration, exact-match result) as the scan runs — "
        "including MATCHED spans, which a plain run never reports. Verbose — "
        "use with --id for one family.",
    )
    args = parser.parse_args()

    lexicon = StrongsLexiconSource()  # loaded once, reused across the whole run

    if args.all:
        total_errors, total_warnings = run_all(lexicon, args.debug)
    elif args.id:
        if not args.type:
            parser.error("--id requires --type")
        total_errors, total_warnings = run_for_family(
            args.type, args.id, lexicon, args.debug
        )
    elif args.type:
        total_errors, total_warnings = run_for_type(args.type, lexicon, args.debug)
    else:
        parser.error("pass --id/--type, --type alone, or --all")

    total_findings = total_errors + total_warnings
    print(f"\n{'=' * 60}")
    if total_findings == 0:
        print("✅ PASSED — no Strong's lexicon findings")
    else:
        print(
            f"❌ FAILED — {total_errors} mismatch(es), {total_warnings} "
            "citation-balance warning(s)/info(s) vs Strong's"
        )
    print(f"{'=' * 60}")

    sys.exit(0 if total_findings == 0 else 1)


if __name__ == "__main__":
    main()
