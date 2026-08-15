"""review_fields.py — per-content-type map of which fields are worth sending to an
AI review pass (e.g. content_batch_graph's flag/verify/critic nodes), as opposed to
every field a structural validator checks for presence.

Not a structural validator: this module never reports errors/warnings, has no
Reporter dependency, and does not care whether a field is missing — it only answers
"if this prose field exists, where is it and what does it say."

Path format: dot/digit only (e.g. "cards.2.content", "data.es.2025-08-01.0.reflexion"),
matching content_batch_graph's domain.validate._resolve_path exactly — NOT this
package's own bracket convention used in check error messages (e.g. "cards[2].content").
A consumer must be able to take a path from here and splice a fix back in without any
translation step.

The "which fields count as reviewable prose" judgment intentionally mirrors, but does
not import, discovery_schema_checks.py's and encounters_schema_checks.py's
_NONEMPTY_CARD_FIELDS — importing them here would invert this package's dependency
direction (those files import FROM shared_validation, never the reverse). Slug/short
fields those lists include for structural completeness (revelation_key,
identity_statement) are deliberately excluded here — not prose worth AI review.
"""

from __future__ import annotations


def _card_text_fields(cards: list, fields_by_type: dict[str, tuple[str, ...]]) -> dict[str, str]:
    """Walk a cards[] list, pulling non-empty string fields named for each card's
    `type` per `fields_by_type`, keyed by dot/digit path."""
    out: dict[str, str] = {}
    for i, card in enumerate(cards):
        for field in fields_by_type.get(card.get("type"), ()):
            value = card.get(field)
            if isinstance(value, str) and value.strip():
                out[f"cards.{i}.{field}"] = value
    return out


# ── Daily devotional ──────────────────────────────────────────────────────────
# Entry shape: {"data": {<lang>: {<date>: [{"reflexion": ..., "oracion": ..., ...}]}}}.
# Only reflexion/oracion are free-form prose worth AI review — versiculo is a quoted
# Bible reference, para_meditar/tags are short structured lists, not prose.

_DEVOTIONAL_ENTRY_FIELDS = ("reflexion", "oracion")


def get_devotional_review_fields(
    data: dict, lang: str, date: str, entry_index: int = 0
) -> dict[str, str]:
    """Returns {dot_digit_path: text} for one devotional entry's reviewable fields."""
    entries = data.get("data", {}).get(lang, {}).get(date, [])
    if entry_index >= len(entries):
        return {}
    entry = entries[entry_index]
    prefix = f"data.{lang}.{date}.{entry_index}"
    return {
        f"{prefix}.{field}": entry[field]
        for field in _DEVOTIONAL_ENTRY_FIELDS
        if isinstance(entry.get(field), str) and entry[field].strip()
    }


# ── Discovery ────────────────────────────────────────────────────────────────
# Every card type carries title/subtitle/content except discovery_activation, whose
# prose lives in nested prayer.title / prayer.content instead.

_DISCOVERY_CARD_FIELDS: dict[str, tuple[str, ...]] = {
    "historical_context": ("title", "subtitle", "content"),
    "greek_exegesis": ("title", "subtitle", "content"),
    "prophetic_thread": ("title", "subtitle", "content"),
    "theological_depth": ("title", "subtitle", "content"),
}


def get_discovery_review_fields(data: dict) -> dict[str, str]:
    """Returns {dot_digit_path: text} for a Discovery study's reviewable fields."""
    out = _card_text_fields(data.get("cards", []), _DISCOVERY_CARD_FIELDS)
    for i, card in enumerate(data.get("cards", [])):
        if card.get("type") != "discovery_activation":
            continue
        prayer = card.get("prayer", {})
        for field in ("title", "content"):
            value = prayer.get(field)
            if isinstance(value, str) and value.strip():
                out[f"cards.{i}.prayer.{field}"] = value
    return out


# ── Encounters ───────────────────────────────────────────────────────────────
# Prose field name varies by card type: narrative (cinematic_scene), content
# (character_moment/theological_depth), reflection (scripture_moment).

_ENCOUNTERS_CARD_FIELDS: dict[str, tuple[str, ...]] = {
    "cinematic_scene": ("title", "narrative"),
    "character_moment": ("title", "subtitle", "content"),
    "theological_depth": ("title", "subtitle", "content"),
    "scripture_moment": ("reflection",),
}


def get_encounters_review_fields(data: dict) -> dict[str, str]:
    """Returns {dot_digit_path: text} for an Encounters study's reviewable fields."""
    out = _card_text_fields(data.get("cards", []), _ENCOUNTERS_CARD_FIELDS)
    for i, card in enumerate(data.get("cards", [])):
        if card.get("type") != "discovery_activation":
            continue
        prayer = card.get("prayer", {})
        for field in ("title", "content"):
            value = prayer.get(field)
            if isinstance(value, str) and value.strip():
                out[f"cards.{i}.prayer.{field}"] = value
    return out


REVIEW_FIELD_GETTERS = {
    "discovery": get_discovery_review_fields,
    "encounters": get_encounters_review_fields,
}
