#!/usr/bin/env python3
"""
family_check.py — content-agnostic cross-file validation for ALL language files of
one content item (a Discovery study or an Encounters encounter).

Why this exists: comparing each translation only against a single fixed baseline (e.g.
"each language vs. EN") cannot catch an error already present in that baseline
silently propagating, unchanged and "consistent," into every language derived from it
— each pairwise check against the baseline passes, because each file faithfully
matches a baseline that was already wrong. This module instead loads every language
file for one content item and cross-checks the whole set against each other, with no
single file treated as ground truth — an outlier is suspicious regardless of which
file disagrees with the rest.

This module holds only the checks that are identical in shape for any content type:
    - Filename ↔ language field consistency
    - Cross-file "untranslated leak": a field expected to differ per language that is
      byte-identical across 2+ files
    - Cross-file "drift": a field expected to match across every language where one or
      more files disagree with what the rest agree on
    - Cross-file structural key parity
    - The load/orchestrate/report shell

Per-content-type structural completeness (which fields/blocks are required, what
"must differ per language" means for that content's cards) is NOT here — each content
type's own script (discovery/discovery_scripts/validate_family.py,
encounters/encounters_scripts/validate_family.py) supplies that as a callback plus its
own must-differ field lists, then calls into this module's `run()`.
"""

import json
import re
import sys
from pathlib import Path
from typing import Callable, Optional

RED, YLW, GRN, CYN, RST = "\033[91m", "\033[93m", "\033[92m", "\033[96m", "\033[0m"


class Reporter:
    """Collects errors/warnings for one validation run. Not a global — each `run()`
    call gets its own instance, so this module is safe to call multiple times in one
    process (e.g. a CI loop over every content item) without cross-contaminating
    counts."""

    def __init__(self):
        self.errors = 0
        self.warnings = 0

    def ok(self, msg):   print(f"  {GRN}✅ {msg}{RST}")
    def warn(self, msg): print(f"  {YLW}⚠️  {msg}{RST}"); self.warnings += 1
    def err(self, msg):  print(f"  {RED}❌ {msg}{RST}"); self.errors += 1
    def info(self, msg): print(f"  {CYN}ℹ️  {msg}{RST}")


def nonempty(val):
    if isinstance(val, str):
        return bool(val.strip())
    if isinstance(val, list):
        return len(val) > 0
    return val is not None


# ── Loading ───────────────────────────────────────────────────────────────────

def load_all(family: dict[str, Path], report: Reporter) -> dict[str, dict]:
    loaded = {}
    for lang, path in family.items():
        if not path.exists():
            report.warn(f"{lang}: file listed in index but not found at {path} (pending translation?)")
            continue
        try:
            loaded[lang] = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            report.err(f"{lang}: invalid JSON in {path.name}: {e}")
    return loaded


# ── Filename <-> language field consistency ──────────────────────────────────

def check_filename_language_match(lang: str, path: Path, data: dict, report: Reporter):
    m = re.search(r"_([a-z]{2,3})_\d+\.json$", path.name)
    if not m:
        report.warn(f"{lang}: filename '{path.name}' doesn't match expected _<lang>_NNN.json pattern")
        return
    filename_lang = m.group(1)
    field_lang = data.get("language")
    if filename_lang != lang:
        report.err(f"{lang}: filename '{path.name}' lang segment is '{filename_lang}', expected '{lang}'")
    if field_lang != lang:
        report.err(f"{lang}: language field is '{field_lang}', expected '{lang}' (filename: {path.name})")


# ── Cross-file: fields that must differ per language ─────────────────────────

def check_untranslated_leak(field_label: str, values_by_lang: dict[str, str],
                             report: Reporter, shared_words: set[str] = frozenset()):
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
        if val in shared_words:
            continue
        report.warn(f"{field_label}: identical across {', '.join(sorted(langs))} — "
                    f"{'one or more of these' if len(langs) > 2 else 'one of these'} may not "
                    f"have been translated: {val[:60]!r}")


# ── Cross-file: fields that must match across every language ─────────────────

def check_drift(field_label: str, values_by_lang: dict[str, object], report: Reporter):
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
        report.err(f"{field_label}: {', '.join(sorted(langs))} disagree with the rest "
                   f"({', '.join(sorted(counts[majority_key]))}) — values: "
                   f"{json.loads(key)!r} vs {json.loads(majority_key)!r}")


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


def check_key_parity(loaded: dict[str, dict], report: Reporter):
    all_keys: dict[str, set] = {lang: set(flatten_keys(data)) for lang, data in loaded.items()}
    union = set().union(*all_keys.values()) if all_keys else set()
    for lang, keys in all_keys.items():
        missing = union - keys
        for key in sorted(missing):
            # Only flag if at least half the family has this key — otherwise it's
            # likely a legitimate optional/content-specific field, not a real gap.
            present_in = sum(1 for k in all_keys.values() if key in k)
            if present_in >= max(2, len(all_keys) // 2):
                report.err(f"{lang}: missing key '{key}' present in {present_in}/{len(all_keys)} sibling files")


# ── Orchestration shell ───────────────────────────────────────────────────────

def run(
    *,
    label: str,
    content_id: str,
    family: dict[str, Path],
    must_differ_top_level: tuple[str, ...],
    must_differ_card_fields: tuple[str, ...],
    check_structural_completeness: Callable[[str, dict, Reporter], None],
    shared_words: set[str] = frozenset(),
    drift_top_level_fields: tuple[str, ...] = ("id", "type"),
) -> int:
    """
    Run the full cross-file family validation and print a report. Returns the exit
    code the caller's main() should sys.exit() with (0 = pass, 1 = fail).

    `family`: {lang: file_path}, already resolved by the caller from its own index.json.
    `check_structural_completeness(lang, data, report)`: caller-supplied per-file
    completeness check (required fields, card structure) — content-type-specific.
    """
    report = Reporter()

    print(f"\n{'='*70}")
    print(f"  {label} — {content_id}")
    print(f"{'='*70}")
    print(f"  Languages in index: {', '.join(sorted(family))}")

    loaded = load_all(family, report)
    if len(loaded) < 2:
        print(f"{RED}Fewer than 2 files loaded — cannot cross-validate.{RST}")
        print(f"{RED}This is a real failure, not a pass: cross-file checks never ran.{RST}")
        print(f"{RED}(If this is mid-batch with only some languages translated so far,{RST}")
        print(f"{RED} that's expected — but the caller must not treat this as 'validated.'){RST}")
        return 1

    print(f"  Languages loaded:    {', '.join(sorted(loaded))}")
    print(f"{'='*70}")

    print(f"\n{CYN}── filename ↔ language field consistency{RST}")
    for lang, path in family.items():
        if lang in loaded:
            check_filename_language_match(lang, path, loaded[lang], report)

    print(f"\n{CYN}── per-file structural completeness{RST}")
    for lang, data in loaded.items():
        check_structural_completeness(lang, data, report)

    print(f"\n{CYN}── cross-file key parity{RST}")
    check_key_parity(loaded, report)

    print(f"\n{CYN}── cross-file: fields that must differ per language{RST}")
    for field in must_differ_top_level:
        check_untranslated_leak(
            f"top-level '{field}'", {l: d.get(field) for l, d in loaded.items()},
            report, shared_words,
        )
    max_cards = max((len(d.get("cards", [])) for d in loaded.values()), default=0)
    for i in range(max_cards):
        for field in must_differ_card_fields:
            values = {}
            for lang, data in loaded.items():
                cards = data.get("cards", [])
                if i < len(cards) and field in cards[i]:
                    values[lang] = cards[i].get(field)
            if values:
                check_untranslated_leak(f"card[{i+1}] '{field}'", values, report, shared_words)

    print(f"\n{CYN}── cross-file: fields that must match across all languages{RST}")
    for field in drift_top_level_fields:
        check_drift(field, {l: d.get(field) for l, d in loaded.items()}, report)
    check_drift("card count", {l: len(d.get("cards", [])) for l, d in loaded.items()}, report)
    for i in range(max_cards):
        order_values, type_values = {}, {}
        for lang, data in loaded.items():
            cards = data.get("cards", [])
            if i < len(cards):
                order_values[lang] = cards[i].get("order")
                type_values[lang] = cards[i].get("type")
        check_drift(f"card[{i+1}].order", order_values, report)
        check_drift(f"card[{i+1}].type", type_values, report)

    print(f"\n{'='*70}")
    print(f"  SUMMARY")
    print(f"{'='*70}")
    if report.errors == 0 and report.warnings == 0:
        print(f"  {GRN}✅ PERFECT — no errors or warnings across {len(loaded)} files{RST}")
    elif report.errors == 0:
        print(f"  {YLW}⚠️  PASSED with {report.warnings} warning(s) — review recommended{RST}")
    else:
        print(f"  {RED}❌ FAILED — {report.errors} error(s), {report.warnings} warning(s){RST}")
    print(f"{'='*70}\n")

    return 0 if report.errors == 0 else 1
