"""corpus_schema_checker.py — cross-corpus check that every entry, across
every file, shares the exact same top-level key structure (and the same
nested para_meditar key structure).

No field list is ever hardcoded here. The reference schema is not assumed
(e.g. "must have id, date, language, ..."); it is derived from the first
entry encountered in the corpus, and every other entry — in every file —
must match that key set exactly. If the schema legitimately changes in the
future (a new field added everywhere), this check adapts automatically —
it only asserts internal corpus-wide agreement, never a fixed field list.

This mirrors CorpusCalendarChecker's shape (a cross-file collaborator, not
a method on CorpusFileValidator, since structural agreement is inherently
a cross-file concern) but is intentionally NOT merged into the same class:
calendar consistency and schema consistency are two independent axes that
happen to both be "compare everything to a corpus-derived reference" —
combining them into one god-class would obscure that each has its own
reference, its own comparison unit (dates vs. key-sets), and its own
reporting shape.
"""

from typing import Dict, Optional, Tuple

from shared_validation.report import ReportLike

from corpus_index_reader import CorpusCombo

_KeySet = Tuple[str, ...]


class CorpusSchemaChecker:
    """Tracks the first entry's key-set (top-level and para_meditar) as the
    corpus-wide reference schema, then flags any entry — in any file — that
    doesn't match it."""

    def __init__(self):
        self._reference_keys: Optional[_KeySet] = None
        self._reference_pm_keys: Optional[_KeySet] = None
        self._reference_source: Optional[str] = None

    def check_file(self, combo: CorpusCombo, entries: list, report: ReportLike) -> None:
        """Call once per file, after CorpusFileValidator has already
        confirmed `entries` is a non-empty list of dicts. Reports any entry
        whose key-set (or whose para_meditar items' key-set) diverges from
        the corpus-wide reference established by the first file/entry
        checked."""
        mismatched_entries = []
        mismatched_pm = []

        for entry in entries:
            keys = tuple(sorted(entry.keys()))

            if self._reference_keys is None:
                self._reference_keys = keys
                self._reference_source = f"{combo.filename}:{entry.get('id', '?')}"
            elif keys != self._reference_keys:
                mismatched_entries.append((entry.get("id", "?"), keys))

            pm = entry.get("para_meditar")
            if isinstance(pm, list):
                for ref in pm:
                    if not isinstance(ref, dict):
                        continue
                    pm_keys = tuple(sorted(ref.keys()))
                    if self._reference_pm_keys is None:
                        self._reference_pm_keys = pm_keys
                    elif pm_keys != self._reference_pm_keys:
                        mismatched_pm.append((entry.get("id", "?"), pm_keys))

        if mismatched_entries:
            report.E(
                f"{combo.filename}: {len(mismatched_entries)}/{len(entries)} entries have "
                f"a different key structure than the corpus reference "
                f"{self._reference_keys} (established from {self._reference_source}) — "
                f"e.g. {mismatched_entries[0][0]} has {mismatched_entries[0][1]}"
            )
        if mismatched_pm:
            report.E(
                f"{combo.filename}: {len(mismatched_pm)} para_meditar item(s) have a "
                f"different key structure than the corpus reference "
                f"{self._reference_pm_keys} — e.g. entry {mismatched_pm[0][0]} has "
                f"{mismatched_pm[0][1]}"
            )
