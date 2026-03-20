#!/usr/bin/env python3
"""
validate_pair.py — Deep field-by-field validation between two devotional JSON files.

Usage:
    python validate_pair.py source.json translation.json
    python validate_pair.py mammon_es.json mammon_en.json

Checks:
    1. Both files are valid JSON
    2. Structural key parity (every key in source exists in translation)
    3. Top-level fields: id, type, date, language, version, estimated_reading_minutes
    4. key_verse: reference translated, text present and non-empty
    5. Cards: count match, order match, type match, all fields present and non-empty
    6. Per-card: title, subtitle, content, revelation_key, identity_statement
    7. Per-card: greek_words / hebrew_words — count, word/transliteration preserved,
                 meaning and revelation translated (not identical to source)
    8. Per-card: scripture_connections — count match, references present,
                 text present and non-empty
    9. Per-card: discovery_questions / reflection_questions — count, categories and
                 questions present and non-empty
   10. Per-card: action_steps — count, title and description present and non-empty
   11. Per-card: prayer — title and content present and non-empty
   12. Per-card: identity_statement present and non-empty
   13. tags: count match
   14. metadata.themes: count match, all themes non-empty
   15. Detects fields present in source but missing from translation (extra gap check)
"""

import json
import sys
from pathlib import Path


# ── Colours ───────────────────────────────────────────────────────────────────

RED   = "\033[91m"
YLW   = "\033[93m"
GRN   = "\033[92m"
CYN   = "\033[96m"
RST   = "\033[0m"

def ok(msg):   print(f"  {GRN}✅ {msg}{RST}")
def warn(msg): print(f"  {YLW}⚠️  {msg}{RST}")
def err(msg):  print(f"  {RED}❌ {msg}{RST}")
def info(msg): print(f"  {CYN}ℹ️  {msg}{RST}")


# ── Counters ──────────────────────────────────────────────────────────────────

errors   = 0
warnings = 0

def E(msg):
    global errors
    errors += 1
    err(msg)

def W(msg):
    global warnings
    warnings += 1
    warn(msg)


# ── Helpers ───────────────────────────────────────────────────────────────────

def load(path: Path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        E(f"Invalid JSON in {path.name}: {e}")
        return None
    except Exception as e:
        E(f"Cannot read {path.name}: {e}")
        return None

def nonempty(val):
    """True if value is a non-empty string or a non-empty list."""
    if isinstance(val, str):
        return bool(val.strip())
    if isinstance(val, list):
        return len(val) > 0
    return val is not None

def check_field(src, tgt, key, ctx, *, must_differ=False, required=True):
    """
    Verify that `key` exists in tgt and is non-empty.
    If must_differ=True, also verify it differs from src (i.e. was actually translated).
    """
    src_val = src.get(key)
    tgt_val = tgt.get(key)

    if required and tgt_val is None:
        E(f"{ctx}: missing field '{key}'")
        return
    if tgt_val is None:
        return  # optional, not present — skip

    if not nonempty(tgt_val):
        E(f"{ctx}: field '{key}' is empty")
        return

    if must_differ and isinstance(src_val, str) and isinstance(tgt_val, str):
        if src_val.strip() == tgt_val.strip():
            W(f"{ctx}: field '{key}' appears untranslated (identical to source)")


def keys_parity(src: dict, tgt: dict, ctx: str):
    """Report keys present in src but absent in tgt."""
    for k in src:
        if k not in tgt:
            E(f"{ctx}: key '{k}' present in source but missing in translation")


# ── Validators ────────────────────────────────────────────────────────────────

def validate_top_level(src, tgt, src_lang, tgt_lang):
    print(f"\n{CYN}── Top-level fields{RST}")

    # id should match
    if src.get("id") != tgt.get("id"):
        E(f"id mismatch: source='{src.get('id')}' vs translation='{tgt.get('id')}'")
    else:
        ok(f"id matches: {src.get('id')}")

    # type should match
    if src.get("type") != tgt.get("type"):
        E(f"type mismatch: '{src.get('type')}' vs '{tgt.get('type')}'")
    else:
        ok(f"type: {src.get('type')}")

    # date should match
    if src.get("date") != tgt.get("date"):
        W(f"date differs: source='{src.get('date')}' vs translation='{tgt.get('date')}'")
    else:
        ok(f"date: {src.get('date')}")

    # language codes
    if tgt.get("language") != tgt_lang:
        E(f"language field is '{tgt.get('language')}', expected '{tgt_lang}'")
    else:
        ok(f"language: {tgt.get('language')}")

    # version must exist and be non-empty
    if not tgt.get("version"):
        E("version field missing or empty in translation")
    else:
        ok(f"version: {tgt.get('version')}")

    # estimated_reading_minutes
    if src.get("estimated_reading_minutes") != tgt.get("estimated_reading_minutes"):
        W(f"estimated_reading_minutes differs: {src.get('estimated_reading_minutes')} vs {tgt.get('estimated_reading_minutes')}")
    else:
        ok(f"estimated_reading_minutes: {tgt.get('estimated_reading_minutes')}")

    # title / subtitle should exist and differ (translated)
    for field in ("title", "subtitle"):
        check_field(src, tgt, field, "top-level", must_differ=True)
    if nonempty(tgt.get("title")) and nonempty(tgt.get("subtitle")):
        ok("title and subtitle present and translated")


def validate_key_verse(src, tgt):
    print(f"\n{CYN}── key_verse{RST}")
    src_kv = src.get("key_verse", {})
    tgt_kv = tgt.get("key_verse", {})

    if not tgt_kv:
        E("key_verse missing entirely")
        return

    # reference — must exist and be non-empty; may differ (translated book names)
    if not tgt_kv.get("reference"):
        E("key_verse.reference missing or empty")
    else:
        ok(f"reference: {tgt_kv['reference']}")

    # text — must exist, non-empty, and differ from source
    src_text = src_kv.get("text", "")
    tgt_text = tgt_kv.get("text", "")
    if not tgt_text:
        E("key_verse.text missing or empty")
    elif tgt_text.strip() == src_text.strip():
        W("key_verse.text appears untranslated (identical to source)")
    else:
        ok("key_verse.text present and translated")


def validate_word_blocks(src_card, tgt_card, card_ctx, key):
    """Validate greek_words or hebrew_words blocks."""
    src_words = src_card.get(key, [])
    tgt_words = tgt_card.get(key, [])

    if not src_words:
        return  # not present in source — skip

    if not tgt_words:
        E(f"{card_ctx}: '{key}' present in source but missing in translation")
        return

    if len(src_words) != len(tgt_words):
        E(f"{card_ctx}: '{key}' count mismatch — source={len(src_words)}, translation={len(tgt_words)}")

    for i, (sw, tw) in enumerate(zip(src_words, tgt_words)):
        wctx = f"{card_ctx} {key}[{i+1}]"

        # word and transliteration should be IDENTICAL (they're the original language terms)
        if sw.get("word") != tw.get("word"):
            W(f"{wctx}: 'word' differs — source='{sw.get('word')}' vs '{tw.get('word')}' (should be identical)")
        if sw.get("transliteration") != tw.get("transliteration"):
            W(f"{wctx}: 'transliteration' differs (should be identical)")

        # meaning and revelation must be translated (non-empty and differ from source)
        for field in ("meaning", "revelation"):
            check_field(sw, tw, field, wctx, must_differ=True)


def validate_scripture_connections(src_card, tgt_card, card_ctx):
    src_sc = src_card.get("scripture_connections", [])
    tgt_sc = tgt_card.get("scripture_connections", [])

    if not src_sc:
        return

    if not tgt_sc:
        E(f"{card_ctx}: scripture_connections present in source but missing in translation")
        return

    if len(src_sc) != len(tgt_sc):
        E(f"{card_ctx}: scripture_connections count mismatch — source={len(src_sc)}, translation={len(tgt_sc)}")

    for i, (ss, ts) in enumerate(zip(src_sc, tgt_sc)):
        ctx = f"{card_ctx} scripture_connections[{i+1}]"
        if not ts.get("reference"):
            E(f"{ctx}: reference missing or empty")
        check_field(ss, ts, "text", ctx, must_differ=True)


def validate_questions(src_card, tgt_card, card_ctx):
    key = "discovery_questions" if "discovery_questions" in src_card else \
          "reflection_questions" if "reflection_questions" in src_card else None
    if not key:
        return

    src_qs = src_card.get(key, [])
    tgt_qs = tgt_card.get(key, [])

    if not tgt_qs:
        E(f"{card_ctx}: '{key}' present in source but missing in translation")
        return

    if len(src_qs) != len(tgt_qs):
        E(f"{card_ctx}: '{key}' count mismatch — source={len(src_qs)}, translation={len(tgt_qs)}")

    for i, (sq, tq) in enumerate(zip(src_qs, tgt_qs)):
        ctx = f"{card_ctx} {key}[{i+1}]"
        check_field(sq, tq, "category", ctx, must_differ=True)
        check_field(sq, tq, "question",  ctx, must_differ=True)


def validate_action_steps(src_card, tgt_card, card_ctx):
    src_steps = src_card.get("action_steps", [])
    tgt_steps = tgt_card.get("action_steps", [])

    if not src_steps:
        return

    if not tgt_steps:
        E(f"{card_ctx}: action_steps present in source but missing in translation")
        return

    if len(src_steps) != len(tgt_steps):
        E(f"{card_ctx}: action_steps count mismatch — source={len(src_steps)}, translation={len(tgt_steps)}")

    for i, (ss, ts) in enumerate(zip(src_steps, tgt_steps)):
        ctx = f"{card_ctx} action_steps[{i+1}]"
        check_field(ss, ts, "title",       ctx, must_differ=True)
        check_field(ss, ts, "description", ctx, must_differ=True)


def validate_prayer(src_card, tgt_card, card_ctx):
    src_p = src_card.get("prayer")
    tgt_p = tgt_card.get("prayer")

    if not src_p:
        return
    if not tgt_p:
        E(f"{card_ctx}: prayer present in source but missing in translation")
        return

    check_field(src_p, tgt_p, "title",   card_ctx + " prayer", must_differ=True)
    check_field(src_p, tgt_p, "content", card_ctx + " prayer", must_differ=True)


def validate_cards(src, tgt):
    print(f"\n{CYN}── cards{RST}")
    src_cards = src.get("cards", [])
    tgt_cards = tgt.get("cards", [])

    if len(src_cards) != len(tgt_cards):
        E(f"Card count mismatch: source={len(src_cards)}, translation={len(tgt_cards)}")
        # Still try to validate what we can
    else:
        ok(f"Card count: {len(src_cards)}")

    for i, (sc, tc) in enumerate(zip(src_cards, tgt_cards)):
        card_ctx = f"card[{sc.get('order', i+1)}] ({sc.get('type', '?')})"

        # order and type must match
        if sc.get("order") != tc.get("order"):
            E(f"{card_ctx}: order mismatch — source={sc.get('order')}, translation={tc.get('order')}")
        if sc.get("type") != tc.get("type"):
            E(f"{card_ctx}: type mismatch — source={sc.get('type')}, translation={tc.get('type')}")

        # icon must match
        if sc.get("icon") != tc.get("icon"):
            W(f"{card_ctx}: icon differs — source={sc.get('icon')}, translation={tc.get('icon')}")

        # check key parity (no source key missing in translation)
        keys_parity(sc, tc, card_ctx)

        # text fields must be translated
        for field in ("title", "subtitle", "content", "revelation_key", "identity_statement"):
            if field in sc:
                check_field(sc, tc, field, card_ctx, must_differ=True)

        # structured sub-fields
        validate_word_blocks(sc, tc, card_ctx, "greek_words")
        validate_word_blocks(sc, tc, card_ctx, "hebrew_words")
        validate_scripture_connections(sc, tc, card_ctx)
        validate_questions(sc, tc, card_ctx)
        validate_action_steps(sc, tc, card_ctx)
        validate_prayer(sc, tc, card_ctx)

    if len(src_cards) == len(tgt_cards):
        ok("All cards validated")


def validate_tags(src, tgt):
    print(f"\n{CYN}── tags{RST}")
    src_tags = src.get("tags", [])
    tgt_tags = tgt.get("tags", [])

    if len(src_tags) != len(tgt_tags):
        E(f"Tags count mismatch: source={len(src_tags)}, translation={len(tgt_tags)}")
        info(f"Source tags:      {src_tags}")
        info(f"Translation tags: {tgt_tags}")
    else:
        ok(f"Tags count: {len(tgt_tags)}")
        # Tags may be translated or kept as slugs — just ensure none are empty
        for t in tgt_tags:
            if not str(t).strip():
                E(f"Empty tag found in translation")


def validate_metadata(src, tgt):
    print(f"\n{CYN}── metadata{RST}")
    src_meta = src.get("metadata", {})
    tgt_meta = tgt.get("metadata", {})

    if not tgt_meta:
        E("metadata missing in translation")
        return

    keys_parity(src_meta, tgt_meta, "metadata")

    # themes count and content
    src_themes = src_meta.get("themes", [])
    tgt_themes = tgt_meta.get("themes", [])

    if len(src_themes) != len(tgt_themes):
        E(f"metadata.themes count mismatch: source={len(src_themes)}, translation={len(tgt_themes)}")
    else:
        ok(f"themes count: {len(tgt_themes)}")
        for i, (st, tt) in enumerate(zip(src_themes, tgt_themes)):
            if not str(tt).strip():
                E(f"metadata.themes[{i+1}]: empty in translation")
            elif st.strip() == tt.strip():
                W(f"metadata.themes[{i+1}]: appears untranslated: '{tt}'")

    # passage — should be translated (book name)
    src_passage = src_meta.get("passage", "")
    tgt_passage = tgt_meta.get("passage", "")
    if src_passage and not tgt_passage:
        E("metadata.passage missing in translation")
    elif src_passage and tgt_passage and src_passage == tgt_passage:
        W(f"metadata.passage appears untranslated: '{tgt_passage}'")
    elif tgt_passage:
        ok(f"passage: {tgt_passage}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 3:
        print(f"Usage: python validate_pair.py <source.json> <translation.json>")
        print(f"Example: python validate_pair.py mammon_es.json mammon_en.json")
        sys.exit(1)

    src_path = Path(sys.argv[1])
    tgt_path = Path(sys.argv[2])

    print(f"\n{'='*70}")
    print(f"  DEVOTIONAL JSON PAIR VALIDATOR")
    print(f"{'='*70}")
    print(f"  Source:      {src_path.name}")
    print(f"  Translation: {tgt_path.name}")

    src = load(src_path)
    tgt = load(tgt_path)

    if src is None or tgt is None:
        print(f"\n{RED}Cannot proceed — fix JSON errors first.{RST}")
        sys.exit(1)

    # Infer language codes from the 'language' field
    src_lang = src.get("language", "?")
    tgt_lang = tgt.get("language", "?")
    print(f"  Languages:   {src_lang.upper()} → {tgt_lang.upper()}")
    print(f"{'='*70}")

    # Top-level key parity
    print(f"\n{CYN}── top-level key parity{RST}")
    keys_parity(src, tgt, "root")

    # Run all validations
    validate_top_level(src, tgt, src_lang, tgt_lang)
    validate_key_verse(src, tgt)
    validate_cards(src, tgt)
    validate_tags(src, tgt)
    validate_metadata(src, tgt)

    # Summary
    print(f"\n{'='*70}")
    print(f"  SUMMARY")
    print(f"{'='*70}")
    if errors == 0 and warnings == 0:
        print(f"  {GRN}✅ PERFECT — no errors or warnings{RST}")
    elif errors == 0:
        print(f"  {YLW}⚠️  PASSED with {warnings} warning(s) — review recommended{RST}")
    else:
        print(f"  {RED}❌ FAILED — {errors} error(s), {warnings} warning(s){RST}")
    print(f"{'='*70}\n")

    sys.exit(0 if errors == 0 else 1)


if __name__ == "__main__":
    main()
