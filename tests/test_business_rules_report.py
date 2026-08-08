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

from shared_validation.report import Report
from tests.golden_utils import capture


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
