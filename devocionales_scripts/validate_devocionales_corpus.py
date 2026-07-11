#!/usr/bin/env python3
"""
validate_devocionales_corpus.py — Validator for the devocionales (devotional
-year) content type.

This is the live validator, invoked by devocionales_master_validator.py.
Built on shared_validation/ — reused directly, unchanged: lint_json_files
(Phase 1), Report/RunReport (phase orchestration + summary), and
load_bible_versions (Phase SOT, Bible-version legitimacy). Only the
devocionales index schema (files.<lang>.<version>.files.<year>, a 3-level
nested dict — structurally different from Discovery's {studies: [...]} and
Encounters' {encounters: [...]} array-of-objects shape) and its file-level
consistency checks are new: CorpusIndexReader and CorpusFileValidator in
this directory.

Unlike Discovery/Encounters, there is no Phase B translation cross-check —
devocionales-year content is independently authored per language, not a
translation of one canonical EN source, so that comparison does not apply.
Content-quality checks (min length, truncation, Amen endings, seasonal-leak
detection) are intentionally out of scope here — that is
validate_devocional_gui.py's job, a separate concern with a separate
(manual/interactive) lifecycle.

  PHASE 1:   Lint — verify all JSON files use indent=2 formatting
  PHASE A:   Validate index.json (schema_version, updated_at, year
             completeness) and resolve every declared (lang, version, year)
             combo — index.json is the sole filename authority, no
             convention-based fallback
  PHASE SOT: Confirm bible_version codes resolved from the live remote SOT
  PHASE B:   Validate each declared file: entries' version/language fields
             match the declaration, declared version is legitimate per the
             Bible SOT, date range matches declared year, no orphaned files
             on disk

Exit codes: 0 = all passed, 1 = errors found
"""

import sys
from pathlib import Path


def _find_repo_root(start: Path) -> Path:
    """Walk upward from `start` looking for the shared_validation/ package,
    rather than assuming a fixed directory depth (which silently breaks if
    this script is ever moved). Raises clearly instead of resolving to the
    wrong place."""
    for candidate in [start, *start.parents]:
        if (candidate / 'shared_validation').is_dir():
            return candidate
    raise RuntimeError(
        f"Could not find shared_validation/ above {start} — "
        "is this script still inside the devocionales-json repo?"
    )


_REPO_ROOT = _find_repo_root(Path(__file__).resolve().parent)
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from shared_validation.report import Report, ReportLike
from shared_validation.run_report import RunReport
from shared_validation.bible_sot import load_bible_versions, REMOTE_INDEX_URL
from shared_validation.lint import lint_json_files

from corpus_index_reader import CorpusIndexReader
from corpus_file_validator import CorpusFileValidator
from corpus_calendar_checker import CorpusCalendarChecker
from corpus_schema_checker import CorpusSchemaChecker

SCRIPTS_DIR = Path(__file__).parent
CORPUS_DIR = SCRIPTS_DIR.parent
INDEX_PATH = CORPUS_DIR / 'index.json'


# ── Phase 1: Lint ────────────────────────────────────────────────────────────

def validate_lint(report: ReportLike) -> dict:
    report.I("=" * 60)
    report.I("PHASE 1: Lint — checking JSON formatting (indent=2)")
    report.I("=" * 60)

    cache = lint_json_files(CORPUS_DIR, report, 'devocionales_scripts', severity='error')

    report.I(f"✓ Checked {len(cache)} JSON files")
    return cache


# ── Phase A: Index validation ─────────────────────────────────────────────────

def validate_index(report: ReportLike):
    report.I("=" * 60)
    report.I("PHASE A: Validating index.json")
    report.I("=" * 60)

    if not INDEX_PATH.exists():
        report.E(f"index.json not found at {INDEX_PATH}")
        return None

    reader = CorpusIndexReader(INDEX_PATH)
    if not reader.load(report):
        return None

    combos = list(reader.iter_combos(report))
    report.I(f"✓ index.json declares {len(combos)} (lang, version, year) combos")
    return reader, combos


# ── Phase SOT: Bible versions source ─────────────────────────────────────────

def validate_sot_source(report: ReportLike, bible_versions: dict, used_remote_sot: bool,
                         last_fetch_error) -> bool:
    if used_remote_sot:
        report.I(f"✓ bible_version codes resolved live from remote SOT ({REMOTE_INDEX_URL}) for all {len(bible_versions)} languages")
        return True
    reason = f" ({last_fetch_error})" if last_fetch_error else ""
    report.W(
        f"Could not reach remote SOT ({REMOTE_INDEX_URL}){reason} — fell back to the "
        f"temp-dir bible_versions cache. Results reflect the LOCAL CACHE, not confirmed "
        f"live data; re-run once network access is available before merging."
    )
    return True


# ── Phase B: Corpus files ─────────────────────────────────────────────────────

def validate_corpus_files(report: ReportLike, combos: list, bible_versions: dict) -> None:
    import json

    report.I("=" * 60)
    report.I("PHASE B: Validating corpus files against index.json + Bible SOT")
    report.I("=" * 60)

    validator = CorpusFileValidator(bible_versions)
    calendar_checker = CorpusCalendarChecker()
    schema_checker = CorpusSchemaChecker()
    declared_filenames = set()
    files_checked = 0
    languages_present = set()

    for combo in combos:
        declared_filenames.add(combo.filename)
        fpath = CORPUS_DIR / combo.filename

        if not fpath.exists():
            report.E(f"FILE MISSING: {combo.filename} (index declares {combo.lang}/{combo.version}/{combo.year})")
            continue

        try:
            data = json.loads(fpath.read_text(encoding='utf-8'))
        except json.JSONDecodeError as ex:
            report.E(f"{combo.filename}: invalid JSON: {ex}")
            continue

        entries, entry_dates = validator.validate(combo, data, report)
        calendar_checker.record(combo, entry_dates)
        if entries:
            schema_checker.check_file(combo, entries, report)
        files_checked += 1
        languages_present.add(combo.lang)

    # Orphan check: files on disk with no index.json entry.
    for fpath in sorted(CORPUS_DIR.glob("Devocional_year_*.json")):
        if fpath.name not in declared_filenames:
            report.E(f"ORPHANED FILE (not declared in index.json): {fpath.name}")

    # Cross-file calendar consistency: every combo declared for the same
    # year must share the same start date, end date, and full day-by-day
    # coverage as every other combo for that year — derived from the
    # corpus's own data, no hardcoded dates.
    calendar_checker.check(report)

    report.I(f"✓ Checked {files_checked}/{len(combos)} declared files across {len(languages_present)} languages")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("🔍 Starting Devocionales Corpus Validation...")
    print(f"📁 Corpus directory: {CORPUS_DIR}")
    print()

    run_report = RunReport("DEVOCIONALES CORPUS VALIDATION")

    bible_versions, used_remote_sot, last_fetch_error = load_bible_versions('devocionales')

    run_report.wrap("PHASE 1: LINT", validate_lint)
    index_result = run_report.wrap("PHASE A: INDEX", validate_index)

    if index_result is None:
        print("\n❌ PHASE A FAILED - Stopping validation")
        run_report.print_summary()
        sys.exit(1)

    reader, combos = index_result

    run_report.wrap("PHASE SOT: BIBLE VERSIONS SOURCE", validate_sot_source,
                     bible_versions, used_remote_sot, last_fetch_error)

    # Coverage must be recorded before the gating Phase B call below —
    # RunReport.wrap() calls sys.exit() internally on gate failure, before
    # control returns here, so anything after that call never runs on a
    # failing Phase B. All coverage figures needed are already known from
    # Phase A (combos, declared languages), so there is no need to wait on
    # Phase B's return value the way this was previously (incorrectly)
    # ordered.
    run_report.add_coverage(
        content_units=len(combos),
        files_scanned=len(combos),
        languages_present=sorted({c.lang for c in combos}),
        expected_languages=len(bible_versions),
        sot_live=used_remote_sot,
    )

    run_report.wrap(
        "PHASE B: CORPUS FILES", validate_corpus_files, combos, bible_versions,
        final=True,
    )

    run_report.print_summary()

    overall_passed = all(p.passed for p in run_report.phases)
    sys.exit(0 if overall_passed else 1)


if __name__ == '__main__':
    main()
