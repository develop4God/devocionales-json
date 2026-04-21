#!/usr/bin/env python3
"""
Fix prayer endings in Tagalog devotionals that end with 'nawa' instead of 'amen'.
Appends ' Amen.' to prayers ending with 'siya nawa.' to meet schema requirements.
"""
import json
import sys

def fix_prayer_endings(file_path: str, dry_run: bool = False):
    """Fix prayers ending with 'nawa' by appending 'Amen.'"""

    # Load the file
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    fixed_count = 0

    # Process each entry
    for lang, dates in data['data'].items():
        for date_key, entries in dates.items():
            for entry in entries:
                oracion = entry['oracion']

                # Check if it ends with 'nawa' (after stripping trailing punctuation)
                stripped = oracion.strip().rstrip('.!,;')
                if stripped.endswith('nawa'):
                    old_oracion = oracion
                    # Append ' Amen.' to the prayer
                    new_oracion = oracion.rstrip() + ' Amen.'

                    if not dry_run:
                        entry['oracion'] = new_oracion

                    print(f"✓ Fixed {entry['id']} ({date_key})")
                    if dry_run:
                        print(f"  Old ending: ...{old_oracion[-60:]}")
                        print(f"  New ending: ...{new_oracion[-60:]}\n")
                    fixed_count += 1

    if not dry_run and fixed_count > 0:
        # Save the file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n✅ Saved {fixed_count} fixes to {file_path}")
    elif dry_run:
        print(f"\n🔍 Dry run: {fixed_count} entries would be fixed")
    else:
        print("✅ No entries needed fixing")

    return fixed_count

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fix_nawa_endings.py <path_to_devotional_json> [--dry-run]")
        sys.exit(1)

    file_path = sys.argv[1]
    dry_run = '--dry-run' in sys.argv

    fixed = fix_prayer_endings(file_path, dry_run)
    sys.exit(0 if fixed >= 0 else 1)
