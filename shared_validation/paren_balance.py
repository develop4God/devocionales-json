"""paren_balance.py — Report-only parenthesis balance validation.

Not aware of Strong codes, JSON structure, or any other pattern.
Single pass over text: does every '(' have a matching ')', properly
nested, by the end of the text?

Usage:
    from shared_validation.paren_balance import check_balance

    issues = check_balance(text)
    if not issues:
        print("balanced")

    # Validate every string value in JSON content files. This never edits
    # content; it returns findings for the caller to report and fail on.
    findings = check_json_file("discovery/en/example.json")
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable, List, NamedTuple


class ParenIssue(NamedTuple):
    """A single unmatched parenthesis.

    Attributes:
        position:   Character offset of the unmatched paren.
        char:       '(' or ')'.
        issue_type: "missing_open"  — a ')' with nothing open to match
                    "missing_close" — a '(' never closed by end of text
    """
    position: int
    char: str
    issue_type: str


class ParenFinding(NamedTuple):
    """An unmatched parenthesis located in one JSON string field."""

    filepath: Path
    field_path: str
    issue: ParenIssue


def check_balance(text: str) -> List[ParenIssue]:
    """Return a list of unmatched parens in text. Empty list = balanced.

    Agnostic to content — only counts '(' and ')' characters in order.
    """
    issues: List[ParenIssue] = []
    open_stack: List[int] = []  # positions of unmatched '(' seen so far

    for i, ch in enumerate(text):
        if ch == '(':
            open_stack.append(i)
        elif ch == ')':
            if open_stack:
                open_stack.pop()  # matched
            else:
                issues.append(ParenIssue(position=i, char=')', issue_type="missing_open"))

    for pos in open_stack:
        issues.append(ParenIssue(position=pos, char='(', issue_type="missing_close"))

    return issues


def is_balanced(text: str) -> bool:
    """True if text has no unmatched parens."""
    return len(check_balance(text)) == 0


def check_json_file(filepath: str | Path) -> List[ParenFinding]:
    """Return parenthesis findings for every string value in a JSON file.

    This is deliberately validation-only: it loads and inspects content but
    never changes the file. ``field_path`` uses familiar dotted/list-indexed
    JSON paths, such as ``cards[2].content``.
    """
    path = Path(filepath)
    with path.open(encoding="utf-8") as file:
        data = json.load(file)

    findings: List[ParenFinding] = []

    def walk(value: object, field_path: str = "") -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                child_path = f"{field_path}.{key}" if field_path else key
                walk(child, child_path)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, f"{field_path}[{index}]")
        elif isinstance(value, str):
            findings.extend(
                ParenFinding(path, field_path, issue)
                for issue in check_balance(value)
            )

    walk(data)
    return findings


def iter_json_files(paths: Iterable[str | Path]) -> Iterable[Path]:
    """Yield JSON files from explicit files or recursively from directories."""
    for raw_path in paths:
        path = Path(raw_path)
        if path.is_dir():
            yield from sorted(path.rglob("*.json"))
        elif path.suffix == ".json":
            yield path


def main(argv: list[str] | None = None) -> int:
    """Run the report-only checker as a CI-friendly command-line tool."""
    parser = argparse.ArgumentParser(description="Report unmatched parentheses in JSON")
    parser.add_argument("paths", nargs="+", help="JSON files or directories to validate")
    args = parser.parse_args(argv)

    files_checked = 0
    findings = 0
    for path in iter_json_files(args.paths):
        files_checked += 1
        try:
            file_findings = check_json_file(path)
        except (OSError, json.JSONDecodeError) as error:
            findings += 1
            print(f"ERROR: {path}: unable to check parentheses: {error}")
            continue

        for finding in file_findings:
            issue = finding.issue
            expected = "opening '('" if issue.issue_type == "missing_open" else "closing ')'"
            print(
                f"ERROR: {finding.filepath}:{finding.field_path}:"
                f"{issue.position}: unmatched {issue.char!r}; missing {expected}"
            )
        findings += len(file_findings)

    if findings:
        print(f"Parenthesis balance failed: {findings} issue(s) in {files_checked} JSON file(s).")
        return 1

    print(f"Parenthesis balance passed: {files_checked} JSON file(s) checked.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
