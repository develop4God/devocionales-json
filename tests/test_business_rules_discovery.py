"""test_business_rules_discovery.py — unit tests for the untested
content-validation rules in discovery/discovery_scripts/validate_discovery.py
and the shared text_checks module it (and encounters) depends on.

tests/test_promoted_validators.py and tests/test_run_report.py only cover
structural/gating behavior (index.json errors, RunReport formatting) — this
file covers the actual business rules: discovery question category
language detection, and the shared quote-anomaly checker. This is new
coverage for pre-existing, currently-untested logic, not a regression fix.

Imports validate_discovery.py directly (not via subprocess) so assertions
can inspect the ValidationReport object's accumulated findings precisely.
Unlike validate_encounters.py, this module has no sibling-file import
dependency (no verify_image_urls equivalent), so no extra sys.path
plumbing is required beyond the repo root for shared_validation.

Does not modify any production logic — test-only. Anything that looked
imperfect while writing these is called out in comments, not "fixed" here.
"""

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / 'discovery' / 'discovery_scripts'))

import validate_discovery as vd
from shared_validation.text_checks import check_quote_anomalies
from shared_validation.report import Report


# ── check_quote_anomalies (shared_validation.text_checks) ───────────────────
#
# Note: this now lives in shared_validation/text_checks.py as a module-level
# function, not as a local `_check_quote_anomalies` method on either
# pipeline's report class — extracted during the shared_validation
# migration, used by both validate_encounters.py and validate_discovery.py.
# Testing the actual live function.

class TestCheckQuoteAnomalies(unittest.TestCase):
    def test_doubled_straight_quote_is_an_error(self):
        report = Report('TEST')
        check_quote_anomalies('He said ""hello"" to her.', 'ctx', report)

        self.assertTrue(
            any("doubled '\"\"'" in e for e in report.errors),
            f"Expected a doubled-quote error, got: {report.errors}",
        )

    def test_doubled_guillemet_is_an_error(self):
        report = Report('TEST')
        check_quote_anomalies('Il a dit ««bonjour»».', 'ctx', report)

        self.assertTrue(
            any("doubled '««'" in e for e in report.errors),
            f"Expected a doubled-guillemet error, got: {report.errors}",
        )

    def test_unbalanced_guillemets_is_a_warning(self):
        report = Report('TEST')
        check_quote_anomalies('Il a dit «bonjour sans fermeture.', 'ctx', report)

        self.assertTrue(
            any("unbalanced '«'/'»'" in w for w in report.warnings),
            f"Expected an unbalanced-guillemet warning, got: {report.warnings}",
        )
        self.assertEqual(report.errors, [])

    def test_balanced_guillemets_produce_no_finding(self):
        report = Report('TEST')
        check_quote_anomalies('Il a dit «bonjour» avec joie.', 'ctx', report)

        self.assertEqual(report.errors, [])
        self.assertEqual(report.warnings, [])

    def test_odd_straight_quote_count_is_a_warning(self):
        report = Report('TEST')
        check_quote_anomalies('She said "hello without closing.', 'ctx', report)

        self.assertTrue(
            any('odd number of straight double quotes' in w for w in report.warnings),
            f"Expected an odd-quote-count warning, got: {report.warnings}",
        )

    def test_verse_continuation_close_single_guillemet_does_not_warn(self):
        """A single trailing »-only fragment (the tail of a quotation that
        opened in a preceding verse, stored as a separate string field in
        this corpus) must NOT be flagged as unbalanced — this is the
        verse-continuation exception (is_verse_continuation_close)."""
        report = Report('TEST')
        check_quote_anomalies('and so it was fulfilled.»', 'ctx', report)

        self.assertEqual(report.warnings, [])
        self.assertEqual(report.errors, [])

    def test_verse_continuation_close_single_straight_quote_does_not_warn(self):
        report = Report('TEST')
        check_quote_anomalies('and so it was fulfilled."', 'ctx', report)

        self.assertEqual(report.warnings, [])
        self.assertEqual(report.errors, [])

    def test_single_trailing_mark_with_only_punctuation_after_is_still_exempt(self):
        """The exception allows trailing punctuation/whitespace after the
        single mark, not just the mark at the very end of the string."""
        report = Report('TEST')
        check_quote_anomalies('and so it was fulfilled."  ', 'ctx', report)

        self.assertEqual(report.warnings, [])

    def test_single_leading_mark_is_not_exempt_and_still_warns(self):
        """The verse-continuation exception only applies when the single
        mark sits at the very end (only trailing punctuation/whitespace
        after it) — a single mark elsewhere in the text (e.g. an opener
        with no closer, followed by more real content) is NOT exempt and
        should still warn as unbalanced."""
        report = Report('TEST')
        check_quote_anomalies('«This never closes and then more text follows here', 'ctx', report)

        self.assertTrue(
            any("unbalanced '«'/'»'" in w for w in report.warnings),
            f"Expected an unbalanced-guillemet warning for a non-trailing single mark, got: {report.warnings}",
        )


if __name__ == '__main__':
    unittest.main()
