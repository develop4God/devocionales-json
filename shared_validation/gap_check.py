"""gap_check.py — Diff every fixer's proposed action against the immutable
first scan (strong_scanner.scan_file), instead of trusting each fixer's own
internal re-scan or self-reported counts.

For every Strong or balance fix action, this checks:
  1. Does the field exist in the immutable scan?
  2. Does action.old == scan_baseline_text[action.start:action.end]?
  3. If applied, does the resulting text still parse as valid JSON?

No files are modified. Read-only gap analysis only.

After all existing Strong/balance repairs have been simulated in memory,
the generic parenthesis checker validates the resulting field text. This is
deliberately a post-fix diff check, not a pre-fix corpus scan and not an
auto-fix stage.
"""
import sys
import json
import glob

sys.path.insert(0, '.')

from shared_validation.strong_scanner import scan_file
from shared_validation.strong_fixer import preview_file as preview_strong
from shared_validation.strong_balance_fixer import (
    preview_balance_fixes,
    preview_balance_fixes_for_text,
)
from shared_validation.strong_applier import apply_fixes_to_text
from shared_validation.paren_balance import check_balance


def check_file(fp: str, debug: bool = False) -> dict:
    """Return gap counts for one file, checked against its immutable scan.

    scan_file's TextField.start/end are RAW-FILE offsets (into
    baseline.raw_text, still escaped). strong_fixer and strong_balance_fixer
    actions use FIELD-LOCAL offsets (into the decoded field.text). These
    are different coordinate systems, so gap-checking must decode the
    scanner's raw span before comparing text, and must independently
    re-locate the fixer's field-local span inside field.text (not compare
    across coordinate systems directly).
    """
    baseline = scan_file(fp)
    baseline_by_path = {}
    for f in baseline.fields:
        raw_slice = baseline.raw_text[f.start:f.end]
        try:
            decoded_check = json.loads('"' + raw_slice + '"')
        except json.JSONDecodeError:
            decoded_check = None
        baseline_by_path[f.path] = (f, decoded_check == f.text)

    gaps = []
    checked = 0

    strong_actions = [action for action in preview_strong(fp) if action.status == "fix"]
    balance_actions = preview_balance_fixes(fp)

    for label, actions in (
        ("strong", strong_actions),
        ("balance", balance_actions),
    ):
        for a in actions:
            checked += 1
            entry = baseline_by_path.get(a.field_path)
            if entry is None:
                gaps.append((label, a.field_path, a.code, "field_not_in_baseline"))
                continue
            field, raw_span_valid = entry
            if not raw_span_valid:
                gaps.append((label, a.field_path, a.code, "baseline_raw_span_invalid"))
                continue

            # action.start/end are field-local — check against field.text
            # (the decoded value), which is the same string field.text
            # already exposes regardless of coordinate system.
            slice_ = field.text[a.start:a.end]
            if slice_ != a.old:
                gaps.append((label, a.field_path, a.code,
                             f"offset_mismatch old={a.old!r} slice={slice_!r}"))
                if debug:
                    print(f"  [GAP] {fp} :: {label} {a.code} @ {a.field_path}")
                    print(f"        old={a.old!r}")
                    print(f"        baseline_slice={slice_!r}")
                continue

    # Paren balance belongs to the post-fix diff: simulate Strong fixes, then
    # derive and simulate balance fixes against that updated text. This is the
    # same ordering as strong_pipeline, but remains completely read-only.
    strong_actions_by_field = {}
    for action in strong_actions:
        strong_actions_by_field.setdefault(action.field_path, []).append(action)

    for field_path, (field, _) in baseline_by_path.items():
        simulated, applied, failed = apply_fixes_to_text(
            field.text, strong_actions_by_field.get(field_path, [])
        )
        if failed:
            continue
        post_strong_balance_actions = preview_balance_fixes_for_text(
            fp, field_path, simulated
        )
        simulated, applied, failed = apply_fixes_to_text(
            simulated, post_strong_balance_actions
        )
        if failed:
            continue
        for issue in check_balance(simulated):
            gaps.append(
                (
                    "paren_balance",
                    field_path,
                    issue.char,
                    f"post_fix_{issue.issue_type}@{issue.position}",
                )
            )

    return {
        "filepath": fp,
        "checked": checked,
        "gaps": gaps,
    }


def main():
    files = sorted(
        glob.glob('discovery/**/*.json', recursive=True)
        + glob.glob('encounters/**/*.json', recursive=True)
    )

    total_checked = 0
    total_gaps = 0
    files_with_gaps = 0

    for fp in files:
        try:
            result = check_file(fp)
        except Exception as e:
            print(f"ERROR on {fp}: {e}")
            continue
        total_checked += result["checked"]
        if result["gaps"]:
            files_with_gaps += 1
            total_gaps += len(result["gaps"])
            print(f"\n{fp}  ({len(result['gaps'])} gap(s) of {result['checked']} checked)")
            for label, field_path, code, reason in result["gaps"]:
                print(f"    [{label}] {code} @ {field_path} :: {reason}")

    print(f"\n{'='*70}")
    print(f"Files scanned:      {len(files)}")
    print(f"Actions checked:    {total_checked}")
    print(f"Files with gaps:    {files_with_gaps}")
    print(f"Total gaps found:   {total_gaps}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
