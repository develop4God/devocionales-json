"""test_lexicon_fixer.py — unit tests for shared_validation/lexicon_fixer.py.

Uses a minimal fake LexiconSource (single unambiguous entry) instead of the
real 13,450-entry Strong's data file — these tests are about the fixer's
text-surgery logic, not lexicon content.
"""

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from shared_validation.lexicon_fixer import (  # noqa: E402
    _fix_file_text,
    triage_bare_latin_glosses,
)
from shared_validation.lexicon_source import LexiconEntry, StrongsLexiconSource  # noqa: E402


class _FakeLexicon:
    """One fixed entry, returned regardless of the lemma asked for — enough
    for _fix_file_text's citation-boundary logic, which is what's under
    test here, not lemma resolution itself."""

    def __init__(self, entry: LexiconEntry):
        self._entry = entry

    def lookup_by_lemma(self, word):
        return [self._entry] if word == self._entry.lemma else []

    def lookup_by_lemma_and_number(self, word, strongs_number):
        if word == self._entry.lemma and strongs_number == self._entry.strongs_number:
            return self._entry
        return None

    def lookup_by_number(self, strongs_number):
        return self._entry if strongs_number == self._entry.strongs_number else None


ASTHENES = LexiconEntry(
    strongs_number="G772", lemma="ἀσθενής", translit="asthenḗs", gloss="weak"
)


class TestFixFileTextCitationParens(unittest.TestCase):
    """Regression coverage for the bug found fixing gethsemane_agony_001/ja:
    a citation already wrapped in full-width CJK parens (（G772）) had only
    its ASCII-paren counterpart recognized as a closing bracket, so the
    reformat step left the original full-width ）behind after inserting the
    new canonical (G772) — producing corrupted text like
    "(asthenḗs) (G772)）". See project_lexicon_strong_sot_fixer_status memory."""

    def test_fullwidth_paren_citation_fully_consumed(self):
        raw = "prefix ἀσθενής, (asthenēs)（Strong G772） suffix"
        new_text, changes = _fix_file_text(raw, _FakeLexicon(ASTHENES), lang="ja")
        self.assertEqual(new_text, "prefix ἀσθενής, (asthenḗs) (G772) suffix")
        self.assertNotIn("）", new_text)
        self.assertEqual(len(changes), 1)

    def test_ascii_paren_citation_fully_consumed(self):
        raw = "prefix ἀσθενής, (asthenēs) (Strong G772) suffix"
        new_text, _ = _fix_file_text(raw, _FakeLexicon(ASTHENES), lang="en")
        self.assertEqual(new_text, "prefix ἀσθενής, (asthenḗs) (G772) suffix")

    def test_already_canonical_is_left_untouched(self):
        raw = "prefix ἀσθενής, (asthenḗs) (G772) suffix"
        new_text, changes = _fix_file_text(raw, _FakeLexicon(ASTHENES), lang="en")
        self.assertEqual(new_text, raw)
        self.assertEqual(changes, [])


class TestTriageBareLatinGlosses(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lexicon = StrongsLexiconSource()

    def test_reports_unique_transliteration_with_canonical_replacement(self):
        findings = triage_bare_latin_glosses(
            "The love (agapē) of God.", self.lexicon, "en"
        )
        self.assertTrue(
            any("ἀγάπη, (agápē) (G26)" in finding for finding in findings),
            findings,
        )

    def test_ignores_existing_canonical_gloss(self):
        findings = triage_bare_latin_glosses("ἀγάπη, (agápē) (G26)", self.lexicon, "en")
        self.assertEqual(findings, [])

    def test_reports_ambiguous_transliteration_for_review(self):
        findings = triage_bare_latin_glosses("was (ēn)", self.lexicon, "en")
        self.assertTrue(any("REVIEW" in finding for finding in findings), findings)


if __name__ == "__main__":
    unittest.main()
