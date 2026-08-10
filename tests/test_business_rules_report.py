"""test_business_rules_report.py — unit tests for shared_validation/report.py's
Report.print() grouping/tag-truncation of warnings, added when that output
was reformatted to group by file and collapse the repeated bare-transliteration
boilerplate tail into a short tag (see shared_validation/report.py
_print_grouped_by_file / _BARE_TRANSLIT_TAIL_RE).

Imports the module directly and inspects captured stdout, matching the
pattern in tests/test_run_report.py.
"""

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from shared_validation.report import Report  # noqa: E402
from tests.golden_utils import capture  # noqa: E402


class TestReportGroupedByFile(unittest.TestCase):
    def test_warnings_grouped_by_file_worst_first(self):
        report = Report("TEST")
        report.W("a.json:cards[0].content: one hit")
        report.W("b.json:cards[0].content: hit one")
        report.W("b.json:cards[1].content: hit two")
        output = capture(report.print, final=False)

        b_pos = output.index("b.json (2):")
        a_pos = output.index("a.json (1):")
        self.assertLess(b_pos, a_pos)

    def test_message_without_file_prefix_still_printed(self):
        report = Report("TEST")
        report.W("lang-only prefix with no filename: something")
        output = capture(report.print, final=False)
        self.assertIn("lang-only prefix with no filename: something", output)

    def test_no_message_dropped_when_grouping(self):
        report = Report("TEST")
        for i in range(5):
            report.W(f"file{i % 2}.json:cards[{i}].content: distinct message {i}")
        output = capture(report.print, final=False)
        for i in range(5):
            self.assertIn(f"distinct message {i}", output)


class TestReportGroupedByFamily(unittest.TestCase):
    def test_family_grouped_worst_first_with_languages_nested(self):
        report = Report("TEST")
        report.W("study_a_ar_001.json:tags[0]: one hit")
        report.W("study_b_ar_001.json:tags[0]: hit one")
        report.W("study_b_hi_001.json:tags[0]: hit two")
        output = capture(report.print, final=False)

        b_pos = output.index("study_b (2):")
        a_pos = output.index("study_a (1):")
        self.assertLess(b_pos, a_pos)
        self.assertIn("[ar] (1):", output)
        self.assertIn("[hi] (1):", output)

    def test_non_family_filename_falls_back_ungrouped(self):
        report = Report("TEST")
        report.W("a.json:cards[0].content: one hit")
        output = capture(report.print, final=False)
        self.assertIn("a.json (1):", output)

    def test_no_message_dropped_when_grouping_by_family(self):
        report = Report("TEST")
        for i in range(5):
            report.W(f"study_x_ar_00{i}.json:cards[{i}].content: distinct message {i}")
        output = capture(report.print, final=False)
        for i in range(5):
            self.assertIn(f"distinct message {i}", output)


class TestCollapseLatinLeakWords(unittest.TestCase):
    def test_repeated_words_on_same_path_collapsed_to_one_line(self):
        report = Report("TEST")
        report.W(
            "study_a_ar_001.json:tags[0]: Latin text 'judgment' in ar field — possible untranslated leftover"
        )
        report.W(
            "study_a_ar_001.json:tags[0]: Latin text 'seat' in ar field — possible untranslated leftover"
        )
        output = capture(report.print, final=False)
        self.assertIn(
            "tags[0]: Latin text judgment, seat — possible untranslated leftover",
            output,
        )
        self.assertNotIn("'judgment' in ar field", output)

    def test_single_occurrence_on_path_left_untouched(self):
        report = Report("TEST")
        report.W(
            "study_a_ar_001.json:tags[0]: Latin text 'judgment' in ar field — possible untranslated leftover"
        )
        output = capture(report.print, final=False)
        self.assertIn(
            "tags[0]: Latin text 'judgment' in ar field — possible untranslated leftover",
            output,
        )

    def test_different_paths_not_merged_together(self):
        report = Report("TEST")
        report.W(
            "study_a_ar_001.json:tags[0]: Latin text 'judgment' in ar field — possible untranslated leftover"
        )
        report.W(
            "study_a_ar_001.json:tags[1]: Latin text 'reward' in ar field — possible untranslated leftover"
        )
        output = capture(report.print, final=False)
        self.assertIn(
            "tags[0]: Latin text 'judgment' in ar field — possible untranslated leftover",
            output,
        )
        self.assertIn(
            "tags[1]: Latin text 'reward' in ar field — possible untranslated leftover",
            output,
        )

    def test_unrelated_message_on_same_path_not_collapsed(self):
        report = Report("TEST")
        report.W("study_a_ar_001.json:cards[0].content: some other warning entirely")
        report.W("study_a_ar_001.json:cards[0].content: some other warning entirely")
        output = capture(report.print, final=False)
        self.assertEqual(output.count("some other warning entirely"), 2)


class TestReportBareTranslitTagCollapse(unittest.TestCase):
    def test_word_form_tail_collapsed_to_tag(self):
        report = Report("TEST")
        report.W(
            "x.json:cards[0].content: 'PHILEŌ' matches Strong's transliteration "
            "for G5368 but the field has no real Hebrew/Greek character anywhere "
            "— likely discussing a word by its transliteration only, with the "
            "actual native-script word never given (verified against the "
            "Strong's dictionary, not just shape)"
        )
        output = capture(report.print, final=False)
        self.assertIn(
            "'PHILEŌ' matches Strong's transliteration for G5368 [bare-translit]",
            output,
        )
        self.assertNotIn("verified against the Strong's dictionary", output)

    def test_clause_form_tail_collapsed_to_tag(self):
        report = Report("TEST")
        report.W(
            "y.json:cards[1].content: '从上到下' (Ap' Anōthen Heōs Katō) has the "
            "shape of a bare Greek clause transliteration/respelling (3+ tokens) "
            "but the field has no real Greek character anywhere — likely "
            "discussing a whole clause by its transliteration only, with the "
            "actual Greek text never given (see gloss_format.json "
            "'Three-or-more-word phrase ... instead of a 1-or-2-word gloss')"
        )
        output = capture(report.print, final=False)
        self.assertIn(
            "'从上到下' (Ap' Anōthen Heōs Katō) has the shape of a bare Greek clause "
            "transliteration/respelling [bare-translit]",
            output,
        )
        self.assertNotIn("gloss_format.json", output)

    def test_unrelated_warning_text_left_intact(self):
        report = Report("TEST")
        report.W(
            "z.json:tags[5]: Latin text 'vs' in zh field — possible untranslated leftover"
        )
        output = capture(report.print, final=False)
        self.assertIn(
            "Latin text 'vs' in zh field — possible untranslated leftover", output
        )
        self.assertNotIn("[bare-translit]", output)


if __name__ == "__main__":
    unittest.main()
