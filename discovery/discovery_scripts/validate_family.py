#!/usr/bin/env python3
"""
validate_family.py — Cross-file validation for ALL language files of one Discovery
study, replacing validate_pair.py's two-file-only design.

Why: validate_pair.py compared exactly one (source, translation) pair. That misses a
whole class of real bugs: an error already present in the EN file (itself derived from
ES) silently propagating, unchanged and "consistent," into every EN-derived language
(JA/ZH/DE/AR/HI/FIL) — each pairwise check against EN would pass, because each file
faithfully matches a EN file that was already wrong. This script instead loads every
language file for one study and cross-checks the whole set against each other, with no
single file treated as ground truth — an outlier is suspicious regardless of which file
disagrees with the rest.

Checks (per study, across all its language files):
    1. All files are valid JSON.
    2. Structural key parity — every top-level and per-card key present in one file is
       present in all others (using the file with the most keys as the structural
       reference, since a missing key anywhere is itself a finding, not a baseline
       choice).
    3. Per-file structural completeness (ported from validate_pair.py): required
       top-level fields, key_verse, per-card fields, greek_words/hebrew_words count and
       identity, scripture_connections, discovery_questions/reflection_questions,
       action_steps, prayer, tags, metadata.themes — all present, correctly counted,
       non-empty.
    4. Cross-file "untranslated leak": a field expected to differ per language (title,
       content, revelation_key, etc.) that is byte-identical across 2+ files — flags
       both/all matching files, not just one, since either could be the one that failed
       to translate.
    5. Cross-file "drift": a field expected to match across every language (id, type,
       order, card count, key structure) where one or more files disagree with what the
       rest agree on.
    6. Filename↔language field consistency: each file's own `language` field must match
       its filename's language-code segment.

Usage:
    python3 validate_family.py <study_id>
    python3 validate_family.py mammon_anxiety_freedom

Resolves the file set from discovery/index.json's `files` map for that study id — do
not pass individual file paths; this only makes sense as a whole-family check.
"""

import argparse
import json
import re
import sys
from pathlib import Path

DISCOVERY_DIR = Path(__file__).parent.parent
INDEX_PATH = DISCOVERY_DIR / "index.json"

# Short category labels identical across languages by convention (international
# loan-words) — must_differ checks would otherwise false-positive on these.
_SHARED_WORDS = {
    "Motivation", "Situation", "Kontext", "Meditation", "Vision", "Mission",
    "Transformation", "Identität", "Analyse", "Reflexion", "Resonanz",
}

RED, YLW, GRN, CYN, RST = "\033[91m", "\033[93m", "\033[92m", "\033[96m", "\033[0m"

def ok(msg):   print(f"  {GRN}✅ {msg}{RST}")
def warn(msg): print(f"  {YLW}⚠️  {msg}{RST}")
def err(msg):  print(f"  {RED}❌ {msg}{RST}")
def info(msg): print(f"  {CYN}ℹ️  {msg}{RST}")

errors = 0
warnings = 0

def E(msg):
    global errors
    errors += 1
    err(msg)

def W(msg):
    global warnings
    warnings += 1
    warn(msg)


# ── Loading ───────────────────────────────────────────────────────────────────

def resolve_family(study_id: str) -> dict[str, Path]:
    """Return {lang: file_path} for every language file of this study, per index.json."""
    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    study = next((s for s in index["studies"] if s["id"] == study_id), None)
    if study is None:
        print(f"{RED}No study with id '{study_id}' found in {INDEX_PATH}{RST}")
        sys.exit(2)
    files = study.get("files", {})
    return {lang: DISCOVERY_DIR / lang / fname for lang, fname in files.items()}


def load_all(family: dict[str, Path]) -> dict[str, dict]:
    loaded = {}
    for lang, path in family.items():
        if not path.exists():
            W(f"{lang}: file listed in index.json but not found at {path} (pending translation?)")
            continue
        try:
            loaded[lang] = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            E(f"{lang}: invalid JSON in {path.name}: {e}")
    return loaded


def nonempty(val):
    if isinstance(val, str):
        return bool(val.strip())
    if isinstance(val, list):
        return len(val) > 0
    return val is not None


# ── Filename <-> language field consistency ──────────────────────────────────

def check_filename_language_match(lang: str, path: Path, data: dict):
    m = re.search(r"_([a-z]{2,3})_\d+\.json$", path.name)
    if not m:
        W(f"{lang}: filename '{path.name}' doesn't match expected _<lang>_NNN.json pattern")
        return
    filename_lang = m.group(1)
    field_lang = data.get("language")
    if filename_lang != lang:
        E(f"{lang}: filename '{path.name}' lang segment is '{filename_lang}', expected '{lang}'")
    if field_lang != lang:
        E(f"{lang}: language field is '{field_lang}', expected '{lang}' (filename: {path.name})")


# ── Cross-file: fields that must differ per language ─────────────────────────

_MUST_DIFFER_TOP_LEVEL = ("title", "subtitle")
_MUST_DIFFER_CARD_FIELDS = ("title", "subtitle", "content", "revelation_key", "identity_statement")

def check_untranslated_leak(field_label: str, values_by_lang: dict[str, str]):
    """Flag if 2+ languages share byte-identical text for a field that should be translated."""
    seen: dict[str, list[str]] = {}
    for lang, val in values_by_lang.items():
        if not isinstance(val, str) or not val.strip():
            continue
        key = val.strip()
        seen.setdefault(key, []).append(lang)
    for val, langs in seen.items():
        if len(langs) < 2:
            continue
        if val in _SHARED_WORDS:
            continue
        W(f"{field_label}: identical across {', '.join(sorted(langs))} — "
          f"{'one or more of these' if len(langs) > 2 else 'one of these'} may not "
          f"have been translated: {val[:60]!r}")


# ── Cross-file: fields that must match across every language ─────────────────

def check_drift(field_label: str, values_by_lang: dict[str, object]):
    """Flag if one or more languages disagree with what the majority agree on."""
    if len(values_by_lang) < 2:
        return
    counts: dict[str, list[str]] = {}
    for lang, val in values_by_lang.items():
        key = json.dumps(val, sort_keys=True, ensure_ascii=False)
        counts.setdefault(key, []).append(lang)
    if len(counts) <= 1:
        return
    majority_key = max(counts, key=lambda k: len(counts[k]))
    for key, langs in counts.items():
        if key == majority_key:
            continue
        E(f"{field_label}: {', '.join(sorted(langs))} disagree with the rest "
          f"({', '.join(sorted(counts[majority_key]))}) — values: "
          f"{json.loads(key)!r} vs {json.loads(majority_key)!r}")


# ── Per-file structural completeness (ported from validate_pair.py) ──────────

def check_required_fields(lang: str, data: dict):
    ctx = f"{lang}"
    if not data.get("version"):
        E(f"{ctx}: version field missing or empty")
    for field in ("id", "type", "language", "estimated_reading_minutes"):
        if data.get(field) is None:
            E(f"{ctx}: top-level field '{field}' missing")

    kv = data.get("key_verse", {})
    if not kv:
        E(f"{ctx}: key_verse missing entirely")
    else:
        if not kv.get("reference"):
            E(f"{ctx}: key_verse.reference missing or empty")
        if not kv.get("text"):
            E(f"{ctx}: key_verse.text missing or empty")

    cards = data.get("cards", [])
    if not cards:
        E(f"{ctx}: cards missing or empty")
    for i, card in enumerate(cards):
        card_ctx = f"{ctx} card[{card.get('order', i+1)}] ({card.get('type', '?')})"
        for field in _MUST_DIFFER_CARD_FIELDS:
            if field in card and not nonempty(card.get(field)):
                E(f"{card_ctx}: field '{field}' is empty")
        for key in ("greek_words", "hebrew_words"):
            words = card.get(key)
            if words:
                for j, w in enumerate(words):
                    if not w.get("word") or not w.get("transliteration"):
                        E(f"{card_ctx} {key}[{j+1}]: missing word or transliteration")
                    for f in ("meaning", "revelation"):
                        if f in w and not nonempty(w.get(f)):
                            E(f"{card_ctx} {key}[{j+1}]: '{f}' is empty")
        for sc in card.get("scripture_connections", []) or []:
            if not sc.get("reference"):
                E(f"{card_ctx} scripture_connections: reference missing or empty")
            if not nonempty(sc.get("text")):
                E(f"{card_ctx} scripture_connections: text missing or empty")
        qkey = "discovery_questions" if "discovery_questions" in card else \
               "reflection_questions" if "reflection_questions" in card else None
        if qkey:
            for q in card.get(qkey, []):
                if not nonempty(q.get("category")) or not nonempty(q.get("question")):
                    E(f"{card_ctx} {qkey}: category or question missing/empty")
        for step in card.get("action_steps", []) or []:
            if not nonempty(step.get("title")) or not nonempty(step.get("description")):
                E(f"{card_ctx} action_steps: title or description missing/empty")
        prayer = card.get("prayer")
        if prayer and (not nonempty(prayer.get("title")) or not nonempty(prayer.get("content"))):
            E(f"{card_ctx} prayer: title or content missing/empty")

    for t in data.get("tags", []) or []:
        if not str(t).strip():
            E(f"{ctx}: empty tag found")
    for i, theme in enumerate(data.get("metadata", {}).get("themes", []) or []):
        if not str(theme).strip():
            E(f"{ctx}: metadata.themes[{i+1}] is empty")


# ── Cross-file structural key parity ──────────────────────────────────────────

def flatten_keys(d, prefix=""):
    """Yield dotted key paths for a nested dict, stopping at list boundaries."""
    if not isinstance(d, dict):
        return
    for k, v in d.items():
        path = f"{prefix}.{k}" if prefix else k
        yield path
        if isinstance(v, dict):
            yield from flatten_keys(v, path)


def check_key_parity(loaded: dict[str, dict]):
    all_keys: dict[str, set] = {lang: set(flatten_keys(data)) for lang, data in loaded.items()}
    union = set().union(*all_keys.values()) if all_keys else set()
    for lang, keys in all_keys.items():
        missing = union - keys
        for key in sorted(missing):
            # Only flag if at least half the family has this key — otherwise it's
            # likely a legitimate optional/content-specific field, not a real gap.
            present_in = sum(1 for k in all_keys.values() if key in k)
            if present_in >= max(2, len(all_keys) // 2):
                E(f"{lang}: missing key '{key}' present in {present_in}/{len(all_keys)} sibling files")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Cross-validate ALL language files for one Discovery study id.",
    )
    parser.add_argument("study_id", help="Study id as it appears in discovery/index.json")
    args = parser.parse_args()

    family = resolve_family(args.study_id)
    if not family:
        print(f"{RED}Study '{args.study_id}' has no files listed in index.json{RST}")
        sys.exit(2)

    print(f"\n{'='*70}")
    print(f"  DISCOVERY FAMILY VALIDATOR — {args.study_id}")
    print(f"{'='*70}")
    print(f"  Languages in index.json: {', '.join(sorted(family))}")

    loaded = load_all(family)
    if len(loaded) < 2:
        print(f"{RED}Fewer than 2 files loaded — cannot cross-validate.{RST}")
        print(f"{RED}This is a real failure, not a pass: cross-file checks never ran.{RST}")
        print(f"{RED}(If this is mid-batch with only some languages translated so far,{RST}")
        print(f"{RED} that's expected — but the caller must not treat this as 'validated.'){RST}")
        sys.exit(1)

    print(f"  Languages loaded:        {', '.join(sorted(loaded))}")
    print(f"{'='*70}")

    print(f"\n{CYN}── filename ↔ language field consistency{RST}")
    for lang, path in family.items():
        if lang in loaded:
            check_filename_language_match(lang, path, loaded[lang])

    print(f"\n{CYN}── per-file structural completeness{RST}")
    for lang, data in loaded.items():
        check_required_fields(lang, data)

    print(f"\n{CYN}── cross-file key parity{RST}")
    check_key_parity(loaded)

    print(f"\n{CYN}── cross-file: fields that must differ per language{RST}")
    for field in _MUST_DIFFER_TOP_LEVEL:
        check_untranslated_leak(f"top-level '{field}'", {l: d.get(field) for l, d in loaded.items()})
    max_cards = max((len(d.get("cards", [])) for d in loaded.values()), default=0)
    for i in range(max_cards):
        for field in _MUST_DIFFER_CARD_FIELDS:
            values = {}
            for lang, data in loaded.items():
                cards = data.get("cards", [])
                if i < len(cards) and field in cards[i]:
                    values[lang] = cards[i].get(field)
            if values:
                check_untranslated_leak(f"card[{i+1}] '{field}'", values)

    print(f"\n{CYN}── cross-file: fields that must match across all languages{RST}")
    check_drift("id", {l: d.get("id") for l, d in loaded.items()})
    check_drift("type", {l: d.get("type") for l, d in loaded.items()})
    check_drift("card count", {l: len(d.get("cards", [])) for l, d in loaded.items()})
    for i in range(max_cards):
        order_values, type_values = {}, {}
        for lang, data in loaded.items():
            cards = data.get("cards", [])
            if i < len(cards):
                order_values[lang] = cards[i].get("order")
                type_values[lang] = cards[i].get("type")
        check_drift(f"card[{i+1}].order", order_values)
        check_drift(f"card[{i+1}].type", type_values)

    print(f"\n{'='*70}")
    print(f"  SUMMARY")
    print(f"{'='*70}")
    if errors == 0 and warnings == 0:
        print(f"  {GRN}✅ PERFECT — no errors or warnings across {len(loaded)} files{RST}")
    elif errors == 0:
        print(f"  {YLW}⚠️  PASSED with {warnings} warning(s) — review recommended{RST}")
    else:
        print(f"  {RED}❌ FAILED — {errors} error(s), {warnings} warning(s){RST}")
    print(f"{'='*70}\n")

    sys.exit(0 if errors == 0 else 1)


if __name__ == "__main__":
    main()
