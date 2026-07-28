"""family_resolver.py — resolve a content id (discovery/encounters) to its
{lang: file_path} family, and list every id of a content type, both read from
that content type's index.json.

Extracted from greek_family_pattern_check.py so any other standalone script
that needs "every language file for one study/encounter id" (or "every id of
one content type") can depend on this single implementation instead of
re-deriving index.json resolution. discovery_scripts/validate_family.py and
encounters_scripts/validate_family.py each have their own copy of the single-
family resolve_family() used by their live validators — this module is for
standalone/cross-cutting scripts (greek_family_pattern_check.py,
lexicon_family_check.py, ...), not a replacement for those.
"""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
DISCOVERY_DIR = REPO_ROOT / "discovery"
ENCOUNTERS_DIR = REPO_ROOT / "encounters"


def _resolve_discovery_family(study_id: str) -> dict[str, Path]:
    index = json.loads((DISCOVERY_DIR / "index.json").read_text(encoding="utf-8"))
    study = next((s for s in index["studies"] if s["id"] == study_id), None)
    if study is None:
        return {}
    return {
        lang: DISCOVERY_DIR / lang / fname
        for lang, fname in study.get("files", {}).items()
    }


def _resolve_encounters_family(encounter_id: str) -> dict[str, Path]:
    index = json.loads((ENCOUNTERS_DIR / "index.json").read_text(encoding="utf-8"))
    enc = next((e for e in index["encounters"] if e["id"] == encounter_id), None)
    if enc is None:
        return {}
    return {
        lang: ENCOUNTERS_DIR / lang / fname
        for lang, fname in enc.get("files", {}).items()
    }


def _all_discovery_ids() -> list[str]:
    index = json.loads((DISCOVERY_DIR / "index.json").read_text(encoding="utf-8"))
    return [s["id"] for s in index["studies"]]


def _all_encounters_ids() -> list[str]:
    index = json.loads((ENCOUNTERS_DIR / "index.json").read_text(encoding="utf-8"))
    return [e["id"] for e in index["encounters"]]


RESOLVERS = {
    "discovery": _resolve_discovery_family,
    "encounters": _resolve_encounters_family,
}
ID_LISTERS = {
    "discovery": _all_discovery_ids,
    "encounters": _all_encounters_ids,
}
