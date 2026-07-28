"""test_business_rules_shared_validation.py — unit tests for check
functions in shared_validation/greek_hebrew_gloss.py that are shared by
both discovery and encounters pipelines but tested by neither pipeline's
own business-rules test file.

tests/test_business_rules_discovery.py and tests/test_business_rules_encounters.py
each import validate_discovery.py / validate_encounters.py directly, but
neither imports shared_validation.greek_hebrew_gloss.py — as of this file's
creation that module had zero test coverage for any of its check functions.
This file is that coverage's home: shared_validation logic used by both
pipelines gets its own test file rather than being arbitrarily attached to
one pipeline's business-rules file.

Imports the module directly (not via subprocess) so assertions can inspect
the Report object's accumulated findings precisely, matching the pattern in
test_business_rules_discovery.py.

Does not modify any production logic — test-only.
"""

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from shared_validation.greek_hebrew_gloss import (  # noqa: E402
    check_word_study_bare_transliteration,
    check_strong_code_bare_transliteration,
)
from shared_validation.lexicon_check import check_lexical_accuracy  # noqa: E402
from shared_validation.lexicon_source import LexiconEntry  # noqa: E402
from shared_validation.report import Report  # noqa: E402


class _FakeLexicon:
    """Minimal LexiconSource test double — a fixed {lemma: [entries]} map,
    no real Strong's data file loaded, so these tests exercise only
    check_lexical_accuracy's own comparison logic, not the real lexicon's
    12,450 entries."""

    def __init__(self, entries: dict[str, list[LexiconEntry]]):
        self._entries = entries

    def lookup_by_lemma(self, word: str) -> list[LexiconEntry]:
        return list(self._entries.get(word, []))

    def lookup_by_lemma_and_number(self, word: str, strongs_number: str):
        for entry in self._entries.get(word, []):
            if entry.strongs_number == strongs_number:
                return entry
        return None

    def lookup_by_number(self, strongs_number: str):
        for entries in self._entries.values():
            for entry in entries:
                if entry.strongs_number == strongs_number:
                    return entry
        return None


# ── check_word_study_bare_transliteration ───────────────────────────────────
#
# Detects a quoted word immediately followed by a parenthetical word (either
# order) where one side carries this corpus's scholarly-transliteration
# macrons (ā ē ī ō ū ḗ ṓ) but the whole string has no real Hebrew/Greek
# character anywhere — evidence a Greek/Hebrew word is being discussed by
# its transliteration only, with the native-script word never given.


class TestCheckWordStudyBareTransliteration(unittest.TestCase):
    def test_bare_transliteration_in_parens_is_a_warning(self):
        report = Report("TEST")
        check_word_study_bare_transliteration(
            "La palabra viene de 'Skēnē' (tienda). Dios no quería estar en un templo.",
            "cards[2].greek_words[0].revelation",
            "ctx",
            report,
        )

        self.assertTrue(
            any(
                "Skēnē" in w and "bare Greek/Hebrew transliteration" in w
                for w in report.warnings
            ),
            f"Expected a bare-transliteration warning, got: {report.warnings}",
        )

    def test_bare_transliteration_as_the_quoted_side_is_also_a_warning(self):
        report = Report("TEST")
        check_word_study_bare_transliteration(
            "Juan dice: 'He aquí el Cordero de Dios que Airōn el pecado del mundo'. "
            "No solo lo cubre con sangre, ¡lo levanta de tus hombros! 'Airōn' (levantar)",
            "cards[2].greek_words[1].revelation",
            "ctx",
            report,
        )

        self.assertTrue(
            any("Airōn" in w for w in report.warnings),
            f"Expected a bare-transliteration warning for the quoted side, got: {report.warnings}",
        )

    def test_ordinary_word_with_its_own_gloss_produces_no_finding(self):
        # 'esclerosis' (endurecimiento) is a real Spanish word with its own
        # meaning in parens — identical shape to the bug, but neither side
        # carries a transliteration diacritic, so this must not fire.
        report = Report("TEST")
        check_word_study_bare_transliteration(
            "Raíz de 'esclerosis' (endurecimiento). Este siervo está acusando a Dios.",
            "cards[1].content",
            "ctx",
            report,
        )

        self.assertEqual(
            report.warnings,
            [],
            f"Ordinary quoted word + gloss should not be flagged, got: {report.warnings}",
        )

    def test_plain_acute_accent_alone_does_not_trigger(self):
        # Plain acutes (á é í ó ú) are ordinary Spanish/Portuguese/French
        # orthography, not exclusive to scholarly transliteration — only
        # macrons should trigger this check.
        report = Report("TEST")
        check_word_study_bare_transliteration(
            "'está pasando' (presente continuo) describe la acción en curso.",
            "cards[1].content",
            "ctx",
            report,
        )

        self.assertEqual(
            report.warnings,
            [],
            f"Plain-acute-only text should not be flagged, got: {report.warnings}",
        )

    def test_real_greek_script_present_anywhere_in_string_suppresses_the_check(self):
        # Even if a bare-transliteration-shaped pair is also present, a real
        # Hebrew/Greek character anywhere in the same string means the
        # find_greek_hebrew_glosses gate is the one responsible for judging
        # this text, not this check — no double-reporting.
        report = Report("TEST")
        check_word_study_bare_transliteration(
            "El texto griego usa πνεῦμα, (Pneuma) y también menciona 'Skēnē' (tienda) más adelante.",
            "cards[1].content",
            "ctx",
            report,
        )

        self.assertEqual(
            report.warnings,
            [],
            f"A string containing real Greek script should be left to the gloss checker, got: {report.warnings}",
        )

    def test_word_key_is_skipped(self):
        # 'word' is the shared _SKIP_KEYS exemption used by every check in
        # this module — a bare 'greek_words[].word' field is structural
        # data, not prose, and must never be scanned.
        report = Report("TEST")
        check_word_study_bare_transliteration(
            "'Skēnē' (tienda)",
            "cards[2].greek_words[0].word",
            "ctx",
            report,
        )

        self.assertEqual(
            report.warnings,
            [],
            f"The 'word' key should be skipped entirely, got: {report.warnings}",
        )


# ── check_strong_code_bare_transliteration ──────────────────────────────────
#
# Detects an ALL-CAPS Latin word immediately followed by a Strong's-code
# citation in parens — "DIATHĒKĒ (Strong G1242)" — in prose that has no real
# Hebrew/Greek character anywhere. The Latin-script twin of
# check_strong_code_native_script: same dangling-citation bug, just with the
# target language's own script already being Latin instead of Arabic/
# Devanagari/etc. Confirmed 2026-07-27 across en/es/pt/fr/de/fil in
# new_covenant_cup, gethsemane_agony, cup_of_wrath, passed_from_death, and
# saints_resurrected.


class TestCheckStrongCodeBareTransliteration(unittest.TestCase):
    def test_allcaps_word_before_strong_code_is_an_error(self):
        report = Report("TEST")
        check_strong_code_bare_transliteration(
            "THE KEY WORD: DIATHĒKĒ (Strong G1242)\n\nIn Greek, diathēkē means TWO things.",
            "cards[0].content",
            "ctx",
            report,
        )

        self.assertTrue(
            any("DIATHĒKĒ" in e and "bare transliteration" in e for e in report.errors),
            f"Expected a bare-transliteration error, got: {report.errors}",
        )

    def test_allcaps_word_without_diacritic_before_strong_code_is_also_an_error(self):
        # ESTIN/KAINOS have no macron/acute at all — the ALL-CAPS shape next
        # to the Strong code is itself the signal, no diacritic needed.
        report = Report("TEST")
        check_strong_code_bare_transliteration(
            "The debate centers on ESTIN (Strong G1510).",
            "cards[1].content",
            "ctx",
            report,
        )

        self.assertTrue(
            any("ESTIN" in e for e in report.errors),
            f"Expected a bare-transliteration error for ESTIN, got: {report.errors}",
        )

    def test_real_greek_script_present_anywhere_in_string_suppresses_the_check(self):
        # If the field already contains real Greek/Hebrew script, that's
        # find_greek_hebrew_glosses' job to judge, not this check's —
        # no double-reporting.
        report = Report("TEST")
        check_strong_code_bare_transliteration(
            "The word διαθήκη, (diathēkē) means covenant. THE KEY WORD: DIATHĒKĒ (Strong G1242)",
            "cards[0].content",
            "ctx",
            report,
        )

        self.assertEqual(
            report.errors,
            [],
            f"A string containing real Greek script should be left to the gloss checker, got: {report.errors}",
        )

    def test_ordinary_allcaps_acronym_without_strong_code_shape_produces_no_finding(
        self,
    ):
        # An ordinary ALL-CAPS acronym followed by an unrelated parenthetical
        # that isn't a Strong's-code shape (no letter+digits) must not fire.
        report = Report("TEST")
        check_strong_code_bare_transliteration(
            "The NASB (a modern translation) renders this differently.",
            "cards[0].content",
            "ctx",
            report,
        )

        self.assertEqual(
            report.errors,
            [],
            f"Non-Strong-code parenthetical should not be flagged, got: {report.errors}",
        )

    def test_word_key_is_skipped(self):
        # 'word' is the shared _SKIP_KEYS exemption used by every check in
        # this module.
        report = Report("TEST")
        check_strong_code_bare_transliteration(
            "DIATHĒKĒ (Strong G1242)",
            "cards[0].greek_words[0].word",
            "ctx",
            report,
        )

        self.assertEqual(
            report.errors,
            [],
            f"The 'word' key should be skipped entirely, got: {report.errors}",
        )


# ── check_lexical_accuracy / _translit_matches ──────────────────────────────
#
# _translit_matches requires an exact (case-insensitive) match against
# Strong's own transliteration — no diacritic-stripping. An earlier version
# stripped combining marks from both sides before comparing, meant to
# tolerate this corpus's occasional bare-ASCII house style (e.g. 'ginomai'
# for 'gínomai'); that also silently accepted a real mismatch whenever the
# given transliteration was missing a required accent, since stripping marks
# from both sides made a wrong spelling indistinguishable from a
# deliberately-plain-ASCII one (found 2026-07-28, peter_restoration_001:
# 'anthrakia'/'lambano'/'bosko'/'poimaino' all silently matched against
# Strong's 'anthrakiá'/'lambánō'/'bóskō'/'poimaínō').


class TestCheckLexicalAccuracy(unittest.TestCase):
    def test_exact_match_is_matched(self):
        lexicon = _FakeLexicon(
            {
                "ἀνθρακιά": [
                    LexiconEntry("G439", "ἀνθρακιά", "anthrakiá", "a bed of coals")
                ]
            }
        )
        report = Report("TEST")
        results = check_lexical_accuracy(
            "ἀνθρακιά, (anthrakiá) appears twice in John.",
            lexicon,
            "path",
            "en",
            "ctx",
            report,
        )

        self.assertEqual(report.errors, [], f"Expected no errors, got: {report.errors}")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status.value, "matched")

    def test_missing_accent_is_translit_mismatch_not_silently_matched(self):
        # This is the exact regression this fix closes: 'anthrakia' (no
        # accent) must NOT be accepted as equivalent to Strong's
        # 'anthrakiá' just because stripping diacritics would make them equal.
        lexicon = _FakeLexicon(
            {
                "ἀνθρακιά": [
                    LexiconEntry("G439", "ἀνθρακιά", "anthrakiá", "a bed of coals")
                ]
            }
        )
        report = Report("TEST")
        results = check_lexical_accuracy(
            "ἀνθρακιά, (anthrakia) appears twice in John.",
            lexicon,
            "path",
            "en",
            "ctx",
            report,
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status.value, "translit_mismatch")
        self.assertTrue(
            any("anthrakia" in e and "anthrakiá" in e for e in report.errors),
            f"Expected a spelling-mismatch error naming both spellings, got: {report.errors}",
        )

    def test_word_not_in_lexicon_is_inflected_no_lemma_match(self):
        lexicon = _FakeLexicon({})  # no entries at all
        report = Report("TEST")
        results = check_lexical_accuracy(
            "ἀγαπᾷς, (agapas) is the word Jesus uses.",
            lexicon,
            "path",
            "en",
            "ctx",
            report,
        )

        self.assertEqual(report.errors, [], f"Expected no errors, got: {report.errors}")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status.value, "inflected_no_lemma_match")


if __name__ == "__main__":
    unittest.main()
