#!/usr/bin/env python3
"""
validate_devocional_index.py
────────────────────────────
Validates index.json against the actual devotional JSON files on disk.

Checks:
  1.  index.json is valid JSON
  2.  schema_version == 1
  3.  updated_at is a valid ISO-8601 date
  4.  Every (lang, version, year) combo declared in index.json has a
      corresponding file on disk and that file:
        - is valid JSON
        - has the expected root data.<lang> key
        - has entries whose 'language' and 'version' fields match
        - has a date range consistent with the declared year
  5.  Both years ("2025" and "2026") are present for every lang/version combo
  6.  Every production file on disk has a corresponding entry in index.json
      (no orphaned files)
  7.  Per-year updated_at timestamps are valid ISO dates

Usage:
  python3 validate_devocional_index.py
  python3 validate_devocional_index.py --index ../index.json
  python3 validate_devocional_index.py --index ../index.json --base ../
"""

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

# ── Constants ──────────────────────────────────────────────────────────────────
EXPECTED_SCHEMA_VERSION = 1
EXPECTED_YEARS = {"2025", "2026"}

# Base files have no lang/version in their filename; they are es/RVR1960.
BASE_FILE_MAP = {
    ("es", "RVR1960", "2025"): "Devocional_year_2025.json",
    ("es", "RVR1960", "2026"): "Devocional_year_2026.json",
}

# Pattern for standard lang/version files
STANDARD_RE = re.compile(
    r"^Devocional_year_(?P<year>\d{4})_(?P<lang>[a-z]{2})_(?P<version>.+)\.json$"
)
BASE_RE = re.compile(r"^Devocional_year_(?P<year>\d{4})\.json$")


# ── Helpers ────────────────────────────────────────────────────────────────────


def expected_filename(lang: str, version: str, year: str) -> str:
    return BASE_FILE_MAP.get(
        (lang, version, str(year)), f"Devocional_year_{year}_{lang}_{version}.json"
    )


def validate_iso_date(value, label: str, errors: list) -> bool:
    try:
        date.fromisoformat(str(value))
        return True
    except (ValueError, TypeError):
        errors.append(f"{label}: invalid ISO date — got {repr(value)}")
        return False


# ── Core validator ─────────────────────────────────────────────────────────────


def validate_index(index_path: Path, base_path: Path):
    """
    Returns (passed: bool, ok_lines: list, errors: list).
    """
    ok, errors = [], []

    # ── 1. Parse JSON ──────────────────────────────────────────────────────────
    try:
        index = json.loads(index_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as ex:
        errors.append(f"INVALID JSON: {ex}")
        return False, ok, errors

    # ── 2. schema_version ─────────────────────────────────────────────────────
    sv = index.get("schema_version")
    if sv != EXPECTED_SCHEMA_VERSION:
        errors.append(
            f"schema_version: expected {EXPECTED_SCHEMA_VERSION}, got {repr(sv)}"
        )
    else:
        ok.append(f"schema_version = {sv}")

    # ── 3. updated_at ─────────────────────────────────────────────────────────
    validate_iso_date(index.get("updated_at"), "updated_at", errors)
    if not errors:
        ok.append(f"updated_at = {index['updated_at']}")

    # ── 4. files section ──────────────────────────────────────────────────────
    files_section = index.get("files")
    if not isinstance(files_section, dict):
        errors.append("'files' key missing or not a JSON object")
        return False, ok, errors

    index_combos: set[tuple[str, str, str]] = set()

    for lang, versions in files_section.items():
        if not isinstance(versions, dict):
            errors.append(
                f"files.{lang}: expected object, got {type(versions).__name__}"
            )
            continue

        # ── 5. Both years present for this lang ────────────────────────────
        for version, years in versions.items():
            if not isinstance(years, dict):
                errors.append(
                    f"files.{lang}.{version}: expected object, got {type(years).__name__}"
                )
                continue

            declared_version_years = set(years.keys())
            missing_years = EXPECTED_YEARS - declared_version_years
            if missing_years:
                errors.append(
                    f"files.{lang}.{version}: missing year(s) {sorted(missing_years)}"
                )

            extra_years = declared_version_years - EXPECTED_YEARS
            if extra_years:
                errors.append(
                    f"files.{lang}.{version}: unexpected year(s) {sorted(extra_years)}"
                )

            for year, upd_date in years.items():
                combo = (lang, version, str(year))
                index_combos.add(combo)

                # ── updated_at per entry ──────────────────────────────────
                validate_iso_date(
                    upd_date,
                    f"files.{lang}.{version}.{year}",
                    errors,
                )

                # ── File existence ────────────────────────────────────────
                fname = expected_filename(lang, version, year)
                fpath = base_path / fname
                if not fpath.exists():
                    errors.append(
                        f"FILE MISSING: {fname}"
                        f" (index declares {lang}/{version}/{year})"
                    )
                    continue

                # ── File validity ─────────────────────────────────────────
                try:
                    data = json.loads(fpath.read_text(encoding="utf-8"))
                except json.JSONDecodeError as ex:
                    errors.append(f"INVALID JSON: {fname}: {ex}")
                    continue

                lang_root = data.get("data", {})
                if lang not in lang_root:
                    errors.append(
                        f"{fname}: language key '{lang}' not in data"
                        f" (found: {list(lang_root.keys())})"
                    )
                    continue

                entries = [e for day in lang_root[lang].values() for e in day]
                if not entries:
                    errors.append(f"{fname}: no entries found")
                    continue

                # ── version field consistency ──────────────────────────────
                wrong_ver = [
                    e.get("id", "?") for e in entries if e.get("version") != version
                ]
                if wrong_ver:
                    errors.append(
                        f"{fname}: {len(wrong_ver)}/{len(entries)} entries"
                        f" have wrong version (expected {version})"
                    )

                # ── language field consistency ─────────────────────────────
                wrong_lang = [
                    e.get("id", "?") for e in entries if e.get("language") != lang
                ]
                if wrong_lang:
                    errors.append(
                        f"{fname}: {len(wrong_lang)}/{len(entries)} entries"
                        f" have wrong language (expected {lang})"
                    )

                # ── Date range matches declared year ──────────────────────
                # Convention: year N covers Aug N … Jul N+1
                entry_dates = sorted(
                    e.get("date", "") for e in entries if e.get("date")
                )
                if entry_dates:
                    first_yr = int(entry_dates[0][:4])
                    last_yr = int(entry_dates[-1][:4])
                    int_year = int(year)
                    expected_yrs = {int_year, int_year + 1}
                    if first_yr not in expected_yrs or last_yr not in expected_yrs:
                        errors.append(
                            f"{fname}: date range {entry_dates[0]}→{entry_dates[-1]}"
                            f" inconsistent with declared year {year}"
                        )

                if not wrong_ver and not wrong_lang:
                    ok.append(
                        f"✅ {fname:<52}  lang={lang}  version={version}"
                        f"  entries={len(entries)}"
                    )

    # ── 6. Orphaned files (on disk but not in index) ───────────────────────────
    for fpath in sorted(base_path.glob("Devocional_year_*.json")):
        fname = fpath.name

        m_base = BASE_RE.match(fname)
        if m_base:
            yr = m_base.group("year")
            if ("es", "RVR1960", yr) not in index_combos:
                errors.append(
                    f"ORPHANED FILE (not in index.json): {fname}"
                    f" — expected at files.es.RVR1960.{yr}"
                )
            continue

        m_std = STANDARD_RE.match(fname)
        if m_std:
            yr = m_std.group("year")
            lang = m_std.group("lang")
            ver = m_std.group("version")
            if (lang, ver, yr) not in index_combos:
                errors.append(
                    f"ORPHANED FILE (not in index.json): {fname}"
                    f" — expected at files.{lang}.{ver}.{yr}"
                )

    return len(errors) == 0, ok, errors


# ── Entry point ────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Validate index.json against the devotional JSON files",
        epilog=(
            "Examples:\n"
            "  python3 validate_devocional_index.py\n"
            "  python3 validate_devocional_index.py --index ../index.json\n"
            "  python3 validate_devocional_index.py --index ../index.json --base ../"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--index",
        default=None,
        help="Path to index.json (default: auto-detect from script location)",
    )
    parser.add_argument(
        "--base",
        default=None,
        help="Directory containing the devotional JSON files (default: auto-detect)",
    )
    args = parser.parse_args()

    script_dir = Path(__file__).parent
    repo_root = script_dir.parent

    index_path = Path(args.index) if args.index else repo_root / "index.json"
    base_path = Path(args.base) if args.base else repo_root

    sep = "=" * 64
    print(sep)
    print("INDEX.JSON VALIDATOR")
    print(sep)
    print(f"  index : {index_path}")
    print(f"  files : {base_path}")
    print()

    passed, ok_lines, errors = validate_index(index_path, base_path)

    for line in ok_lines:
        print(f"  {line}")

    print()

    if errors:
        print(f"  ❌ {len(errors)} error(s):")
        for err in errors:
            print(f"    ❌ {err}")
        print()
        print(sep)
        print(f"❌ FAILED — {len(errors)} error(s) found")
        print(sep)
        sys.exit(1)
    else:
        print(sep)
        print(
            f"✅ PASSED — index.json is consistent with all {len(ok_lines)} file entries"
        )
        print(sep)
        sys.exit(0)


if __name__ == "__main__":
    main()
