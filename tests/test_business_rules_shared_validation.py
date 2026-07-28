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

from shared_validation.greek_hebrew_gloss import check_word_study_bare_transliteration  # noqa: E402
from shared_validation.report import Report  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
