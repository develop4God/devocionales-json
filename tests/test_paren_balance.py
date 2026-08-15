"""Tests for report-only parenthesis balance validation."""

import json
import tempfile
import unittest
from pathlib import Path

from shared_validation.tools.paren_balance import check_balance, check_json_file, main


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


if __name__ == "__main__":
    unittest.main()
