#!/usr/bin/env python3
"""
discovery_schema_checks.py — Discovery-specific structural completeness rules for
one language file, used by validate_family.py's cross-file check.

Kept separate from validate_family.py (pure wiring) and from
encounters_schema_checks.py (a different schema) so neither content type's rules can
be edited in a way that accidentally touches the other.
"""

from shared_validation.family_check import Reporter, nonempty

# Card fields that must be non-empty when present.
_NONEMPTY_CARD_FIELDS = ("title", "subtitle", "content", "revelation_key", "identity_statement")


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
        for field in _NONEMPTY_CARD_FIELDS:
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
