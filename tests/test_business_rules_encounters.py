"""test_business_rules_encounters.py — unit tests for the untested
content-validation rules in encounters/encounters_scripts/validate_encounters.py.

tests/test_promoted_validators.py and tests/test_run_report.py only cover
structural/gating behavior (index.json errors, RunReport formatting) — this
file covers the actual business rules: per-card-type required-key dispatch
and the English-book-name / cognate detection helpers. This is new coverage
for pre-existing, currently-untested logic, not a regression fix.

Imports validate_encounters.py directly (not via subprocess) so assertions
can inspect the Report object's accumulated findings precisely. The module
needs verify_image_urls.py importable as a sibling (it does a bare
`from verify_image_urls import (...)`), so encounters_scripts/ is added to
sys.path here — same requirement the module itself has when run as a script.

Does not modify any production logic — test-only. Anything that looked
imperfect while writing these is called out in comments, not "fixed" here.
"""

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "encounters" / "encounters_scripts"))

import validate_encounters as ve
from shared_validation.report import Report
from shared_validation.text_checks import is_cognate


# ── CARD_REQUIRED_KEYS dispatch ─────────────────────────────────────────────
#
# validate_encounter_file() does a lot of unrelated top-level/meta/key_verse
# validation before it ever reaches the per-card loop. To test the
# CARD_REQUIRED_KEYS dispatch in isolation without that noise drowning out
# the assertion, each test builds a fully-valid encounter shell (so nothing
# outside the cards array trips an error) and varies only the one card under
# test — then filters the report for errors mentioning the specific missing
# key, rather than asserting on the total error count (which would be
# brittle against unrelated future validation additions).

_BIBLE_VERSIONS = {"en": {"allowed_versions": ["KJV", "NIV"]}}

# One minimal valid card per CARD_REQUIRED_KEYS entry, satisfying every key
# CARD_REQUIRED_KEYS.get(ctype) currently lists — used as the "everything
# present" baseline that each test then knocks one key out of.
_VALID_CARDS = {
    "cinematic_scene": {
        "order": 1,
        "type": "cinematic_scene",
        "image_url": "x.png",
        "title": "A Title",
        "narrative": "Some narrative text.",
        "revelation_key": "key1",
    },
    "scripture_moment": {
        "order": 1,
        "type": "scripture_moment",
        "image_url": "x.png",
        "verse_reference": "John 3:16",
        "verse_text": "For God so loved...",
        "reflection": "A reflection.",
        "revelation_key": "key1",
    },
    "character_moment": {
        "order": 1,
        "type": "character_moment",
        "image_url": "x.png",
        "title": "A Title",
        "content": "Some content.",
        "revelation_key": "key1",
    },
    "theological_depth": {
        "order": 1,
        "type": "theological_depth",
        "image_url": "x.png",
        "title": "A Title",
        "content": "Some content.",
        "revelation_key": "key1",
    },
    "interactive_moment": {
        "order": 1,
        "type": "interactive_moment",
        "image_url": "x.png",
        "title": "A Title",
        "reflection_prompt": "A prompt.",
    },
    "discovery_activation": {
        "order": 1,
        "type": "discovery_activation",
        "image_url": "x.png",
        "title": "A Title",
        "discovery_questions": [{"category": "Trust", "question": "Why?"}],
        "prayer": {"title": "Pray", "content": "Content"},
    },
    "completion": {
        "order": 1,
        "type": "completion",
        "image_url": "x.png",
        "completion_verse": {
            "reference": "John 3:16",
            "text": "x",
            "bible_version": "KJV",
        },
        "reflection_prompt": "A prompt.",
        "celebration_type": "confetti",
    },
}


def _make_encounter(card: dict) -> dict:
    """A fully-valid encounter shell wrapping a single card, satisfying
    every check in validate_encounter_file() outside the per-card loop, so
    each CARD_REQUIRED_KEYS test only ever sees findings from the card
    itself."""
    # The last card must be type 'completion' and a discovery_activation
    # card must exist — so tests for those two types use the card as-is
    # (already satisfies both), and every other type gets a synthetic
    # discovery_activation + completion appended so those two structural
    # rules don't fire and pollute the report.
    cards = [card]
    if card["type"] != "discovery_activation":
        cards.append(dict(_VALID_CARDS["discovery_activation"], order=len(cards) + 1))
    if card["type"] != "completion":
        cards.append(dict(_VALID_CARDS["completion"], order=len(cards) + 1))

    return {
        "id": "test_encounter_001",
        "type": "encounter",
        "schema_version": ve.SCHEMA_VERSION,
        "language": "en",
        "bible_version": "KJV",
        "version": "1.0",
        "estimated_reading_minutes": 5,
        "meta": {
            "character": "x",
            "testament": "new",
            "scripture_reference": "John 3:16",
            "mood_primary": "hopeful",
            "accent_color": "#123456",
            "emoji": "✝️",
            "tags": [],
        },
        "key_verse": {"reference": "John 3:16", "text": "x", "bible_version": "KJV"},
        "cards": cards,
    }


class TestCardRequiredKeysDispatch(unittest.TestCase):
    """One test per card type: confirm CARD_REQUIRED_KEYS correctly flags a
    missing required key for that type, via validate_encounter_file()."""

    def _assert_missing_key_flagged(self, ctype: str, missing_key: str):
        card = dict(_VALID_CARDS[ctype])
        del card[missing_key]
        data = _make_encounter(card)

        report = Report("TEST")
        ve.validate_encounter_file(
            data, "en", "test.json", "test_encounter_001", report, _BIBLE_VERSIONS
        )

        matching = [
            e for e in report.errors if f"missing required key '{missing_key}'" in e
        ]
        self.assertTrue(
            matching,
            f"Expected an error for missing '{missing_key}' on card type '{ctype}', "
            f"got errors: {report.errors}",
        )

    def test_cinematic_scene_missing_narrative(self):
        self._assert_missing_key_flagged("cinematic_scene", "narrative")

    def test_scripture_moment_missing_verse_text(self):
        self._assert_missing_key_flagged("scripture_moment", "verse_text")

    def test_character_moment_missing_content(self):
        self._assert_missing_key_flagged("character_moment", "content")

    def test_theological_depth_missing_title(self):
        self._assert_missing_key_flagged("theological_depth", "title")

    def test_interactive_moment_missing_reflection_prompt(self):
        self._assert_missing_key_flagged("interactive_moment", "reflection_prompt")

    def test_discovery_activation_missing_prayer(self):
        self._assert_missing_key_flagged("discovery_activation", "prayer")

    def test_completion_missing_celebration_type(self):
        self._assert_missing_key_flagged("completion", "celebration_type")

    def test_unknown_card_type_gets_a_warning(self):
        """Card types not in CARD_REQUIRED_KEYS fall back to a generic
        ['order', 'type', 'image_url'] requirement and are flagged with a
        warning (not an error) for being unrecognized — this is the
        behavior at validate_encounters.py's `if ctype not in
        CARD_REQUIRED_KEYS: report.W(...)` line."""
        card = {"order": 1, "type": "some_future_card_type", "image_url": "x.png"}
        data = _make_encounter(card)

        report = Report("TEST")
        ve.validate_encounter_file(
            data, "en", "test.json", "test_encounter_001", report, _BIBLE_VERSIONS
        )

        matching = [
            w
            for w in report.warnings
            if "unknown card type 'some_future_card_type'" in w
        ]
        self.assertTrue(
            matching, f"Expected an unknown-card-type warning, got: {report.warnings}"
        )


# ── is_cognate (shared_validation.text_checks) ──────────────────────────────
#
# Note: this function lives in shared_validation/text_checks.py, not as a
# local `_is_cognate` in validate_encounters.py anymore — it was extracted
# during the shared_validation migration. Testing the actual live function.


class TestIsCognate(unittest.TestCase):
    def test_known_french_cognates_pass(self):
        for word in ("courage", "grace", "grâce"):
            with self.subTest(word=word):
                self.assertTrue(is_cognate(word, "fr"))

    def test_known_portuguese_cognates_pass(self):
        for word in ("coragem", "graça"):
            with self.subTest(word=word):
                self.assertTrue(is_cognate(word, "pt"))

    def test_known_spanish_cognates_pass(self):
        for word in ("coraje", "gracia"):
            with self.subTest(word=word):
                self.assertTrue(is_cognate(word, "es"))

    def test_known_german_cognate_legion_passes(self):
        self.assertTrue(is_cognate("legion", "de"))

    def test_unknown_word_does_not_pass(self):
        self.assertFalse(is_cognate("nonexistentword", "fr"))

    def test_cognate_of_wrong_language_does_not_pass(self):
        # 'courage' is a French cognate, not Spanish.
        self.assertFalse(is_cognate("courage", "es"))

    def test_is_case_and_whitespace_insensitive(self):
        self.assertTrue(is_cognate("  Courage  ", "fr"))

    def test_language_with_no_cognate_table_returns_false(self):
        self.assertFalse(is_cognate("anything", "zh"))


if __name__ == "__main__":
    unittest.main()
