#!/usr/bin/env python3
"""
validate_family.py — Cross-file validation for ALL language files of one Encounter.

Closes the same gap validate_encounters.py's validate_cross_translation() has: that
function only ever checks each non-EN language against a fixed EN baseline, so an
error already present in EN (itself derived from ES) would propagate unchanged into
every EN-derived language and pass every pairwise check, since each file faithfully
matches an EN that was already wrong. This script instead loads every language file
for one encounter and cross-checks the whole set against each other, with no single
file treated as ground truth.

Pure wiring: content-agnostic cross-file logic (structural drift detection,
filename↔language consistency, key parity) lives in shared_validation/family_check.py.
Encounters' own structural completeness rules live in encounters_schema_checks.py, kept
out of this file so Encounters' schema rules can never be edited in the same place as
Discovery's (see discovery_scripts/validate_family.py + discovery_schema_checks.py).

Usage:
    python3 validate_family.py <encounter_id>
    python3 validate_family.py peter_water_001

Resolves the file set from encounters/index.json's `files` map for that encounter id
— do not pass individual file paths; this only makes sense as a whole-family check.

Does NOT replace validate_encounters.py — that script's per-file schema/structure
checks (schema_version, card-type-specific required keys, image URL validity,
scripture reference resolution) are unaffected and still required. This adds the
cross-file layer neither validate_encounters.py nor the old validate_pair.py-style
per-language-pair approach could provide.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from shared_validation.family_check import run
from encounters_schema_checks import check_required_fields

ENCOUNTERS_DIR = Path(__file__).parent.parent
INDEX_PATH = ENCOUNTERS_DIR / "index.json"


def resolve_family(encounter_id: str) -> dict[str, Path]:
    """Return {lang: file_path} for every language file of this encounter, per index.json."""
    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    enc = next((e for e in index["encounters"] if e["id"] == encounter_id), None)
    if enc is None:
        print(f"No encounter with id '{encounter_id}' found in {INDEX_PATH}")
        sys.exit(2)
    files = enc.get("files", {})
    return {lang: ENCOUNTERS_DIR / lang / fname for lang, fname in files.items()}


def main():
    parser = argparse.ArgumentParser(
        description="Cross-validate ALL language files for one Encounter id.",
    )
    parser.add_argument(
        "encounter_id", help="Encounter id as it appears in encounters/index.json"
    )
    args = parser.parse_args()

    family = resolve_family(args.encounter_id)
    if not family:
        print(f"Encounter '{args.encounter_id}' has no files listed in index.json")
        sys.exit(2)

    exit_code = run(
        label="ENCOUNTERS FAMILY VALIDATOR",
        content_id=args.encounter_id,
        family=family,
        check_structural_completeness=check_required_fields,
        drift_top_level_fields=("id", "type", "schema_version"),
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
