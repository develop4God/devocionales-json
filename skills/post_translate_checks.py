#!/usr/bin/env python3
"""
post_translate_checks.py

Mechanical post-translation checks, driven by skills/language_notes/{lang}.json.
Runs the checkable subset of each language's rules (forbidden patterns like ZH's
您) against a delivered file's string values — catching in milliseconds what would
otherwise require an LLM critic pass to notice.

Greek/Hebrew Latin-transliteration checking is NOT duplicated here — it already
exists, correctly implemented and wired into both master validators, at
shared_validation/text_checks.py::check_greek_hebrew_transliteration (run via
validate_encounters.py / validate_discovery.py / validate_pair.py). Run those for
that check; this script only covers what they don't.

This does NOT replace the native-speaker critic review (register/grammar judgment
calls like the HI ergative exception or JA keigo aren't mechanically checkable — see
each language's .md note for those). It only covers what a script can verify for real.

Usage:
    python3 skills/post_translate_checks.py path/to/{content_id}_{lang}_001.json

Exit code 0 = no violations found. Exit code 1 = violations found (printed to stdout).
"""

import json
import re
import sys
from pathlib import Path

SKILLS_DIR = Path(__file__).parent
LANGUAGE_NOTES_DIR = SKILLS_DIR / "language_notes"


def load_language_note(lang: str) -> dict | None:
    path = LANGUAGE_NOTES_DIR / f"{lang}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def iter_string_values(obj, path=""):
    """Yield (json_path, string_value) for every string value in a nested JSON structure."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from iter_string_values(v, f"{path}.{k}" if path else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from iter_string_values(v, f"{path}[{i}]")
    elif isinstance(obj, str):
        yield path, obj


def check_forbidden_patterns(data: dict, rules: list[dict]) -> list[str]:
    violations = []
    for json_path, value in iter_string_values(data):
        for rule in rules:
            pattern = rule["pattern"]
            if re.search(pattern, value):
                hint = f" -> use {rule['replacement']!r}" if rule.get("replacement") else ""
                violations.append(
                    f"  [{json_path}] matched forbidden pattern {pattern!r}: "
                    f"{rule['reason']}{hint}\n"
                    f"    value: {value[:80]!r}"
                )
    return violations


def run_checks(file_path: str, lang: str) -> list[str]:
    data = json.loads(Path(file_path).read_text(encoding="utf-8"))
    violations = []

    note = load_language_note(lang)
    if note and note.get("forbidden_patterns"):
        violations += check_forbidden_patterns(data, note["forbidden_patterns"])

    return violations


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} path/to/{{content_id}}_{{lang}}_001.json", file=sys.stderr)
        sys.exit(2)

    file_path = sys.argv[1]
    stem = Path(file_path).stem  # e.g. "zacchaeus_zh_001"
    parts = stem.split("_")
    if len(parts) < 2:
        print(f"Cannot infer language code from filename: {file_path}", file=sys.stderr)
        sys.exit(2)
    lang = parts[-2]  # second-to-last segment, before the trailing "001"

    violations = run_checks(file_path, lang)

    if violations:
        print(f"FAIL: {len(violations)} mechanical rule violation(s) in {file_path}\n")
        print("\n".join(violations))
        sys.exit(1)

    print(f"OK: no mechanical rule violations in {file_path} (lang={lang})")
    sys.exit(0)


if __name__ == "__main__":
    main()
