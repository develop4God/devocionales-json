#!/usr/bin/env python3
import sys
sys.path.insert(0, '/home/runner/work/devocionales-json/devocionales-json/devocionales_scripts')
from verse_resolver import VerseResolver
import json

db_path = '/home/runner/work/devocionales-json/devocionales-json/bible_database/ADB_tl.SQLite3'

verses_to_lookup = [
    "John 11:33",
    "John 11:17",
    "John 11:35",
    "John 11:38",
    "John 11:43",
    "John 11:44",
    "John 12:27",
    "John 13:21"
]

results = {}

with VerseResolver(db_path) as resolver:
    for verse_ref in verses_to_lookup:
        citation, text, error = resolver.resolve(verse_ref)
        results[verse_ref] = {
            "citation": citation,
            "text": text,
            "error": error
        }

print(json.dumps(results, indent=2, ensure_ascii=False))
