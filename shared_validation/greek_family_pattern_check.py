#!/usr/bin/env python3
"""
greek_family_pattern_check.py — standalone cross-file Greek/Hebrew gloss
consistency scanner.

Extracted from shared_validation/family_check.py (previously
check_greek_hebrew_consistency, wired into every PHASE E family-validation
run). Kept here as the same detection primitive, decoupled from run() so it
can be wired back in — into family_check.run(), a master validator phase,
or a standalone CI job — without re-deriving the logic. Not currently called
by any validate_*.py entrypoint or master validator; this module is the
detection layer only, run manually or via the CLI below until a caller
wires it in.

What it checks: the same source-language item translated into N languages
should carry the exact same sequence of native-script Greek/Hebrew words at
the exact same field position (a translation changes the surrounding prose,
never the word being studied), and the same Latin transliteration for each
occurrence. No language is treated as ground truth — the "correct" pattern
for each occurrence is the one the majority of well-formed languages agree
on (ties broken by first-seen), then every language at that position is
graded against it: ✓ if it matches, ✗ if it doesn't. Malformed occurrences
(see gloss_format.json) are excluded from the vote so a shared spec
violation can't outvote a compliant minority — malformed-format checking
itself is greek_hebrew_gloss.py's job, not this module's; a malformed
occurrence here is shown as excluded, not marked ✗.

Reuses, never reimplements:
    - shared_validation.family_check.{Reporter, load_all, check_drift}
    - shared_validation.greek_hebrew_gloss.find_greek_hebrew_glosses
    - shared_validation.text_checks.iter_strings
    - each pipeline's own index.json + files map (same resolution
      discovery_scripts/validate_family.py and
      encounters_scripts/validate_family.py already use)

Usage:
    # one family (a single study or encounter id)
    python3 shared_validation/greek_family_pattern_check.py --type discovery --id mammon_anxiety_freedom_001
    python3 shared_validation/greek_family_pattern_check.py --type encounters --id peter_water_001

    # one folder (every id of one content type)
    python3 shared_validation/greek_family_pattern_check.py --type discovery
    python3 shared_validation/greek_family_pattern_check.py --type encounters

    # whole corpus (both content types, every id)
    python3 shared_validation/greek_family_pattern_check.py --all

Exit code: 0 if no cross-file Greek/Hebrew gloss errors found, 1 otherwise.
"""

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from shared_validation.family_check import Reporter, load_all, check_drift  # noqa: E402
from shared_validation.family_resolver import RESOLVERS, ID_LISTERS  # noqa: E402
from shared_validation.greek_hebrew_gloss import find_greek_hebrew_glosses  # noqa: E402
from shared_validation.text_checks import iter_strings  # noqa: E402


# ── Detection primitive ───────────────────────────────────────────────────────


def _build_gloss_index(loaded: dict[str, dict]) -> dict[str, dict[str, list]]:
    """{field_path: {lang: [(word, inner, well_formed), ...]}} for every
    Greek/Hebrew gloss occurrence found in every loaded language file."""
    by_field: dict[str, dict[str, list]] = {}
    for lang, data in loaded.items():
        for path, text in iter_strings(data):
            spans = find_greek_hebrew_glosses(text)
            if not spans:
                continue
            field = re.sub(r"\[\d+\]", "[]", path)
            occurrences = [(word, inner, wf) for _, _, word, inner, wf in spans]
            by_field.setdefault(field, {})[lang] = occurrences
    return by_field


def _triage_occurrence(
    field: str, i: int, per_lang: dict[str, list], report: Reporter
) -> None:
    """Grade every language's gloss #i of `field` against the majority-agreed
    correct pattern (word + transliteration), per gloss_format.json's single
    canonical form. Prints one ✓/✗ line per language; ✗ increments
    report.errors, matching every other family_check finding."""
    wellformed = {
        lang: (occ[i][0], occ[i][1])
        for lang, occ in per_lang.items()
        if i < len(occ) and occ[i][2]
    }
    if len(wellformed) < 2:
        return  # not enough well-formed data at this position to vote on a "correct" pattern

    (correct_word, correct_inner), _ = Counter(wellformed.values()).most_common(1)[0]
    report.info(
        f"'{field}' gloss #{i + 1} — correct pattern: '{correct_word}, ({correct_inner})'"
    )
    for lang in sorted(per_lang):
        occ = per_lang[lang]
        if i >= len(occ):
            report.warn(f"  {lang}: no occurrence at this position (excluded)")
            continue
        word, inner, wf = occ[i]
        if not wf:
            report.warn(
                f"  {lang}: malformed gloss near '{word}' (excluded — see greek_hebrew_gloss.py)"
            )
            continue
        if (word, inner) == (correct_word, correct_inner):
            report.ok(f"  ✓ {lang}: '{word}, ({inner})'")
        else:
            report.err(
                f"  ✗ {lang}: '{word}, ({inner})' — expected '{correct_word}, ({correct_inner})'"
            )


def check_greek_hebrew_consistency(loaded: dict[str, dict], report: Reporter) -> None:
    """Cross-file consistency for inline Greek/Hebrew word-study glosses across
    every loaded language file of one content item. See module docstring for
    the full rationale."""
    by_field = _build_gloss_index(loaded)
    for field, per_lang in sorted(by_field.items()):
        if len(per_lang) < 2:
            continue
        check_drift(
            f"greek/hebrew gloss count in '{field}'",
            {lang: len(occ) for lang, occ in per_lang.items()},
            report,
        )
        max_n = max(len(occ) for occ in per_lang.values())
        for i in range(max_n):
            _triage_occurrence(field, i, per_lang, report)


# ── Runner ────────────────────────────────────────────────────────────────────


def run_for_family(content_type: str, content_id: str) -> int:
    """Run the Greek/Hebrew cross-file check for one content item. Returns the
    error count."""
    family = RESOLVERS[content_type](content_id)
    if not family:
        print(f"No {content_type} item with id '{content_id}' found in index.json")
        return 1

    report = Reporter()
    loaded = load_all(family, report)
    if len(loaded) < 2:
        print(
            f"{content_type}/{content_id}: fewer than 2 files loaded — skipping (need at least 2 languages to cross-check)"
        )
        return report.errors

    print(f"\n── {content_type}/{content_id} ──")
    check_greek_hebrew_consistency(loaded, report)
    if report.errors == 0:
        print("  ✅ no cross-file Greek/Hebrew gloss drift")
    return report.errors


def run_for_type(content_type: str) -> int:
    """Run the check for every id of one content type. Returns the total error
    count across all ids."""
    total_errors = 0
    for content_id in ID_LISTERS[content_type]():
        total_errors += run_for_family(content_type, content_id)
    return total_errors


def run_all() -> int:
    """Run the check across the whole corpus (both content types)."""
    total_errors = 0
    for content_type in RESOLVERS:
        total_errors += run_for_type(content_type)
    return total_errors


def main():
    parser = argparse.ArgumentParser(
        description="Cross-file Greek/Hebrew gloss consistency scanner "
        "(family, folder, or whole-corpus scope)."
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
    args = parser.parse_args()

    if args.all:
        total_errors = run_all()
    elif args.id:
        if not args.type:
            parser.error("--id requires --type")
        total_errors = run_for_family(args.type, args.id)
    elif args.type:
        total_errors = run_for_type(args.type)
    else:
        parser.error("pass --id/--type, --type alone, or --all")

    print(f"\n{'=' * 60}")
    if total_errors == 0:
        print("✅ PASSED — no cross-file Greek/Hebrew gloss drift found")
    else:
        print(f"❌ FAILED — {total_errors} cross-file Greek/Hebrew gloss error(s)")
    print(f"{'=' * 60}")

    sys.exit(0 if total_errors == 0 else 1)


if __name__ == "__main__":
    main()
