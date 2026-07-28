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
scope). It is READ-ONLY — see lexicon_fixer.py for the separate script that
rewrites TRANSLIT_MISMATCH occurrences in place.

Usage:
    # one family (a single study or encounter id)
    python3 shared_validation/lexicon_family_check.py --type discovery --id gold_silver_ashes_001
    python3 shared_validation/lexicon_family_check.py --type encounters --id peter_water_001

    # one folder (every id of one content type)
    python3 shared_validation/lexicon_family_check.py --type discovery
    python3 shared_validation/lexicon_family_check.py --type encounters

    # whole corpus (both content types, every id)
    python3 shared_validation/lexicon_family_check.py --all

Exit code: 0 if no TRANSLIT_MISMATCH found anywhere scanned, 1 otherwise.
INFLECTED_NO_LEMMA_MATCH is informational only and never affects exit code.
"""

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from shared_validation.family_resolver import RESOLVERS, ID_LISTERS  # noqa: E402
from shared_validation.lexicon_check import (  # noqa: E402
    check_lexical_accuracy,
    check_structured_word_study_accuracy,
    LexicalStatus,
)
from shared_validation.lexicon_source import StrongsLexiconSource  # noqa: E402
from shared_validation.text_checks import iter_strings  # noqa: E402

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

    def E(self, msg):  # noqa: N802
        print(f"  {RED}❌ {msg}{RST}")
        self.errors += 1

    def W(self, msg):  # noqa: N802
        print(f"  {YLW}⚠️  {msg}{RST}")
        self.warnings += 1

    def I(self, msg):  # noqa: E743, N802
        print(f"  {CYN}ℹ️  {msg}{RST}")
        self.infos += 1


def run_for_family(
    content_type: str,
    content_id: str,
    lexicon: StrongsLexiconSource,
    debug: bool = False,
) -> int:
    """Run the lexical-accuracy check for every language file of one content
    item. Returns the TRANSLIT_MISMATCH count (the only outcome that fails
    the gate)."""
    family = RESOLVERS[content_type](content_id)
    if not family:
        print(f"No {content_type} item with id '{content_id}' found in index.json")
        return 1

    report = _ReportAdapter()
    print(f"\n── {content_type}/{content_id} ──")
    matched = 0
    for lang, path in sorted(family.items()):
        if not path.exists():
            report.W(f"{lang}: file listed in index but not found at {path}")
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            report.E(f"{lang}: invalid JSON in {path.name}: {e}")
            continue
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
            matched += sum(1 for r in results if r.status == LexicalStatus.MATCHED)

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
                    )
                    if result.status == LexicalStatus.MATCHED:
                        matched += 1

    if report.errors == 0:
        print(
            f"  {GRN}✅ no lexical mismatches ({matched} gloss(es) matched Strong's){RST}"
        )
    return report.errors


def run_for_type(
    content_type: str, lexicon: StrongsLexiconSource, debug: bool = False
) -> int:
    """Run the check for every id of one content type. Returns the total
    TRANSLIT_MISMATCH count across all ids."""
    total_errors = 0
    for content_id in ID_LISTERS[content_type]():
        total_errors += run_for_family(content_type, content_id, lexicon, debug)
    return total_errors


def run_all(lexicon: StrongsLexiconSource, debug: bool = False) -> int:
    """Run the check across the whole corpus (both content types)."""
    total_errors = 0
    for content_type in RESOLVERS:
        total_errors += run_for_type(content_type, lexicon, debug)
    return total_errors


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
        total_errors = run_all(lexicon, args.debug)
    elif args.id:
        if not args.type:
            parser.error("--id requires --type")
        total_errors = run_for_family(args.type, args.id, lexicon, args.debug)
    elif args.type:
        total_errors = run_for_type(args.type, lexicon, args.debug)
    else:
        parser.error("pass --id/--type, --type alone, or --all")

    print(f"\n{'=' * 60}")
    if total_errors == 0:
        print("✅ PASSED — no Strong's transliteration mismatches found")
    else:
        print(f"❌ FAILED — {total_errors} transliteration mismatch(es) vs Strong's")
    print(f"{'=' * 60}")

    sys.exit(0 if total_errors == 0 else 1)


if __name__ == "__main__":
    main()
