#!/usr/bin/env python3
"""
Final Duplicate ID Validator

This script checks all devotional files for duplicate IDs across all files.
"""

import json
import os
from collections import defaultdict

# Constants
MAX_DUPLICATES_TO_DISPLAY = 20  # Maximum number of duplicates to show in output


def validate_all_files():
    """Check all files for duplicate IDs globally"""
    # Use relative path from script location or environment variable
    base_path = os.environ.get(
        "DEVOTIONAL_PATH", os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )

    all_ids = defaultdict(list)  # id -> list of (filename, date)

    # All files to check
    all_files = [
        # Base Spanish/RVR1960 (previously missing — caused 66 duplicates to go undetected)
        "Devocional_year_2025.json",
        "Devocional_year_2026.json",
        # German (previously missing)
        "Devocional_year_2025_de_LU17.json",
        "Devocional_year_2025_de_SCH2000.json",
        "Devocional_year_2026_de_LU17.json",
        "Devocional_year_2026_de_SCH2000.json",
        # English
        "Devocional_year_2025_en_KJV.json",
        "Devocional_year_2025_en_NIV.json",
        "Devocional_year_2026_en_KJV.json",
        "Devocional_year_2026_en_NIV.json",
        # Spanish NVI
        "Devocional_year_2025_es_NVI.json",
        "Devocional_year_2026_es_NVI.json",
        # French
        "Devocional_year_2025_fr_LSG1910.json",
        "Devocional_year_2025_fr_TOB.json",
        "Devocional_year_2026_fr_LSG1910.json",
        "Devocional_year_2026_fr_TOB.json",
        # Hindi (previously missing)
        "Devocional_year_2025_hi_HERV.json",
        "Devocional_year_2025_hi_HIOV.json",
        "Devocional_year_2026_hi_HERV.json",
        "Devocional_year_2026_hi_HIOV.json",
        # Japanese
        "Devocional_year_2025_ja_リビングバイブル.json",
        "Devocional_year_2025_ja_新改訳2003.json",
        "Devocional_year_2026_ja_リビングバイブル.json",
        "Devocional_year_2026_ja_新改訳2003.json",
        # Portuguese
        "Devocional_year_2025_pt_ARC.json",
        "Devocional_year_2025_pt_NVI.json",
        "Devocional_year_2026_pt_ARC.json",
        "Devocional_year_2026_pt_NVI.json",
        # Chinese
        "Devocional_year_2025_zh_和合本1919.json",
        "Devocional_year_2025_zh_新译本.json",
        "Devocional_year_2026_zh_和合本1919.json",
        "Devocional_year_2026_zh_新译本.json",
    ]

    print("=" * 80)
    print("FINAL DUPLICATE ID VALIDATION")
    print("=" * 80)
    print()

    total_entries = 0

    for filename in all_files:
        filepath = os.path.join(base_path, filename)
        if not os.path.exists(filepath):
            print(f"⚠️  File not found: {filename}")
            continue

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            file_count = 0
            for lang_data in data.get("data", {}).values():
                for entries in lang_data.values():
                    for entry in entries:
                        entry_id = entry.get("id", "")
                        date = entry.get("date", "")
                        all_ids[entry_id].append((filename, date))
                        file_count += 1
                        total_entries += 1

            print(f"✓ {filename}: {file_count} entries")

        except Exception as e:  # noqa: BLE001
            print(f"❌ Error reading {filename}: {e!s}")

    print()
    print("=" * 80)
    print("VALIDATION RESULTS")
    print("=" * 80)
    print(f"Total entries checked: {total_entries}")
    print()

    # Check for duplicates
    duplicates = {
        id_val: locations for id_val, locations in all_ids.items() if len(locations) > 1
    }

    if duplicates:
        print(f"⚠️  FOUND {len(duplicates)} DUPLICATE IDs:")
        print()
        for id_val, locations in sorted(duplicates.items())[
            :MAX_DUPLICATES_TO_DISPLAY
        ]:  # Show limited number
            print(f"ID: {id_val}")
            for filename, date in locations:
                print(f"  - {filename} (date: {date})")
            print()

        if len(duplicates) > MAX_DUPLICATES_TO_DISPLAY:
            print(
                f"... and {len(duplicates) - MAX_DUPLICATES_TO_DISPLAY} more duplicates"
            )

        return 1
    else:
        print("✅ NO DUPLICATE IDs FOUND!")
        print()
        print("All devotional files have unique IDs. ✨")
        return 0


if __name__ == "__main__":
    exit(validate_all_files())
