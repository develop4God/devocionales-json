"""strong_pipeline.py — Orchestrator for the Strong code fixing pipeline.

Provides a unified interface to run the complete workflow:
  SCAN → ANALYZE → APPLY → VALIDATE

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


class BalanceFixAction(NamedTuple):
    """Balance fix action."""
    filepath: str
    field_path: str
    code: str
    old: str
    new: str
    start: int
    end: int
    issue_type: str


class PipelineReport(NamedTuple):
    """Report from running the pipeline."""
    filepath: str
    dry_run: bool
    strong_fixes_preview: List[StrongFixAction]
    balance_fixes_preview: List[BalanceFixAction]
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
    2. ANALYZE_BALANCE - Find balance issues
    3. APPLY_STRONG - Apply Strong code fixes (if not dry_run)
    4. APPLY_BALANCE - Apply balance fixes (if not dry_run)
    5. VALIDATE - Verify file is clean

    Note: strong_fixer.preview_file/apply_fixes and
    strong_balance_fixer.preview_balance_fixes each read and parse the
    JSON file independently — there is no shared scan artifact wired
    between stages. If a shared scan is reintroduced later, every
    downstream stage must actually consume it, not just the orchestrator.
    
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
    
    # Stage 2: ANALYZE_BALANCE (preview only, for the report — NOT reused
    # for applying; see Stage 4 note below on why this must be re-run)
    balance_actions = preview_balance_fixes(filepath)
    
    # Initialize counters
    strong_applied = 0
    strong_failed = 0
    balance_applied = 0
    balance_failed = 0
    is_valid = False
    validation_issues = 0
    abort_reason = None
    
    if not dry_run:
        # Stage 3: APPLY_STRONG
        if strong_fixes:
            # apply_strong_fixes (strong_fixer.apply_fixes) returns the full
            # FixResult — applied AND failed must both be read, never just
            # applied, or a fix that silently fails goes unnoticed again.
            strong_result = apply_strong_fixes(filepath, strong_fixes)
            strong_applied = strong_result.applied
            strong_failed = strong_result.failed
        
        # Stage 4: APPLY_BALANCE
        # CRITICAL: balance_actions from Stage 2 were computed against the
        # file BEFORE strong fixes rewrote it. Applying strong fixes
        # shifts every character offset downstream of each edit within
        # the same field, so the Stage 2 balance offsets are stale the
        # moment Stage 3 writes anything. Re-analyze against the file's
        # current on-disk state (post-strong-fix) instead of reusing the
        # pre-fix preview — this was previously a silent, corpus-wide
        # failure (confirmed: 63 balance fixes across 27 files failed to
        # apply for exactly this reason before this fix).
        balance_actions_to_apply = (
            preview_balance_fixes(filepath) if strong_applied else balance_actions
        )
        if balance_actions_to_apply:
            balance_result = apply_balance_fixes(filepath, balance_actions_to_apply)
            balance_applied = balance_result.applied
            balance_failed = balance_result.failed
        
        # Stage 5: VALIDATE
        is_valid, validation_issues = validate_after_fix(filepath)

        # Surface silent-failure risk explicitly rather than leaving it
        # to the caller to remember to check strong_failed/balance_failed.
        if strong_failed or balance_failed:
            abort_reason = (
                f"{strong_failed} strong fix(es) and {balance_failed} balance "
                f"fix(es) failed to apply (old text no longer matched on disk)"
            )
        elif not is_valid:
            abort_reason = f"Post-apply validation failed: {validation_issues} issue(s) remain"
    else:
        # Dry run never touches the file, so "valid" here only means
        # "nothing was flagged" — NOT the same guarantee as the
        # post-apply schema/structure validation done in production mode.
        is_valid = len(strong_fixes) == 0 and len(balance_actions) == 0
        validation_issues = 0
    
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
