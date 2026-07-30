"""strong_pipeline.py — Orchestrator for the Strong code fixing pipeline.

Provides a unified interface to run the Strong-code workflow:
  ANALYZE → APPLY

Modes:
  - dry_run: Preview all changes without modifying files
  - production: Apply fixes and validate

Usage:
    from shared_validation.strong_pipeline import run_pipeline

    # Dry run
    report = run_pipeline('discovery/es/passed_from_death_es_001.json', dry_run=True)
    print(f"Would apply {report.total_fixes} fixes")

    # Production
    report = run_pipeline('discovery/es/passed_from_death_es_001.json', dry_run=False)
    print(f"Applied {report.applied} fixes, validation: {report.is_valid}")
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Dict, List, NamedTuple


class StrongFixAction(NamedTuple):
    """Strong code fix action."""
    filepath: str
    field_path: str
    code: str
    old: str
    new: str
    start: int
    end: int
    status: str


class PipelineReport(NamedTuple):
    """Report from running the pipeline."""
    filepath: str
    dry_run: bool
    strong_fixes_preview: List[StrongFixAction]
    balance_fixes_preview: List[object]
    strong_applied: int
    strong_failed: int
    balance_applied: int
    balance_failed: int
    is_valid: bool
    validation_issues: int
    abort_reason: Optional[str]


def run_pipeline(filepath: str, dry_run: bool = True) -> PipelineReport:
    """Run the complete Strong code fixing pipeline.
    
    Pipeline stages:
    1. ANALYZE_STRONG - Find Strong code issues
    2. APPLY_STRONG - Apply Strong code fixes (if not dry_run)

    Parenthesis balance repairs remain available through
    ``strong_balance_fixer``. The generic checker is also available for
    report-only dry runs; it is not part of CI.
    
    Args:
        filepath: Path to JSON file
        dry_run: If True, only preview changes. If False, apply fixes.
        
    Returns:
        PipelineReport with all actions and results
    """
    from shared_validation.strong_fixer import preview_file as preview_strong
    from shared_validation.strong_balance_fixer import preview_balance_fixes, apply_balance_fixes, validate_after_fix
    from shared_validation.strong_fixer import apply_fixes as apply_strong_fixes
    
    # Stage 1: ANALYZE_STRONG
    strong_actions = preview_strong(filepath)
    strong_fixes = [a for a in strong_actions if a.status == "fix"]
    strong_fixed_fields = {a.field_path for a in strong_fixes}
    balance_actions = [
        action for action in preview_balance_fixes(filepath)
        if action.field_path in strong_fixed_fields
    ]
    # Initialize counters
    strong_applied = 0
    strong_failed = 0
    balance_applied = 0
    balance_failed = 0
    is_valid = True
    validation_issues = 0
    abort_reason = None
    
    if not dry_run:
        # Stage 2: APPLY_STRONG
        if strong_fixes:
            # apply_strong_fixes (strong_fixer.apply_fixes) returns the full
            # FixResult — applied AND failed must both be read, never just
            # applied, or a fix that silently fails goes unnoticed again.
            strong_result = apply_strong_fixes(filepath, strong_fixes)
            strong_applied = strong_result.applied
            strong_failed = strong_result.failed

        # Re-scan after Strong fixes so balance action offsets are current.
        balance_actions_to_apply = (
            [action for action in preview_balance_fixes(filepath)
             if action.field_path in strong_fixed_fields]
            if strong_applied else balance_actions
        )
        if balance_actions_to_apply:
            balance_result = apply_balance_fixes(filepath, balance_actions_to_apply)
            balance_applied = balance_result.applied
            balance_failed = balance_result.failed

        is_valid, validation_issues = validate_after_fix(filepath)

        if strong_failed or balance_failed:
            abort_reason = (
                f"{strong_failed} strong and {balance_failed} balance fix(es) "
                "failed to apply (old text no longer matched on disk)"
            )
            is_valid = False
        elif not is_valid:
            abort_reason = f"Post-apply validation failed: {validation_issues} issue(s) remain"
    else:
        # Dry run never touches the file, so "valid" here only means
        # "nothing was flagged" — NOT the same guarantee as the
        # post-apply schema/structure validation done in production mode.
        is_valid = len(strong_fixes) == 0 and len(balance_actions) == 0
    
    return PipelineReport(
        filepath=filepath,
        dry_run=dry_run,
        strong_fixes_preview=strong_fixes,
        balance_fixes_preview=balance_actions,
        strong_applied=strong_applied,
        strong_failed=strong_failed,
        balance_applied=balance_applied,
        balance_failed=balance_failed,
        is_valid=is_valid,
        validation_issues=validation_issues,
        abort_reason=abort_reason,
    )


def run_pipeline_batch(filepaths: List[str], dry_run: bool = True) -> List[PipelineReport]:
    """Run pipeline on multiple files.
    
    Args:
        filepaths: List of JSON file paths
        dry_run: If True, only preview changes
        
    Returns:
        List of PipelineReport objects
    """
    reports = []
    for filepath in filepaths:
        report = run_pipeline(filepath, dry_run=dry_run)
        reports.append(report)
    return reports


def print_report(report: PipelineReport):
    """Print a formatted pipeline report."""
    print(f'\n{"="*70}')
    print(f'  Pipeline Report: {Path(report.filepath).name}')
    print(f'  Mode: {"DRY RUN" if report.dry_run else "PRODUCTION"}')
    print(f'{"="*70}')
    
    print(f'\n  Strong Code Fixes: {len(report.strong_fixes_preview)}')
    for action in report.strong_fixes_preview[:5]:
        print(f'    {action.code:8s}  "{action.old:25s}" → "{action.new}"')
    if len(report.strong_fixes_preview) > 5:
        print(f'    ... and {len(report.strong_fixes_preview) - 5} more')

    print(f'\n  Balance Fixes: {len(report.balance_fixes_preview)}')
    for action in report.balance_fixes_preview[:5]:
        print(f'    {action.code:8s}  {action.issue_type:15s}  "{action.old:25s}" → "{action.new}"')
    if len(report.balance_fixes_preview) > 5:
        print(f'    ... and {len(report.balance_fixes_preview) - 5} more')
    
    if not report.dry_run:
        print(f'\n  Applied:')
        print(f'    Strong fixes: {report.strong_applied}')
        if report.strong_failed:
            print(f'    ⚠ Strong fixes FAILED: {report.strong_failed}')
        print(f'    Balance fixes: {report.balance_applied}')
        if report.balance_failed:
            print(f'    ⚠ Balance fixes FAILED: {report.balance_failed}')
        print(f'    Validation: {"✓ PASS" if report.is_valid else "✗ FAIL"}')
        if report.validation_issues > 0:
            print(f'    Remaining issues: {report.validation_issues}')
        if report.abort_reason:
            print(f'    ⚠ {report.abort_reason}')
    else:
        print(f'\n  Dry run - no changes made')
        print(f'  Would apply: {len(report.strong_fixes_preview) + len(report.balance_fixes_preview)} fixes')
    
    print(f'{"="*70}')
