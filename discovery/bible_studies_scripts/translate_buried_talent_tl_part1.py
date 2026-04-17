#!/usr/bin/env python3
"""
Translate buried_talent from English to Tagalog - Part 1: Resolution
"""
import json
import sys

# Add parent directory to path
sys.path.insert(0, '/home/runner/work/devocionales-json/devocionales-json/devocionales_scripts')
from verse_resolver import VerseResolver

DB_PATH = '/home/runner/work/devocionales-json/devocionales-json/bible_database/ADB_tl.SQLite3'
resolver = VerseResolver(DB_PATH)

# Resolve all verses
print("Resolving verses...")

key_verse = resolver.resolve("Matthew 25:26-28")
card3_verses = [resolver.resolve(r) for r in ["James 2:17", "Matthew 7:21-23", "1 John 4:18"]]
card6_verses = [resolver.resolve(r) for r in ["James 1:22", "Proverbs 29:25", "2 Timothy 1:7"]]
card7_verses = [resolver.resolve(r) for r in ["Proverbs 3:27", "Ecclesiastes 11:4", "2 Timothy 1:6"]]

resolver.close()

# Save resolved verses to JSON
result = {
    "key_verse": {"reference": key_verse[0], "text": key_verse[1]},
    "card3": [{"reference": v[0], "text": v[1]} for v in card3_verses],
    "card6": [{"reference": v[0], "text": v[1]} for v in card6_verses],
    "card7": [{"reference": v[0], "text": v[1]} for v in card7_verses]
}

with open('buried_talent_verses_tl.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=2)

print("✓ All verses resolved and saved")
