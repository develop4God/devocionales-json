#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, '/home/runner/work/devocionales-json/devocionales-json/devocionales_scripts')
from verse_resolver import VerseResolver

DB_PATH = '/home/runner/work/devocionales-json/devocionales-json/bible_database/ADB_tl.SQLite3'

with VerseResolver(DB_PATH) as resolver:
    verses = [
        "John 2:19",
        "Mark 11:17",
        "Malachi 3:1-3",
        "Psalm 69:9"
    ]

    for v in verses:
        cita, texto, error = resolver.resolve(v)
        if error:
            print(f"ERROR {v}: {error}")
        else:
            print(f"{v} → {cita}")
            print(f"  {texto[:100]}...")
            print()
