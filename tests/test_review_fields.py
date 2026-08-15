"""test_review_fields.py — unit tests for shared_validation/checks/review_fields.py.

Covers the per-content-type extraction functions against small inline fixtures
(not real corpus files — those are exercised indirectly by content_batch_graph's own
integration, this file's job is the extraction logic itself) and the dot/digit path
format contract that content_batch_graph's domain.validate._resolve_path depends on.
"""

import unittest

from shared_validation.checks.review_fields import (
    get_devotional_review_fields,
    get_discovery_review_fields,
    get_encounters_review_fields,
)

# ── Devotional ──────────────────────────────────────────────────────────────────


class TestDevotionalReviewFields(unittest.TestCase):
    def test_extracts_reflexion_and_oracion(self):
        data = {
            "data": {
                "es": {
                    "2025-08-01": [
                        {
                            "reflexion": "Un texto de reflexion.",
                            "oracion": "Una oracion.",
                            "versiculo": "Juan 3:16",
                            "para_meditar": ["a", "b"],
                        }
                    ]
                }
            }
        }
        fields = get_devotional_review_fields(data, "es", "2025-08-01")
        self.assertEqual(
            fields,
            {
                "data.es.2025-08-01.0.reflexion": "Un texto de reflexion.",
                "data.es.2025-08-01.0.oracion": "Una oracion.",
            },
        )

    def test_missing_date_returns_empty(self):
        data = {"data": {"es": {}}}
        self.assertEqual(get_devotional_review_fields(data, "es", "2099-01-01"), {})

    def test_missing_language_returns_empty(self):
        data = {"data": {}}
        self.assertEqual(get_devotional_review_fields(data, "fr", "2025-08-01"), {})

    def test_blank_field_excluded(self):
        data = {"data": {"es": {"2025-08-01": [{"reflexion": "  ", "oracion": "x"}]}}}
        fields = get_devotional_review_fields(data, "es", "2025-08-01")
        self.assertEqual(fields, {"data.es.2025-08-01.0.oracion": "x"})


# ── Discovery ─────────────────────────────────────────────────────────────────


class TestDiscoveryReviewFields(unittest.TestCase):
    def test_extracts_title_subtitle_content_per_card(self):
        data = {
            "cards": [
                {
                    "type": "historical_context",
                    "title": "T1",
                    "subtitle": "S1",
                    "content": "C1",
                    "revelation_key": "not_reviewed",
                },
                {
                    "type": "greek_exegesis",
                    "title": "T2",
                    "subtitle": "S2",
                    "content": "C2",
                },
            ]
        }
        fields = get_discovery_review_fields(data)
        self.assertEqual(
            fields,
            {
                "cards.0.title": "T1",
                "cards.0.subtitle": "S1",
                "cards.0.content": "C1",
                "cards.1.title": "T2",
                "cards.1.subtitle": "S2",
                "cards.1.content": "C2",
            },
        )

    def test_discovery_activation_uses_nested_prayer_fields(self):
        data = {
            "cards": [
                {
                    "type": "discovery_activation",
                    "title": "Activation title",
                    "prayer": {"title": "Prayer title", "content": "Prayer content"},
                }
            ]
        }
        fields = get_discovery_review_fields(data)
        self.assertEqual(
            fields,
            {
                "cards.0.prayer.title": "Prayer title",
                "cards.0.prayer.content": "Prayer content",
            },
        )

    def test_unknown_card_type_yields_no_fields(self):
        data = {"cards": [{"type": "some_future_type", "content": "unreviewed"}]}
        self.assertEqual(get_discovery_review_fields(data), {})

    def test_no_cards_returns_empty(self):
        self.assertEqual(get_discovery_review_fields({}), {})


# ── Encounters ────────────────────────────────────────────────────────────────


class TestEncountersReviewFields(unittest.TestCase):
    def test_cinematic_scene_uses_narrative_not_content(self):
        data = {"cards": [{"type": "cinematic_scene", "title": "T", "narrative": "N"}]}
        fields = get_encounters_review_fields(data)
        self.assertEqual(fields, {"cards.0.title": "T", "cards.0.narrative": "N"})

    def test_scripture_moment_uses_reflection_only(self):
        data = {
            "cards": [
                {
                    "type": "scripture_moment",
                    "verse_reference": "Jn 3:16",
                    "reflection": "R",
                }
            ]
        }
        fields = get_encounters_review_fields(data)
        self.assertEqual(fields, {"cards.0.reflection": "R"})

    def test_character_moment_uses_title_subtitle_content(self):
        data = {
            "cards": [
                {
                    "type": "character_moment",
                    "title": "T",
                    "subtitle": "S",
                    "content": "C",
                }
            ]
        }
        fields = get_encounters_review_fields(data)
        self.assertEqual(
            fields, {"cards.0.title": "T", "cards.0.subtitle": "S", "cards.0.content": "C"}
        )

    def test_discovery_activation_uses_nested_prayer_fields(self):
        data = {
            "cards": [
                {
                    "type": "discovery_activation",
                    "prayer": {"title": "PT", "content": "PC"},
                }
            ]
        }
        fields = get_encounters_review_fields(data)
        self.assertEqual(fields, {"cards.0.prayer.title": "PT", "cards.0.prayer.content": "PC"})

    def test_completion_card_yields_no_prose_fields(self):
        data = {
            "cards": [
                {
                    "type": "completion",
                    "completion_verse": {"reference": "x", "text": "y"},
                }
            ]
        }
        self.assertEqual(get_encounters_review_fields(data), {})


if __name__ == "__main__":
    unittest.main()
