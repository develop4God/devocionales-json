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
sys.path.insert(0, str(REPO_ROOT / "discovery" / "discovery_scripts"))

from shared_validation.text_checks import (  # noqa: E402
    check_quote_anomalies,
    check_halfwidth_colon_in_title,
)
from shared_validation.report import Report  # noqa: E402


# ── check_quote_anomalies (shared_validation.text_checks) ───────────────────
#
# Note: this now lives in shared_validation/text_checks.py as a module-level
# function, not as a local `_check_quote_anomalies` method on either
# pipeline's report class — extracted during the shared_validation
# migration, used by both validate_encounters.py and validate_discovery.py.
# Testing the actual live function.


class TestCheckQuoteAnomalies(unittest.TestCase):
    def test_doubled_straight_quote_is_an_error(self):
        report = Report("TEST")
        check_quote_anomalies('He said ""hello"" to her.', "ctx", report)

        self.assertTrue(
            any("doubled '\"\"'" in e for e in report.errors),
            f"Expected a doubled-quote error, got: {report.errors}",
        )

    def test_doubled_guillemet_is_an_error(self):
        report = Report("TEST")
        check_quote_anomalies("Il a dit ««bonjour»».", "ctx", report)

        self.assertTrue(
            any("doubled '««'" in e for e in report.errors),
            f"Expected a doubled-guillemet error, got: {report.errors}",
        )

    def test_unbalanced_guillemets_is_a_warning(self):
        report = Report("TEST")
        check_quote_anomalies("Il a dit «bonjour sans fermeture.", "ctx", report)

        self.assertTrue(
            any("unbalanced '«'/'»'" in w for w in report.warnings),
            f"Expected an unbalanced-guillemet warning, got: {report.warnings}",
        )
        self.assertEqual(report.errors, [])

    def test_balanced_guillemets_produce_no_finding(self):
        report = Report("TEST")
        check_quote_anomalies("Il a dit «bonjour» avec joie.", "ctx", report)

        self.assertEqual(report.errors, [])
        self.assertEqual(report.warnings, [])

    def test_odd_straight_quote_count_is_a_warning(self):
        report = Report("TEST")
        check_quote_anomalies('She said "hello without closing.', "ctx", report)

        self.assertTrue(
            any("odd number of straight double quotes" in w for w in report.warnings),
            f"Expected an odd-quote-count warning, got: {report.warnings}",
        )

    def test_unbalanced_parens_is_an_error(self):
        """A dropped/extra parenthesis is an ERROR (not a warning like the
        guillemet/quote balance checks) — this is the shape lexicon_fixer.py
        left behind twice in real corpus content: an outer paren wrapping a
        whole "(word, (translit) — Strong Gxxxx)" gloss that the fixer's
        rewrite failed to re-close after inserting its own inner citation
        parens."""
        report = Report("TEST")
        check_quote_anomalies(
            "The word (καταπέτασμα, (katapétasma) (G2665) means veil.",
            "ctx",
            report,
        )

        self.assertTrue(
            any("unbalanced '('/')'" in e for e in report.errors),
            f"Expected an unbalanced-paren error, got: {report.errors}",
        )

    def test_balanced_parens_produce_no_finding(self):
        report = Report("TEST")
        check_quote_anomalies(
            "The word (καταπέτασμα, (katapétasma) (G2665)) means veil.",
            "ctx",
            report,
        )

        self.assertEqual(report.errors, [])
        self.assertEqual(report.warnings, [])

    def test_fullwidth_and_ascii_parens_balance_across_styles(self):
        """ja/zh content legitimately opens with a full-width '（' and closes
        the same span with an ASCII ')' (or the reverse) — e.g.
        '金（χρυσίον, (chrysíon) (G5553))：' from a real gold_silver_ashes_ja
        card: one full-width opener, two ASCII pairs, balanced overall once
        both styles are counted as the same pair. Counting '()' and '（）'
        separately would flag this real, correct content as unbalanced."""
        report = Report("TEST")
        check_quote_anomalies(
            "金（χρυσίον, (chrysíon) (G5553))：value",
            "ctx",
            report,
        )

        self.assertEqual(report.errors, [])

    def test_verse_continuation_close_single_guillemet_does_not_warn(self):
        """A single trailing »-only fragment (the tail of a quotation that
        opened in a preceding verse, stored as a separate string field in
        this corpus) must NOT be flagged as unbalanced — this is the
        verse-continuation exception (is_verse_continuation_close)."""
        report = Report("TEST")
        check_quote_anomalies("and so it was fulfilled.»", "ctx", report)

        self.assertEqual(report.warnings, [])
        self.assertEqual(report.errors, [])

    def test_verse_continuation_close_single_straight_quote_does_not_warn(self):
        report = Report("TEST")
        check_quote_anomalies('and so it was fulfilled."', "ctx", report)

        self.assertEqual(report.warnings, [])
        self.assertEqual(report.errors, [])

    def test_single_trailing_mark_with_only_punctuation_after_is_still_exempt(self):
        """The exception allows trailing punctuation/whitespace after the
        single mark, not just the mark at the very end of the string."""
        report = Report("TEST")
        check_quote_anomalies('and so it was fulfilled."  ', "ctx", report)

        self.assertEqual(report.warnings, [])

    def test_single_leading_mark_is_not_exempt_and_still_warns(self):
        """The verse-continuation exception only applies when the single
        mark sits at the very end (only trailing punctuation/whitespace
        after it) — a single mark elsewhere in the text (e.g. an opener
        with no closer, followed by more real content) is NOT exempt and
        should still warn as unbalanced."""
        report = Report("TEST")
        check_quote_anomalies(
            "«This never closes and then more text follows here", "ctx", report
        )

        self.assertTrue(
            any("unbalanced '«'/'»'" in w for w in report.warnings),
            f"Expected an unbalanced-guillemet warning for a non-trailing single mark, got: {report.warnings}",
        )


# ── check_halfwidth_colon_in_title (shared_validation.text_checks) ──────────
#
# Added alongside a corpus-wide fix (commit 75c714f) for ja/zh title fields
# that used a half-width ':' instead of native full-width '：' typography.
# Wired into both discovery and encounters validators as a hard error.


class TestCheckHalfwidthColonInTitle(unittest.TestCase):
    def test_halfwidth_colon_in_zh_title_is_an_error(self):
        report = Report("TEST")
        check_halfwidth_colon_in_title("杯:神审判的象征", "title", "zh", "ctx", report)

        self.assertTrue(
            any("half-width ':' in title" in e for e in report.errors),
            f"Expected a half-width colon error, got: {report.errors}",
        )

    def test_halfwidth_colon_in_ja_title_is_an_error(self):
        report = Report("TEST")
        check_halfwidth_colon_in_title(
            "ベタニア:悲しみに引き裂かれた家", "title", "ja", "ctx", report
        )

        self.assertTrue(
            any("half-width ':' in title" in e for e in report.errors),
            f"Expected a half-width colon error, got: {report.errors}",
        )

    def test_halfwidth_colon_in_subtitle_is_also_an_error(self):
        """subtitle is a title-like field too — the original fix only
        covered 'title' and missed 3 real instances in 'subtitle' until
        this check was added and run against the live corpus."""
        report = Report("TEST")
        check_halfwidth_colon_in_title(
            "最终的启示:你不能被'未出生'", "subtitle", "zh", "ctx", report
        )

        self.assertTrue(
            any("half-width ':' in title" in e for e in report.errors),
            f"Expected a half-width colon error for subtitle, got: {report.errors}",
        )

    def test_fullwidth_colon_produces_no_finding(self):
        report = Report("TEST")
        check_halfwidth_colon_in_title("杯：神审判的象征", "title", "zh", "ctx", report)

        self.assertEqual(report.errors, [])

    def test_non_cjk_language_is_not_checked(self):
        """A half-width colon is correct/expected in en/es/fr/etc. titles —
        the check must only fire for ja/zh."""
        report = Report("TEST")
        check_halfwidth_colon_in_title(
            "Betania: A house broken by grief", "title", "en", "ctx", report
        )

        self.assertEqual(report.errors, [])

    def test_non_title_field_is_not_checked(self):
        """content/revelation_key/etc. legitimately mix half-width colons
        (e.g. inline Bible chapter:verse citations) — only title-like
        fields are checked."""
        report = Report("TEST")
        check_halfwidth_colon_in_title(
            "正如约翰福音11:25所说:这是应许", "content", "zh", "ctx", report
        )

        self.assertEqual(report.errors, [])

    def test_colon_followed_by_digit_is_a_scripture_reference_and_exempt(self):
        """Bible chapter:verse citations embedded in a title (e.g.
        'ヨハネ1:1の三つのハンマーの打撃') must stay half-width — this is
        the false-positive the first implementation attempt produced."""
        report = Report("TEST")
        check_halfwidth_colon_in_title(
            "ヨハネ1:1の三つのハンマーの打撃", "title", "ja", "ctx", report
        )

        self.assertEqual(report.errors, [])

    def test_label_colon_and_scripture_colon_both_present_only_flags_label(self):
        """A title with both patterns should still be flagged once for the
        genuine label colon, while the digit-adjacent one is skipped."""
        report = Report("TEST")
        check_halfwidth_colon_in_title(
            "诗篇22:基督前1000年的预言", "title", "zh", "ctx", report
        )

        self.assertEqual(len(report.errors), 1, report.errors)

    def test_path_with_card_index_prefix_still_matches_title_key(self):
        """Real call sites pass dotted/indexed paths like
        'cards[0].subtitle', not the bare key — the key must be extracted
        correctly from the full path."""
        report = Report("TEST")
        check_halfwidth_colon_in_title(
            "六天之后:预言的背景", "cards[0].subtitle", "zh", "ctx", report
        )

        self.assertTrue(
            any("half-width ':' in title" in e for e in report.errors),
            f"Expected a half-width colon error for a nested path, got: {report.errors}",
        )


if __name__ == "__main__":
    unittest.main()
