"""test_lexicon_source.py — unit tests for shared_validation/lexicon_source.py.

Regression coverage for the case-insensitive lookup fallback: a corpus
word capitalized per normal Greek grammar (sentence/heading start) was
silently treated as "not a Strong's headword" because lookup_by_lemma did
an exact-string dict lookup with no case normalization, identical in
outcome to a genuinely-absent inflected form. Found via a corpus-wide
casefold() scan: ᾍδης (discovery/saints_resurrected_001), Λογίζομαι
(discovery/union_with_christ_001), Δύναμις (encounters/bleeding_woman_001)
— 30 occurrences across both corpora went unmatched and uncorrected
through every fixer/checker run before this fix. See
project_lexicon_strong_sot_fixer_status memory.
"""

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from shared_validation.lexicon_source import StrongsLexiconSource  # noqa: E402


class TestCaseInsensitiveLemmaLookup(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lex = StrongsLexiconSource()

    def test_capitalized_hades_resolves(self):
        entries = self.lex.lookup_by_lemma("ᾍδης")
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].strongs_number, "G86")
        self.assertEqual(entries[0].translit, "háidēs")

    def test_capitalized_logizomai_resolves(self):
        entries = self.lex.lookup_by_lemma("Λογίζομαι")
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].strongs_number, "G3049")

    def test_capitalized_dynamis_resolves(self):
        entries = self.lex.lookup_by_lemma("Δύναμις")
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].strongs_number, "G1411")

    def test_exact_case_match_still_preferred_no_behavior_change(self):
        exact = self.lex.lookup_by_lemma("λογίζομαι")
        self.assertEqual(len(exact), 1)
        self.assertEqual(exact[0].strongs_number, "G3049")

    def test_genuinely_absent_inflected_form_still_empty(self):
        # ἐκθαμβεῖσθαι is a real inflected surface form with no Strong's
        # headword under any casing — must stay empty, not falsely resolve.
        self.assertEqual(self.lex.lookup_by_lemma("ἐκθαμβεῖσθαι"), [])
        self.assertEqual(self.lex.lookup_by_lemma("Ἐκθαμβεῖσθαι"), [])

    def test_case_fold_collision_surfaces_both_candidates_not_silently_merged(self):
        # Strong's own data has Στέφανος ("Stephen", G4736) and στέφανος
        # ("crown", G4735) as two distinct headwords that collide under
        # casefold(). A query matching neither entry's own exact case must
        # surface BOTH as candidates (real ambiguity for the caller's
        # existing disambiguation path to resolve), never silently pick one.
        entries = self.lex.lookup_by_lemma("ΣΤΈΦΑΝΟΣ")
        numbers = sorted(e.strongs_number for e in entries)
        self.assertEqual(numbers, ["G4735", "G4736"])

    def test_lookup_by_lemma_and_number_also_case_insensitive(self):
        entry = self.lex.lookup_by_lemma_and_number("ᾍδης", "G86")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.translit, "háidēs")

    def test_lookup_by_lemma_and_number_wrong_number_still_none(self):
        self.assertIsNone(self.lex.lookup_by_lemma_and_number("ᾍδης", "G9999"))


if __name__ == "__main__":
    unittest.main()
