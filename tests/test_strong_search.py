"""test_strong_search.py — unit tests for shared_validation/strong_search.py.

Tests each phase of the search pipeline against known patterns from the
corpus, including edge cases like overlapping matches, multi-line content,
and the "Strong" prefix vs. bare code distinction.
"""

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from shared_validation.strong_search import (
    find_strong_codes_phase1,
    find_strong_codes_phase2,
    find_strong_codes_phase3,
    find_strong_codes_in_file,
    resolve_strong_results,
    summarize_results,
)
from shared_validation.lexicon_source import StrongsLexiconSource


class TestPhase1StrongPrefix(unittest.TestCase):
    """Phase 1: patterns with the literal word 'Strong'."""

    def test_parens_strong_greek(self):
        """(Strong G3327) — the most common pattern."""
        results = find_strong_codes_phase1(
            "La palabra clave aquí es μεταβέβηκεν, (metabebēken) (Strong G3327)."
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].code, "G3327")
        self.assertEqual(results[0].prefix, "G")
        self.assertEqual(results[0].number, "3327")
        self.assertIn("(Strong G3327)", results[0].full_match)

    def test_parens_strong_hebrew(self):
        """(Strong H5782) — Hebrew pattern."""
        results = find_strong_codes_phase1("The word is עוּר, (ʻûwr) (Strong H5782).")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].code, "H5782")
        self.assertEqual(results[0].prefix, "H")

    def test_strong_without_parens(self):
        """Strong G1568 — 'Strong' prefix without parentheses (bullet points)."""
        results = find_strong_codes_phase1(
            "• PRIMERA PALABRA: ἐκθαμβεῖσθαι, (ekthambeisthai) (Strong G1568)"
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].code, "G1568")

    def test_strong_short_number(self):
        """(Strong G5) — short number (1 digit)."""
        results = find_strong_codes_phase1("ἀββά, (abba) (Strong G5)")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].code, "G5")

    def test_multiple_strong_prefixes(self):
        """Multiple Strong prefix patterns in the same text."""
        results = find_strong_codes_phase1(
            "ἐκθαμβεῖσθαι, (ekthambeisthai) (Strong G1568) and "
            "ἀδημονεῖν, (adēmonein) (Strong G85) and "
            "γρηγορέω, (grēgoreō) (Strong G1127)."
        )
        self.assertEqual(len(results), 3)
        codes = [r.code for r in results]
        self.assertIn("G1568", codes)
        self.assertIn("G85", codes)
        self.assertIn("G1127", codes)

    def test_no_strong_pattern(self):
        """Text with no Strong patterns returns empty list."""
        results = find_strong_codes_phase1(
            "This is just ordinary text with no Strong's numbers."
        )
        self.assertEqual(len(results), 0)


class TestPhase2BareCodes(unittest.TestCase):
    """Phase 2: bare code patterns without the 'Strong' prefix."""

    def test_bare_parens_code(self):
        """(G3327) — bare code in parentheses."""
        results = find_strong_codes_phase2("The word (G3327) appears in parentheses.")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].code, "G3327")

    def test_dash_prefix_code(self):
        """- G728) — dash-prefixed inside parens (common in bullet lists)."""
        results = find_strong_codes_phase2("ARRAS (ἀρραβών, (arrabon) - G728):")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].code, "G728")

    def test_standalone_code(self):
        """G728 — standalone code without any wrapping."""
        results = find_strong_codes_phase2("The word is G728, a pledge.")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].code, "G728")

    def test_phase2_excludes_phase1_overlaps(self):
        """Phase 2 must not return patterns already caught by Phase 1."""
        text = "Here is (Strong G3327) and also (G728) separately."
        results = find_strong_codes_phase2(text)
        codes = [r.code for r in results]
        self.assertNotIn(
            "G3327", codes, "G3327 has 'Strong' prefix, should be Phase 1 only"
        )
        self.assertIn("G728", codes, "G728 is bare code, should be in Phase 2")

    def test_hebrew_bare_code(self):
        """(H5782) — Hebrew bare code."""
        results = find_strong_codes_phase2("The Hebrew word (H5782) means 'to wake'.")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].code, "H5782")

    def test_no_bare_code(self):
        """Text with no bare codes returns empty list."""
        results = find_strong_codes_phase2("This text has no codes at all.")
        self.assertEqual(len(results), 0)


class TestPhase3Combined(unittest.TestCase):
    """Phase 3: combined search for all patterns."""

    def test_combined_results(self):
        """Phase 3 includes both Phase 1 and Phase 2 results."""
        text = "(Strong G3327) is a prefix pattern, while (G728) is a bare code."
        results = find_strong_codes_phase3(text)
        self.assertEqual(len(results), 2)
        codes = [r.code for r in results]
        self.assertIn("G3327", codes)
        self.assertIn("G728", codes)

    def test_combined_no_duplicates(self):
        """Phase 3 must not have duplicates."""
        text = "(Strong G3327) and (Strong G1568) and (G728)."
        results = find_strong_codes_phase3(text)
        codes = [r.code for r in results]
        # Count occurrences of each code
        from collections import Counter

        counts = Counter(codes)
        for code, count in counts.items():
            self.assertEqual(count, 1, f"Code {code} appears {count} times, expected 1")

    def test_combined_ordering(self):
        """Results are ordered by position in text."""
        text = "first (G728) then (Strong G3327) then (G85)."
        results = find_strong_codes_phase3(text)
        codes = [r.code for r in results]
        self.assertEqual(codes, ["G728", "G3327", "G85"])

    def test_real_corpus_pattern(self):
        """A realistic multi-line corpus excerpt."""
        text = """ANÁLISIS DE μεταβέβηκεν, (metabebēken) (Strong G3327):
• META = Cambio de lugar
• BEBĒKEN = Verbo 'baino' (ir, caminar)
• Tiempo: PERFECTO

ARRAS (ἀρραβών, (arrabon) - G728):
• Pago inicial que GARANTIZA el pago completo"""
        results = find_strong_codes_phase3(text)
        self.assertEqual(len(results), 2)
        codes = [r.code for r in results]
        self.assertEqual(codes, ["G3327", "G728"])


class TestPhase4Resolution(unittest.TestCase):
    """Phase 4: resolve results to lexicon entries."""

    @classmethod
    def setUpClass(cls):
        cls.lex = StrongsLexiconSource()

    def test_resolve_greek_code(self):
        """G3327 resolves to μεταβαίνω."""
        text = "(Strong G3327)"
        results = find_strong_codes_phase3(text)
        resolved = resolve_strong_results(results, self.lex)
        self.assertEqual(len(resolved), 1)
        r, entry = resolved[0]
        self.assertEqual(r.code, "G3327")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.lemma, "μεταβαίνω")
        self.assertEqual(entry.translit, "metabaínō")

    def test_resolve_hebrew_code(self):
        """H5782 resolves to עוּר."""
        text = "(Strong H5782)"
        results = find_strong_codes_phase3(text)
        resolved = resolve_strong_results(results, self.lex)
        self.assertEqual(len(resolved), 1)
        r, entry = resolved[0]
        self.assertEqual(r.code, "H5782")
        self.assertIsNotNone(entry)
        self.assertEqual(entry.lemma, "עוּר")

    def test_resolve_invalid_code(self):
        """An invalid code returns None."""
        text = "(Strong G99999)"
        results = find_strong_codes_phase3(text)
        resolved = resolve_strong_results(results, self.lex)
        self.assertEqual(len(resolved), 1)
        r, entry = resolved[0]
        self.assertIsNone(entry)

    def test_resolve_multiple_codes(self):
        """Multiple codes resolved correctly."""
        text = "(Strong G3327) and (Strong G1568)."
        results = find_strong_codes_phase3(text)
        resolved = resolve_strong_results(results, self.lex)
        self.assertEqual(len(resolved), 2)
        for r, entry in resolved:
            self.assertIsNotNone(entry, f"Entry for {r.code} should not be None")


class TestFindInFile(unittest.TestCase):
    """Integration tests for find_strong_codes_in_file."""

    def test_passed_from_death_file(self):
        """The file the user mentioned should have known codes."""
        fp = "discovery/es/passed_from_death_es_001.json"
        results = find_strong_codes_in_file(fp, phase=3)
        self.assertGreaterEqual(len(results), 2)
        codes = [r.code for r in results]
        self.assertIn("G3327", codes)
        self.assertIn("G728", codes)

    def test_gethsemane_file(self):
        """gethsemane_agony has multiple Strong's codes."""
        fp = "discovery/es/gethsemane_agony_es_001.json"
        results = find_strong_codes_in_file(fp, phase=3)
        self.assertGreaterEqual(len(results), 4)
        codes = [r.code for r in results]
        self.assertIn("G1568", codes)
        self.assertIn("G85", codes)
        self.assertIn("G1127", codes)
        self.assertIn("G4289", codes)

    def test_phase_filtering(self):
        """Phase parameter filters correctly.

        Uses a synthetic fixture rather than a live corpus file: the corpus
        is expected to converge on zero "Strong "-prefixed citations over
        time as the fixer is applied, which would make a real-file
        assertion of "at least one Strong-prefixed match" flaky by design.
        """
        import tempfile
        import json as json_module

        fixture = {
            "cards": [
                {
                    "content": (
                        "La palabra clave aquí es μεταβέβηκεν, "
                        "(metabebēken) (Strong G3327). Otro término es (G728)."
                    )
                }
            ]
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json_module.dump(fixture, f)
            fp = f.name

        try:
            phase1 = find_strong_codes_in_file(fp, phase=1)
            phase2 = find_strong_codes_in_file(fp, phase=2)
            phase3 = find_strong_codes_in_file(fp, phase=3)
            # Phase 1 finds only "Strong" prefix patterns
            self.assertGreaterEqual(len(phase1), 1)
            # Phase 2 finds only bare codes
            self.assertGreaterEqual(len(phase2), 1)
            # Phase 3 combines both
            self.assertEqual(len(phase3), len(phase1) + len(phase2))
        finally:
            Path(fp).unlink()


class TestSummarizeResults(unittest.TestCase):
    """Tests for the summarize_results helper."""

    def test_summary_structure(self):
        """Summary has expected keys."""
        text = "(Strong G3327) and (Strong G1568) and (G728)."
        results = find_strong_codes_phase3(text)
        summary = summarize_results(results)
        self.assertIn("total", summary)
        self.assertIn("unique_codes", summary)
        self.assertIn("by_prefix", summary)
        self.assertIn("codes_sorted", summary)

    def test_summary_counts(self):
        """Summary counts are correct."""
        text = "(Strong G3327) and (Strong G3327) again."
        results = find_strong_codes_phase3(text)
        summary = summarize_results(results)
        self.assertEqual(summary["total"], 2)
        self.assertEqual(summary["unique_codes"], {"G3327": 2})

    def test_summary_by_prefix(self):
        """Summary by_prefix groups correctly."""
        text = "(Strong G3327) and (Strong H5782)."
        results = find_strong_codes_phase3(text)
        summary = summarize_results(results)
        self.assertEqual(summary["by_prefix"], {"G": 1, "H": 1})

    def test_empty_results(self):
        """Empty results produce empty summary."""
        summary = summarize_results([])
        self.assertEqual(summary["total"], 0)
        self.assertEqual(summary["unique_codes"], {})
        self.assertEqual(summary["by_prefix"], {})


class TestEdgeCases(unittest.TestCase):
    """Edge cases and robustness."""

    def test_empty_string(self):
        """Empty string returns empty list."""
        self.assertEqual(find_strong_codes_phase1(""), [])
        self.assertEqual(find_strong_codes_phase2(""), [])
        self.assertEqual(find_strong_codes_phase3(""), [])

    def test_unicode_content(self):
        """Unicode content (Greek, Hebrew) doesn't interfere."""
        text = "μεταβέβηκεν, (metabebēken) (Strong G3327)"
        results = find_strong_codes_phase3(text)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].code, "G3327")

    def test_context_window(self):
        """Custom context_window changes the context snippet."""
        text = "This is a very long sentence with (Strong G3327) in the middle of it."
        results_default = find_strong_codes_phase3(text, context_window=40)
        results_short = find_strong_codes_phase3(text, context_window=10)
        self.assertGreater(
            len(results_default[0].context), len(results_short[0].context)
        )

    def test_numeric_edge_cases(self):
        """Very short (G5) and very long (G12345) codes."""
        text = "Short (G5) and long (G12345)."
        results = find_strong_codes_phase3(text)
        codes = [r.code for r in results]
        self.assertIn("G5", codes)
        self.assertIn("G12345", codes)

    def test_no_false_positive_on_plain_text(self):
        """Plain text like 'G1234' could be a misinterpretation."""
        # "G1234" as part of a larger word should not match
        text = "The word G1234 something."
        results = find_strong_codes_phase3(text)
        # This should match because it's a standalone G-prefix code
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].code, "G1234")

    def test_no_false_positive_on_french_time_notation(self):
        """French time notation like '3h00'/'6h00' is not a Strong's code.

        The broad regex is case-insensitive on the G/H prefix and the
        original lowercase is lost by the time is_correct_format runs (the
        prefix is uppercased at match time), so this can only be caught by
        a whitelist exclusion — see strong_whitelist.json.
        """
        text = "pendant la quatrième veille (entre 3h00 et 6h00 du matin)"
        results = find_strong_codes_phase3(text)
        self.assertEqual(results, [])

    def test_real_hebrew_code_not_excluded_by_time_notation_whitelist(self):
        """The french-time-notation whitelist entry must not swallow a
        real 2-digit-adjacent Hebrew code like (Strong H50)."""
        results = find_strong_codes_phase3("(Strong H50)")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].code, "H50")


if __name__ == "__main__":
    unittest.main()
