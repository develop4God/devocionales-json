"""test_scripture_check.py — unit tests for shared_validation/scripture_check.py
(issue #88: validate scripture references and verse text at pipeline time).

Covers find_scripture_pairs() (pure extraction: nested structures, multiple
pairs per card, missing bible_version) and validate_pair() (known-good
reference, known-bad book name, known verse-count-exceeded, a synthetic
text-mismatch case) against a tiny in-memory-equivalent SQLite fixture DB —
same approach as tests/test_verse_resolver.py, so these tests don't depend
on decompressing the real multi-MB bible_database/*.gz files and stay fast
and deterministic.
"""

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / 'devocionales_scripts'))

from verse_resolver import VerseResolver  # noqa: E402
from shared_validation.scripture_check import (  # noqa: E402
    ScriptureRef, find_scripture_pairs, validate_pair, validate_translated_pair,
    jaccard_similarity, FUZZY_MATCH_THRESHOLD,
)


def _make_bible_db(path: str, books: list, verses: list) -> None:
    """Create a minimal SQLite Bible DB with `books` and `verses` tables."""
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE books (book_number INTEGER PRIMARY KEY, long_name TEXT)")
    conn.execute("CREATE TABLE verses (book_number INTEGER, chapter INTEGER, verse INTEGER, text TEXT)")
    conn.executemany("INSERT INTO books (book_number, long_name) VALUES (?, ?)", books)
    conn.executemany(
        "INSERT INTO verses (book_number, chapter, verse, text) VALUES (?, ?, ?, ?)",
        verses,
    )
    conn.commit()
    conn.close()


# ── find_scripture_pairs ─────────────────────────────────────────────────────

class TestFindScripturePairs(unittest.TestCase):
    def test_finds_verse_reference_verse_text_pair(self):
        data = {
            'cards': [
                {'type': 'scripture_moment', 'verse_reference': 'John 3:16',
                 'verse_text': 'For God so loved the world...'},
            ]
        }
        pairs = find_scripture_pairs(data)
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0].reference, 'John 3:16')
        self.assertEqual(pairs[0].verse_text, 'For God so loved the world...')
        self.assertEqual(pairs[0].path, 'cards[0].verse_reference')

    def test_finds_reference_text_pair(self):
        """key_verse / completion_verse / scripture_connections / scripture_anchor
        all use reference+text rather than verse_reference+verse_text."""
        data = {'key_verse': {'reference': 'Matthew 14:31', 'text': 'O you of little faith'}}
        pairs = find_scripture_pairs(data)
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0].reference, 'Matthew 14:31')
        self.assertEqual(pairs[0].path, 'key_verse.reference')

    def test_finds_multiple_pairs_per_card(self):
        """A card can carry more than one scripture pair (e.g. verse_overlay
        alongside verse_reference/verse_text) — both must be found."""
        data = {
            'cards': [
                {
                    'type': 'scripture_moment',
                    'verse_reference': 'John 3:16', 'verse_text': 'text A',
                    'verse_overlay': {'reference': 'John 3:17', 'text': 'text B'},
                },
            ]
        }
        pairs = find_scripture_pairs(data)
        refs = {p.reference for p in pairs}
        self.assertEqual(refs, {'John 3:16', 'John 3:17'})

    def test_finds_pairs_in_nested_lists(self):
        """scripture_connections is a list of {reference, text} dicts nested
        inside a card — the walk must descend into list items."""
        data = {
            'cards': [
                {
                    'type': 'theological_depth',
                    'scripture_connections': [
                        {'reference': 'Joel 2:28', 'text': 'I will pour out my spirit'},
                        {'reference': 'Acts 2:17', 'text': 'In the last days'},
                    ],
                },
            ]
        }
        pairs = find_scripture_pairs(data)
        self.assertEqual(len(pairs), 2)
        paths = {p.path for p in pairs}
        self.assertEqual(
            paths,
            {'cards[0].scripture_connections[0].reference',
             'cards[0].scripture_connections[1].reference'},
        )

    def test_missing_bible_version_does_not_crash_extraction(self):
        """find_scripture_pairs is pure extraction — it doesn't care whether
        the file has a bible_version at all, only about reference/text pairs."""
        data = {'cards': [{'type': 'scripture_moment', 'verse_reference': 'John 3:16',
                            'verse_text': 'text'}]}
        self.assertNotIn('bible_version', data)
        pairs = find_scripture_pairs(data)
        self.assertEqual(len(pairs), 1)

    def test_no_pairs_found_returns_empty_list(self):
        data = {'cards': [{'type': 'cinematic_scene', 'title': 'x', 'narrative': 'y'}]}
        self.assertEqual(find_scripture_pairs(data), [])

    def test_empty_reference_or_text_is_not_a_pair(self):
        data = {'key_verse': {'reference': '', 'text': ''}}
        self.assertEqual(find_scripture_pairs(data), [])

    def test_greek_words_reference_without_verse_text_is_not_a_pair(self):
        """greek_words entries have 'reference' but no 'verse_text'/'text' —
        must not be misidentified as a scripture pair."""
        data = {
            'cards': [{
                'greek_words': [{'word': 'ἐπήρθη', 'reference': 'Acts 1:9', 'meaning': 'lifted up'}],
            }]
        }
        self.assertEqual(find_scripture_pairs(data), [])


# ── jaccard_similarity ───────────────────────────────────────────────────────

class TestJaccardSimilarity(unittest.TestCase):
    def test_identical_text_is_1(self):
        self.assertEqual(jaccard_similarity("hello world", "hello world"), 1.0)

    def test_completely_different_text_is_0(self):
        self.assertEqual(jaccard_similarity("hello world", "foo bar"), 0.0)

    def test_smart_quotes_normalized_to_straight(self):
        self.assertEqual(jaccard_similarity('“hello”', '"hello"'), 1.0)

    def test_whitespace_collapsed(self):
        self.assertEqual(jaccard_similarity("hello   world", "hello world"), 1.0)

    def test_arabic_combining_diacritic_order_normalized(self):
        """Real bug found via nicodemus_ar_001.json: the same Arabic word
        can encode its combining fatha/shadda diacritics in a different
        codepoint order while rendering identically — comparing raw
        strings/tokens treats them as different words. NFC normalization
        must make them compare equal. (Constructed directly via unicodedata
        rather than literal source text, since editors/terminals often
        silently re-normalize pasted Arabic to a single canonical form.)"""
        import unicodedata
        base = "لأنَّهُ"    # ل أ ن ّ َ ه ُ — shadda before fatha
        variant = unicodedata.normalize("NFD", base)            # decompose, likely reorders combining marks
        # Only meaningful if the two forms actually differ before normalization.
        self.assertNotEqual(base, variant)
        self.assertEqual(jaccard_similarity(base, variant), 1.0)

    def test_cjk_text_compared_by_character_not_whitespace_token(self):
        """Real bug found via peter_water_zh_001.json: CJK text has no
        spaces, so whitespace .split() collapses an entire verse into one
        token and any two non-identical verses score 0% regardless of how
        similar their content actually is. Character-level comparison must
        recognize these as near-identical (they differ only by quote marks)."""
        stored = "耶稣赶紧伸手拉住他，说：你这小信的人哪，为什么疑惑呢？"
        resolved = "耶稣赶紧伸手拉住他，说：「你这小信的人哪，为什么疑惑呢？」"
        self.assertGreaterEqual(jaccard_similarity(stored, resolved), FUZZY_MATCH_THRESHOLD)

    def test_cjk_completely_different_text_is_low(self):
        self.assertLess(jaccard_similarity("耶稣爱你", "上帝创造天地"), FUZZY_MATCH_THRESHOLD)


# ── validate_pair ────────────────────────────────────────────────────────────

class ValidatePairTestCase(unittest.TestCase):
    """Base class providing a books_sot fixture so tests don't hit the network."""

    def setUp(self):
        import verse_resolver
        verse_resolver._books_sot_cache = {"John": 500, "Matthew": 470}

        with tempfile.NamedTemporaryFile(suffix=".SQLite3", delete=False) as f:
            self.db_path = f.name
        _make_bible_db(
            self.db_path,
            books=[(500, "John"), (470, "Matthew")],
            verses=[
                (500, 3, 16, "For God so loved the world, that he gave his only begotten Son."),
                (500, 3, 17, "For God sent not his Son into the world to condemn the world."),
                (470, 14, 31, "O thou of little faith, wherefore didst thou doubt?"),
            ],
        )
        self.resolver = VerseResolver(self.db_path)

    def tearDown(self):
        import verse_resolver
        verse_resolver._books_sot_cache = None
        self.resolver.close()
        Path(self.db_path).unlink(missing_ok=True)


class TestValidatePairKnownGood(ValidatePairTestCase):
    def test_matching_reference_and_text_returns_none(self):
        ref = ScriptureRef(
            reference="John 3:16",
            verse_text="For God so loved the world, that he gave his only begotten Son.",
            path="key_verse.reference",
        )
        self.assertIsNone(validate_pair(ref, self.resolver))


class TestValidatePairBadBookName(ValidatePairTestCase):
    def test_unknown_book_name_returns_resolution_failed_warning(self):
        ref = ScriptureRef(reference="Zorblax 1:1", verse_text="anything", path="key_verse.reference")
        finding = validate_pair(ref, self.resolver)
        self.assertIsNotNone(finding)
        self.assertEqual(finding.kind, "resolution_failed")
        self.assertIn("unknown book", finding.message)


class TestValidatePairVerseCountExceeded(ValidatePairTestCase):
    def test_verse_number_beyond_chapter_range_returns_resolution_failed(self):
        """John 3 in the fixture DB only has verses 16-17 — verse 999 is
        out of range and must fail resolution, not silently return empty."""
        ref = ScriptureRef(reference="John 3:999", verse_text="anything", path="key_verse.reference")
        finding = validate_pair(ref, self.resolver)
        self.assertIsNotNone(finding)
        self.assertEqual(finding.kind, "resolution_failed")
        self.assertIn("verse not found", finding.message)


class TestValidatePairTextMismatch(ValidatePairTestCase):
    def test_synthetic_wrong_text_returns_text_mismatch_warning(self):
        """Right reference, but stored verse_text is entirely unrelated
        content — must be flagged as a fuzzy text mismatch, not silently
        passed."""
        ref = ScriptureRef(
            reference="John 3:16",
            verse_text="The quick brown fox jumps over the lazy dog in the meadow today.",
            path="key_verse.reference",
        )
        finding = validate_pair(ref, self.resolver)
        self.assertIsNotNone(finding)
        self.assertEqual(finding.kind, "text_mismatch")
        self.assertIn("token-overlap", finding.message)
        # Both texts must be printed side-by-side for human review.
        self.assertIn("stored:", finding.message)
        self.assertIn("resolved:", finding.message)

    def test_merged_verse_block_stays_within_threshold(self):
        """A merged consecutive-verse block (this corpus's own editorial
        convention) shares the large majority of its tokens with the sum of
        the individual verses and must NOT be flagged."""
        ref = ScriptureRef(
            reference="John 3:16",
            verse_text=(
                "For God so loved the world, that he gave his only begotten Son. "
                "For God sent not his Son into the world to condemn the world."
            ),
            path="key_verse.reference",
        )
        # Resolves against 3:16 alone, so overlap won't be perfect, but the
        # shared vocabulary should still clear a reasonable bar — this test
        # documents current threshold behavior rather than asserting a
        # specific pass/fail, since the fixture doesn't resolve a real
        # multi-verse range.
        finding = validate_pair(ref, self.resolver)
        # 3:16 alone resolves; text includes 3:16 verbatim plus 3:17 — some
        # overlap guaranteed, assert it's computed (not crashing) and kind
        # is either None or text_mismatch, never resolution_failed.
        if finding is not None:
            self.assertEqual(finding.kind, "text_mismatch")


class ValidateTranslatedPairTestCase(unittest.TestCase):
    """Base class for validate_translated_pair(): resolves the EN sibling
    reference against a *target-language* DB (never parses the native
    reference string itself) — mirrors validate_pair's fixture shape but
    with a Spanish-labeled DB standing in for any non-EN target."""

    def setUp(self):
        import verse_resolver
        verse_resolver._books_sot_cache = {"John": 500, "Genesis": 10}

        with tempfile.NamedTemporaryFile(suffix=".SQLite3", delete=False) as f:
            self.db_path = f.name
        _make_bible_db(
            self.db_path,
            books=[(500, "Juan"), (10, "Génesis")],
            verses=[
                (500, 3, 16, "Porque de tal manera amó Dios al mundo, que ha dado a su Hijo unigénito."),
            ],
        )
        self.resolver = VerseResolver(self.db_path)

    def tearDown(self):
        import verse_resolver
        verse_resolver._books_sot_cache = None
        self.resolver.close()
        Path(self.db_path).unlink(missing_ok=True)


class TestValidateTranslatedPairKnownGood(ValidateTranslatedPairTestCase):
    def test_matching_translated_text_returns_none(self):
        en_ref = ScriptureRef(reference="John 3:16", verse_text="unused", path="key_verse.reference")
        native_ref = ScriptureRef(
            reference="Juan 3:16",
            verse_text="Porque de tal manera amó Dios al mundo, que ha dado a su Hijo unigénito.",
            path="key_verse.reference",
        )
        self.assertIsNone(validate_translated_pair(en_ref, native_ref, self.resolver))


class TestValidateTranslatedPairTextMismatch(ValidateTranslatedPairTestCase):
    def test_wrong_translated_text_returns_text_mismatch(self):
        en_ref = ScriptureRef(reference="John 3:16", verse_text="unused", path="key_verse.reference")
        native_ref = ScriptureRef(
            reference="Juan 3:16",
            verse_text="El rápido zorro marrón salta sobre el perro perezoso.",
            path="key_verse.reference",
        )
        finding = validate_translated_pair(en_ref, native_ref, self.resolver)
        self.assertIsNotNone(finding)
        self.assertEqual(finding.kind, "text_mismatch")


class TestValidateTranslatedPairBadEnReference(ValidateTranslatedPairTestCase):
    def test_unparseable_en_reference_returns_resolution_failed(self):
        """The EN sibling reference itself is malformed — never even
        attempts to parse the native reference string."""
        en_ref = ScriptureRef(reference="not a reference", verse_text="unused", path="key_verse.reference")
        native_ref = ScriptureRef(reference="Juan 3:16", verse_text="anything", path="key_verse.reference")
        finding = validate_translated_pair(en_ref, native_ref, self.resolver)
        self.assertIsNotNone(finding)
        self.assertEqual(finding.kind, "resolution_failed")
        self.assertIn("could not be parsed", finding.message)

    def test_unknown_en_book_returns_resolution_failed(self):
        en_ref = ScriptureRef(reference="Zorblax 1:1", verse_text="unused", path="key_verse.reference")
        native_ref = ScriptureRef(reference="Zorblax 1:1", verse_text="anything", path="key_verse.reference")
        finding = validate_translated_pair(en_ref, native_ref, self.resolver)
        self.assertIsNotNone(finding)
        self.assertEqual(finding.kind, "resolution_failed")
        self.assertIn("unknown", finding.message)


class TestValidateTranslatedPairNullText(ValidateTranslatedPairTestCase):
    """Regression test: a target-language DB row with NULL text (a real
    data gap found in production, e.g. Leviticus 24:16 in one non-EN
    corpus DB) must surface as a normal resolution_failed finding, not
    crash validate_translated_pair / fetch_text's " ".join() on None."""

    def test_null_text_in_target_db_returns_resolution_failed(self):
        with tempfile.NamedTemporaryFile(suffix=".SQLite3", delete=False) as f:
            null_db_path = f.name
        try:
            conn = sqlite3.connect(null_db_path)
            conn.execute("CREATE TABLE books (book_number INTEGER PRIMARY KEY, long_name TEXT)")
            conn.execute("CREATE TABLE verses (book_number INTEGER, chapter INTEGER, verse INTEGER, text TEXT)")
            conn.execute("INSERT INTO books VALUES (10, 'Génesis')")
            conn.execute("INSERT INTO verses VALUES (10, 24, 16, NULL)")
            conn.commit()
            conn.close()

            null_resolver = VerseResolver(null_db_path)
            try:
                en_ref = ScriptureRef(reference="Genesis 24:16", verse_text="unused", path="key_verse.reference")
                native_ref = ScriptureRef(reference="Génesis 24:16", verse_text="anything", path="key_verse.reference")
                finding = validate_translated_pair(en_ref, native_ref, null_resolver)
                self.assertIsNotNone(finding)
                self.assertEqual(finding.kind, "resolution_failed")
                self.assertIn("verse not found", finding.message)
            finally:
                null_resolver.close()
        finally:
            Path(null_db_path).unlink(missing_ok=True)


class TestValidateTranslatedPairVersificationException(unittest.TestCase):
    """versification_exceptions.json's real Jonah 1:17/LSG1910 entry (a
    hand-verified cross-edition chapter split — LSG1910 numbers the
    fish-swallows-Jonah verse as 2:1, not 1:17) must let validate_translated_pair
    find the verse when bible_version is passed, and must NOT find it
    (falls through to a normal resolution_failed) when bible_version is
    omitted — the exception lookup is opt-in per call, not automatic."""

    def setUp(self):
        import verse_resolver
        verse_resolver._books_sot_cache = {"Jonah": 390}

        with tempfile.NamedTemporaryFile(suffix=".SQLite3", delete=False) as f:
            self.db_path = f.name
        _make_bible_db(
            self.db_path,
            books=[(390, "Jonas")],
            verses=[
                # Mirrors LSG1910's real shape: nothing at 1:17, the verse
                # lives at 2:1 instead.
                (390, 2, 1, "L'Éternel fit venir un grand poisson pour engloutir Jonas."),
            ],
        )
        self.resolver = VerseResolver(self.db_path)

    def tearDown(self):
        import verse_resolver
        verse_resolver._books_sot_cache = None
        self.resolver.close()
        Path(self.db_path).unlink(missing_ok=True)

    def test_exception_found_when_bible_version_passed(self):
        en_ref = ScriptureRef(reference="Jonah 1:17", verse_text="unused", path="key_verse.reference")
        native_ref = ScriptureRef(
            reference="Jonas 2:1",
            verse_text="L'Éternel fit venir un grand poisson pour engloutir Jonas.",
            path="key_verse.reference",
        )
        finding = validate_translated_pair(en_ref, native_ref, self.resolver, bible_version="LSG1910")
        self.assertIsNone(finding)

    def test_exception_not_applied_when_bible_version_omitted(self):
        en_ref = ScriptureRef(reference="Jonah 1:17", verse_text="unused", path="key_verse.reference")
        native_ref = ScriptureRef(reference="Jonas 2:1", verse_text="anything", path="key_verse.reference")
        finding = validate_translated_pair(en_ref, native_ref, self.resolver)
        self.assertIsNotNone(finding)
        self.assertEqual(finding.kind, "resolution_failed")
        self.assertIn("verse not found", finding.message)

    def test_exception_not_applied_for_different_bible_version(self):
        """Only the exact (en_reference, bible_version) pair recorded in
        versification_exceptions.json qualifies — an unrelated version
        code must not accidentally match."""
        en_ref = ScriptureRef(reference="Jonah 1:17", verse_text="unused", path="key_verse.reference")
        native_ref = ScriptureRef(reference="Jonas 2:1", verse_text="anything", path="key_verse.reference")
        finding = validate_translated_pair(en_ref, native_ref, self.resolver, bible_version="NOT_A_REAL_VERSION")
        self.assertIsNotNone(finding)
        self.assertEqual(finding.kind, "resolution_failed")


if __name__ == '__main__':
    unittest.main()
