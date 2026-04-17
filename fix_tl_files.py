#!/usr/bin/env python3
"""
Fix version names and English references in Tagalog translations
"""

import json
import os

# List of Tagalog files to fix
tl_files = [
    'discovery/tl/good_shepherd_tl_001.json',
    'discovery/tl/temple_cleansing_tl_001.json',
    'discovery/tl/woman_at_well_tl_001.json',
    'discovery/tl/natanael_fig_tree_tl_001.json',
    'discovery/tl/cana_wedding_tl_001.json',
    'discovery/tl/i_am_before_abraham_tl_001.json'
]

# Reference mapping from English to Tagalog
reference_map = {
    'John': 'Juan',
    'Genesis': 'Genesis',
    'Ezekiel': 'Ezekiel',
    'Isaiah': 'Isaias'
}

def translate_reference(ref):
    """Translate English book names to Tagalog"""
    for eng, tl in reference_map.items():
        if ref.startswith(eng):
            return ref.replace(eng, tl, 1)
    return ref

def fix_file(filepath):
    """Fix version name and references in a file"""
    print(f"\nFixing {os.path.basename(filepath)}...")

    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    changes_made = []

    # Fix version name
    if data.get('version') == 'Ang Dating Biblia':
        data['version'] = 'ADB'
        changes_made.append('Changed version to ADB')

    # Fix references in cards
    for i, card in enumerate(data.get('cards', [])):
        # Fix greek_words references
        for j, greek_word in enumerate(card.get('greek_words', [])):
            if 'reference' in greek_word:
                old_ref = greek_word['reference']
                new_ref = translate_reference(old_ref)
                if old_ref != new_ref:
                    greek_word['reference'] = new_ref
                    changes_made.append(f"Card {i+1} greek_word {j+1}: {old_ref} → {new_ref}")

        # Fix scripture_anchor
        if 'scripture_anchor' in card:
            if 'reference' in card['scripture_anchor']:
                old_ref = card['scripture_anchor']['reference']
                new_ref = translate_reference(old_ref)
                if old_ref != new_ref:
                    card['scripture_anchor']['reference'] = new_ref
                    changes_made.append(f"Card {i+1} scripture_anchor: {old_ref} → {new_ref}")

        # Fix scripture_connections
        for j, conn in enumerate(card.get('scripture_connections', [])):
            if 'reference' in conn:
                old_ref = conn['reference']
                new_ref = translate_reference(old_ref)
                if old_ref != new_ref:
                    conn['reference'] = new_ref
                    changes_made.append(f"Card {i+1} scripture_connection {j+1}: {old_ref} → {new_ref}")

        # Fix timeline entries
        for j, entry in enumerate(card.get('timeline', [])):
            if 'reference' in entry:
                old_ref = entry['reference']
                new_ref = translate_reference(old_ref)
                if old_ref != new_ref:
                    entry['reference'] = new_ref
                    changes_made.append(f"Card {i+1} timeline {j+1}: {old_ref} → {new_ref}")

    # Save the fixed file
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    if changes_made:
        for change in changes_made:
            print(f"  ✓ {change}")
    else:
        print("  No changes needed")

# Fix all files
for filepath in tl_files:
    fix_file(filepath)

print("\n✅ All files fixed!")
