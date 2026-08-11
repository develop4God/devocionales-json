"""Tests for report-only parenthesis balance validation."""

import json
import tempfile
import unittest
from pathlib import Path

from shared_validation.paren_balance import check_balance, check_json_file, main
from shared_validation.strong_balance_fixer import preview_balance_fixes


class ParenBalanceTests(unittest.TestCase):
    def test_reports_unmatched_open_and_close_with_positions(self):
        self.assertEqual(
            check_balance(")a("),
            [
                (0, ")", "missing_open"),
                (2, "(", "missing_close"),
            ],
        )

    def test_json_scan_reports_each_string_field_without_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "content.json"
            original = {"cards": [{"content": "bad ("}, {"title": "fine"}]}
            path.write_text(json.dumps(original), encoding="utf-8")

            findings = check_json_file(path)

            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0].field_path, "cards[0].content")
            self.assertEqual(findings[0].issue.issue_type, "missing_close")
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), original)

    def test_cli_returns_failure_for_an_unbalanced_json_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "content.json"
            path.write_text('{"text": "bad )"}', encoding="utf-8")

            self.assertEqual(main([str(path)]), 1)

    def test_strong_balance_fixer_supports_the_four_repair_patterns(self):
        cases = {
            "(G1234))": ("double_close", "(G1234))", "(G1234)"),
            "G1234)": ("missing_open", "G1234)", "(G1234)"),
            "((G1234)": ("double_open", "((G1234)", "(G1234)"),
            "(G1234": ("missing_close", "(G1234", "(G1234)"),
        }
        with tempfile.TemporaryDirectory() as directory:
            for index, (text, expected) in enumerate(cases.items()):
                path = Path(directory) / f"case-{index}.json"
                path.write_text(json.dumps({"text": text}), encoding="utf-8")

                actions = preview_balance_fixes(str(path))

                self.assertEqual(len(actions), 1)
                self.assertEqual(
                    (actions[0].issue_type, actions[0].old, actions[0].new), expected
                )


if __name__ == "__main__":
    unittest.main()
