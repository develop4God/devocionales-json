"""report.py — Report class + run_phase() gate/warn helper.

Based on the Report class in encounters/encounters_scripts/validate_encounters.py
(cleaner than discovery's ValidationReport). The E/W/I contract is defined as
an explicit typing.Protocol so callers can type-hint against either the
concrete Report class here or their own compatible report object.
"""

import re
from collections.abc import Callable
from typing import Protocol, TypeVar

# Matches the "<file.json>:<location>: <detail>" shape most check functions
# already emit (e.g. "restoration_by_fire_en_001.json:cards[2].content: ...").
# Used only to group an already-printed message list by file for scanability
# — it does not change what a check emits, just how Report.print() renders it.
_FILE_PREFIX_RE = re.compile(r"^(?:❌ ERROR|⚠️  WARNING): ([A-Za-z0-9_.-]+\.json):")

# The fixed explanatory tail greek_hebrew_gloss.py's bare-transliteration
# checks repeat verbatim on every hit (same wording regardless of word/file)
# — real information (word, code, location) is always before this point, so
# for display only it's collapsed to a short tag. The messages themselves
# are untouched; this only affects how Report.print() renders them.
_BARE_TRANSLIT_TAIL_RE = re.compile(
    r"(?: \(scholarly diacritic present\))?"
    r"(?: \(3\+ tokens\))?"
    r" but the field has no real (?:Hebrew/Greek|Greek) character anywhere"
    r" — likely discussing a (?:word|whole clause) by its transliteration only,"
    r" with the actual (?:native-script word|Greek text) never given"
    r" \([^)]*\)$"
)


class ReportLike(Protocol):
    """Structural contract for anything that can receive E/W/I findings."""

    def E(self, msg: str) -> None: ...
    def W(self, msg: str) -> None: ...
    def I(self, msg: str) -> None: ...  # noqa: E743


class Report:
    def __init__(self, phase: str):
        self.phase = phase
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.info: list[str] = []

    def E(self, msg):
        self.errors.append(f"❌ ERROR: {msg}")

    def W(self, msg):
        self.warnings.append(f"⚠️  WARNING: {msg}")

    def I(self, msg):  # noqa: E743
        self.info.append(f"ℹ️  INFO: {msg}")

    def print(self, final=True) -> bool:
        print(f"\n{'=' * 80}")
        print(f"{self.phase} VALIDATION REPORT")
        print("=" * 80)
        # On a fully clean pass, RunReport's rollup already covers what ran
        # and how it went — the full per-message INFO dump here is only
        # worth the noise when there's a warning/error to give context for.
        clean = not self.errors and not self.warnings
        if self.info and not clean:
            print(f"\nℹ️  INFORMATION ({len(self.info)}):")
            for m in self.info:
                print(f"  {m}")
        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            _print_grouped_by_file(self.warnings)
        if self.errors:
            print(f"\n❌ ERRORS ({len(self.errors)}):")
            _print_grouped_by_file(self.errors)
            print("=" * 80)
            return False
        msg = (
            "✅ ALL VALIDATIONS PASSED!"
            if final
            else "✅ PHASE PASSED - Proceeding to next phase"
        )
        print(f"\n{msg}")
        print("=" * 80)
        return True


def _print_grouped_by_file(messages: list[str]) -> None:
    """Render a message list grouped by the leading 'file.json:' each
    message already carries, worst-offender file first, so a large finding
    count (e.g. 289 warnings from one recurring rule) is scannable by file
    instead of a flat wall of near-identical lines. Messages without a
    parseable file prefix are printed as-is, ungrouped, at the end — nothing
    is ever dropped for not matching the pattern."""
    by_file: dict[str, list[str]] = {}
    unmatched: list[str] = []
    for m in messages:
        match = _FILE_PREFIX_RE.match(m)
        if match:
            by_file.setdefault(match.group(1), []).append(m[match.end() :].strip())
        else:
            unmatched.append(m)

    for filename, items in sorted(by_file.items(), key=lambda kv: -len(kv[1])):
        print(f"  {filename} ({len(items)}):")
        for item in items:
            print(f"    {_BARE_TRANSLIT_TAIL_RE.sub(' [bare-translit]', item)}")

    for m in unmatched:
        print(f"  {m}")


T = TypeVar("T")


def run_phase(
    name: str, fn: Callable[[Report], T], on_fail_msg: str | None = None
) -> tuple:
    """Run a single validation phase: construct a Report, call fn(report),
    print it (non-final), and return (result, report, passed).

    This is a convenience helper for pipelines that want a uniform
    "build report, run phase function, print, gate" pattern across phases.
    It does not call sys.exit — callers decide what to do with `passed`.
    """
    report = Report(name)
    result = fn(report)
    passed = report.print(final=False)
    if not passed and on_fail_msg:
        print(on_fail_msg)
    return result, report, passed
