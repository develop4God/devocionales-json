"""bump_devocionales_date.py — auto-update index.json's per-file "last
updated" date when a Devocional_year_*.json file changes but index.json
wasn't already updated in the same diff.

Why this exists: index.json's files.<lang>.<version>.<year> entry is a
date string (e.g. "2025": "2026-04-27") next to that combo's filename —
this is the devocionales corpus's equivalent of Discovery/Encounters'
per-family version (see shared_validation/tools/bump_family_version.py),
just date-typed instead of semver-typed. There is no established manual
convention here (unlike the discovery "+0.1" pattern) because this file
serves a production app read by real users (6000+ MAU, 1000+ DAU) — the
app displays a side card driven by the corpus's freshness, so a stale or
forgotten date here is a real user-facing correctness issue, not just a
bookkeeping gap.

A combo's date is bumped to the push date only if: the combo already
existed in index.json at base_sha (a brand-new lang/version/year combo
sets its own initial date, same reasoning as
bump_family_version.py's new-family skip) and its date wasn't already
manually changed in the same diff. The top-level "updated_at" is bumped
to the same push date whenever any per-combo date changes.

Usage:
    python3 devocionales_scripts/bump_devocionales_date.py <base_sha> <head_sha>
    python3 devocionales_scripts/bump_devocionales_date.py --dry-run <base_sha> <head_sha>

Exit codes: 0 = ran (bumped 0 or more combos), 1 = git diff/show or
index.json read/write failure.
"""

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
INDEX_PATH = REPO_ROOT / "index.json"
INDEX_REL_PATH = "index.json"


def changed_files(base_sha: str, head_sha: str) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", f"{base_sha}..{head_sha}"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in result.stdout.splitlines() if line.strip()]


def index_at_revision(sha: str) -> dict:
    result = subprocess.run(
        ["git", "show", f"{sha}:{INDEX_REL_PATH}"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def combo_dates(index: dict) -> dict[str, str]:
    """Map filename -> declared date string, flattened across every
    lang/version/year combo in files{}."""
    result = {}
    for versions in index.get("files", {}).values():
        if not isinstance(versions, dict):
            continue
        for payload in versions.values():
            if not isinstance(payload, dict):
                continue
            files_map = payload.get("files", {})
            for year, filename in files_map.items():
                result[filename] = payload.get(year)
    return result


def apply_bumps(
    base_sha: str, head_sha: str, dry_run: bool, today: str | None = None
) -> int:
    today = today or datetime.now(UTC).date().isoformat()
    paths = changed_files(base_sha, head_sha)
    changed_devocionales_files = {
        Path(p).name
        for p in paths
        if Path(p).name.startswith("Devocional_year_") and Path(p).parent == Path(".")
    }
    if not changed_devocionales_files:
        print("ℹ️  No Devocional_year_*.json files changed.")
        return 0

    head_index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    try:
        base_index = index_at_revision(base_sha)
    except subprocess.CalledProcessError:
        base_index = {"files": {}}  # index.json is new at base_sha

    base_dates = combo_dates(base_index)
    total_bumped = 0

    for versions in head_index.get("files", {}).values():
        if not isinstance(versions, dict):
            continue
        for payload in versions.values():
            if not isinstance(payload, dict):
                continue
            files_map = payload.get("files", {})
            for year, filename in files_map.items():
                if filename not in changed_devocionales_files:
                    continue
                if filename not in base_dates:
                    print(f"ℹ️  {filename}: new combo — skipping auto-bump.")
                    continue
                if payload.get(year) != base_dates[filename]:
                    print(
                        f"ℹ️  {filename}: date already changed "
                        f"({base_dates[filename]} → {payload.get(year)}) — skipping auto-bump."
                    )
                    continue

                old = payload.get(year)
                payload[year] = today
                total_bumped += 1
                print(f"🔧 {filename}: {old} → {today}")

    if total_bumped > 0:
        head_index["updated_at"] = today
        if not dry_run:
            INDEX_PATH.write_text(
                json.dumps(head_index, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
    else:
        print("ℹ️  No combo dates needed a bump.")

    return total_bumped


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("base_sha")
    parser.add_argument("head_sha")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    try:
        apply_bumps(args.base_sha, args.head_sha, dry_run=args.dry_run)
    except subprocess.CalledProcessError as e:
        print(f"❌ git diff/show failed: {e.stderr}", file=sys.stderr)
        sys.exit(1)
    except (KeyError, json.JSONDecodeError) as e:
        print(f"❌ index.json read/write failed: {e}", file=sys.stderr)
        sys.exit(1)
