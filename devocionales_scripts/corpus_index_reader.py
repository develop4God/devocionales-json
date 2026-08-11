"""corpus_index_reader.py — parses the repo-root index.json for the
devocionales (devotional-year) corpus.

This is the ONLY place a devotional-year filename is ever resolved. There is
no filename-convention fallback (e.g. the old BASE_FILE_MAP special-case for
es/RVR1960) — index.json's files.<lang>.<version>.files.<year> value is
taken as-is and is the sole source of truth, exactly as Discovery and
Encounters already treat their own index.json.

Mirrors the Discovery/Encounters pattern of a thin, single-purpose reader
feeding a Report — but the devocionales index schema (a 3-level nested dict:
files.<lang>.<version>.files.<year>) is structurally different from
Discovery's {studies: [...]} or Encounters' {encounters: [...]} array-of-
objects shape, so this parsing logic is not a shared_validation candidate:
forcing one shared reader to branch on content-type schema would be worse
than three small, content-type-specific readers.
"""

import json
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from shared_validation.report import ReportLike

EXPECTED_SCHEMA_VERSION = 1
EXPECTED_YEARS = {"2025", "2026"}


@dataclass(frozen=True)
class CorpusCombo:
    """One declared (lang, version, year) -> filename entry from index.json."""

    lang: str
    version: str
    year: str
    filename: str


class CorpusIndexReader:
    """Parses index.json and exposes declared (lang, version, year, filename)
    combos. Owns schema_version/updated_at/year-completeness checks — the
    concerns that belong to the index document itself, not to any individual
    corpus file."""

    def __init__(self, index_path: Path):
        self._index_path = index_path
        self._data: dict | None = None

    def load(self, report: ReportLike) -> bool:
        """Parse index.json and validate its own shape. Returns False (and
        reports errors) if the index itself is malformed enough that combo
        iteration cannot proceed."""
        try:
            self._data = json.loads(self._index_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as ex:
            report.E(f"index.json: invalid JSON: {ex}")
            return False
        except OSError as ex:
            report.E(f"index.json: cannot read {self._index_path}: {ex}")
            return False

        sv = self._data.get("schema_version")
        if sv != EXPECTED_SCHEMA_VERSION:
            report.E(
                f"index.json: schema_version expected {EXPECTED_SCHEMA_VERSION}, got {sv!r}"
            )
        else:
            report.I(f"✓ index.json schema_version = {sv}")

        self._validate_iso_date(
            self._data.get("updated_at"), "index.json: updated_at", report
        )

        if not isinstance(self._data.get("files"), dict):
            report.E("index.json: 'files' key missing or not an object")
            return False

        return True

    @staticmethod
    def _validate_iso_date(value, label: str, report: ReportLike) -> bool:
        try:
            date.fromisoformat(str(value))
            return True
        except (ValueError, TypeError):
            report.E(f"{label}: invalid ISO date — got {value!r}")
            return False

    def iter_combos(self, report: ReportLike) -> Iterator[CorpusCombo]:
        """Yield every declared (lang, version, year) combo with its exact
        filename, straight from index.json. Also reports year-completeness
        problems (missing/extra years) and per-entry updated_at validity —
        these are properties of the index declaration itself, checked once
        here rather than re-derived by every caller."""
        files_section = self._data.get("files", {})

        for lang, versions in files_section.items():
            if not isinstance(versions, dict):
                report.E(
                    f"index.json: files.{lang} expected object, got {type(versions).__name__}"
                )
                continue

            for version, payload in versions.items():
                if not isinstance(payload, dict):
                    report.E(
                        f"index.json: files.{lang}.{version} expected object, got {type(payload).__name__}"
                    )
                    continue

                files_map = payload.get("files", {})
                if not isinstance(files_map, dict):
                    report.E(
                        f"index.json: files.{lang}.{version}.files missing or not an object"
                    )
                    continue

                declared_years = set(files_map.keys())
                missing_years = EXPECTED_YEARS - declared_years
                if missing_years:
                    report.E(
                        f"index.json: files.{lang}.{version} missing year(s) {sorted(missing_years)}"
                    )
                extra_years = declared_years - EXPECTED_YEARS
                if extra_years:
                    report.E(
                        f"index.json: files.{lang}.{version} unexpected year(s) {sorted(extra_years)}"
                    )

                for year, filename in files_map.items():
                    upd_date = payload.get(year)
                    self._validate_iso_date(
                        upd_date, f"index.json: files.{lang}.{version}.{year}", report
                    )
                    yield CorpusCombo(
                        lang=lang, version=version, year=str(year), filename=filename
                    )

    def declared_filenames(self) -> set:
        """All filenames declared anywhere in index.json — used by the
        orphan check (files on disk with no index.json entry)."""
        result = set()
        for versions in self._data.get("files", {}).values():
            if not isinstance(versions, dict):
                continue
            for payload in versions.values():
                if not isinstance(payload, dict):
                    continue
                result.update(payload.get("files", {}).values())
        return result
