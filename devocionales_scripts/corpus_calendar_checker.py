"""corpus_calendar_checker.py — cross-file check that every declared combo
for a given devotional year shares the exact same set of entry dates
(same start date, same end date, same day-by-day coverage — no gaps, no
duplicates).

No date is ever hardcoded here. The expected date-set for a year is not
assumed (e.g. "must be 2025-08-01..2026-07-31") — it is derived entirely
from the corpus's own data: for each declared year, one combo's date-set
is taken as the reference, and every other combo declared for that same
year must match it exactly. If the Aug-N-to-Jul-(N+1) convention ever
changes, this check adapts automatically — it only asserts internal
corpus-wide consistency, never a fixed calendar assumption.

This is a genuinely cross-file concern (unlike CorpusFileValidator, which
validates one file against its own declared combo) so it is a separate
collaborator, not a method added to CorpusFileValidator — SRP: one class
owns single-file rules, this one owns the "do all files for year N agree
with each other" rule.
"""

from collections import defaultdict

from corpus_index_reader import CorpusCombo

from shared_validation.report import ReportLike


class CorpusCalendarChecker:
    """Accumulates each combo's entry-date set as it's collected, then
    compares all combos sharing the same declared year against a reference
    date-set for that year."""

    def __init__(self):
        self._dates_by_year: dict[str, dict[CorpusCombo, set[str]]] = defaultdict(dict)

    def record(self, combo: CorpusCombo, entry_dates: set[str]) -> None:
        """Record one combo's entry-date set. Call once per combo as files
        are validated; call check() once at the end after all combos for
        all years have been recorded."""
        if entry_dates:
            self._dates_by_year[combo.year][combo] = entry_dates

    def check(self, report: ReportLike) -> None:
        """Compare every combo's date-set against a reference for its
        declared year. The reference is simply the first combo recorded
        for that year — no assumption about which language/version it is,
        since the point is corpus-wide agreement, not agreement with any
        particular "base" language."""
        for year, combos_dates in sorted(self._dates_by_year.items()):
            if len(combos_dates) < 2:
                continue  # nothing to cross-compare

            combos = list(combos_dates.keys())
            reference_combo = combos[0]
            reference_dates = combos_dates[reference_combo]
            ref_start, ref_end = min(reference_dates), max(reference_dates)

            report.I(
                f"Year {year}: comparing {len(combos)} combos against reference "
                f"{reference_combo.lang}/{reference_combo.version} "
                f"({ref_start} → {ref_end}, {len(reference_dates)} dates)"
            )

            for combo in combos[1:]:
                dates = combos_dates[combo]
                if dates == reference_dates:
                    continue

                start, end = min(dates), max(dates)
                missing = reference_dates - dates
                extra = dates - reference_dates

                if start != ref_start or end != ref_end:
                    report.E(
                        f"{combo.filename}: date range {start} → {end} does not match "
                        f"the year {year} reference range {ref_start} → {ref_end} "
                        f"(reference: {reference_combo.lang}/{reference_combo.version})"
                    )
                elif missing or extra:
                    detail = []
                    if missing:
                        detail.append(
                            f"missing {len(missing)} date(s), e.g. {sorted(missing)[:3]}"
                        )
                    if extra:
                        detail.append(
                            f"{len(extra)} unexpected date(s), e.g. {sorted(extra)[:3]}"
                        )
                    report.E(
                        f"{combo.filename}: same start/end as reference but "
                        f"{'; '.join(detail)} — day-by-day coverage does not match "
                        f"{reference_combo.lang}/{reference_combo.version}"
                    )
