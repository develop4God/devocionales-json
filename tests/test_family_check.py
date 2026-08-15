"""test_family_check.py — unit tests for shared_validation/family_check.py and the
two per-content-type schema-check modules (discovery_schema_checks.py,
encounters_schema_checks.py) that supply its check_structural_completeness callback.

Previously untested: PHASE E (cross-file family validation) had no unit coverage at
all prior to this file — only exercised indirectly via the master validators running
against real corpus data, which never hits error paths on a clean corpus.

Imports directly (not via subprocess) so assertions can inspect Reporter's error/
warning counts precisely. discovery_schema_checks.py and encounters_schema_checks.py
are imported by their own directories being added to sys.path, mirroring how
validate_family.py imports them (both live beside their respective validate_family.py).
"""

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "discovery" / "discovery_scripts"))
sys.path.insert(0, str(REPO_ROOT / "encounters" / "encounters_scripts"))

import discovery_schema_checks  # noqa: E402
import encounters_schema_checks  # noqa: E402

from shared_validation.checks.family_check import (  # noqa: E402
    Reporter,
    check_drift,
    check_filename_language_match,
    check_key_parity,
    nonempty,
)

# ── nonempty ──────────────────────────────────────────────────────────────────


class TestNonempty(unittest.TestCase):
    def test_blank_string_is_empty(self):
        self.assertFalse(nonempty("   "))

    def test_nonblank_string_is_nonempty(self):
        self.assertTrue(nonempty("hello"))

    def test_empty_list_is_empty(self):
        self.assertFalse(nonempty([]))

    def test_nonempty_list_is_nonempty(self):
        self.assertTrue(nonempty([1]))

    def test_none_is_empty(self):
        self.assertFalse(nonempty(None))

    def test_zero_is_nonempty(self):
        # Only None/blank-string/empty-list count as empty — 0 is a real value.
        self.assertTrue(nonempty(0))


# ── check_drift ───────────────────────────────────────────────────────────────


class TestCheckDrift(unittest.TestCase):
    def test_all_agree_no_finding(self):
        report = Reporter()
        check_drift("type", {"en": "a", "es": "a", "fr": "a"}, report)
        self.assertEqual(report.errors, 0)

    def test_single_outlier_flagged(self):
        report = Reporter()
        check_drift("type", {"en": "a", "es": "a", "fr": "b"}, report)
        self.assertEqual(report.errors, 1)

    def test_fewer_than_two_values_skipped(self):
        report = Reporter()
        check_drift("type", {"en": "a"}, report)
        self.assertEqual(report.errors, 0)


# ── check_key_parity ────────────────────────────────────────────────────────


class TestCheckKeyParity(unittest.TestCase):
    def test_matching_keys_no_finding(self):
        report = Reporter()
        loaded = {
            "en": {"id": "x", "cards": [{"title": "a"}]},
            "es": {"id": "x", "cards": [{"title": "b"}]},
        }
        check_key_parity(loaded, report)
        self.assertEqual(report.errors, 0)

    def test_missing_top_level_key_flagged(self):
        report = Reporter()
        loaded = {
            "en": {"id": "x", "extra_field": 1, "cards": []},
            "es": {"id": "x", "cards": []},
        }
        check_key_parity(loaded, report)
        self.assertEqual(report.errors, 1)

    def test_missing_card_level_key_flagged(self):
        report = Reporter()
        loaded = {
            "en": {"id": "x", "cards": [{"title": "a", "subtitle": "b"}]},
            "es": {"id": "x", "cards": [{"title": "a"}]},
        }
        check_key_parity(loaded, report)
        self.assertEqual(report.errors, 1)


# ── check_filename_language_match ──────────────────────────────────────────


class TestCheckFilenameLanguageMatch(unittest.TestCase):
    def test_matching_filename_and_field_no_finding(self):
        report = Reporter()
        check_filename_language_match(
            "es", Path("foo_es_001.json"), {"language": "es"}, report
        )
        self.assertEqual(report.errors, 0)
        self.assertEqual(report.warnings, 0)

    def test_language_field_mismatch_flagged(self):
        report = Reporter()
        check_filename_language_match(
            "es", Path("foo_es_001.json"), {"language": "en"}, report
        )
        self.assertEqual(report.errors, 1)

    def test_filename_lang_segment_mismatch_flagged(self):
        report = Reporter()
        check_filename_language_match(
            "es", Path("foo_en_001.json"), {"language": "es"}, report
        )
        self.assertEqual(report.errors, 1)

    def test_unrecognized_filename_pattern_warns(self):
        report = Reporter()
        check_filename_language_match(
            "es", Path("foo.json"), {"language": "es"}, report
        )
        self.assertEqual(report.warnings, 1)
        self.assertEqual(report.errors, 0)


# ── discovery_schema_checks.check_required_fields ──────────────────────────


class TestDiscoverySchemaChecks(unittest.TestCase):
    def _valid_study(self):
        return {
            "id": "x",
            "type": "study",
            "language": "en",
            "version": "RVR1960",
            "estimated_reading_minutes": 5,
            "key_verse": {"reference": "Juan 3:16", "text": "For God so loved..."},
            "cards": [
                {"order": 1, "type": "intro", "title": "Intro", "subtitle": "Sub"}
            ],
            "tags": ["faith"],
            "metadata": {"themes": ["love"]},
        }

    def test_valid_study_no_errors(self):
        report = Reporter()
        discovery_schema_checks.check_required_fields("en", self._valid_study(), report)
        self.assertEqual(report.errors, 0)

    def test_missing_version_flagged(self):
        data = self._valid_study()
        del data["version"]
        report = Reporter()
        discovery_schema_checks.check_required_fields("en", data, report)
        self.assertGreaterEqual(report.errors, 1)

    def test_missing_key_verse_flagged(self):
        data = self._valid_study()
        del data["key_verse"]
        report = Reporter()
        discovery_schema_checks.check_required_fields("en", data, report)
        self.assertGreaterEqual(report.errors, 1)

    def test_empty_card_title_flagged(self):
        data = self._valid_study()
        data["cards"][0]["title"] = "   "
        report = Reporter()
        discovery_schema_checks.check_required_fields("en", data, report)
        self.assertGreaterEqual(report.errors, 1)

    def test_incomplete_greek_word_flagged(self):
        data = self._valid_study()
        data["cards"][0]["greek_words"] = [{"word": "agape"}]  # missing transliteration
        report = Reporter()
        discovery_schema_checks.check_required_fields("en", data, report)
        self.assertGreaterEqual(report.errors, 1)


# ── encounters_schema_checks.check_required_fields ─────────────────────────


class TestEncountersSchemaChecks(unittest.TestCase):
    def _valid_encounter(self):
        return {
            "id": "x",
            "type": "encounter",
            "schema_version": 1,
            "language": "en",
            "bible_version": "RVR1960",
            "version": 1,
            "estimated_reading_minutes": 5,
            "meta": {
                "character": "Peter",
                "testament": "new",
                "scripture_reference": "Juan 21:1-19",
                "mood_primary": "hope",
                "accent_color": "#000",
                "emoji": "🐟",
                "tags": ["faith"],
            },
            "key_verse": {
                "reference": "Juan 21:1",
                "text": "text",
                "bible_version": "RVR1960",
            },
            "cards": [
                {
                    "order": 1,
                    "type": "discovery_activation",
                    "discovery_questions": [{"category": "c", "question": "q"}],
                    "prayer": {"title": "t", "content": "c"},
                },
                {
                    "order": 2,
                    "type": "completion",
                    "completion_verse": {
                        "reference": "r",
                        "text": "t",
                        "bible_version": "RVR1960",
                    },
                },
            ],
        }

    def test_valid_encounter_no_errors(self):
        report = Reporter()
        encounters_schema_checks.check_required_fields(
            "en", self._valid_encounter(), report
        )
        self.assertEqual(report.errors, 0)

    def test_last_card_not_completion_flagged(self):
        data = self._valid_encounter()
        data["cards"][-1]["type"] = "discovery_activation"
        del data["cards"][-1]["completion_verse"]
        report = Reporter()
        encounters_schema_checks.check_required_fields("en", data, report)
        self.assertGreaterEqual(report.errors, 1)

    def test_missing_discovery_activation_card_flagged(self):
        data = self._valid_encounter()
        data["cards"] = [data["cards"][-1]]  # only the completion card remains
        report = Reporter()
        encounters_schema_checks.check_required_fields("en", data, report)
        self.assertGreaterEqual(report.errors, 1)

    def test_missing_meta_field_flagged(self):
        data = self._valid_encounter()
        del data["meta"]["emoji"]
        report = Reporter()
        encounters_schema_checks.check_required_fields("en", data, report)
        self.assertGreaterEqual(report.errors, 1)

    def test_empty_scripture_connection_flagged(self):
        data = self._valid_encounter()
        data["cards"][0]["scripture_connections"] = [{"reference": "", "text": "x"}]
        report = Reporter()
        encounters_schema_checks.check_required_fields("en", data, report)
        self.assertGreaterEqual(report.errors, 1)


if __name__ == "__main__":
    unittest.main()
