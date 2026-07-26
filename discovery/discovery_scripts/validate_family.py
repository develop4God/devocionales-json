#!/usr/bin/env python3
"""
validate_family.py — Cross-file validation for ALL language files of one Discovery
study.

Thin wrapper: content-agnostic cross-file logic (untranslated-leak detection, drift
detection, filename↔language consistency, key parity) lives in
shared_validation/family_check.py. This file supplies Discovery-specific structural
completeness checks and field lists only.

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
from shared_validation.family_check import run, nonempty, Reporter

DISCOVERY_DIR = Path(__file__).parent.parent
INDEX_PATH = DISCOVERY_DIR / "index.json"

# Short category labels identical across languages by convention (international
# loan-words) — must_differ checks would otherwise false-positive on these.
_SHARED_WORDS = {
    "Motivation", "Situation", "Kontext", "Meditation", "Vision", "Mission",
    "Transformation", "Identität", "Analyse", "Reflexion", "Resonanz",
}

_MUST_DIFFER_TOP_LEVEL = ("title", "subtitle")
_MUST_DIFFER_CARD_FIELDS = ("title", "subtitle", "content", "revelation_key", "identity_statement")
# Per-card, nested one or more levels deep or inside a list of objects — flat
# card-field lookup can't reach these, see shared_validation.family_check.extract_path.
_MUST_DIFFER_NESTED_PATHS = (
    "scripture_connections[].text",
    "scripture_connections[].reference",
    "discovery_questions[].category",
    "discovery_questions[].question",
    "action_steps[].title",
    "action_steps[].description",
    "prayer.title",
    "prayer.content",
)
# Document-level (not per-card)
_MUST_DIFFER_TOP_LEVEL_PATHS = (
    "key_verse.text",
    "key_verse.reference",
)


def resolve_family(study_id: str) -> dict[str, Path]:
    """Return {lang: file_path} for every language file of this study, per index.json."""
    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    study = next((s for s in index["studies"] if s["id"] == study_id), None)
    if study is None:
        print(f"No study with id '{study_id}' found in {INDEX_PATH}")
        sys.exit(2)
    files = study.get("files", {})
    return {lang: DISCOVERY_DIR / lang / fname for lang, fname in files.items()}


def check_required_fields(lang: str, data: dict, report: Reporter):
    ctx = f"{lang}"
    if not data.get("version"):
        report.err(f"{ctx}: version field missing or empty")
    for field in ("id", "type", "language", "estimated_reading_minutes"):
        if data.get(field) is None:
            report.err(f"{ctx}: top-level field '{field}' missing")

    kv = data.get("key_verse", {})
    if not kv:
        report.err(f"{ctx}: key_verse missing entirely")
    else:
        if not kv.get("reference"):
            report.err(f"{ctx}: key_verse.reference missing or empty")
        if not kv.get("text"):
            report.err(f"{ctx}: key_verse.text missing or empty")

    cards = data.get("cards", [])
    if not cards:
        report.err(f"{ctx}: cards missing or empty")
    for i, card in enumerate(cards):
        card_ctx = f"{ctx} card[{card.get('order', i+1)}] ({card.get('type', '?')})"
        for field in _MUST_DIFFER_CARD_FIELDS:
            if field in card and not nonempty(card.get(field)):
                report.err(f"{card_ctx}: field '{field}' is empty")
        for key in ("greek_words", "hebrew_words"):
            words = card.get(key)
            if words:
                for j, w in enumerate(words):
                    if not w.get("word") or not w.get("transliteration"):
                        report.err(f"{card_ctx} {key}[{j+1}]: missing word or transliteration")
                    for f in ("meaning", "revelation"):
                        if f in w and not nonempty(w.get(f)):
                            report.err(f"{card_ctx} {key}[{j+1}]: '{f}' is empty")
        for sc in card.get("scripture_connections", []) or []:
            if not sc.get("reference"):
                report.err(f"{card_ctx} scripture_connections: reference missing or empty")
            if not nonempty(sc.get("text")):
                report.err(f"{card_ctx} scripture_connections: text missing or empty")
        qkey = "discovery_questions" if "discovery_questions" in card else \
               "reflection_questions" if "reflection_questions" in card else None
        if qkey:
            for q in card.get(qkey, []):
                if not nonempty(q.get("category")) or not nonempty(q.get("question")):
                    report.err(f"{card_ctx} {qkey}: category or question missing/empty")
        for step in card.get("action_steps", []) or []:
            if not nonempty(step.get("title")) or not nonempty(step.get("description")):
                report.err(f"{card_ctx} action_steps: title or description missing/empty")
        prayer = card.get("prayer")
        if prayer and (not nonempty(prayer.get("title")) or not nonempty(prayer.get("content"))):
            report.err(f"{card_ctx} prayer: title or content missing/empty")

    for t in data.get("tags", []) or []:
        if not str(t).strip():
            report.err(f"{ctx}: empty tag found")
    for i, theme in enumerate(data.get("metadata", {}).get("themes", []) or []):
        if not str(theme).strip():
            report.err(f"{ctx}: metadata.themes[{i+1}] is empty")


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
        must_differ_top_level=_MUST_DIFFER_TOP_LEVEL,
        must_differ_card_fields=_MUST_DIFFER_CARD_FIELDS,
        must_differ_nested_paths=_MUST_DIFFER_NESTED_PATHS,
        must_differ_top_level_paths=_MUST_DIFFER_TOP_LEVEL_PATHS,
        check_structural_completeness=check_required_fields,
        shared_words=_SHARED_WORDS,
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
