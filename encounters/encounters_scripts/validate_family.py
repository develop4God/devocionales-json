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

Thin wrapper: content-agnostic cross-file logic (untranslated-leak detection, drift
detection, filename↔language consistency, key parity) lives in
shared_validation/family_check.py. This file supplies Encounters-specific structural
completeness checks and field lists only.

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
from shared_validation.family_check import run, nonempty, Reporter

ENCOUNTERS_DIR = Path(__file__).parent.parent
INDEX_PATH = ENCOUNTERS_DIR / "index.json"

_MUST_DIFFER_TOP_LEVEL = ()  # encounters have no top-level title/subtitle; cards carry these
_MUST_DIFFER_CARD_FIELDS = ("title", "subtitle", "narrative", "content", "reflection",
                             "revelation_key", "reflection_prompt")
# Per-card, nested one or more levels deep or inside a list of objects — flat
# card-field lookup can't reach these, see shared_validation.family_check.extract_path.
# Not every card type has every one of these (verse_overlay/completion_verse/prayer
# are card-type-specific) — extract_path returns [] when absent, safe to list all.
_MUST_DIFFER_NESTED_PATHS = (
    "verse_overlay.text",
    "verse_overlay.reference",
    "completion_verse.text",
    "completion_verse.reference",
    "scripture_connections[].text",
    "scripture_connections[].reference",
    "discovery_questions[].category",
    "discovery_questions[].question",
    "prayer.title",
    "prayer.content",
)
# scripture_moment cards carry verse_text/verse_reference directly on the card, not
# nested — these already work via _MUST_DIFFER_CARD_FIELDS, listed here for clarity
# since the skill groups them with the other "always translate" scripture fields.
_MUST_DIFFER_CARD_FIELDS = _MUST_DIFFER_CARD_FIELDS + ("verse_text", "verse_reference")
# Document-level (not per-card)
_MUST_DIFFER_TOP_LEVEL_PATHS = (
    "key_verse.text",
    "key_verse.reference",
    "meta.character",
)


def resolve_family(encounter_id: str) -> dict[str, Path]:
    """Return {lang: file_path} for every language file of this encounter, per index.json."""
    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    enc = next((e for e in index["encounters"] if e["id"] == encounter_id), None)
    if enc is None:
        print(f"No encounter with id '{encounter_id}' found in {INDEX_PATH}")
        sys.exit(2)
    files = enc.get("files", {})
    return {lang: ENCOUNTERS_DIR / lang / fname for lang, fname in files.items()}


def check_required_fields(lang: str, data: dict, report: Reporter):
    ctx = f"{lang}"
    for field in ("id", "type", "schema_version", "language", "bible_version",
                  "version", "estimated_reading_minutes", "meta", "key_verse", "cards"):
        if field not in data:
            report.err(f"{ctx}: missing required field '{field}'")

    kv = data.get("key_verse", {})
    if not isinstance(kv, dict) or not kv:
        report.err(f"{ctx}: key_verse missing entirely")
    else:
        for field in ("reference", "text", "bible_version"):
            if not kv.get(field):
                report.err(f"{ctx}: key_verse.{field} missing or empty")

    meta = data.get("meta", {})
    if not isinstance(meta, dict) or not meta:
        report.err(f"{ctx}: meta missing entirely")
    else:
        for field in ("character", "testament", "scripture_reference", "mood_primary",
                       "accent_color", "emoji", "tags"):
            if field not in meta:
                report.err(f"{ctx}: meta missing field '{field}'")

    cards = data.get("cards", [])
    if not cards:
        report.err(f"{ctx}: cards missing or empty")
        return

    if cards[-1].get("type") != "completion":
        report.err(f"{ctx}: last card must be type 'completion', got '{cards[-1].get('type')}'")
    if "discovery_activation" not in [c.get("type") for c in cards]:
        report.err(f"{ctx}: missing required 'discovery_activation' card")

    for card in cards:
        ctype = card.get("type", "unknown")
        card_ctx = f"{ctx} card[{card.get('order', '?')}] ({ctype})"

        for field in _MUST_DIFFER_CARD_FIELDS:
            if field in card and not nonempty(card.get(field)):
                report.err(f"{card_ctx}: field '{field}' is empty")

        if ctype == "discovery_activation":
            dqs = card.get("discovery_questions", [])
            if not dqs:
                report.err(f"{card_ctx}: discovery_questions is empty")
            else:
                for j, dq in enumerate(dqs):
                    if not nonempty(dq.get("category")) or not nonempty(dq.get("question")):
                        report.err(f"{card_ctx} discovery_questions[{j+1}]: category or question empty")
            prayer = card.get("prayer", {})
            if not nonempty(prayer.get("title")) or not nonempty(prayer.get("content")):
                report.err(f"{card_ctx}: prayer.title or prayer.content is empty")

        vo = card.get("verse_overlay")
        if vo is not None:
            for field in ("reference", "text"):
                if not nonempty(vo.get(field)):
                    report.err(f"{card_ctx}: verse_overlay.{field} is empty")

        if ctype == "completion":
            cv = card.get("completion_verse", {})
            for field in ("reference", "text", "bible_version"):
                if not nonempty(cv.get(field)):
                    report.err(f"{card_ctx}: completion_verse.{field} is empty")

        if ctype == "scripture_moment":
            for field in ("verse_reference", "verse_text"):
                if not nonempty(card.get(field)):
                    report.err(f"{card_ctx}: '{field}' is empty")

        for j, sc in enumerate(card.get("scripture_connections", []) or []):
            for field in ("reference", "text"):
                if not nonempty(sc.get(field)):
                    report.err(f"{card_ctx} scripture_connections[{j+1}]: '{field}' is empty")


def main():
    parser = argparse.ArgumentParser(
        description="Cross-validate ALL language files for one Encounter id.",
    )
    parser.add_argument("encounter_id", help="Encounter id as it appears in encounters/index.json")
    args = parser.parse_args()

    family = resolve_family(args.encounter_id)
    if not family:
        print(f"Encounter '{args.encounter_id}' has no files listed in index.json")
        sys.exit(2)

    exit_code = run(
        label="ENCOUNTERS FAMILY VALIDATOR",
        content_id=args.encounter_id,
        family=family,
        must_differ_top_level=_MUST_DIFFER_TOP_LEVEL,
        must_differ_card_fields=_MUST_DIFFER_CARD_FIELDS,
        must_differ_nested_paths=_MUST_DIFFER_NESTED_PATHS,
        must_differ_top_level_paths=_MUST_DIFFER_TOP_LEVEL_PATHS,
        check_structural_completeness=check_required_fields,
        drift_top_level_fields=("id", "type", "schema_version"),
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
