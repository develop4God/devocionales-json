"""lint.py — JSON formatting lint shared by both pipelines: indent=2 check,
tab-character check, trailing-newline check.

Encounters currently treats odd-indent/tab findings as errors and returns a
Path->parsed_json cache reused later in its pipeline; discovery currently
treats them as warnings and returns nothing. The shared function always
returns the parse cache (harmless for discovery, which can ignore the return
value) and lets the caller choose severity explicitly — it never hardcodes
one pipeline's choice.
"""

import json
from pathlib import Path

from ..report import ReportLike


def lint_json_files(
    directory: Path, report: ReportLike, exclude_dir_part: str, severity: str = "error"
) -> dict:
    """Check that all JSON files under `directory` use indent=2 formatting
    and end with a trailing newline.

    `exclude_dir_part` is a path-parts substring to skip (e.g. the
    pipeline's own scripts directory name, so the validator script itself
    isn't linted as content).

    `severity` is 'error' or 'warning' — controls whether odd-indent/tab
    findings (and invalid-JSON findings) go to report.E() or report.W().
    Missing trailing newline is always a warning in both original
    implementations, so that stays fixed.

    Note: the two original pipelines diverged here — encounters reports
    invalid JSON from this function (report.E, unconditionally); discovery
    silently skips it here because its own load_json_file reports invalid
    JSON later with more detail. Gating invalid-JSON reporting on `severity`
    like the other findings reproduces encounters' behavior when
    severity='error' and is a no-op change for discovery when it passes
    severity='warning' AND does not use this return value's invalid-JSON
    reporting (which discovery's current code does not — it re-parses via
    load_json_file separately). Both corpora currently contain zero invalid
    JSON files, so this path is unexercised by baseline comparison.

    Returns a dict mapping absolute Path -> parsed JSON for every
    successfully-parsed file (an empty dict entry is never created for
    invalid JSON).
    """
    if severity not in ("error", "warning"):
        raise ValueError(f"severity must be 'error' or 'warning', got {severity!r}")
    findings_fn = report.E if severity == "error" else report.W

    EXCLUDED_DIR_PARTS = {".venv", ".claude", ".git", "node_modules"}

    cache: dict = {}
    # Exclusions must only match directories *within* the scanned tree, not
    # ancestors of it — checking f.parts directly misfires when the repo
    # checkout itself sits under a path containing one of these names (e.g.
    # a worktree at .../.claude/worktrees/<branch>/), silently excluding
    # every file in the corpus.
    json_files = sorted(
        f
        for f in directory.rglob("*.json")
        if f.is_file()
        and exclude_dir_part not in f.relative_to(directory).parts
        and EXCLUDED_DIR_PARTS.isdisjoint(f.relative_to(directory).parts)
    )
    checked = 0
    for fpath in json_files:
        raw = fpath.read_text(encoding="utf-8")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            if severity == "error":
                report.E(f"{fpath.name}: invalid JSON")
            continue
        rel = fpath.relative_to(directory)
        for line_no, line in enumerate(raw.splitlines(), 1):
            stripped = line.lstrip(" ")
            indent = len(line) - len(stripped)
            if indent > 0 and indent % 2 != 0:
                findings_fn(
                    f"{rel}:{line_no}: odd indentation ({indent} spaces), expected multiples of 2"
                )
                break
            if "\t" in line:
                findings_fn(
                    f"{rel}:{line_no}: contains tab character, use 2-space indent"
                )
                break
        if not raw.endswith("\n"):
            report.W(f"{rel}: missing trailing newline")
        cache[fpath] = data
        checked += 1

    return cache
