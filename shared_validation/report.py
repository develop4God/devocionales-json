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

# Every content filename in this corpus is "<family>_<lang>_<seq>.json" (e.g.
# "gold_silver_ashes_ar_001.json" -> family "gold_silver_ashes", lang "ar").
# Splits on the trailing "_<letters>_<digits>" so no hardcoded language list
# is needed — matches this project's existing convention of deriving such
# splits structurally rather than maintaining a second source of truth.
_FAMILY_LANG_RE = re.compile(r"^(.+)_([a-z]{2,3})_(\d+)\.json$")

# Matches the single-word "Latin text 'X' in <lang> field — possible
# untranslated leftover" message text_checks.check_no_latin_leak emits (see
# shared_validation/text_checks.py). Used only to collapse several such hits
# on the same file+field into one line listing the distinct words, since a
# tags[] list or a dense card can otherwise repeat this exact wording once
# per leaked word.
_LATIN_LEAK_WORD_RE = re.compile(
    r"^Latin text '([^']+)' in ([a-z]{2,3}) field — possible untranslated leftover$"
)

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


def _collapse_latin_leak_words(items: list[str]) -> list[str]:
    """Within one file's already-grouped messages, merge repeated
    "Latin text 'X' in <lang> field — possible untranslated leftover" hits
    that share the same leading path (e.g. several tags[i] entries reporting
    single leaked words one line each) into one "<path>: word, word, word"
    line. A dense tags[] list or card can otherwise repeat this exact
    wording once per leaked word — the path and words are still fully
    present, just joined instead of restated. Any message that doesn't
    match this exact shape (other checks, or a path that appears only once)
    is left untouched and in its original position."""
    per_path: dict[str, list[str]] = {}
    for item in items:
        path, _, rest = item.partition(": ")
        m = _LATIN_LEAK_WORD_RE.match(rest)
        if not m:
            continue
        per_path.setdefault(path, []).append(m.group(1))
    collapsible_paths = {p for p, words in per_path.items() if len(words) > 1}
    if not collapsible_paths:
        return items

    result: list[str] = []
    emitted_paths: set[str] = set()
    for item in items:
        path, _, rest = item.partition(": ")
        if path in collapsible_paths and _LATIN_LEAK_WORD_RE.match(rest):
            if path in emitted_paths:
                continue
            emitted_paths.add(path)
            words = ", ".join(per_path[path])
            result.append(
                f"{path}: Latin text {words} — possible untranslated leftover"
            )
        else:
            result.append(item)
    return result


def _print_grouped_by_file(messages: list[str]) -> None:
    """Render a message list grouped by family (the "<family>_<lang>_<seq>
    .json" filename each message already carries) and then by language
    within it, worst-offender-count first at both levels, so a large
    finding count (e.g. 163 warnings from one recurring rule) is scannable
    per study rather than scattered across arbitrarily-ordered individual
    filenames or a flat wall of near-identical lines. Files whose name
    doesn't match that pattern, and messages without a parseable file
    prefix at all, are printed as-is, ungrouped, at the end — nothing is
    ever dropped for not matching a pattern."""
    by_file: dict[str, list[str]] = {}
    unmatched: list[str] = []
    for m in messages:
        match = _FILE_PREFIX_RE.match(m)
        if match:
            by_file.setdefault(match.group(1), []).append(m[match.end() :].strip())
        else:
            unmatched.append(m)

    by_family: dict[str, dict[str, list[str]]] = {}
    unfamilied: list[tuple[str, list[str]]] = []
    for filename, items in by_file.items():
        fam_match = _FAMILY_LANG_RE.match(filename)
        if fam_match:
            family, lang = fam_match.group(1), fam_match.group(2)
            by_family.setdefault(family, {}).setdefault(lang, []).extend(items)
        else:
            unfamilied.append((filename, items))

    def family_count(langs: dict[str, list[str]]) -> int:
        return sum(len(v) for v in langs.values())

    for family, langs in sorted(by_family.items(), key=lambda kv: -family_count(kv[1])):
        print(f"  {family} ({family_count(langs)}):")
        for lang, items in sorted(langs.items(), key=lambda kv: -len(kv[1])):
            print(f"    [{lang}] ({len(items)}):")
            for item in _collapse_latin_leak_words(items):
                print(f"      {_BARE_TRANSLIT_TAIL_RE.sub(' [bare-translit]', item)}")

    for filename, items in sorted(unfamilied, key=lambda kv: -len(kv[1])):
        print(f"  {filename} ({len(items)}):")
        for item in _collapse_latin_leak_words(items):
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
