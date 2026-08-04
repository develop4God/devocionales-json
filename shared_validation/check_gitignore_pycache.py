#!/usr/bin/env python3
"""
check_gitignore_pycache.py — Verify no __pycache__ directory anywhere in the
repo is tracked by git or visible as untracked (i.e. .gitignore actually
covers it), regardless of nesting depth.

Exit codes: 0 = clean, 1 = one or more __pycache__ dirs are tracked or
appear as untracked in git status.
"""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent


def find_pycache_dirs() -> list:
    return [
        p
        for p in REPO_ROOT.rglob("__pycache__")
        if p.is_dir() and ".git" not in p.parts
    ]


def git_sees(path: Path) -> bool:
    result = subprocess.run(
        ["git", "status", "--porcelain", "--ignored=no", str(path)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    return bool(result.stdout.strip())


def main() -> int:
    pycache_dirs = find_pycache_dirs()
    leaked = [p for p in pycache_dirs if git_sees(p)]

    print(
        f"Found {len(pycache_dirs)} __pycache__ director{'y' if len(pycache_dirs) == 1 else 'ies'} on disk."
    )

    if leaked:
        print(f"NOT ignored by git ({len(leaked)}):")
        for p in leaked:
            print(f"   - {p.relative_to(REPO_ROOT)}")
        return 1

    print("All __pycache__ directories are correctly ignored by .gitignore.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
