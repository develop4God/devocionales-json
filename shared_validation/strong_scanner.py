r"""scanner.py — Single source of truth for scanning JSON corpus files.

Scans JSON files once and extracts all text fields with their positions.
Produces an immutable artifact used by all downstream stages.

Usage:
    from shared_validation.strong_scanner import scan_file, ScanResult

    result = scan_file('discovery/es/passed_from_death_es_001.json')
    for field in result.fields:
        print(f"{field.path}: {field.text[:50]}...")
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List, NamedTuple, Optional


class TextField(NamedTuple):
    """A text field found in a JSON file.
    
    Attributes:
        path: Dotted path to the field (e.g. "cards[0].content")
        text: The text content
        start: Character start position in the full file text
        end: Character end position in the full file text
    """
    path: str
    text: str
    start: int
    end: int


class ScanResult(NamedTuple):
    """Result of scanning a JSON file.
    
    Attributes:
        filepath: Path to the scanned file
        fields: List of TextField objects found in the file
        raw_text: The complete raw text of the file (for position tracking)
    """
    filepath: str
    fields: List[TextField]
    raw_text: str


def scan_file(filepath: str) -> ScanResult:
    r"""Scan a JSON file and extract all text fields with positions.
    
    This is the SINGLE SOURCE OF TRUTH for file scanning.
    All downstream stages should use this instead of re-scanning.
    
    Args:
        filepath: Path to a JSON corpus file
        
    Returns:
        ScanResult with all text fields and their positions

    Note: `start`/`end` on each TextField are raw-file character offsets
    (into `raw_text`), consistent with the TextField docstring above.
    They point at the *raw, still-escaped* JSON string literal — e.g. for
    a field containing a newline, the raw span includes the two
    characters `\` `n`, not one newline character. Escaped and decoded
    lengths diverge whenever a field contains `\n`, `\"`, `\\`, or a
    unicode escape, so `end - start` is NOT `len(field.text)` for such
    fields. Callers needing field-local offsets (matching `field.text`
    directly) must compute their own by re-scanning that field's decoded
    text — this scanner's contract is raw-file position only.
    """
    with open(filepath, encoding="utf-8") as f:
        raw_text = f.read()
    
    data = json.loads(raw_text)
    fields: List[TextField] = []
    
    # Locate each field's still-escaped JSON string literal in raw_text,
    # decode THAT literal (not compare raw bytes to the already-decoded
    # value), and confirm it matches the parsed value before recording it.
    # This is what correctly handles \n, \", \\, unicode escapes, etc.
    def _collect(obj, path_prefix: str = ""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                ctx_key = f"{path_prefix}.{k}" if path_prefix else k
                if isinstance(v, str):
                    _record_string_field(k, v, ctx_key)
                elif isinstance(v, (dict, list)):
                    _collect(v, ctx_key)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                _collect(item, f"{path_prefix}[{i}]")

    def _record_string_field(key: str, value: str, ctx_key: str) -> None:
        json_pattern = f'"{re.escape(key)}"\\s*:\\s*"'
        start_search = 0
        while True:
            match = re.search(json_pattern, raw_text[start_search:])
            if not match:
                break
            literal_start = start_search + match.end()
            # Decode the raw JSON string literal starting right after the
            # opening quote already consumed by json_pattern. scanstring
            # returns (decoded_value, index_after_closing_quote) — we
            # subtract 1 below so literal_end points at the quote itself,
            # i.e. the exact raw-file span of the string's content.
            try:
                decoded, quote_end = json.decoder.scanstring(raw_text, literal_start)
            except (ValueError, json.JSONDecodeError):
                start_search = literal_start
                continue
            # scanstring's returned index is AFTER the closing quote;
            # the content span itself ends one character earlier.
            literal_end = quote_end - 1
            if decoded == value:
                fields.append(TextField(
                    path=ctx_key,
                    text=value,
                    start=literal_start,
                    end=literal_end,
                ))
                return
            start_search = quote_end

    _collect(data)
    
    return ScanResult(
        filepath=filepath,
        fields=fields,
        raw_text=raw_text
    )


def get_field_text(scan_result: ScanResult, field_path: str) -> Optional[str]:
    """Get the text for a specific field from a scan result.
    
    Args:
        scan_result: Result from scan_file()
        field_path: Dotted path to the field
        
    Returns:
        The text content, or None if not found
    """
    for field in scan_result.fields:
        if field.path == field_path:
            return field.text
    return None
