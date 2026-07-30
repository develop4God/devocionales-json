"""scanner.py — Single source of truth for scanning JSON corpus files.

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
    """Scan a JSON file and extract all text fields with positions.
    
    This is the SINGLE SOURCE OF TRUTH for file scanning.
    All downstream stages should use this instead of re-scanning.
    
    Args:
        filepath: Path to a JSON corpus file
        
    Returns:
        ScanResult with all text fields and their positions
    """
    with open(filepath, encoding="utf-8") as f:
        raw_text = f.read()
    
    data = json.loads(raw_text)
    fields: List[TextField] = []
    
    # Track position in raw_text as we encounter fields
    # We'll search for each field value in the raw text to get positions
    def _collect(obj, path_prefix: str = ""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                ctx_key = f"{path_prefix}.{k}" if path_prefix else k
                if isinstance(v, str):
                    # Find this string in the raw text
                    # Search for the value with its JSON key
                    json_pattern = f'"{re.escape(k)}"\\s*:\\s*"'
                    start_search = 0
                    while True:
                        match = re.search(json_pattern, raw_text[start_search:])
                        if not match:
                            break
                        abs_pos = start_search + match.end()
                        # Verify the text matches
                        if raw_text[abs_pos:abs_pos + len(v)] == v:
                            fields.append(TextField(
                                path=ctx_key,
                                text=v,
                                start=abs_pos,
                                end=abs_pos + len(v)
                            ))
                            break
                        start_search = abs_pos
                elif isinstance(v, (dict, list)):
                    _collect(v, ctx_key)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                _collect(item, f"{path_prefix}[{i}]")
    
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
