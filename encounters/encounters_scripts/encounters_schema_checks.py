#!/usr/bin/env python3
"""
encounters_schema_checks.py — Encounters-specific structural completeness rules for
one language file, used by validate_family.py's cross-file check.

Kept separate from validate_family.py (pure wiring) and from
discovery_schema_checks.py (a different schema) so neither content type's rules can
be edited in a way that accidentally touches the other.
"""

from shared_validation.family_check import Reporter, nonempty

# Card fields that must be non-empty when present.
_NONEMPTY_CARD_FIELDS = ("title", "subtitle", "narrative", "content", "reflection",
                          "revelation_key", "reflection_prompt", "verse_text", "verse_reference")


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

        for field in _NONEMPTY_CARD_FIELDS:
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
