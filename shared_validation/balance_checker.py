"""balance_checker.py — Post-fix validation helper.

After applying Strong code fixes, scan the modified text for balanced
parentheses around Strong codes. Flags any occurrence of:
  - ((GXXXX)  — double open paren
  - (GXXXX))  — double close paren
  - (GXXXX    — missing close paren
  - GXXXX)    — missing open paren

Usage:
    from shared_validation.balance_checker import check_balance, BalanceIssue

    issues = check_balance(text)
    for issue in issues:
        print(f"{issue.code}: {issue.match} at pos {issue.start}")
"""

from __future__ import annotations

import re
from typing import List, NamedTuple


# ---------------------------------------------------------------------------
# Named tuple for a balance issue
# ---------------------------------------------------------------------------

class BalanceIssue(NamedTuple):
    """A parenthesis balance problem found in text.

    Attributes:
        code:         The Strong code, e.g. "G3327".
        match:        The exact matched substring with the problem.
        start:        Character offset where the problem begins.
        end:          Character offset where the problem ends.
        context:      Surrounding text for human review.
        issue_type:   Description of the problem:
                      - "double_open":  `((GXXXX)`
                      - "double_close": `(GXXXX))`
                      - "missing_open":  `GXXXX)`
                      - "missing_close": `(GXXXX`
    """
    code: str
    match: str
    start: int
    end: int
    context: str
    issue_type: str


# ---------------------------------------------------------------------------
# Regex to find Strong codes with potential balance issues
# ---------------------------------------------------------------------------

# Matches any G/H + digits with surrounding parens (possibly unbalanced)
_BALANCE_RE = re.compile(
    r"\(*\s*(?:Strong\s+)?([GHgh])(\d{1,5})\s*\)*",
    re.IGNORECASE,
)


def check_balance(text: str, context_window: int = 30) -> List[BalanceIssue]:
    """Scan text for unbalanced parentheses around Strong codes.

    Args:
        text: The prose text to check.
        context_window: Characters of surrounding context (default 30).

    Returns:
        List of BalanceIssue for any problems found.
    """
    issues: List[BalanceIssue] = []
    for m in _BALANCE_RE.finditer(text):
        full = m.group(0)
        code = f"{m.group(1).upper()}{m.group(2)}"
        start = m.start()
        end = m.end()

        # Count parens before and after the code
        before = full[:full.index(code)] if code in full else full
        after = full[full.index(code) + len(code):] if code in full else ""

        open_before = before.count('(')
        close_before = before.count(')')
        open_after = after.count('(')
        close_after = after.count(')')

        total_open = open_before + open_after
        total_close = close_before + close_after

        issue_type = None

        # Check for double open: ((GXXXX)
        if open_before >= 2 and close_after >= 1:
            issue_type = "double_open"

        # Check for double close: (GXXXX))
        elif open_before >= 1 and close_after >= 2:
            issue_type = "double_close"

        # Check for missing open: GXXXX)
        elif open_before == 0 and close_after >= 1:
            issue_type = "missing_open"

        # Check for missing close: (GXXXX
        elif open_before >= 1 and close_after == 0:
            issue_type = "missing_close"

        if issue_type:
            ctx_start = max(0, start - context_window)
            ctx_end = min(len(text), end + context_window)
            context = text[ctx_start:ctx_end].replace("\n", " ")
            issues.append(BalanceIssue(
                code=code,
                match=full.strip(),
                start=start,
                end=end,
                context=context,
                issue_type=issue_type,
            ))

    return issues


def check_file_balance(filepath: str, text_fields: List[str] = None) -> List[BalanceIssue]:
    """Convenience: load a JSON file and check balance across text fields.

    Args:
        filepath: Path to a JSON corpus file.
        text_fields: List of field names to check (default: content, reflection, narrative, title, question, answer, note).

    Returns:
        List of BalanceIssue across all specified text fields.
    """
    import json

    if text_fields is None:
        text_fields = ["content", "reflection", "narrative", "title", "question", "answer", "note"]

    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)

    issues: List[BalanceIssue] = []

    def _collect(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, str) and k in text_fields:
                    issues.extend(check_balance(v))
                elif isinstance(v, (dict, list)):
                    _collect(v)
        elif isinstance(obj, list):
            for item in obj:
                _collect(item)

    _collect(data)
    return issues


def summarize_balance_issues(issues: List[BalanceIssue]) -> dict:
    """Produce a summary dict from a list of BalanceIssue.

    Returns:
        dict with keys:
            - total: total number of issues
            - by_type: dict of {issue_type: count}
            - by_code: dict of {code: count}
            - issues: list of issue dicts with code, match, context, type
    """
    from collections import Counter

    total = len(issues)
    by_type = dict(Counter(i.issue_type for i in issues))
    by_code = dict(Counter(i.code for i in issues))
    issue_list = [
        {
            "code": i.code,
            "match": i.match,
            "context": i.context,
            "type": i.issue_type,
        }
        for i in issues
    ]

    return {
        "total": total,
        "by_type": by_type,
        "by_code": by_code,
        "issues": issue_list,
    }