#!/usr/bin/env python3
"""
Update index.json with Tagalog entries for 6 new Bible studies
"""

import json

# Studies to update with their titles and subtitles from the translated files
studies_to_update = {
    'jesus_troubled_himself_001': {
        'file': 'jesus_troubled_himself_tl_001.json',
        'reading_minutes': 8
    },
    'passed_from_death_001': {
        'file': 'passed_from_death_tl_001.json',
        'reading_minutes': 10
    },
    'transfiguration_001': {
        'file': 'transfiguration_tl_001.json',
        'reading_minutes': 9
    },
    'buried_talent_001': {
        'file': 'buried_talent_tl_001.json',
        'reading_minutes': 10
    },
    'triumphal_entry_001': {
        'file': 'triumphal_entry_tl_001.json',
        'reading_minutes': 7
    },
    'gethsemane_agony_001': {
        'file': 'gethsemane_agony_tl_001.json',
        'reading_minutes': 9
    }
}

# Load the index
with open('discovery/index.json', 'r', encoding='utf-8') as f:
    index_data = json.load(f)

# Update each study
for study in index_data['studies']:
    study_id = study['id']

    if study_id in studies_to_update:
        info = studies_to_update[study_id]

        # Load the translated file to get title and subtitle
        tl_file_path = f"discovery/tl/{info['file']}"
        with open(tl_file_path, 'r', encoding='utf-8') as f:
            tl_data = json.load(f)

        # Add tl to files
        study['files']['tl'] = info['file']

        # Add tl title
        study['titles']['tl'] = tl_data['title']

        # Add tl subtitle
        study['subtitles']['tl'] = tl_data['subtitle']

        # Add tl reading minutes
        study['estimated_reading_minutes']['tl'] = info['reading_minutes']

        print(f"✓ Updated {study_id}")
        print(f"  Title: {tl_data['title']}")
        print(f"  Subtitle: {tl_data['subtitle']}")
        print(f"  Reading time: {info['reading_minutes']} min")
        print()

# Save the updated index
with open('discovery/index.json', 'w', encoding='utf-8') as f:
    json.dump(index_data, f, ensure_ascii=False, indent=2)

print("✅ Index.json updated successfully!")
print(f"\nTotal studies updated: {len(studies_to_update)}")
