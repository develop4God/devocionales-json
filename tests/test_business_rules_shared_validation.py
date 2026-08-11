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

import json
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from shared_validation import bible_sot  # noqa: E402
from shared_validation.greek_hebrew_gloss import (  # noqa: E402
    check_bare_transliteration_reuse,
    check_bare_transliteration_reuse_cross_field,
    check_native_script_bare_transliteration,
    check_strong_code_bare_transliteration,
    check_word_study_bare_clause_transliteration,
    check_word_study_bare_transliteration,
    check_word_study_lexicon_verified_bare_transliteration,
)
from shared_validation.lexicon_check import (  # noqa: E402
    check_lexical_accuracy,
    check_structured_word_study_accuracy,
)
from shared_validation.lexicon_family_check import (  # noqa: E402
    check_family_citation_balance,
)
from shared_validation.lexicon_source import LexiconEntry  # noqa: E402
from shared_validation.lint import lint_json_files  # noqa: E402
from shared_validation.report import Report  # noqa: E402
from shared_validation.text_checks import check_no_latin_leak  # noqa: E402


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

    def lookup_by_translit(self, translit: str) -> list[LexiconEntry]:
        # Diacritic-stripped, casefolded comparison — mirrors
        # StrongsLexiconSource.lookup_by_translit's real normalization
        # (lexicon_source._normalized_translit) so a fake-lexicon entry
        # written WITH its real accent (e.g. 'anámnēsis') still matches a
        # corpus string written without one ('anamnesis'), same as the
        # real dictionary data.
        import unicodedata

        def norm(w):
            return "".join(
                c
                for c in unicodedata.normalize("NFD", w).casefold()
                if not unicodedata.combining(c)
            )

        target = norm(translit)
        results = []
        for entries in self._entries.values():
            for entry in entries:
                if norm(entry.translit) == target:
                    results.append(entry)
        return results


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

    def test_real_greek_script_nearby_suppresses_the_check(self):
        # If real Greek/Hebrew script appears within the window around a
        # bare-transliteration match, that's find_greek_hebrew_glosses' job
        # to judge, not this check's — no double-reporting.
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
            f"A bare match with real Greek script nearby should be left to the gloss checker, got: {report.errors}",
        )

    def test_titlecase_word_before_strong_code_is_an_error(self):
        # Confirmed in the wild 2026-08-10: veil_torn/hammer_of_god had this
        # exact shape ("Katapetasma (G2665)", "Parrhēsía (G3954)") in six
        # Latin-script languages, invisible to the original ALL-CAPS-only
        # regex because only the first letter was capitalized.
        report = Report("TEST")
        check_strong_code_bare_transliteration(
            "WHAT WAS THE VEIL? (Katapetasma (G2665))",
            "cards[0].content",
            "ctx",
            report,
        )

        self.assertTrue(
            any(
                "Katapetasma" in e and "bare transliteration" in e
                for e in report.errors
            ),
            f"Expected a bare-transliteration error for Title Case, got: {report.errors}",
        )

    def test_lowercase_word_before_strong_code_is_an_error(self):
        report = Report("TEST")
        check_strong_code_bare_transliteration(
            "The debate centers on mashiach (H4899).",
            "cards[0].content",
            "ctx",
            report,
        )

        self.assertTrue(
            any("mashiach" in e for e in report.errors),
            f"Expected a bare-transliteration error for lowercase, got: {report.errors}",
        )

    def test_real_greek_script_far_away_in_same_field_does_not_suppress_a_later_bare_match(
        self,
    ):
        # A field can legitimately contain one correct, well-formed
        # citation (a verse quote) alongside a second, later bare one (a
        # "KEY WORD" restatement) — confirmed in the wild 2026-08-10,
        # hammer_of_god's de/ar/hi/ja/zh files. Whole-string suppression
        # would silently miss the second, broken occurrence; the window
        # must be local to each match.
        report = Report("TEST")
        check_strong_code_bare_transliteration(
            "'Thus saith the LORD to his ANOINTED (מָשִׁיחַ, (mâshîyach) (H4899)), to Cyrus...'"
            + " " * 200
            + "THE KEY WORD: Mashiach (H4899) = MESSIAH",
            "cards[0].content",
            "ctx",
            report,
        )

        self.assertTrue(
            any("Mashiach" in e for e in report.errors),
            f"Expected the far-away bare restatement to still be flagged, got: {report.errors}",
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


# ── check_structured_word_study_accuracy ────────────────────────────────────
#
# The hebrew_words[]/greek_words[] array shape (word + transliteration as
# separate JSON keys) has no surrounding prose for resolve_lemma_entry's
# text-scan hint to search — so an ambiguous lemma (e.g. Hebrew עָמַד,
# H5975 "to stand" vs H5976 "to shake") always reported AMBIGUOUS_LEMMA
# with no way to resolve it, even when the caller already knows which
# headword is meant (zechariah_14_return_001, all 10 languages, 2026-08-08).
# strongs_hint closes that gap by feeding the array entry's own optional
# "strongs" field into resolve_lemma_entry's explicit_hint path.


class TestCheckStructuredWordStudyAccuracy(unittest.TestCase):
    def _ambiguous_lexicon(self):
        return _FakeLexicon(
            {
                "עָמַד": [
                    LexiconEntry("H5975", "עָמַד", "ʻâmad", "to stand"),
                    LexiconEntry("H5976", "עָמַד", "ʻâmad", "to shake"),
                ]
            }
        )

    def test_ambiguous_lemma_with_no_hint_is_reported(self):
        report = Report("TEST")
        result = check_structured_word_study_accuracy(
            word="עָמַד",
            transliteration="ʻâmad",
            lexicon=self._ambiguous_lexicon(),
            path="path",
            lang="en",
            ctx="ctx",
            report=report,
        )

        self.assertEqual(result.status.value, "ambiguous_lemma")
        self.assertEqual(report.errors, [])
        self.assertTrue(
            any("distinct Strong's headwords" in i for i in report.info),
            f"Expected an AMBIGUOUS_LEMMA info notice, got: {report.info}",
        )

    def test_correct_strongs_hint_resolves_to_matched(self):
        report = Report("TEST")
        result = check_structured_word_study_accuracy(
            word="עָמַד",
            transliteration="ʻâmad",
            lexicon=self._ambiguous_lexicon(),
            path="path",
            lang="en",
            ctx="ctx",
            report=report,
            strongs_hint="H5975",
        )

        self.assertEqual(result.status.value, "matched")
        self.assertEqual(result.strongs_number, "H5975")
        self.assertEqual(report.errors, [])
        self.assertEqual(report.info, [])

    def test_unknown_strongs_hint_falls_back_to_ambiguous(self):
        # A hint that doesn't match either candidate (typo, wrong code) must
        # not silently resolve to nothing found — same AMBIGUOUS_LEMMA
        # outcome as no hint at all, not a crash or a wrong resolution.
        report = Report("TEST")
        result = check_structured_word_study_accuracy(
            word="עָמַד",
            transliteration="ʻâmad",
            lexicon=self._ambiguous_lexicon(),
            path="path",
            lang="en",
            ctx="ctx",
            report=report,
            strongs_hint="H9999",
        )

        self.assertEqual(result.status.value, "ambiguous_lemma")


# ── check_native_script_bare_transliteration ────────────────────────────────
#
# Detects `lang`'s own native script glued directly (zero space, no comma)
# to a bare Latin transliteration in parens — e.g. Chinese '道(Logos)' —
# meaning the real Greek/Hebrew word was never given, only a native-language
# gloss word standing next to the transliteration. Confirmed in the wild
# 2026-07-28: 52 occurrences across the zh discovery+encounters corpus.


class TestCheckNativeScriptBareTransliteration(unittest.TestCase):
    def test_zh_word_glued_to_bare_translit_is_an_error(self):
        report = Report("TEST")
        check_native_script_bare_transliteration(
            "主耶稣啊,我的道(Logos)和我的晨星。",
            "cards[4].prayer.content",
            "zh",
            "ctx",
            report,
        )

        self.assertTrue(
            any("Logos" in e and "glued directly" in e for e in report.errors),
            f"Expected a glued-native-script error, got: {report.errors}",
        )

    def test_latin_script_meaning_word_glued_to_translit_is_an_error(self):
        report = Report("TEST")
        check_native_script_bare_transliteration(
            "The love(agape) of God is shown here.",
            "cards[0].content",
            "en",
            "ctx",
            report,
        )

        self.assertTrue(
            any("agape" in e and "meaning-word 'love'" in e for e in report.errors),
            f"Expected a Latin meaning-word error, got: {report.errors}",
        )

    def test_latin_script_repeated_translit_is_not_an_error(self):
        report = Report("TEST")
        check_native_script_bare_transliteration(
            "The AGAPAS(agapās) form appears here.",
            "cards[0].content",
            "en",
            "ctx",
            report,
        )

        self.assertEqual(
            report.errors,
            [],
            f"Repeated transliteration must not be flagged, got: {report.errors}",
        )

    def test_latin_inclusive_suffix_is_not_a_transliteration(self):
        report = Report("TEST")
        check_native_script_bare_transliteration(
            "Merci de me recevoir tel(le) que je suis.",
            "cards[0].content",
            "fr",
            "ctx",
            report,
        )

        self.assertEqual(
            report.errors,
            [],
            f"Inclusive-language suffix must not be flagged, got: {report.errors}",
        )

    def test_word_key_is_skipped(self):
        # 'word' is the shared _SKIP_KEYS exemption used by every check in
        # this module.
        report = Report("TEST")
        check_native_script_bare_transliteration(
            "道(Logos)",
            "cards[0].greek_words[0].word",
            "zh",
            "ctx",
            report,
        )

        self.assertEqual(
            report.errors,
            [],
            f"The 'word' key should be skipped entirely, got: {report.errors}",
        )

    def test_space_before_paren_does_not_trigger(self):
        # A space between the native word and the parenthetical is a
        # different (still likely wrong) shape, but not this specific
        # glued-with-zero-space bug — out of scope for this check.
        report = Report("TEST")
        check_native_script_bare_transliteration(
            "我的道 (Logos)是光。",
            "cards[0].content",
            "zh",
            "ctx",
            report,
        )

        self.assertEqual(
            report.errors,
            [],
            f"A space before the parenthesis should not trigger this check, got: {report.errors}",
        )

    def test_lexicon_none_falls_back_to_shape_only_error(self):
        # Default behavior (no lexicon wired in) must be unchanged from the
        # shape-only detection — this is the actual call shape used by both
        # validate_discovery.py and validate_encounters.py when lexicon
        # loading is skipped/unavailable.
        report = Report("TEST")
        check_native_script_bare_transliteration(
            "拯救者(Amnos)是羔羊。",
            "cards[2].revelation_key",
            "zh",
            "ctx",
            report,
            lexicon=None,
        )

        self.assertTrue(
            any("Amnos" in e and "glued directly" in e for e in report.errors),
            f"Expected the shape-only error with lexicon=None, got: {report.errors}",
        )

    def test_lexicon_present_with_nearby_strong_code_checks_spelling(self):
        # When a Strong's code sits right after the bare transliteration,
        # the real headword is knowable even though never written out —
        # verify the given spelling against Strong's own, rather than the
        # generic missing-word message.
        lexicon = _FakeLexicon(
            {"λόγος": [LexiconEntry("G3056", "λόγος", "lógos", "a word")]}
        )
        report = Report("TEST")
        check_native_script_bare_transliteration(
            "太初有道(Logoz) G3056。",
            "cards[0].content",
            "zh",
            "ctx",
            report,
            lexicon=lexicon,
        )

        self.assertTrue(
            any(
                "Logoz" in e and "lógos" in e and "check spelling" in e
                for e in report.errors
            ),
            f"Expected a Strong's-verified spelling-mismatch error, got: {report.errors}",
        )

    def test_lexicon_present_no_nearby_strong_code_falls_back_to_shape_only(self):
        # Most real corpus occurrences (all 52 found 2026-07-28) have no
        # nearby Strong's code — lexicon being passed in must not change
        # that outcome.
        lexicon = _FakeLexicon(
            {"λόγος": [LexiconEntry("G3056", "λόγος", "lógos", "a word")]}
        )
        report = Report("TEST")
        check_native_script_bare_transliteration(
            "我的道(Logos)和我的晨星。",
            "cards[4].prayer.content",
            "zh",
            "ctx",
            report,
            lexicon=lexicon,
        )

        self.assertTrue(
            any("Logos" in e and "glued directly" in e for e in report.errors),
            f"Expected the shape-only fallback with no nearby Strong code, got: {report.errors}",
        )


# ── check_bare_transliteration_reuse_cross_field ────────────────────────────
#
# The cross-field twin of check_bare_transliteration_reuse: a transliteration
# established by a well-formed gloss in one field of a card must not reappear
# as bare Latin text in a LATER field of the same card. Confirmed in the wild
# 2026-08-01: e.g. bread_of_life_en_001's cards[1].content correctly glosses
# 'ἄρτος, (ártos)', then cards[1].greek_words[0].revelation reuses 'ártos'
# bare with no native-script anchor.


class TestCheckBareTransliterationReuseCrossField(unittest.TestCase):
    def test_bare_reuse_in_a_later_field_is_an_error(self):
        report = Report("TEST")
        fields = [
            (
                "cards[1].content",
                "Jesus uses the Greek word ἄρτος, (ártos) (G740) — everyday bread.",
            ),
            (
                "cards[1].greek_words[0].revelation",
                "Jesus uses the word ártos in John 6:35 when he says 'I am the bread of life.'",
            ),
        ]
        check_bare_transliteration_reuse_cross_field(fields, "ctx", report)

        self.assertTrue(
            any(
                "ártos" in e
                and "cards[1].content" in e
                and "cards[1].greek_words[0].revelation" in e
                for e in report.errors
            ),
            f"Expected a cross-field bare-reuse error, got: {report.errors}",
        )

    def test_gloss_correctly_repeated_in_a_later_field_is_not_an_error(self):
        # The word is re-glossed properly in the later field too — this is
        # not bare reuse, it's a second correct occurrence.
        report = Report("TEST")
        fields = [
            ("cards[1].content", "The Greek word ἄρτος, (ártos) means bread."),
            (
                "cards[1].greek_words[0].revelation",
                "Here ἄρτος, (ártos) again refers to daily bread.",
            ),
        ]
        check_bare_transliteration_reuse_cross_field(fields, "ctx", report)

        self.assertEqual(
            report.errors,
            [],
            f"A correctly-repeated gloss must not be flagged, got: {report.errors}",
        )

    def test_transliteration_key_is_excluded_from_scanning(self):
        # greek_words[].transliteration holds a bare transliteration by
        # schema design (the native word lives in the sibling 'word' key,
        # a separate JSON field) — scanning it as a reuse target would
        # falsely flag every structured word-study entry in the corpus.
        report = Report("TEST")
        fields = [
            ("cards[1].content", "The Greek word ἄρτος, (ártos) means bread."),
            ("cards[1].greek_words[0].transliteration", "ártos"),
        ]
        check_bare_transliteration_reuse_cross_field(fields, "ctx", report)

        self.assertEqual(
            report.errors,
            [],
            f"transliteration field must be excluded from scanning, got: {report.errors}",
        )

    def test_reuse_in_an_earlier_field_is_not_flagged(self):
        # Reuse detection is strictly forward: a field cannot "reuse" a
        # gloss established later in the list, matching
        # check_bare_transliteration_reuse's own within-field forward order.
        report = Report("TEST")
        fields = [
            ("cards[1].greek_words[0].revelation", "Jesus uses the word ártos here."),
            ("cards[1].content", "The Greek word ἄρτος, (ártos) means bread."),
        ]
        check_bare_transliteration_reuse_cross_field(fields, "ctx", report)

        self.assertEqual(
            report.errors,
            [],
            f"Bare text before the gloss is established must not be flagged, got: {report.errors}",
        )


# ── check_bare_transliteration_reuse: case-insensitive matching ────────────
#
# Confirmed in the wild 2026-08-01: veil_torn_zh_001's content establishes
# 'ἐσχίσθη, (eschisthē)' then re-emphasizes the same word in all-caps prose
# ('It says ESCHISTHĒ:') a few lines later — a real bare-reuse instance the
# original case-sensitive \b-search missed entirely.


class TestCheckBareTransliterationReuseCaseInsensitive(unittest.TestCase):
    def test_reuse_in_a_different_case_is_still_an_error(self):
        report = Report("TEST")
        check_bare_transliteration_reuse(
            "It says ἐσχίσθη, (eschisthē) violently. It says ESCHISTHĒ: torn apart.",
            "cards[1].content",
            "ctx",
            report,
        )

        self.assertTrue(
            any("ESCHISTHĒ" in e or "eschisthē" in e for e in report.errors),
            f"Expected a case-insensitive reuse error, got: {report.errors}",
        )

    def test_same_case_reuse_still_an_error(self):
        # Regression guard: the original exact-case behavior must still work.
        report = Report("TEST")
        check_bare_transliteration_reuse(
            "It says ἐσχίσθη, (eschisthē) violently. It says eschisthē again.",
            "cards[1].content",
            "ctx",
            report,
        )

        self.assertTrue(
            any("eschisthē" in e for e in report.errors),
            f"Expected a same-case reuse error, got: {report.errors}",
        )


# ── check_word_study_bare_clause_transliteration: unquoted prefix + local
#    Greek/Hebrew guard ───────────────────────────────────────────────────
#
# Two fixes confirmed in the wild 2026-08-01 via veil_torn_zh_001: (1) the
# translated phrase before the parenthetical clause is not always wrapped
# in quote marks (numbered-list prose style like '2️⃣ 从上到下(Ap' Anōthen
# Heōs Katō)'), and (2) a real Greek/Hebrew citation earlier in the same
# field must not blind the check to a DIFFERENT bare clause later in that
# field.


class TestCheckWordStudyBareClauseTransliterationUnquotedAndLocalGuard(
    unittest.TestCase
):
    def test_unquoted_bare_prefix_clause_is_a_warning(self):
        report = Report("TEST")
        check_word_study_bare_clause_transliteration(
            "3️⃣ 从上到下(Ap' Anōthen Heōs Katō)\n\n这是最重要的细节",
            "cards[1].content",
            "zh",
            "ctx",
            report,
        )

        self.assertTrue(
            any("Anōthen" in w for w in report.warnings),
            f"Expected an unquoted-prefix clause warning, got: {report.warnings}",
        )

    def test_quoted_prefix_clause_still_works(self):
        # Regression guard: the original quoted-prefix behavior must still work.
        report = Report("TEST")
        check_word_study_bare_clause_transliteration(
            '"太初有道"(Ēn archē ēn ho Logos) 这是约翰福音的开篇',
            "cards[1].content",
            "zh",
            "ctx",
            report,
        )

        self.assertTrue(
            any("Logos" in w for w in report.warnings),
            f"Expected a quoted-prefix clause warning, got: {report.warnings}",
        )

    def test_real_greek_far_away_in_the_same_field_does_not_suppress_a_local_bare_clause(
        self,
    ):
        report = Report("TEST")
        text = (
            "裂开了(ἐσχίσθη, (eschisthē) (G4977))\n\n"
            + ("填充文字 " * 30)
            + "3️⃣ 从上到下(Ap' Anōthen Heōs Katō)"
        )
        check_word_study_bare_clause_transliteration(
            text, "cards[1].content", "zh", "ctx", report
        )

        self.assertTrue(
            any("Anōthen" in w for w in report.warnings),
            f"Expected the far-away real citation to not suppress this finding, got: {report.warnings}",
        )

    def test_real_greek_right_next_to_the_match_still_suppresses_it(self):
        # The local guard must still protect a match that genuinely sits
        # right next to real Greek/Hebrew script.
        report = Report("TEST")
        text = "从上到下(Ap' Anōthen Heōs Katō) ἐσχίσθη, (eschisthē)"
        check_word_study_bare_clause_transliteration(
            text, "cards[1].content", "zh", "ctx", report
        )

        self.assertEqual(
            report.warnings,
            [],
            f"A match right next to real Greek script must still be suppressed, got: {report.warnings}",
        )


# ── check_word_study_lexicon_verified_bare_transliteration ─────────────────
#
# Catches a bare Latin word in parens that resolves to a REAL Strong's
# headword transliteration, verified via a dictionary lookup rather than a
# diacritic-shape heuristic — closes the precision gap
# check_word_study_bare_transliteration leaves open for transliterations
# with no scholarly diacritic at all (e.g. 'anamnesis', 'kippur'). Confirmed
# in the wild 2026-08-01: new_covenant_cup's 'a memorial (anamnesis)',
# 'Covered sin (kippur)' — real Strong's transliterations (G364, H3725)
# invisible to the shape-only check.


class TestCheckWordStudyLexiconVerifiedBareTransliteration(unittest.TestCase):
    def setUp(self):
        self.lex = _FakeLexicon(
            {
                "ἀνάμνησις": [
                    LexiconEntry("G364", "ἀνάμνησις", "anámnēsis", "recollection")
                ],
                "כִּפֻּר": [LexiconEntry("H3725", "כִּפֻּר", "kippur", "expiation")],
                "πέτρα": [LexiconEntry("G4073", "πέτρα", "petra", "a (mass of) rock")],
            }
        )

    def test_diacritic_free_translit_resolving_to_a_real_headword_is_a_warning(self):
        report = Report("TEST")
        check_word_study_lexicon_verified_bare_transliteration(
            "It is a memorial (anamnesis) of his death.",
            "cards[1].content",
            "ctx",
            report,
            self.lex,
        )

        self.assertTrue(
            any("anamnesis" in w and "G364" in w for w in report.warnings),
            f"Expected a lexicon-verified bare-transliteration warning, got: {report.warnings}",
        )

    def test_word_with_no_lexicon_match_produces_no_finding(self):
        report = Report("TEST")
        check_word_study_lexicon_verified_bare_transliteration(
            "This happened on a Tuesday (weekday) in spring.",
            "cards[1].content",
            "ctx",
            report,
            self.lex,
        )

        self.assertEqual(
            report.warnings,
            [],
            f"An ordinary English word with no lexicon match must not be flagged, got: {report.warnings}",
        )

    def test_whitelisted_coincidental_collision_is_not_flagged(self):
        # Regression test for the confirmed false positive: 'Peter' (the
        # disciple's name) diacritic-strips to the same letters as Strong's
        # H6363 'peṭer' ('a fissure, firstling'), a completely unrelated
        # Hebrew word — coincidental spelling overlap, not a real content
        # gap. Uses 'petra' (G4073) in the fake lexicon as a stand-in
        # collision target so this test doesn't depend on the real 13k-entry
        # data file; the whitelist itself is read from gloss_format.json
        # and already contains 'Peter'.
        report = Report("TEST")
        check_word_study_lexicon_verified_bare_transliteration(
            "The apostle appeared to Simon (Peter) after the resurrection.",
            "cards[11].narrative",
            "ctx",
            report,
            self.lex,
        )

        self.assertEqual(
            report.warnings,
            [],
            f"Whitelisted word 'Peter' must never be flagged, got: {report.warnings}",
        )

    def test_real_greek_script_locally_near_the_match_suppresses_it(self):
        report = Report("TEST")
        text = "It is a memorial (anamnesis) πέτρα, (petra) right here."
        check_word_study_lexicon_verified_bare_transliteration(
            text, "cards[1].content", "ctx", report, self.lex
        )

        self.assertEqual(
            report.warnings,
            [],
            f"A match right next to real Greek script must be suppressed, got: {report.warnings}",
        )

    def test_word_key_is_skipped(self):
        report = Report("TEST")
        check_word_study_lexicon_verified_bare_transliteration(
            "a memorial (anamnesis)",
            "cards[2].greek_words[0].word",
            "ctx",
            report,
            self.lex,
        )

        self.assertEqual(
            report.warnings,
            [],
            f"The 'word' key should be skipped entirely, got: {report.warnings}",
        )

    def test_inflected_translit_with_diacritic_and_no_exact_match_is_flagged(self):
        # Regression test for the confirmed silent-failure bug: a real
        # Strong's word cited by its INFLECTED spelling (not the dictionary
        # lemma) has no exact match in lookup_by_translit, so the
        # already-existing branch below (no entries -> continue) used to
        # skip it with zero finding, same as an ordinary English word.
        # Confirmed in the wild 2026-08-08: morning_star_001's
        # revelation_key wrote '(Eskēnōsen)' for G4637's lemma 'skēnóō' (the
        # augment 'e-' and the ending both differ) with no Hebrew/Greek
        # character anywhere in the field — this check stayed completely
        # silent even though the word carries the same macron diacritic
        # check_word_study_bare_transliteration already uses as its signal.
        # 'Eskēnōsen' itself isn't in the fake lexicon (only 'anámnēsis',
        # 'kippur', 'petra' are) precisely because the whole point is: no
        # exact match is required to raise this — only the diacritic shape.
        report = Report("TEST")
        check_word_study_lexicon_verified_bare_transliteration(
            "the close presence (Eskēnōsen), and the total liberator (Amnos)",
            "cards[2].revelation_key",
            "ctx",
            report,
            self.lex,
        )

        self.assertTrue(
            any("Eskēnōsen" in w and "does not match" in w for w in report.warnings),
            f"Expected a distinct 'no exact match' warning for the inflected "
            f"form, got: {report.warnings}",
        )

    def test_ordinary_word_with_no_diacritic_and_no_match_still_produces_no_finding(
        self,
    ):
        # The new no-match branch must stay silent for ordinary prose with
        # no scholarly-transliteration shape — same diacritic gate
        # check_word_study_bare_transliteration already uses, reused here
        # rather than flagging every unmatched bare word (which would flood
        # every language's ordinary vocabulary). This is the same input as
        # test_word_with_no_lexicon_match_produces_no_finding above, kept
        # as its own test so a future change to the diacritic branch can't
        # silently regress this without a dedicated failure.
        report = Report("TEST")
        check_word_study_lexicon_verified_bare_transliteration(
            "This happened on a Tuesday (weekday) in spring.",
            "cards[1].content",
            "ctx",
            report,
            self.lex,
        )

        self.assertEqual(
            report.warnings,
            [],
            f"An ordinary word with no diacritic and no lexicon match must "
            f"not be flagged, got: {report.warnings}",
        )


# ── check_no_latin_leak ──────────────────────────────────────────────────────
#
# Flags Latin letters leaking into a non-Latin-script language's text field.
# Regression coverage for the 2026-08-04 false-positive fix: a Latin word
# that exactly matches a real Strong's headword's own transliteration (the
# corpus's house style of quoting the original verse in Latin transliteration,
# e.g. zh new_covenant_cup_001's "'TOUTO ESTIN TO SŌMA MOU'") must not be
# flagged as an untranslated leftover when a lexicon is supplied — but a
# genuine untranslated word (no lexicon match at all) must still be flagged,
# both with and without a lexicon available.


class TestCheckNoLatinLeak(unittest.TestCase):
    def setUp(self):
        self.lex = _FakeLexicon(
            {
                "τοῦτο": [LexiconEntry("G5124", "τοῦτο", "touto", "this")],
                "σῶμα": [LexiconEntry("G4983", "σῶμα", "sōma", "the body")],
            }
        )

    def test_real_strongs_translit_is_suppressed_when_lexicon_given(self):
        report = Report("TEST")
        check_no_latin_leak(
            "马可福音14:22——耶稣拿起饼说:'TOUTO...SŌMA'(这是我的身体)。",
            "cards[1].content",
            "zh",
            "ctx",
            report,
            self.lex,
        )

        self.assertEqual(
            report.warnings,
            [],
            f"A word matching a real Strong's transliteration must not be flagged when a lexicon is supplied, got: {report.warnings}",
        )

    def test_genuine_untranslated_word_still_flagged_with_lexicon(self):
        report = Report("TEST")
        check_no_latin_leak(
            "产业vs.功德",
            "cards[4].discovery_questions[2].category",
            "zh",
            "ctx",
            report,
            self.lex,
        )

        self.assertTrue(
            any("vs" in w for w in report.warnings),
            f"Expected 'vs' to still be flagged as a genuine untranslated leftover, got: {report.warnings}",
        )

    def test_real_strongs_translit_still_flagged_with_no_lexicon(self):
        # lexicon=None (the default) preserves the check's prior behavior —
        # no lexicon means no SOT verification is possible, so the word is
        # flagged same as before this fix.
        report = Report("TEST")
        check_no_latin_leak(
            "马可福音14:22——耶稣拿起饼说:'TOUTO'(这是我的身体)。",
            "cards[1].content",
            "zh",
            "ctx",
            report,
        )

        self.assertTrue(
            any("TOUTO" in w for w in report.warnings),
            f"Without a lexicon, a real Strong's transliteration should still be flagged (no verification possible), got: {report.warnings}",
        )

    def test_literal_escaped_newline_is_flagged_as_error_not_warning(self):
        # Regression coverage for the 2026-08-04 discovery/zh/jordan_convergence_zh_001
        # bug: a double-escaped "\\n" survives json.load() as the two literal
        # characters '\' + 'n' instead of becoming a real newline. That 'n' was
        # previously misreported as a generic "possible untranslated leftover"
        # Latin warning — it must now be a distinct, clearer error.
        report = Report("TEST")
        check_no_latin_leak(
            "第一段文字。\\n\\n第二段文字。",
            "cards[0].content",
            "zh",
            "ctx",
            report,
        )

        self.assertEqual(
            report.warnings,
            [],
            f"A literal escape artifact must not also be reported as a generic Latin-leak warning, got: {report.warnings}",
        )
        self.assertTrue(
            any("literal escape sequence" in e for e in report.errors),
            f"Expected a literal escape sequence error for the double-escaped '\\\\n', got: {report.errors}",
        )

    def test_genuine_leftover_word_starting_with_escape_letter_not_misclassified(self):
        # A real untranslated word that happens to start with 'n'/'r'/'t' (the
        # same letters used by escape codes) must still be flagged as a normal
        # leftover warning — only a letter immediately preceded by a literal
        # backslash is an escape artifact.
        report = Report("TEST")
        check_no_latin_leak(
            "这是一个not translated的词。",
            "cards[0].content",
            "zh",
            "ctx",
            report,
        )

        self.assertEqual(
            report.errors,
            [],
            f"A genuine leftover word must not be misclassified as an escape artifact, got: {report.errors}",
        )
        self.assertTrue(
            any("not" in w for w in report.warnings),
            f"Expected 'not' to still be flagged as a genuine untranslated leftover, got: {report.warnings}",
        )

    def test_allowed_word_from_config_is_suppressed(self):
        # Regression coverage for the lamb_of_god_zh_001 false positive:
        # '×' is standard multiplication notation in this corpus's math
        # ("2只羊羔 × 365天"), not an untranslated leftover, but
        # _LATIN_LETTER_RE's accented-Latin range incidentally matches it.
        # Listed in no_latin_languages.json's allowed_words.zh and must not
        # be flagged.
        report = Report("TEST")
        check_no_latin_leak(
            "每日两只羊羔 × 365天",
            "cards[0].content",
            "zh",
            "ctx",
            report,
        )

        self.assertEqual(
            report.warnings,
            [],
            f"Allowed words from config must not be flagged, got: {report.warnings}",
        )

    def test_allowed_word_match_is_case_insensitive(self):
        # allowed_words lookup casefolds the matched token before comparing
        # (see check_no_latin_leak's `m.group(0).lower() in allowed_words`) —
        # covered against a mixed-case allowed word, since '×' has no case
        # to vary and can't exercise this path on its own.
        report = Report("TEST")
        check_no_latin_leak(
            "衍生词：×",
            "cards[0].content",
            "zh",
            "ctx",
            report,
        )

        self.assertEqual(
            report.warnings,
            [],
            f"Allowed word matching must still work, got: {report.warnings}",
        )

    def test_divide_sign_not_in_allowed_list_still_flagged(self):
        # '÷' (U+00F7) sits in the same accented-Latin Unicode range as '×'
        # and would hit the same false-positive mechanism, but it does not
        # appear anywhere in the real corpus (confirmed via full-corpus
        # scan) and so is deliberately NOT in allowed_words — must still be
        # flagged if it ever shows up, not silently assumed safe by analogy
        # with '×'.
        report = Report("TEST")
        check_no_latin_leak(
            "3600 ÷ 24小时",
            "cards[0].content",
            "zh",
            "ctx",
            report,
        )

        self.assertTrue(
            any("÷" in w for w in report.warnings),
            f"'÷' is not in allowed_words.zh, so it must still be flagged, got: {report.warnings}",
        )

    def test_word_not_in_allowed_list_still_flagged(self):
        # A word that merely looks similar (shares a prefix) to an allowed
        # word must not be silently suppressed — only an exact (case-insensitive)
        # match against the configured allowed_words entry is exempt.
        report = Report("TEST")
        check_no_latin_leak(
            "这是cryptography的意思",
            "cards[3].content",
            "zh",
            "ctx",
            report,
        )

        self.assertTrue(
            any("cryptography" in w for w in report.warnings),
            f"Expected 'cryptography' (not in allowed_words) to still be flagged, got: {report.warnings}",
        )


# ── check_family_citation_balance ────────────────────────────────────────
#
# check_lexical_accuracy grades one gloss span in isolation and has no
# notion of "how many times should this word appear in THIS language given
# its 9 siblings" — a citation can be individually well-formed and still be
# missing several times where a sibling language cited the same word. Found
# 2026-08-10, restoration_by_fire_001: a dropped bracket or phonetic
# respelling in one language's dialogue quote is invisible to every
# shape-based check but shows up immediately as a per-language count that
# diverges from its siblings'.


class TestCheckFamilyCitationBalance(unittest.TestCase):
    def test_divergent_language_is_flagged(self):
        # 9 languages cite G25 once; zh cites it twice — zh should be
        # flagged, the 9 agreeing languages should not.
        counts_by_lang = {
            lang: {"G25": 1}
            for lang in ["ar", "de", "en", "es", "fil", "fr", "hi", "ja", "pt"]
        }
        counts_by_lang["zh"] = {"G25": 2}
        report = Report("TEST")

        check_family_citation_balance(counts_by_lang, report)

        self.assertEqual(
            len(report.warnings),
            1,
            f"Expected exactly 1 warning, got: {report.warnings}",
        )
        self.assertTrue(
            any("zh" in w and "G25" in w for w in report.warnings),
            f"Expected the warning to name zh and G25, got: {report.warnings}",
        )

    def test_missing_citation_in_one_language_is_flagged(self):
        # A language that never cites a code its siblings all cite once is
        # exactly as reportable as a count mismatch — a 0 count is still a
        # divergent count, not a special case.
        counts_by_lang = {
            lang: {"G1392": 1}
            for lang in ["de", "en", "es", "fr", "pt", "hi", "ja", "zh", "ar"]
        }
        counts_by_lang["fil"] = {}  # never cites G1392 at all
        report = Report("TEST")

        check_family_citation_balance(counts_by_lang, report)

        self.assertEqual(
            len(report.warnings),
            1,
            f"Expected exactly 1 warning, got: {report.warnings}",
        )
        self.assertTrue(
            any("fil" in w and "0 time(s)" in w for w in report.warnings),
            f"Expected fil flagged with a 0 count, got: {report.warnings}",
        )

    def test_all_languages_agreeing_produces_no_warning(self):
        # Every language citing the same code the same number of times is
        # the balanced, expected state — must not be flagged just because
        # a code exists.
        counts_by_lang = {
            lang: {"G25": 4, "G5368": 8}
            for lang in ["ar", "de", "en", "es", "fil", "fr", "hi", "ja", "pt", "zh"]
        }
        report = Report("TEST")

        check_family_citation_balance(counts_by_lang, report)

        self.assertEqual(
            report.warnings, [], f"Expected no warnings, got: {report.warnings}"
        )

    def test_code_cited_by_only_one_language_is_not_flagged(self):
        # A code that only ONE language happens to cite (e.g. a structured
        # greek_words[] entry present in just that language's file) is not
        # a cross-family imbalance by definition — there's no sibling count
        # to diverge from. Must not be flagged.
        counts_by_lang = {
            "en": {"G1392": 1},
            "de": {},
            "es": {},
        }
        report = Report("TEST")

        check_family_citation_balance(counts_by_lang, report)

        self.assertEqual(
            report.warnings, [], f"Expected no warnings, got: {report.warnings}"
        )

    def test_tie_breaks_toward_smallest_count(self):
        # 5 languages cite a code once, 5 cite it twice — an exact tie.
        # Under-citing is the more common real bug in this corpus's history
        # (a dropped bracket), so the smaller count wins the tie and the
        # "cited twice" languages are the ones flagged, not the reverse.
        counts_by_lang = {}
        for lang in ["ar", "de", "en", "es", "fil"]:
            counts_by_lang[lang] = {"G25": 1}
        for lang in ["fr", "hi", "ja", "pt", "zh"]:
            counts_by_lang[lang] = {"G25": 2}
        report = Report("TEST")

        check_family_citation_balance(counts_by_lang, report)

        flagged_langs = {w.split(": ")[1].split(":")[0] for w in report.warnings}
        self.assertEqual(
            flagged_langs,
            {"fr", "hi", "ja", "pt", "zh"},
            f"Expected the double-citing languages flagged against a baseline of 1, got: {report.warnings}",
        )


class TestLintJsonFiles(unittest.TestCase):
    """lint_json_files() — indent=2 / tab / trailing-newline / invalid-JSON
    checks, shared by both pipelines' Phase 1 lint pass."""

    def _write(self, tmpdir: Path, name: str, raw: str) -> None:
        (tmpdir / name).write_text(raw, encoding="utf-8")

    def test_odd_indentation_flagged_at_error_severity(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            self._write(tmp_path, "bad.json", '{\n   "a": 1\n}\n')
            report = Report("TEST")

            lint_json_files(tmp_path, report, exclude_dir_part="scripts")

            self.assertTrue(
                any("odd indentation" in e for e in report.errors),
                f"Expected an odd-indentation error, got: {report.errors}",
            )

    def test_odd_indentation_flagged_at_warning_severity(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            self._write(tmp_path, "bad.json", '{\n   "a": 1\n}\n')
            report = Report("TEST")

            lint_json_files(
                tmp_path, report, exclude_dir_part="scripts", severity="warning"
            )

            self.assertEqual(report.errors, [])
            self.assertTrue(
                any("odd indentation" in w for w in report.warnings),
                f"Expected an odd-indentation warning, got: {report.warnings}",
            )

    def test_tab_character_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            self._write(tmp_path, "tabbed.json", '{\n\t"a": 1\n}\n')
            report = Report("TEST")

            lint_json_files(tmp_path, report, exclude_dir_part="scripts")

            self.assertTrue(
                any("tab character" in e for e in report.errors),
                f"Expected a tab-character error, got: {report.errors}",
            )

    def test_missing_trailing_newline_is_always_a_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            # Well-formed indent, but no trailing newline.
            self._write(tmp_path, "no_newline.json", '{\n  "a": 1\n}')
            report = Report("TEST")

            lint_json_files(tmp_path, report, exclude_dir_part="scripts")

            self.assertEqual(report.errors, [])
            self.assertTrue(
                any("missing trailing newline" in w for w in report.warnings),
                f"Expected a missing-trailing-newline warning, got: {report.warnings}",
            )

    def test_well_formed_file_produces_no_findings(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            self._write(tmp_path, "clean.json", '{\n  "a": 1\n}\n')
            report = Report("TEST")

            cache = lint_json_files(tmp_path, report, exclude_dir_part="scripts")

            self.assertEqual(report.errors, [])
            self.assertEqual(report.warnings, [])
            self.assertEqual(len(cache), 1)

    def test_exclude_dir_part_skips_matching_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scripts_dir = tmp_path / "scripts"
            scripts_dir.mkdir()
            # Malformed, but lives under the excluded dir part.
            self._write(scripts_dir, "bad.json", '{\n\t"a": 1\n}\n')
            report = Report("TEST")

            cache = lint_json_files(tmp_path, report, exclude_dir_part="scripts")

            self.assertEqual(report.errors, [])
            self.assertEqual(cache, {})

    def test_invalid_json_reported_only_at_error_severity(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            self._write(tmp_path, "broken.json", "{not valid json")

            report_error = Report("TEST")
            lint_json_files(tmp_path, report_error, exclude_dir_part="scripts")
            self.assertTrue(
                any("invalid JSON" in e for e in report_error.errors),
                f"Expected an invalid-JSON error, got: {report_error.errors}",
            )

            report_warning = Report("TEST")
            lint_json_files(
                tmp_path,
                report_warning,
                exclude_dir_part="scripts",
                severity="warning",
            )
            self.assertEqual(
                report_warning.errors,
                [],
                "Invalid JSON must not be reported when severity='warning'",
            )

    def test_invalid_severity_raises_value_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = Report("TEST")
            with self.assertRaises(ValueError):
                lint_json_files(
                    Path(tmp), report, exclude_dir_part="scripts", severity="bogus"
                )


class TestBibleSotLoadBibleVersions(unittest.TestCase):
    """load_bible_versions() — remote SOT fetch, offline cache fallback, and
    the hard-failure path when neither is available."""

    _REMOTE_INDEX = {
        "languages": {
            "en": {
                "name": "English",
                "script": "Latin",
                "primary_version": "KJV",
                "fallback_version": "ASV",
                "reading_speed": 200,
            }
        }
    }

    def test_successful_remote_fetch_returns_shaped_languages(self):
        with (
            tempfile.TemporaryDirectory() as tmp,
            patch("shared_validation.bible_sot.tempfile.gettempdir", return_value=tmp),
            patch(
                "shared_validation.bible_sot._fetch_remote_index",
                return_value=(self._REMOTE_INDEX, None),
            ),
        ):
            languages, used_remote, err = bible_sot.load_bible_versions("test_cache")

        self.assertTrue(used_remote)
        self.assertIsNone(err)
        self.assertEqual(
            languages["en"],
            {
                "name": "English",
                "script": "Latin",
                "primary_version": "KJV",
                "fallback_version": "ASV",
                "allowed_versions": ["KJV", "ASV"],
                "reading_speed": 200,
            },
        )

    def test_successful_fetch_refreshes_local_cache(self):
        with (
            tempfile.TemporaryDirectory() as tmp,
            patch("shared_validation.bible_sot.tempfile.gettempdir", return_value=tmp),
            patch(
                "shared_validation.bible_sot._fetch_remote_index",
                return_value=(self._REMOTE_INDEX, None),
            ),
        ):
            bible_sot.load_bible_versions("test_cache")

            cache_path = Path(tmp) / "test_cache_bible_versions_cache.json"
            self.assertTrue(cache_path.exists())
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            self.assertIn("en", cached["languages"])

    def test_falls_back_to_local_cache_when_remote_unreachable(self):
        fetch_err = urllib.error.URLError("network unreachable")
        with tempfile.TemporaryDirectory() as tmp:
            cache_path = Path(tmp) / "test_cache_bible_versions_cache.json"
            cache_path.write_text(
                json.dumps({"languages": {"es": {"name": "Spanish"}}}),
                encoding="utf-8",
            )
            with (
                patch(
                    "shared_validation.bible_sot.tempfile.gettempdir", return_value=tmp
                ),
                patch(
                    "shared_validation.bible_sot._fetch_remote_index",
                    return_value=(None, fetch_err),
                ),
            ):
                languages, used_remote, err = bible_sot.load_bible_versions(
                    "test_cache"
                )

        self.assertFalse(used_remote)
        self.assertIs(err, fetch_err)
        self.assertEqual(languages, {"es": {"name": "Spanish"}})

    def test_raises_runtime_error_when_remote_and_cache_both_unavailable(self):
        with (
            tempfile.TemporaryDirectory() as tmp,
            patch("shared_validation.bible_sot.tempfile.gettempdir", return_value=tmp),
            patch(
                "shared_validation.bible_sot._fetch_remote_index",
                return_value=(None, urllib.error.URLError("network unreachable")),
            ),
        ):
            with self.assertRaises(RuntimeError):
                bible_sot.load_bible_versions("test_cache")


if __name__ == "__main__":
    unittest.main()
