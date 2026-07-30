"""paren_balance.py — Plain, agnostic parenthesis balance checker.

Not aware of Strong codes, JSON structure, or any other pattern.
Single pass over text: does every '(' have a matching ')', properly
nested, by the end of the text?

Usage:
    from shared_validation.paren_balance import check_balance

    issues = check_balance(text)
    if not issues:
        print("balanced")
"""

from __future__ import annotations

from typing import List, NamedTuple


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
