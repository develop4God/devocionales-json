#!/usr/bin/env python3
"""
validate_family.py — Cross-file validation for ALL language files of one Discovery
study.

Pure wiring: content-agnostic cross-file logic (structural drift detection,
filename↔language consistency, key parity) lives in shared_validation/family_check.py.
Discovery's own structural completeness rules live in discovery_schema_checks.py, kept
out of this file so Discovery's schema rules can never be edited in the same place as
Encounters' (see encounters_scripts/validate_family.py + encounters_schema_checks.py).

Usage:
    python3 validate_family.py <study_id>
    python3 validate_family.py mammon_anxiety_freedom_001

Resolves the file set from discovery/index.json's `files` map for that study id — do
not pass individual file paths; this only makes sense as a whole-family check.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from shared_validation.family_check import run
from discovery_schema_checks import check_required_fields

DISCOVERY_DIR = Path(__file__).parent.parent
INDEX_PATH = DISCOVERY_DIR / "index.json"


def resolve_family(study_id: str) -> dict[str, Path]:
    """Return {lang: file_path} for every language file of this study, per index.json."""
    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    study = next((s for s in index["studies"] if s["id"] == study_id), None)
    if study is None:
        print(f"No study with id '{study_id}' found in {INDEX_PATH}")
        sys.exit(2)
    files = study.get("files", {})
    return {lang: DISCOVERY_DIR / lang / fname for lang, fname in files.items()}


def main():
    parser = argparse.ArgumentParser(
        description="Cross-validate ALL language files for one Discovery study id.",
    )
    parser.add_argument("study_id", help="Study id as it appears in discovery/index.json")
    args = parser.parse_args()

    family = resolve_family(args.study_id)
    if not family:
        print(f"Study '{args.study_id}' has no files listed in index.json")
        sys.exit(2)

    exit_code = run(
        label="DISCOVERY FAMILY VALIDATOR",
        content_id=args.study_id,
        family=family,
        check_structural_completeness=check_required_fields,
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
