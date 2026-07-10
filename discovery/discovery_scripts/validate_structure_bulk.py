import os
import json
import glob
import sys
from collections import deque

def get_structure(obj):
    """Recursively get the structure of a JSON object as nested keys."""
    if isinstance(obj, dict):
        return {k: get_structure(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [get_structure(obj[0])] if obj else []
    else:
        return type(obj).__name__

def compare_structures(base_struct, other_struct, path=""):
    """Compare two structures recursively and return differences."""
    diffs = []
    if isinstance(base_struct, dict) and isinstance(other_struct, dict):
        base_keys = set(base_struct.keys())
        other_keys = set(other_struct.keys())
        missing = base_keys - other_keys
        extra = other_keys - base_keys
        for m in missing:
            diffs.append(f"Missing key '{m}' at {path}")
        for e in extra:
            diffs.append(f"Extra key '{e}' at {path}")
        for k in base_keys & other_keys:
            diffs.extend(compare_structures(base_struct[k], other_struct[k], path + f"/{k}"))
    elif isinstance(base_struct, list) and isinstance(other_struct, list):
        if base_struct and other_struct:
            diffs.extend(compare_structures(base_struct[0], other_struct[0], path + "[0]"))
        elif base_struct and not other_struct:
            diffs.append(f"Missing list at {path}")
        elif not base_struct and other_struct:
            diffs.append(f"Extra list at {path}")
    else:
        if base_struct != other_struct:
            diffs.append(f"Type mismatch at {path}: {base_struct} vs {other_struct}")
    return diffs

def find_related_files(base_file):
    """Find all files with the same study prefix as the base file (excluding language)."""
    base_name = os.path.basename(base_file)
    if "_" not in base_name:
        return []
    prefix = "_".join(base_name.split("_")[:-2])
    pattern = f"*{prefix}_*_*.json"
    search_dir = os.path.dirname(base_file)
    # Search in sibling language folders
    parent_dir = os.path.dirname(search_dir)
    files = []
    for lang_dir in os.listdir(parent_dir):
        lang_path = os.path.join(parent_dir, lang_dir)
        if os.path.isdir(lang_path):
            files.extend(glob.glob(os.path.join(lang_path, pattern)))
    return files

def main(base_file):
    try:
        with open(base_file, 'r', encoding='utf-8') as f:
            base_json = json.load(f)
    except Exception as e:
        print(f"Error loading base file: {e}")
        return
    base_struct = get_structure(base_json)
    related_files = find_related_files(base_file)
    print(f"Base file: {base_file}")
    print(f"Found {len(related_files)} related files.")
    for file in related_files:
        if file == base_file:
            continue
        try:
            with open(file, 'r', encoding='utf-8') as f:
                other_json = json.load(f)
        except Exception as e:
            print(f"Error loading {file}: {e}")
            continue
        other_struct = get_structure(other_json)
        diffs = compare_structures(base_struct, other_struct)
        if diffs:
            print(f"\nDifferences in {file}:")
            for d in diffs:
                print(f"  - {d}")
        else:
            print(f"\n{file} matches structure.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validate_structure_bulk.py <base_file.json>")
        sys.exit(1)
    main(sys.argv[1])
