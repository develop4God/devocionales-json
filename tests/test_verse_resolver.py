"""test_verse_resolver.py — unit tests for devocionales_scripts/verse_resolver.py,
specifically the HIOV long-form -> short-form book name normalization (issue #83)
and the surrounding _native_book_name / resolve edge cases.

Builds tiny in-memory-equivalent SQLite fixtures (temp files, since VerseResolver
opens sqlite3.connect(path) rather than accepting a connection) instead of using
the real bible_database/*.gz files, so these tests don't depend on decompressing
multi-MB binaries and stay fast/deterministic. Covers: the HIOV mapping applying
by content regardless of filename, non-HIOV DBs being unaffected even if they
happen to contain the same long_name string, books absent from the mapping
passing through unchanged, and the pre-existing `books` table absent / row
missing fallback behavior.
"""

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / 'devocionales_scripts'))

from verse_resolver import VerseResolver, _HIOV_LONG_TO_SHORT  # noqa: E402


def _make_bible_db(path: str, books: list[tuple[int, str]], verses: list[tuple[int, int, int, str]]) -> None:
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


class VerseResolverTestCase(unittest.TestCase):
    """Base class providing a books_sot fixture so tests don't hit the network."""

    def setUp(self):
        import verse_resolver
        verse_resolver._books_sot_cache = {
            "Matthew": 470,
            "Mark": 480,
            "Luke": 490,
            "John": 500,
            "Genesis": 10,
        }

    def tearDown(self):
        import verse_resolver
        verse_resolver._books_sot_cache = None


class TestHIOVLongFormNormalization(VerseResolverTestCase):
    """The core issue #83 fix: HIOV's liturgical long_name is normalized to
    the short form used everywhere else in the corpus."""

    def test_luke_long_form_normalized_to_short(self):
        with tempfile.NamedTemporaryFile(suffix=".SQLite3", delete=False) as f:
            path = f.name
        try:
            _make_bible_db(
                path,
                books=[(490, "लूका रचित सुसमाचार")],
                verses=[(490, 24, 13, "verse text")],
            )
            with VerseResolver(path) as r:
                cita, texto, error = r.resolve("Luke 24:13")
            self.assertIsNone(error)
            self.assertEqual(cita, "लूका 24:13")
            self.assertEqual(texto, "verse text")
        finally:
            Path(path).unlink(missing_ok=True)

    def test_all_four_gospels_normalized(self):
        with tempfile.NamedTemporaryFile(suffix=".SQLite3", delete=False) as f:
            path = f.name
        try:
            _make_bible_db(
                path,
                books=[
                    (470, "मत्ती रचित सुसमाचार"),
                    (480, "मरकुस रचित सुसमाचार"),
                    (490, "लूका रचित सुसमाचार"),
                    (500, "यूहन्ना रचित सुसमाचार"),
                ],
                verses=[
                    (470, 3, 16, "t"), (480, 5, 1, "t"),
                    (490, 19, 1, "t"), (500, 4, 1, "t"),
                ],
            )
            with VerseResolver(path) as r:
                self.assertEqual(r.resolve("Matthew 3:16")[0], "मत्ती 3:16")
                self.assertEqual(r.resolve("Mark 5:1")[0], "मरकुस 5:1")
                self.assertEqual(r.resolve("Luke 19:1")[0], "लूका 19:1")
                self.assertEqual(r.resolve("John 4:1")[0], "यूहन्ना 4:1")
        finally:
            Path(path).unlink(missing_ok=True)

    def test_mapping_applies_regardless_of_db_filename(self):
        """The fix must key off DB *content* (long_name), not the filename —
        a copy, symlink, or differently-named temp file must still normalize."""
        with tempfile.NamedTemporaryFile(suffix=".SQLite3", prefix="not_hiov_named_", delete=False) as f:
            path = f.name
        try:
            _make_bible_db(
                path,
                books=[(490, "लूका रचित सुसमाचार")],
                verses=[(490, 24, 13, "verse text")],
            )
            with VerseResolver(path) as r:
                cita, _, error = r.resolve("Luke 24:13")
            self.assertIsNone(error)
            self.assertEqual(cita, "लूका 24:13")
        finally:
            Path(path).unlink(missing_ok=True)


class TestNonHIOVBooksUnaffected(VerseResolverTestCase):
    """Books not in the liturgical long-form mapping — including non-Gospel
    HIOV books and any other language's DB — must pass through unchanged."""

    def test_non_gospel_book_passes_through_unchanged(self):
        with tempfile.NamedTemporaryFile(suffix=".SQLite3", delete=False) as f:
            path = f.name
        try:
            _make_bible_db(
                path,
                books=[(10, "उत्पत्ति")],
                verses=[(10, 1, 1, "verse text")],
            )
            with VerseResolver(path) as r:
                cita, _, error = r.resolve("Genesis 1:1")
            self.assertIsNone(error)
            self.assertEqual(cita, "उत्पत्ति 1:1")
        finally:
            Path(path).unlink(missing_ok=True)

    def test_other_language_long_name_not_mistakenly_mapped(self):
        """A non-Hindi DB's long_name won't coincidentally collide with the
        HIOV mapping's keys (they're Devanagari strings), but this guards
        the general case: an unmapped long_name always passes through as-is."""
        with tempfile.NamedTemporaryFile(suffix=".SQLite3", delete=False) as f:
            path = f.name
        try:
            _make_bible_db(
                path,
                books=[(490, "Lukas")],
                verses=[(490, 24, 13, "verse text")],
            )
            with VerseResolver(path) as r:
                cita, _, error = r.resolve("Luke 24:13")
            self.assertIsNone(error)
            self.assertEqual(cita, "Lukas 24:13")
        finally:
            Path(path).unlink(missing_ok=True)


class TestNativeBookNameFallbacks(VerseResolverTestCase):
    """Pre-existing fallback behavior, re-verified after the HIOV change to
    confirm it wasn't disturbed."""

    def test_missing_books_table_falls_back_to_english(self):
        with tempfile.NamedTemporaryFile(suffix=".SQLite3", delete=False) as f:
            path = f.name
        try:
            conn = sqlite3.connect(path)
            conn.execute("CREATE TABLE verses (book_number INTEGER, chapter INTEGER, verse INTEGER, text TEXT)")
            conn.execute("INSERT INTO verses VALUES (490, 24, 13, 'verse text')")
            conn.commit()
            conn.close()

            with VerseResolver(path) as r:
                cita, _, error = r.resolve("Luke 24:13")
            self.assertIsNone(error)
            self.assertEqual(cita, "Luke 24:13")
        finally:
            Path(path).unlink(missing_ok=True)

    def test_missing_book_row_falls_back_to_english(self):
        with tempfile.NamedTemporaryFile(suffix=".SQLite3", delete=False) as f:
            path = f.name
        try:
            _make_bible_db(
                path,
                books=[(470, "मत्ती रचित सुसमाचार")],  # only Matthew present
                verses=[(490, 24, 13, "verse text")],   # but Luke has verses
            )
            with VerseResolver(path) as r:
                cita, _, error = r.resolve("Luke 24:13")
            self.assertIsNone(error)
            self.assertEqual(cita, "Luke 24:13")
        finally:
            Path(path).unlink(missing_ok=True)


class TestNullVerseText(VerseResolverTestCase):
    """A verse row with NULL text (a real data gap seen in some Bible DBs,
    e.g. Leviticus 24:16 in one non-EN corpus DB) must resolve as
    "verse not found" like a missing row, not crash fetch_text's
    " ".join() on a None item."""

    def test_null_text_cell_treated_as_not_found(self):
        with tempfile.NamedTemporaryFile(suffix=".SQLite3", delete=False) as f:
            path = f.name
        try:
            conn = sqlite3.connect(path)
            conn.execute("CREATE TABLE books (book_number INTEGER PRIMARY KEY, long_name TEXT)")
            conn.execute("CREATE TABLE verses (book_number INTEGER, chapter INTEGER, verse INTEGER, text TEXT)")
            conn.execute("INSERT INTO books VALUES (10, 'Genesis')")
            conn.execute("INSERT INTO verses VALUES (10, 24, 16, NULL)")
            conn.commit()
            conn.close()

            with VerseResolver(path) as r:
                cita, texto, error = r.resolve("Genesis 24:16")
            self.assertIsNone(cita)
            self.assertIsNone(texto)
            self.assertIsNotNone(error)
            self.assertIn("verse not found", error)
        finally:
            Path(path).unlink(missing_ok=True)

    def test_null_text_among_multiple_verses_treated_as_not_found(self):
        """A multi-verse range (e.g. 'Genesis 24:15-16') where only one row
        is NULL must still fail cleanly, not silently drop the NULL row and
        return a partial/wrong combined text."""
        with tempfile.NamedTemporaryFile(suffix=".SQLite3", delete=False) as f:
            path = f.name
        try:
            conn = sqlite3.connect(path)
            conn.execute("CREATE TABLE books (book_number INTEGER PRIMARY KEY, long_name TEXT)")
            conn.execute("CREATE TABLE verses (book_number INTEGER, chapter INTEGER, verse INTEGER, text TEXT)")
            conn.execute("INSERT INTO books VALUES (10, 'Genesis')")
            conn.execute("INSERT INTO verses VALUES (10, 24, 15, 'verse fifteen text')")
            conn.execute("INSERT INTO verses VALUES (10, 24, 16, NULL)")
            conn.commit()
            conn.close()

            with VerseResolver(path) as r:
                cita, texto, error = r.resolve("Genesis 24:15-16")
            self.assertIsNone(cita)
            self.assertIsNone(texto)
            self.assertIsNotNone(error)
        finally:
            Path(path).unlink(missing_ok=True)


class TestFootnoteAndNoteElementsStripped(VerseResolverTestCase):
    """Real data gap found in CUV1919 (Chinese): footnote-marker numbers
    and translator's notes are stored inline as <f>[N]</f> and
    <n>...</n> elements (e.g. '<pb/>起初神创<f>[1]</f>造天地。'). The
    generic tag-stripper only removes the markup, leaving the bracketed
    number/note text behind — which then tanks Jaccard token-overlap to
    ~0% against a clean corpus reference even when the underlying verse
    matches. fetch_text must drop these two elements INCLUDING their
    content, while still keeping other tags' content (<pb/>, <J> direct
    speech, <i> supplied words) since those wrap real verse text."""

    def test_footnote_marker_element_and_content_removed(self):
        with tempfile.NamedTemporaryFile(suffix=".SQLite3", delete=False) as f:
            path = f.name
        try:
            conn = sqlite3.connect(path)
            conn.execute("CREATE TABLE books (book_number INTEGER PRIMARY KEY, long_name TEXT)")
            conn.execute("CREATE TABLE verses (book_number INTEGER, chapter INTEGER, verse INTEGER, text TEXT)")
            conn.execute("INSERT INTO books VALUES (10, 'Genesis')")
            conn.execute("INSERT INTO verses VALUES (10, 1, 1, '<pb/>起初神创<f>[1]</f>造天地。')")
            conn.commit()
            conn.close()

            with VerseResolver(path) as r:
                _, texto, error = r.resolve("Genesis 1:1")
            self.assertIsNone(error)
            self.assertEqual(texto, "起初神创造天地。")
            self.assertNotIn("[1]", texto)
        finally:
            Path(path).unlink(missing_ok=True)

    def test_translator_note_element_and_content_removed(self):
        with tempfile.NamedTemporaryFile(suffix=".SQLite3", delete=False) as f:
            path = f.name
        try:
            conn = sqlite3.connect(path)
            conn.execute("CREATE TABLE books (book_number INTEGER PRIMARY KEY, long_name TEXT)")
            conn.execute("CREATE TABLE verses (book_number INTEGER, chapter INTEGER, verse INTEGER, text TEXT)")
            conn.execute("INSERT INTO books VALUES (10, 'Genesis')")
            conn.execute(
                "INSERT INTO verses VALUES (10, 4, 1, "
                "'夏娃就怀孕，生了该隐<n>〔注：就是『得』的意思〕</n>，便说：「耶和华使我得了一个男子。」')"
            )
            conn.commit()
            conn.close()

            with VerseResolver(path) as r:
                _, texto, error = r.resolve("Genesis 4:1")
            self.assertIsNone(error)
            self.assertNotIn("注", texto)
            self.assertNotIn("〔", texto)

        finally:
            Path(path).unlink(missing_ok=True)

    def test_other_tags_keep_their_content(self):
        """<J> (direct speech) and <i> (supplied words) wrap real verse
        text — only their markup should be stripped, never their content."""
        with tempfile.NamedTemporaryFile(suffix=".SQLite3", delete=False) as f:
            path = f.name
        try:
            conn = sqlite3.connect(path)
            conn.execute("CREATE TABLE books (book_number INTEGER PRIMARY KEY, long_name TEXT)")
            conn.execute("CREATE TABLE verses (book_number INTEGER, chapter INTEGER, verse INTEGER, text TEXT)")
            conn.execute("INSERT INTO books VALUES (10, 'Genesis')")
            conn.execute("INSERT INTO verses VALUES (10, 1, 3, '神说：<J>「要有光。」</J>就有了<f>[3]</f>光。')")
            conn.commit()
            conn.close()

            with VerseResolver(path) as r:
                _, texto, error = r.resolve("Genesis 1:3")
            self.assertIsNone(error)
            self.assertEqual(texto, "神说：「要有光。」就有了光。")
        finally:
            Path(path).unlink(missing_ok=True)


class TestHIOVMappingTableIntegrity(unittest.TestCase):
    """Guards the mapping data itself against silent drift/typos."""

    def test_mapping_has_exactly_the_four_gospels(self):
        self.assertEqual(len(_HIOV_LONG_TO_SHORT), 4)
        for short in _HIOV_LONG_TO_SHORT.values():
            self.assertNotIn("रचित सुसमाचार", short, "short form must not retain the liturgical suffix")

    def test_mapping_values_are_nonempty(self):
        for long_form, short_form in _HIOV_LONG_TO_SHORT.items():
            self.assertTrue(long_form.strip())
            self.assertTrue(short_form.strip())


if __name__ == "__main__":
    unittest.main()
