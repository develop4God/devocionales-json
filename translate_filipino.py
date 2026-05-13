#!/usr/bin/env python3
"""
Filipino Translation Helper for Discovery Bible Studies
Uses verse_resolver.py for all verse lookups
"""

import json
import sys
import os

# Add the scripts directory to path
sys.path.insert(0, '/home/runner/work/devocionales-json/devocionales-json/devocionales_scripts')
from verse_resolver import VerseResolver

# Filipino Bible database
DB_PATH = "/home/runner/work/devocionales-json/devocionales-json/bible_database/MBB05_fil.SQLite3"

def resolve_verse(reference):
    """Resolve a single verse reference to Filipino"""
    with VerseResolver(DB_PATH) as resolver:
        cita, texto, error = resolver.resolve(reference)
        return cita, texto, error

def test_verses():
    """Test verse resolver with sample verses"""
    test_refs = [
        "Mark 15:34",
        "Mark 15:38",
        "Matthew 27:52-53",
        "John 20:22",
        "Luke 24:30-31"
    ]

    print("Testing verse resolution:")
    print("=" * 80)
    for ref in test_refs:
        cita, texto, error = resolve_verse(ref)
        print(f"\nEN: {ref}")
        if error:
            print(f"ERROR: {error}")
        else:
            print(f"FIL: {cita}")
            print(f"Text: {texto[:100]}...")
    print("=" * 80)

if __name__ == "__main__":
    test_verses()
