"""golden_utils.py — helpers for golden-file snapshot tests: capture stdout
from a RunReport run, normalize the parts that vary between runs
(timestamp, branch, per-phase/total elapsed seconds), and compare against
a committed golden file.

Branch and elapsed time are normalized because they're real, intentional,
non-deterministic output (see run_report.py's docstring) — a snapshot test
that pinned an exact elapsed value or the branch name of whoever happens to
run the suite would be flaky by construction, not a meaningful regression
check.
"""

import io
import os
import re
from contextlib import redirect_stdout
from pathlib import Path

GOLDEN_DIR = Path(__file__).parent / "golden"

_TIMESTAMP_RE = re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")
_BRANCH_RE = re.compile(r"branch \S+")
_ELAPSED_RE = re.compile(r"\(\d+\.\d+s\)")
_TOTAL_ELAPSED_RE = re.compile(r"\(total: \d+\.\d+s\)")


def normalize(output: str) -> str:
    """Replace run-dependent substrings with fixed placeholders so two runs
    of the same logical scenario produce byte-identical normalized output."""
    output = _TIMESTAMP_RE.sub("<TIMESTAMP>", output)
    output = _BRANCH_RE.sub("branch <BRANCH>", output)
    output = _TOTAL_ELAPSED_RE.sub("(total: <ELAPSED>s)", output)
    output = _ELAPSED_RE.sub("(<ELAPSED>s)", output)
    return output


def capture(fn, *args, **kwargs) -> str:
    """Run fn (which prints to stdout, and may call sys.exit) and return its
    normalized stdout output, regardless of whether it exits or returns.

    Also hides GITHUB_STEP_SUMMARY for the duration of the call. RunReport
    writes to that file as a side effect of a gate failure (see
    RunReport.wrap/record_phase), and under real CI it's always set — so
    without this, these tests' synthetic fixture data (e.g. "a required
    field was missing") would leak into the real job's GitHub Actions
    summary panel alongside the actual validator results.
    """
    buf = io.StringIO()
    old_summary = os.environ.pop("GITHUB_STEP_SUMMARY", None)
    try:
        with redirect_stdout(buf):
            try:
                fn(*args, **kwargs)
            except SystemExit:
                pass
    finally:
        if old_summary is not None:
            os.environ["GITHUB_STEP_SUMMARY"] = old_summary
    return normalize(buf.getvalue())


def assert_matches_golden(testcase, actual: str, golden_name: str) -> None:
    """Compare `actual` (already normalized) against a committed golden
    file. Set REGENERATE_GOLDEN=1 in the environment to write/update the
    golden file instead of asserting — used only when a change to
    run_report.py's output format is deliberate."""
    import os

    GOLDEN_DIR.mkdir(exist_ok=True)
    golden_path = GOLDEN_DIR / golden_name

    if os.environ.get("REGENERATE_GOLDEN") == "1" or not golden_path.exists():
        golden_path.write_text(actual, encoding="utf-8")
        if not os.environ.get("REGENERATE_GOLDEN"):
            testcase.fail(
                f"Golden file {golden_path} did not exist — created it now. "
                "Re-run the test to verify, then review and commit the new golden file."
            )
        return

    expected = golden_path.read_text(encoding="utf-8")
    testcase.assertEqual(
        expected,
        actual,
        f"Output for {golden_name} no longer matches the committed golden file.\n"
        f"If this change is deliberate, re-run with REGENERATE_GOLDEN=1 to update it.",
    )
