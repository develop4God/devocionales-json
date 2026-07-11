"""corpus_file_validator.py — validates one loaded devotional-year JSON file
against its declared (lang, version, year) combo from index.json, and
against the remote Bible-versions SOT (shared_validation.bible_sot).

This intentionally does NOT re-implement per-entry content-quality checks
(min length, truncation, Amen endings, seasonal-leak detection, etc.) —
that is validate_devocional_gui.py's job, a separate concern with a
separate (manual/interactive) lifecycle. This module owns exactly one
thing: does this file's content match what the index — and the Bible
version SOT — say it should be.
"""

from typing import Optional

from shared_validation.report import ReportLike

from corpus_index_reader import CorpusCombo
from sot_exceptions import ACKNOWLEDGED_SOT_MISMATCHES


class CorpusFileValidator:
    """Validates one parsed devotional-year file's entries against its
    declared combo. Constructed once per run with the Bible-versions SOT
    (allowed_versions per language) so every file check can cross-reference
    it without re-fetching."""

    def __init__(self, bible_versions: dict):
        self._bible_versions = bible_versions

    def validate(self, combo: CorpusCombo, data: dict, report: ReportLike) -> "tuple[list, set]":
        """Validates this file's entries against its declared combo. Returns
        (entries, entry_dates) — ([], set()) on any structural failure — so
        the caller can feed them to cross-file checks (calendar, schema)
        without re-parsing the file. This module stays scoped to
        single-file validation; it does not itself compare across combos."""
        lang_root = data.get("data", {})
        if combo.lang not in lang_root:
            report.E(
                f"{combo.filename}: language key '{combo.lang}' not in data "
                f"(found: {list(lang_root.keys())})"
            )
            return [], set()

        entries = [e for day in lang_root[combo.lang].values() for e in day]
        if not entries:
            report.E(f"{combo.filename}: no entries found")
            return [], set()

        self._check_declared_consistency(combo, entries, report)
        self._check_against_bible_sot(combo, report)
        self._check_date_range(combo, entries, report)

        entry_dates = {e.get("date", "") for e in entries if e.get("date")}
        return entries, entry_dates

    def _check_declared_consistency(self, combo: CorpusCombo, entries: list, report: ReportLike) -> None:
        """Every entry's own version/language fields must match what
        index.json declares for this file. This is the check that catches
        drift like a batch mislabeling entries as language='tl',
        version='ADB' inside a file index.json declares as fil/MBB05."""
        wrong_version = [e.get("id", "?") for e in entries if e.get("version") != combo.version]
        wrong_lang = [e.get("id", "?") for e in entries if e.get("language") != combo.lang]

        if wrong_version:
            report.E(
                f"{combo.filename}: {len(wrong_version)}/{len(entries)} entries have "
                f"wrong version (expected '{combo.version}') — e.g. {wrong_version[:3]}"
            )
        if wrong_lang:
            report.E(
                f"{combo.filename}: {len(wrong_lang)}/{len(entries)} entries have "
                f"wrong language (expected '{combo.lang}') — e.g. {wrong_lang[:3]}"
            )

    def _check_against_bible_sot(self, combo: CorpusCombo, report: ReportLike) -> None:
        """Cross-check the declared version itself against the remote Bible
        versions SOT — catches a version code that isn't even legitimate
        for this language (independent of whether the file's own entries
        match the declaration checked above)."""
        lang_cfg = self._bible_versions.get(combo.lang)
        if lang_cfg is None:
            report.W(
                f"{combo.filename}: language '{combo.lang}' not found in Bible versions SOT "
                f"— cannot verify '{combo.version}' is a legitimate version"
            )
            return

        allowed = lang_cfg.get("allowed_versions", [])
        if combo.version not in allowed:
            exception_note = ACKNOWLEDGED_SOT_MISMATCHES.get((combo.lang, combo.version))
            if exception_note is not None:
                report.W(
                    f"{combo.filename}: declared version '{combo.version}' is not in the "
                    f"Bible versions SOT allowed list for '{combo.lang}' ({allowed}) — "
                    f"acknowledged exception: {exception_note}"
                )
            else:
                report.E(
                    f"{combo.filename}: declared version '{combo.version}' is not in the "
                    f"Bible versions SOT allowed list for '{combo.lang}' ({allowed})"
                )

    def _check_date_range(self, combo: CorpusCombo, entries: list, report: ReportLike) -> None:
        """Convention: devotional year N covers Aug N .. Jul N+1."""
        entry_dates = sorted(e.get("date", "") for e in entries if e.get("date"))
        if not entry_dates:
            return

        try:
            first_yr = int(entry_dates[0][:4])
            last_yr = int(entry_dates[-1][:4])
        except ValueError:
            report.E(f"{combo.filename}: could not parse entry dates for range check")
            return

        year_int = int(combo.year)
        expected_years = {year_int, year_int + 1}
        if first_yr not in expected_years or last_yr not in expected_years:
            report.E(
                f"{combo.filename}: date range {entry_dates[0]} -> {entry_dates[-1]} "
                f"inconsistent with declared year {combo.year}"
            )
