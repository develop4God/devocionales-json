"""test_devotional_scripture.py — unit tests for
shared_validation/checks/devotional_scripture.py (verse validation for the
devotional-year corpus, whose entries store reference and verse text in one
`versiculo` string, e.g. 'John 3:16 NIV: "For God so loved..."').

Same fixture approach as test_scripture_check.py: a tiny SQLite Bible DB, so
nothing here touches the real multi-MB databases or the network.
"""

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from bible_resolver import VerseResolver

from shared_validation.checks.devotional_scripture import (
    build_native_book_map,
    parse_versiculo,
    validate_devotional_entries,
    validate_versiculo,
)

JOHN_316 = "For God so loved the world that he gave his one and only Son"


def _make_resolver(testcase) -> VerseResolver:
    """In-memory-equivalent EN DB: John 3:16-17 and Psalm 23:1."""
    tmpdir = tempfile.TemporaryDirectory()
    testcase.addCleanup(tmpdir.cleanup)
    db_path = Path(tmpdir.name) / "en.sqlite3"
    sot_path = Path(tmpdir.name) / "bible_books.json"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE books (book_number INTEGER PRIMARY KEY, long_name TEXT)")
    conn.execute(
        "CREATE TABLE verses (book_number INTEGER, chapter INTEGER, verse INTEGER, text TEXT)"
    )
    conn.executemany("INSERT INTO books VALUES (?, ?)", [(43, "John"), (19, "Psalms")])
    conn.executemany(
        "INSERT INTO verses VALUES (?, ?, ?, ?)",
        [
            (43, 3, 16, JOHN_316),
            (43, 3, 17, "For God did not send his Son into the world to condemn"),
            (19, 23, 1, "The Lord is my shepherd, I lack nothing."),
        ],
    )
    conn.commit()
    conn.close()
    sot_path.write_text(
        json.dumps(
            {
                "books": {
                    "John": {"book_number": 43},
                    "Psalms": {"book_number": 19},
                    "Psalm": {"book_number": 19},
                }
            }
        ),
        encoding="utf-8",
    )
    resolver = VerseResolver(str(db_path), books_sot_path=str(sot_path), language="en")
    testcase.addCleanup(resolver.close)
    return resolver


class TestParseVersiculo(unittest.TestCase):
    def test_parses_reference_version_and_text(self):
        p = parse_versiculo('John 3:16 NIV: "For God so loved the world"')
        self.assertEqual(
            (p.book, p.chapter, p.verse_start, p.verse_end), ("John", 3, 16, 16)
        )
        self.assertEqual(p.text, "For God so loved the world")

    def test_parses_verse_range_and_numbered_book(self):
        p = parse_versiculo('1 Corinthians 13:4-7 KJV: "Charity suffereth long"')
        self.assertEqual(
            (p.book, p.chapter, p.verse_start, p.verse_end), ("1 Corinthians", 13, 4, 7)
        )

    def test_parses_without_version_code_and_with_guillemets(self):
        p = parse_versiculo("Marc 11:24: « C’est pourquoi je vous le dis »")
        self.assertEqual(p.book, "Marc")
        self.assertEqual(p.text, "C’est pourquoi je vous le dis")

    def test_empty_quoted_text_parses_to_empty_string(self):
        p = parse_versiculo('Acts 14:22 HERV: ""')
        self.assertEqual(p.text, "")

    def test_text_containing_colon_is_kept_whole(self):
        p = parse_versiculo('John 1:1 NIV: "In the beginning: the Word"')
        self.assertEqual(p.text, "In the beginning: the Word")

    def test_parses_multiword_version_label(self):
        p = parse_versiculo('यूहन्ना 15:5 पवित्र बाइबल (HERV): "वह दाखलता मैं हूँ"')
        self.assertEqual((p.book, p.chapter, p.verse_start), ("यूहन्ना", 15, 5))
        self.assertEqual(p.text, "वह दाखलता मैं हूँ")

    def test_parses_french_space_before_colon(self):
        p = parse_versiculo('Jean 12:24 TOB : "Amen, amen, je vous le dis"')
        self.assertEqual((p.book, p.chapter, p.verse_start), ("Jean", 12, 24))
        self.assertEqual(p.text, "Amen, amen, je vous le dis")

    def test_parses_cjk_citation_with_no_space_before_chapter(self):
        p = parse_versiculo('ガラテヤ5:22-23: "しかし、御霊の実は、愛、喜び"')
        self.assertEqual(
            (p.book, p.chapter, p.verse_start, p.verse_end), ("ガラテヤ", 5, 22, 23)
        )

    def test_numbered_book_still_splits_correctly_without_required_space(self):
        p = parse_versiculo('1 Corinthians 13:4-7 KJV: "Charity suffereth long"')
        self.assertEqual((p.book, p.chapter), ("1 Corinthians", 13))

    def test_discontiguous_reference_is_unparsed(self):
        self.assertIsNone(parse_versiculo('Éphésiens 5:1-2, 18 LSG1910: "Devenez"'))

    def test_garbage_is_unparsed(self):
        self.assertIsNone(parse_versiculo("not a verse"))


class TestBuildNativeBookMap(unittest.TestCase):
    def test_maps_citation_title_to_book_number(self):
        resolver = _make_resolver(self)
        book_map = build_native_book_map(resolver, "en")
        self.assertEqual(book_map["John"], 43)
        self.assertEqual(book_map["Psalms"], 19)


class TestCanonicalTitlesOnly(unittest.TestCase):
    def test_singular_psalm_is_not_accepted_only_the_canonical_title(self):
        resolver = _make_resolver(self)
        book_map = build_native_book_map(resolver, "en")
        self.assertNotIn("Psalm", book_map)
        finding = validate_versiculo(
            "e1",
            'Psalm 23:1 KJV: "The Lord is my shepherd, I lack nothing."',
            resolver,
            book_map,
        )
        self.assertEqual(finding.kind, "unknown_book")


class TestBuildNativeBookMapAliases(unittest.TestCase):
    def test_configured_alias_resolves_to_canonical_book_number(self):
        resolver = _make_resolver(self)
        with mock.patch(
            "shared_validation.checks.devotional_scripture.load_title_aliases",
            return_value={"Ang Ebanghelyo ni Juan": "John"},
        ):
            book_map = build_native_book_map(resolver, "en")
        self.assertEqual(book_map["Ang Ebanghelyo ni Juan"], 43)


class TestValidateVersiculo(unittest.TestCase):
    def setUp(self):
        self.resolver = _make_resolver(self)
        self.book_map = build_native_book_map(self.resolver, "en")

    def _check(self, versiculo, resolver="default"):
        return validate_versiculo(
            "e1",
            versiculo,
            self.resolver if resolver == "default" else resolver,
            self.book_map,
        )

    def test_clean_verse_returns_none(self):
        self.assertIsNone(self._check(f'John 3:16 NIV: "{JOHN_316}"'))

    def test_empty_text_is_flagged_even_without_a_database(self):
        finding = self._check('John 3:16 NIV: ""', resolver=None)
        self.assertEqual(finding.kind, "empty_text")

    def test_wrong_text_is_text_mismatch(self):
        finding = self._check('John 3:16 NIV: "The Lord is my shepherd I lack nothing"')
        self.assertEqual(finding.kind, "text_mismatch")

    def test_unknown_book_is_flagged(self):
        self.assertEqual(self._check('Nahum 1:1 NIV: "x y z"').kind, "unknown_book")

    def test_missing_range_message_shows_the_full_range(self):
        finding = self._check('John 3:16-99 NIV: "something"')
        self.assertIn("John 3:16-99", finding.message)

    def test_missing_verse_is_resolution_failed(self):
        self.assertEqual(
            self._check('John 3:99 NIV: "something"').kind, "resolution_failed"
        )

    def test_unparsed_versiculo_is_flagged(self):
        self.assertEqual(self._check("not a verse").kind, "unparsed")

    def test_without_database_a_non_empty_verse_passes_shape_check(self):
        self.assertIsNone(self._check(f'John 3:16 NIV: "{JOHN_316}"', resolver=None))


class TestValidateDevotionalEntries(unittest.TestCase):
    def test_returns_one_finding_per_bad_entry_with_entry_id(self):
        resolver = _make_resolver(self)
        entries = [
            {"id": "ok", "versiculo": f'John 3:16 NIV: "{JOHN_316}"'},
            {"id": "empty", "versiculo": 'Psalms 23:1 NIV: ""'},
            {
                "id": "wrong",
                "versiculo": 'Psalms 23:1 NIV: "totally different words here"',
            },
        ]
        findings = validate_devotional_entries(entries, resolver, "en")
        self.assertEqual(
            sorted((f.ref.path, f.kind) for f in findings),
            [("empty", "empty_text"), ("wrong", "text_mismatch")],
        )

    def test_entry_without_versiculo_is_flagged_empty(self):
        findings = validate_devotional_entries([{"id": "x"}], None, "en")
        self.assertEqual([f.kind for f in findings], ["empty_text"])


class TestParaMeditarVerses(unittest.TestCase):
    def setUp(self):
        self.resolver = _make_resolver(self)

    def _findings(self, para_meditar):
        entry = {
            "id": "d1",
            "versiculo": f'John 3:16 NIV: "{JOHN_316}"',
            "para_meditar": para_meditar,
        }
        return validate_devotional_entries([entry], self.resolver, "en")

    def test_clean_para_meditar_verse_passes(self):
        self.assertEqual(self._findings([{"cita": "John 3:16", "texto": JOHN_316}]), [])

    def test_wrong_text_is_flagged_with_item_path(self):
        findings = self._findings(
            [
                {"cita": "John 3:16", "texto": JOHN_316},
                {"cita": "Psalms 23:1", "texto": "totally different words here"},
            ]
        )
        self.assertEqual(
            [(f.ref.path, f.kind) for f in findings],
            [("d1/para_meditar[1]", "text_mismatch")],
        )

    def test_empty_texto_is_empty_text(self):
        findings = self._findings([{"cita": "John 3:16", "texto": ""}])
        self.assertEqual([f.kind for f in findings], ["empty_text"])

    def test_unknown_book_in_cita_is_flagged(self):
        findings = self._findings([{"cita": "Salmo 23:1", "texto": "x y z"}])
        self.assertEqual([f.kind for f in findings], ["unknown_book"])

    def test_missing_para_meditar_key_is_fine(self):
        entry = {"id": "d1", "versiculo": f'John 3:16 NIV: "{JOHN_316}"'}
        self.assertEqual(validate_devotional_entries([entry], self.resolver, "en"), [])


class TestParaMeditar(unittest.TestCase):
    def setUp(self):
        self.resolver = _make_resolver(self)

    def _entry(self, items):
        return {
            "id": "d1",
            "versiculo": f'John 3:16 NIV: "{JOHN_316}"',
            "para_meditar": items,
        }

    def test_clean_para_meditar_has_no_findings(self):
        entry = self._entry([{"cita": "John 3:16", "texto": JOHN_316}])
        self.assertEqual(validate_devotional_entries([entry], self.resolver, "en"), [])

    def test_wrong_texto_is_flagged_with_indexed_path(self):
        entry = self._entry(
            [
                {"cita": "John 3:16", "texto": JOHN_316},
                {"cita": "Psalms 23:1", "texto": "completely different words"},
            ]
        )
        findings = validate_devotional_entries([entry], self.resolver, "en")
        self.assertEqual(
            [(f.ref.path, f.kind) for f in findings],
            [("d1/para_meditar[1]", "text_mismatch")],
        )

    def test_empty_texto_is_flagged_even_without_a_database(self):
        entry = self._entry([{"cita": "John 3:16", "texto": ""}])
        findings = validate_devotional_entries([entry], None, "en")
        self.assertEqual([f.kind for f in findings], ["empty_text"])

    def test_entry_without_para_meditar_is_fine(self):
        entry = {"id": "d1", "versiculo": f'John 3:16 NIV: "{JOHN_316}"'}
        self.assertEqual(validate_devotional_entries([entry], self.resolver, "en"), [])


class TestInvisibleCharacterTitles(unittest.TestCase):
    def setUp(self):
        self.resolver = _make_resolver(self)
        self.book_map = build_native_book_map(self.resolver, "en")

    def _msg(self, book):
        return validate_versiculo(
            "e1", f'{book} 3:16 NIV: "{JOHN_316}"', self.resolver, self.book_map
        ).message

    def test_hair_space_in_title_is_named(self):
        msg = self._msg("Mga\u200aGawa")
        self.assertIn("U+200A", msg)

    def test_cyrillic_lookalike_in_title_is_named(self):
        msg = self._msg("J\u043ehn")  # Cyrillic о inside a Latin word
        self.assertIn("CYRILLIC", msg)

    def test_plain_unknown_title_has_no_character_hint(self):
        self.assertNotIn("U+", self._msg("Nahum"))


class TestCorpusScripturePhase(unittest.TestCase):
    """validate_corpus_scripture wiring: empty verse -> error, missing DB ->
    warning (and only DB-free checks run)."""

    def test_empty_verse_is_error_and_missing_db_is_warning(self):
        sys.path.insert(0, str(REPO_ROOT / "devocionales_scripts"))
        import validate_devocionales_corpus as phase
        from corpus_index_reader import CorpusCombo

        from shared_validation.report import Report

        combo = CorpusCombo("en", "NIV", "2027", "f.json")
        data = {
            "data": {
                "en": {
                    "2027-01-01": [
                        {"id": "a", "versiculo": 'John 3:16 NIV: ""'},
                        {"id": "b", "versiculo": 'John 3:16 NIV: "text"'},
                    ]
                }
            }
        }
        cache = {phase.CORPUS_DIR / "f.json": data}
        report = Report("C")
        with mock.patch.object(
            phase.ScriptureValidator, "get_resolver", return_value=None
        ):
            phase.validate_corpus_scripture(report, [combo], cache)
        self.assertEqual(len(report.errors), 1)
        self.assertIn("empty verse", report.errors[0])
        self.assertEqual(len(report.warnings), 1)
        self.assertIn("no local Bible DB", report.warnings[0])


class TestBibleVersionAliases(unittest.TestCase):
    """The file-declared user-facing name (e.g. 新改訳2003) resolves to the
    bible_versions index code (SK2003) for both the allowed-versions check
    and the database lookup; unknown names pass through unchanged."""

    def setUp(self):
        sys.path.insert(0, str(REPO_ROOT / "devocionales_scripts"))

    def test_native_name_maps_to_index_code(self):
        from sot_exceptions import canonical_version

        self.assertEqual(canonical_version("ja", "新改訳2003"), "SK2003")
        self.assertEqual(canonical_version("zh", "和合本1919"), "CUV1919")

    def test_unaliased_version_passes_through(self):
        from sot_exceptions import canonical_version

        self.assertEqual(canonical_version("en", "NIV"), "NIV")
        self.assertEqual(canonical_version("fr", "TOB"), "TOB")

    def test_alias_is_per_language(self):
        from sot_exceptions import canonical_version

        self.assertEqual(canonical_version("zh", "新改訳2003"), "新改訳2003")

    def test_phase_b_accepts_aliased_version_without_warning(self):
        from corpus_file_validator import CorpusFileValidator
        from corpus_index_reader import CorpusCombo

        from shared_validation.report import Report

        validator = CorpusFileValidator({"ja": {"allowed_versions": ["SK2003", "JCB"]}})
        report = Report("B")
        validator._check_against_bible_sot(
            CorpusCombo("ja", "新改訳2003", "2026", "f.json"), report
        )
        self.assertEqual(report.errors, [])
        self.assertEqual(report.warnings, [])

    def test_phase_b_still_errors_on_unknown_unaliased_version(self):
        from corpus_file_validator import CorpusFileValidator
        from corpus_index_reader import CorpusCombo

        from shared_validation.report import Report

        validator = CorpusFileValidator({"en": {"allowed_versions": ["KJV", "NIV"]}})
        report = Report("B")
        validator._check_against_bible_sot(
            CorpusCombo("en", "XYZ", "2026", "f.json"), report
        )
        self.assertEqual(len(report.errors), 1)

    def test_phase_c_resolves_database_with_canonical_version(self):
        import validate_devocionales_corpus as phase
        from corpus_index_reader import CorpusCombo

        from shared_validation.report import Report

        combo = CorpusCombo("ja", "新改訳2003", "2026", "f.json")
        data = {"data": {"ja": {"2026-01-01": [{"id": "a", "versiculo": "x"}]}}}
        cache = {phase.CORPUS_DIR / "f.json": data}
        with mock.patch.object(
            phase.ScriptureValidator, "get_resolver", return_value=None
        ) as get_resolver:
            phase.validate_corpus_scripture(Report("C"), [combo], cache)
        get_resolver.assert_called_once_with("SK2003", "ja")


if __name__ == "__main__":
    unittest.main()
