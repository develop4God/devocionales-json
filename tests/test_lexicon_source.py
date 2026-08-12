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

from shared_validation.checks.lexicon_source import StrongsLexiconSource  # noqa: E402


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


class TestLookupByTranslit(unittest.TestCase):
    """Coverage for lookup_by_translit — diacritic/case-insensitive lookup
    by a word's OWN transliteration, not its native-script lemma. Added
    2026-08-01 after finding 6 real corpus content gaps (anamnesis,
    koinonia, kippur, apolytrōsis, aphesis, ephapax — new_covenant_cup)
    that check_word_study_bare_transliteration's diacritic-shape heuristic
    couldn't catch because these transliterations carry none of the
    corpus's own scholarly diacritics — only a real dictionary lookup can
    tell them apart from ordinary vocabulary of the same shape."""

    @classmethod
    def setUpClass(cls):
        cls.lex = StrongsLexiconSource()

    def test_accent_free_spelling_resolves_to_the_accented_headword(self):
        # Corpus wrote 'anamnesis'; Strong's own transliteration is
        # 'anámnēsis' (G364) — the whole point of this lookup.
        entries = self.lex.lookup_by_translit("anamnesis")
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].strongs_number, "G364")
        self.assertEqual(entries[0].lemma, "ἀνάμνησις")

    def test_hebrew_translit_resolves(self):
        entries = self.lex.lookup_by_translit("kippur")
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].strongs_number, "H3725")

    def test_exact_accented_spelling_also_resolves(self):
        entries = self.lex.lookup_by_translit("apolýtrōsis")
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].strongs_number, "G629")

    def test_uppercase_spelling_also_resolves(self):
        entries = self.lex.lookup_by_translit("EPHAPAX")
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].strongs_number, "G2178")

    def test_ordinary_english_word_does_not_falsely_resolve(self):
        # Confirmed false-positive-risk cases from the same corpus scan:
        # 'DNA' and 'vs' must not accidentally collide with any real
        # transliteration under diacritic-stripped casefold comparison.
        self.assertEqual(self.lex.lookup_by_translit("DNA"), [])
        self.assertEqual(self.lex.lookup_by_translit("vs"), [])

    def test_translit_collision_surfaces_all_candidates(self):
        # 'ō' alone maps to 3 distinct Strong's numbers in the combined
        # data — real ambiguity, same shape as the lemma-collision case
        # above, must not silently pick one.
        entries = self.lex.lookup_by_translit("ō")
        numbers = sorted(e.strongs_number for e in entries)
        self.assertEqual(len(numbers), 3)


if __name__ == "__main__":
    unittest.main()
