"""run_report.py — RunReport: a run-level summary layer wrapping per-phase
Report objects.

Neither validate_encounters.py nor validate_discovery.py tell an operator,
at a glance, what was actually checked (file/language/content counts), how
each phase did (a scannable table), how long it took, or when/against what
branch. This module adds that as an additive summary layer on top of the
existing phase-level Report/print output — it does not replace per-message
I/W/E reporting.

Coverage fields are collected via one explicit add_coverage(...) call with a
closed, typed parameter list — not scattered stats['x'] += 1 increments
(which can silently drift out of sync with new code paths) and not an
untyped **kwargs bag (which would just relocate the same drift risk behind
a differently-shaped hardcoded call).
"""

import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .report import Report


@dataclass
class _PhaseResult:
    name: str
    report: Any  # duck-typed: anything with .info / .warnings / .errors lists
    passed: bool
    elapsed: float
    ran: bool = True


@dataclass
class Coverage:
    content_units: int | None = None
    published: int | None = None
    coming_soon: int | None = None
    files_scanned: int | None = None
    languages_present: list[str] | None = None
    expected_languages: int | None = None
    studies_found: int | None = None
    sot_live: bool | None = None


def _current_branch() -> str:
    """Best-effort branch name for the summary header. Must never crash the
    run over a cosmetic field — detached HEAD, shallow clones, or running
    outside a git repo all fall back to 'unknown'."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        branch = result.stdout.strip()
        return branch if result.returncode == 0 and branch else "unknown"
    except Exception:
        return "unknown"


class RunReport:
    """Wraps a sequence of phase-level Report objects, records per-phase
    timing, collects one explicit coverage snapshot, and renders a run-level
    summary. Does not replace each phase's own Report.print() output — this
    is an additive layer printed after (or, on gate failure, in place of)
    the rest of a normal run.
    """

    def __init__(self, title: str):
        self.title = title
        self.phases: list[_PhaseResult] = []
        self.coverage: Coverage = Coverage()
        self.exit_code: int = 0
        self._start_time = time.monotonic()
        self._started_at = datetime.now()
        self._branch = _current_branch()

    def add_coverage(
        self,
        content_units: int | None = None,
        published: int | None = None,
        coming_soon: int | None = None,
        files_scanned: int | None = None,
        languages_present: list[str] | None = None,
        expected_languages: int | None = None,
        studies_found: int | None = None,
        sot_live: bool | None = None,
    ) -> None:
        """Record the run's coverage snapshot. Explicit typed parameters,
        one per Coverage field — a typo'd or renamed field is a call-site
        TypeError at the point of the mistake, not a silently-dropped or
        misrendered value the way an untyped **kwargs bag would allow."""
        self.coverage = Coverage(
            content_units=content_units,
            published=published,
            coming_soon=coming_soon,
            files_scanned=files_scanned,
            languages_present=languages_present,
            expected_languages=expected_languages,
            studies_found=studies_found,
            sot_live=sot_live,
        )

    def wrap(self, name: str, fn, *args, gate: bool = True, final: bool = False):
        """Run one phase: build its Report, call fn(report, *args), print it,
        record timing + pass/fail for the summary table, and (for gating
        phases) print the run summary before exiting on failure.

        Mirrors each script's local _run_phase signature (*args, gate,
        final, sys.exit on gate failure) rather than the plain
        shared_validation.report.run_phase() free function, which does not
        exit — this method owns the exit decision itself so it can print
        the summary first.
        """
        report = Report(name)
        phase_start = time.monotonic()
        result = fn(report, *args)
        elapsed = time.monotonic() - phase_start
        passed = report.print(final=final)

        self.phases.append(
            _PhaseResult(name=name, report=report, passed=passed, elapsed=elapsed)
        )

        if gate and not passed:
            print(f"\n❌ {name} FAILED - Stopping validation")
            # Print the summary BEFORE exiting — this is the exact case an
            # operator most needs to see what ran and how far it got, and
            # it must not be silently skipped just because the run is
            # aborting.
            self.print_summary()
            self.write_github_summary()
            sys.exit(1)

        return result

    def record_phase(
        self, name: str, report: Any, passed: bool, elapsed: float, gate: bool = True
    ) -> None:
        """Record a phase whose Report-like object and pass/fail were
        already produced by the caller, instead of being constructed by
        wrap(). For pipelines (e.g. discovery) whose own report object
        doesn't match the per-phase Report(name)-per-call shape wrap()
        assumes — the caller times and prints the phase itself, then
        hands the result here purely for the summary table/coverage layer.

        `report` only needs .info / .warnings / .errors list attributes
        (duck-typed) — RunReport does not require shared_validation.Report
        specifically, only that shape.
        """
        self.phases.append(
            _PhaseResult(name=name, report=report, passed=passed, elapsed=elapsed)
        )

        if gate and not passed:
            print(f"\n❌ {name} FAILED - Stopping validation")
            self.print_summary()
            self.write_github_summary()
            sys.exit(1)

    def _status_icon(self, phase: _PhaseResult) -> str:
        if not phase.ran:
            return "⬜ SKIP"
        if not phase.passed:
            return "❌ FAIL"
        if phase.report.warnings:
            return "⚠️  WARN"
        return "✅ PASS"

    def print_summary(self) -> None:
        total_elapsed = time.monotonic() - self._start_time
        timestamp = self._started_at.strftime("%Y-%m-%d %H:%M:%S")

        print(f"\n{'=' * 80}")
        print(f"{self.title} — {timestamp} — branch {self._branch}")
        print("=" * 80)

        print("\n📊 COVERAGE")
        c = self.coverage
        if c.content_units is not None:
            extra = ""
            if c.published is not None or c.coming_soon is not None:
                extra = (
                    f" ({c.published or 0} published, {c.coming_soon or 0} coming_soon)"
                )
            print(f"  Content units checked:     {c.content_units}{extra}")
        if c.studies_found is not None:
            print(f"  Studies found:             {c.studies_found}")
        if c.files_scanned is not None:
            lang_count = len(c.languages_present) if c.languages_present else 0
            print(
                f"  Files scanned:             {c.files_scanned} JSON files across {lang_count} languages"
            )
        if c.languages_present is not None:
            expected = (
                f" ({len(c.languages_present)}/{c.expected_languages} expected)"
                if c.expected_languages
                else ""
            )
            print(
                f"  Languages present:         {', '.join(sorted(c.languages_present))}{expected}"
            )
        if c.sot_live is not None:
            status = (
                "✓ live remote"
                if c.sot_live
                else "⚠️  cached fallback (re-run before merging)"
            )
            print(f"  Bible SOT source:          {status}")

        print(f"\n{'─' * 80}")
        for phase in self.phases:
            icon = self._status_icon(phase)
            print(f"{phase.name:<60} {icon}  ({phase.elapsed:.1f}s)")
        print("─" * 80)

        total_warnings = sum(len(p.report.warnings) for p in self.phases)
        total_errors = sum(len(p.report.errors) for p in self.phases)
        if total_warnings or total_errors:
            # Messages themselves already printed once, in full, by each
            # phase's own Report.print() call above — that output carries
            # phase context via the section header, so re-listing every
            # message again here (previously prefixed "[phase name]") was
            # pure duplication with no added information, just verbatim
            # noise doubling the report's length.
            print(f"\n⚠️  WARNINGS ({total_warnings})     ❌ ERRORS ({total_errors})")

        overall_passed = all(p.passed for p in self.phases) and total_warnings == 0
        print(f"\n{'=' * 80}")
        if overall_passed:
            print(f"✅ RUN PASSED     (total: {total_elapsed:.1f}s)")
        else:
            exit_code = 1
            print(
                f"❌ RUN FAILED — {total_errors} errors, {total_warnings} warnings, exit code {exit_code}     (total: {total_elapsed:.1f}s)"
            )
        print("=" * 80)
        self.exit_code = 0 if overall_passed else 1

    def write_github_summary(self) -> None:
        """Append a Markdown summary to $GITHUB_STEP_SUMMARY, if set (i.e.
        running as a GitHub Actions step). No-op locally. Renders as its own
        panel in the Actions UI, so warnings/errors don't have to be found
        by scrolling the raw console log.

        Scripture-reference findings get their own collapsible section
        since that phase is currently WARNING-only (see validate_discovery.
        py / validate_encounters.py Phase D docstrings) and would otherwise
        be lost among every other phase's warnings.
        """
        summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
        if not summary_path:
            return

        total_warnings = sum(len(p.report.warnings) for p in self.phases)
        total_errors = sum(len(p.report.errors) for p in self.phases)
        overall_passed = all(p.passed for p in self.phases) and total_warnings == 0

        lines = []
        lines.append(f"## {self.title}")
        if overall_passed:
            lines.append("✅ PASSED\n")
        else:
            lines.append(
                f"❌ FAILED — {total_errors} errors, {total_warnings} warnings\n"
            )

        lines.append("| Phase | Status | Time |")
        lines.append("|---|---|---|")
        for phase in self.phases:
            icon = self._status_icon(phase)
            lines.append(f"| {phase.name} | {icon} | {phase.elapsed:.1f}s |")

        scripture_phases = [p for p in self.phases if "SCRIPTURE" in p.name.upper()]
        for phase in scripture_phases:
            if not phase.report.warnings and not phase.report.errors:
                continue
            count = len(phase.report.warnings) + len(phase.report.errors)
            lines.append(
                f"\n<details>\n<summary>⚠️ {phase.name} — {count} finding(s)</summary>\n"
            )
            for msg in phase.report.errors:
                lines.append(f"- {msg}")
            for msg in phase.report.warnings:
                lines.append(f"- {msg}")
            lines.append("\n</details>")

        other_findings = [
            (phase, msg)
            for phase in self.phases
            if phase not in scripture_phases
            for msg in (phase.report.errors + phase.report.warnings)
        ]
        if other_findings:
            lines.append(
                f"\n<details>\n<summary>Other findings — {len(other_findings)}</summary>\n"
            )
            for phase, msg in other_findings:
                lines.append(f"- [{phase.name}] {msg}")
            lines.append("\n</details>")

        with open(summary_path, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
