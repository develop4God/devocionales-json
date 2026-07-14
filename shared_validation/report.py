"""report.py — Report class + run_phase() gate/warn helper.

Based on the Report class in encounters/encounters_scripts/validate_encounters.py
(cleaner than discovery's ValidationReport). The E/W/I contract is defined as
an explicit typing.Protocol so callers can type-hint against either the
concrete Report class here or their own compatible report object.
"""

from typing import Callable, List, Protocol, TypeVar


class ReportLike(Protocol):
    """Structural contract for anything that can receive E/W/I findings."""

    def E(self, msg: str) -> None: ...
    def W(self, msg: str) -> None: ...
    def I(self, msg: str) -> None: ...


class Report:
    def __init__(self, phase: str):
        self.phase = phase
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []

    def E(self, msg): self.errors.append(f"❌ ERROR: {msg}")
    def W(self, msg): self.warnings.append(f"⚠️  WARNING: {msg}")
    def I(self, msg): self.info.append(f"ℹ️  INFO: {msg}")

    def print(self, final=True) -> bool:
        print(f"\n{'='*80}")
        print(f"{self.phase} VALIDATION REPORT")
        print('='*80)
        if self.info:
            print(f"\nℹ️  INFORMATION ({len(self.info)}):")
            for m in self.info: print(f"  {m}")
        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for m in self.warnings: print(f"  {m}")
        if self.errors:
            print(f"\n❌ ERRORS ({len(self.errors)}):")
            for m in self.errors: print(f"  {m}")
            print('='*80)
            return False
        msg = "✅ ALL VALIDATIONS PASSED!" if final else "✅ PHASE PASSED - Proceeding to next phase"
        print(f"\n{msg}")
        print('='*80)
        return True


T = TypeVar('T')


def run_phase(name: str, fn: Callable[[Report], T], on_fail_msg: str = None) -> tuple:
    """Run a single validation phase: construct a Report, call fn(report),
    print it (non-final), and return (result, report, passed).

    This is a convenience helper for pipelines that want a uniform
    "build report, run phase function, print, gate" pattern across phases.
    It does not call sys.exit — callers decide what to do with `passed`.
    """
    report = Report(name)
    result = fn(report)
    passed = report.print(final=False)
    if not passed and on_fail_msg:
        print(on_fail_msg)
    return result, report, passed
