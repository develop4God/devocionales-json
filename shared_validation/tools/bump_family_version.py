"""bump_family_version.py — auto-bump a study/encounter family's index.json
"version" by +0.1 when its content changed but the family wasn't already
bumped in the same diff.

Why this exists: discovery/index.json and encounters/index.json each carry
one content version per family (not per language file) — see each family
entry's "version" key, e.g. discovery/index.json's foot_washing_love_001. The
existing convention (git log: "bump family versions" commits) is a human
manually adding +0.1 to every touched family after a content fix. That step
gets forgotten or mis-keyed; this script closes that gap by making the bump
automatic and consistent, run from CI on push to main (see
.github/workflows/ci.yml). It does not change the versioning scheme itself
(family-level, not per-file/fingerprint) — only removes the manual step.

New families (an id not present in base_sha's index.json — this corpus adds
studies/encounters continuously) are never auto-bumped: whoever authors a new
family sets its starting version themselves (e.g. "1.0"), and this script
only ever adjusts versions for families that already existed at base_sha.
A family is also skipped if its own version already changed between
base_sha and head_sha (a manual bump already happened) — only per-family,
so one manually-bumped family in a PR doesn't block auto-bumping a different
family touched in the same PR.

Usage:
    python3 shared_validation/tools/bump_family_version.py <base_sha> <head_sha>
    python3 shared_validation/tools/bump_family_version.py --dry-run <base_sha> <head_sha>

Exit codes: 0 = ran (bumped 0 or more families), 1 = git diff or index.json
read/write failure.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
CONTENT_TYPES = {
    "discovery": (REPO_ROOT / "discovery", "studies"),
    "encounters": (REPO_ROOT / "encounters", "encounters"),
}


def changed_files(base_sha: str, head_sha: str) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", f"{base_sha}..{head_sha}"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in result.stdout.splitlines() if line.strip()]


def index_at_revision(sha: str, index_rel_path: str) -> dict:
    result = subprocess.run(
        ["git", "show", f"{sha}:{index_rel_path}"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def bump_version(version: str) -> str:
    major, _, minor = version.partition(".")
    return f"{major}.{int(minor or 0) + 1}"


def families_with_changed_files(
    paths: list[str], index: dict, index_key: str, content_dir: Path
) -> set[str]:
    """Family ids (from the given index snapshot) whose language files
    appear in the changed-paths list, derived from each family's files{}."""
    basename_to_id = {
        fname: entry["id"]
        for entry in index[index_key]
        for fname in entry.get("files", {}).values()
    }
    rel_prefix = f"{content_dir.relative_to(REPO_ROOT)}/"
    touched = set()
    for path in paths:
        if not path.startswith(rel_prefix) or path.endswith("index.json"):
            continue
        family_id = basename_to_id.get(Path(path).name)
        if family_id:
            touched.add(family_id)
    return touched


def apply_bumps(base_sha: str, head_sha: str, dry_run: bool) -> int:
    paths = changed_files(base_sha, head_sha)
    total_bumped = 0

    for content_type, (content_dir, index_key) in CONTENT_TYPES.items():
        index_rel_path = str((content_dir / "index.json").relative_to(REPO_ROOT))
        head_index = json.loads(
            (content_dir / "index.json").read_text(encoding="utf-8")
        )

        try:
            base_index = index_at_revision(base_sha, index_rel_path)
        except subprocess.CalledProcessError:
            base_index = {index_key: []}  # index.json is new at base_sha

        base_versions = {e["id"]: e["version"] for e in base_index[index_key]}
        touched_ids = families_with_changed_files(
            paths, head_index, index_key, content_dir
        )

        changed_any = False
        for entry in head_index[index_key]:
            family_id = entry["id"]
            if family_id not in touched_ids:
                continue
            if family_id not in base_versions:
                print(
                    f"ℹ️  {content_type}/{family_id}: new family — skipping auto-bump."
                )
                continue
            if entry["version"] != base_versions[family_id]:
                print(
                    f"ℹ️  {content_type}/{family_id}: version already changed "
                    f"({base_versions[family_id]} → {entry['version']}) — skipping auto-bump."
                )
                continue

            old = entry["version"]
            new = bump_version(old)
            entry["version"] = new
            total_bumped += 1
            changed_any = True
            print(f"🔧 {content_type}/{family_id}: {old} → {new}")

        if changed_any and not dry_run:
            index_path = content_dir / "index.json"
            index_path.write_text(
                json.dumps(head_index, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

    if total_bumped == 0:
        print("ℹ️  No family versions needed a bump.")
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
