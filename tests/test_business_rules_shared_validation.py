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

from shared_validation.greek_hebrew_gloss import (
    check_bare_transliteration_reuse,
    check_bare_transliteration_reuse_cross_field,
    check_native_script_bare_transliteration,
    check_strong_code_bare_transliteration,
    check_word_study_bare_clause_transliteration,
    check_word_study_bare_transliteration,
    check_word_study_lexicon_verified_bare_transliteration,
)
from shared_validation.lexicon_check import check_lexical_accuracy
from shared_validation.lexicon_source import LexiconEntry
from shared_validation.report import Report


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


if __name__ == "__main__":
    unittest.main()
