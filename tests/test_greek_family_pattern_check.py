"""test_greek_family_pattern_check.py — unit tests for
shared_validation/greek_family_pattern_check.py, the standalone cross-file
Greek/Hebrew gloss consistency scanner extracted from family_check.py's
former check_greek_hebrew_consistency.

check_greek_hebrew_consistency itself was previously covered in
test_family_check.py (as TestCheckGreekHebrewConsistency) before the
function moved to this standalone module; those two cases are ported here
verbatim since the assertions describe the function's contract, not where
it lives. resolve-family coverage is new: it proves --id/--type scoping
picks up the real index.json files, not a hardcoded fixture.

Imports the module directly (not via subprocess) so assertions can inspect
Reporter's error count precisely, matching the pattern in
test_family_check.py.
"""

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from shared_validation.family_check import Reporter  # noqa: E402
from shared_validation.greek_family_pattern_check import (  # noqa: E402
    check_greek_hebrew_consistency,
    _resolve_discovery_family,
    _resolve_encounters_family,
    _all_discovery_ids,
    _all_encounters_ids,
    run_for_family,
)


# ── check_greek_hebrew_consistency ─────────────────────────────────────────


class TestCheckGreekHebrewConsistency(unittest.TestCase):
    def test_well_formed_minority_not_outvoted_by_malformed_majority(self):
        """A majority of languages sharing the same malformed (ungloss'd) native
        word must not outvote a well-formed minority — that would flag the
        compliant file as the outlier instead of the shared spec violation."""
        loaded = {
            "en": {"content": "θεός, (theos) is good"},
            "es": {"content": "θεός is good"},
            "fr": {"content": "θεός is good"},
        }
        report = Reporter()
        check_greek_hebrew_consistency(loaded, report)
        self.assertEqual(report.errors, 0)

    def test_genuine_word_drift_still_flagged(self):
        """A real mismatch (different native word at the same position, all
        well-formed) must still be caught — both the word and its
        transliteration disagree, so two errors are expected."""
        loaded = {
            "en": {"content": "θεός, (theos) is good"},
            "es": {"content": "θεός, (theos) is good"},
            "fr": {"content": "λόγος, (logos) is good"},
        }
        report = Reporter()
        check_greek_hebrew_consistency(loaded, report)
        self.assertEqual(report.errors, 2)

    def test_agreeing_languages_no_findings(self):
        loaded = {
            "en": {"content": "θεός, (theos) is good"},
            "es": {"content": "θεός, (theos) is good"},
        }
        report = Reporter()
        check_greek_hebrew_consistency(loaded, report)
        self.assertEqual(report.errors, 0)


# ── family/type resolution against the real corpus index.json files ─────────


class TestFamilyResolution(unittest.TestCase):
    def test_resolve_discovery_family_known_id(self):
        ids = _all_discovery_ids()
        self.assertTrue(ids, "discovery/index.json listed no study ids")
        family = _resolve_discovery_family(ids[0])
        self.assertGreaterEqual(len(family), 1)
        for path in family.values():
            self.assertTrue(str(path).endswith(".json"))

    def test_resolve_discovery_family_unknown_id(self):
        self.assertEqual(_resolve_discovery_family("__not_a_real_study_id__"), {})

    def test_resolve_encounters_family_known_id(self):
        ids = _all_encounters_ids()
        self.assertTrue(ids, "encounters/index.json listed no encounter ids")
        family = _resolve_encounters_family(ids[0])
        self.assertGreaterEqual(len(family), 1)

    def test_resolve_encounters_family_unknown_id(self):
        self.assertEqual(_resolve_encounters_family("__not_a_real_encounter_id__"), {})

    def test_run_for_family_unknown_id_reports_error(self):
        errors = run_for_family("discovery", "__not_a_real_study_id__")
        self.assertEqual(errors, 1)


if __name__ == "__main__":
    unittest.main()
