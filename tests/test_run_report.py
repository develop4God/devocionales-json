"""test_run_report.py — golden-file regression tests for
shared_validation.run_report.RunReport.

Three scenarios, per the plan this implements:
  1. Clean pass — all phases pass, no findings.
  2. Gate failure — a gating phase fails; the summary must print in full
     BEFORE sys.exit(1) (the bug an earlier architecture review caught:
     without this fix, the summary silently vanished on exactly the runs
     where an operator most needs to see what ran and how far it got).
  3. Warnings-only pass — phases pass overall but a non-gating phase has
     warnings (mirrors encounters' real Phase C: image URL warnings never
     fail the run).

Uses synthetic phase functions, not real repository content, so these
tests are fast, deterministic, and independent of network access or
content changes in encounters/ or discovery/.

Run with:  python3 -m unittest discover tests -v
Regenerate golden files after a deliberate output-format change:
  REGENERATE_GOLDEN=1 python3 -m unittest discover tests
"""

import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from shared_validation.checks.run_report import RunReport
from tests.golden_utils import assert_matches_golden, capture

_saved_step_summary = None


def setUpModule():
    """Hide GITHUB_STEP_SUMMARY for this whole module. Several tests here
    call run_scenario() directly (not through golden_utils.capture) just to
    assert on the exit code, and RunReport.wrap() writes to that file as a
    side effect of a gate failure. Under real CI it's always set, so
    without this these tests' synthetic fixture data (e.g. "a required
    field was missing") leaks into the real job's GitHub Actions summary
    panel alongside the actual validator results."""
    global _saved_step_summary
    _saved_step_summary = os.environ.pop("GITHUB_STEP_SUMMARY", None)


def tearDownModule():
    if _saved_step_summary is not None:
        os.environ["GITHUB_STEP_SUMMARY"] = _saved_step_summary


def _phase_ok(report):
    report.I("phase completed with no issues")
    return "ok"


def _phase_fails(report):
    report.E("a required field was missing")
    report.E("a second, unrelated error")


def _phase_warns(report):
    report.I("scanned some things")
    report.W("one item could not be reached, but this is non-fatal")
    return "ok"


class TestRunReportCleanPass(unittest.TestCase):
    def run_scenario(self):
        run_report = RunReport("TEST VALIDATION")
        run_report.wrap("PHASE 1: FIRST", _phase_ok, final=False)
        run_report.wrap("PHASE 2: SECOND", _phase_ok, final=False)
        run_report.add_coverage(
            content_units=3,
            published=2,
            coming_soon=1,
            files_scanned=42,
            languages_present=["en", "es"],
            expected_languages=2,
            sot_live=True,
        )
        run_report.print_summary()
        sys.exit(0)

    def test_clean_pass_matches_golden(self):
        output = capture(self.run_scenario)
        assert_matches_golden(self, output, "clean_pass.txt")

    def test_clean_pass_exit_code(self):
        with self.assertRaises(SystemExit) as ctx:
            self.run_scenario()
        self.assertEqual(ctx.exception.code, 0)


class TestRunReportGateFailure(unittest.TestCase):
    def run_scenario(self):
        run_report = RunReport("TEST VALIDATION")
        run_report.wrap("PHASE 1: FIRST", _phase_ok, final=False)
        run_report.add_coverage(content_units=3, files_scanned=42, sot_live=True)
        # This phase fails and gates — wrap() must exit(1) here, meaning
        # PHASE 3 below never runs.
        run_report.wrap("PHASE 2: FAILS", _phase_fails, final=False)
        run_report.wrap(
            "PHASE 3: NEVER REACHED", _phase_ok, final=False
        )  # pragma: no cover

    def test_gate_failure_matches_golden(self):
        output = capture(self.run_scenario)
        assert_matches_golden(self, output, "gate_failure.txt")

    def test_gate_failure_exit_code(self):
        with self.assertRaises(SystemExit) as ctx:
            self.run_scenario()
        self.assertEqual(ctx.exception.code, 1)

    def test_summary_prints_before_exit_not_after(self):
        """The specific bug the architecture review caught: the summary
        must actually be part of the captured output on a gate failure,
        not silently skipped. Assert on content, not just exit code."""
        output = capture(self.run_scenario)
        self.assertIn("RUN FAILED", output)
        self.assertIn("📊 COVERAGE", output)
        self.assertIn("PHASE 1: FIRST", output)
        self.assertIn("PHASE 2: FAILS", output)
        # The phase after the failing one must never have run or appear
        # as having run in the table.
        self.assertNotIn("PHASE 3: NEVER REACHED", output)


class TestRunReportWarningsOnlyFails(unittest.TestCase):
    def run_scenario(self):
        run_report = RunReport("TEST VALIDATION")
        run_report.wrap("PHASE 1: GATE", _phase_ok, final=False)
        run_report.wrap("PHASE 2: WARNS", _phase_warns, gate=False, final=True)
        run_report.add_coverage(
            content_units=5,
            files_scanned=10,
            languages_present=["en"],
            expected_languages=1,
            sot_live=False,
        )
        run_report.print_summary()
        sys.exit(run_report.exit_code)

    def test_warnings_only_matches_golden(self):
        output = capture(self.run_scenario)
        assert_matches_golden(self, output, "warnings_only_pass.txt")

    def test_warnings_only_exit_code_is_nonzero(self):
        """Any warning anywhere fails the overall run, even from a
        non-gating phase — mirrors encounters' real Phase C (image URL
        checks), which now must also fail CI on unreachable images."""
        with self.assertRaises(SystemExit) as ctx:
            self.run_scenario()
        self.assertEqual(ctx.exception.code, 1)

    def test_sot_cached_fallback_wording_appears(self):
        output = capture(self.run_scenario)
        self.assertIn("cached fallback", output)


class TestRunReportAddCoverageTypoProtection(unittest.TestCase):
    def test_unknown_field_raises_typeerror(self):
        """add_coverage() uses explicit typed parameters, not **kwargs —
        a typo'd field name must fail loudly at the call site, not
        silently misrender or vanish from the summary."""
        run_report = RunReport("TEST")
        with self.assertRaises(TypeError):
            run_report.add_coverage(fiels_scanned=5)  # deliberate typo


if __name__ == "__main__":
    unittest.main()
