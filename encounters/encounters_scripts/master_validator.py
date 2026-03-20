#!/usr/bin/env python3
"""
Master validator: orchestrates all validation for the entire database.
1. validate_translations.py  — discovery studies: index + bulk translation
2. validate_structure_bulk.py — discovery studies: schema drift per study
3. validate_encounters.py    — encounters: index + file validation

Exit codes: 0 = all passed, 1 = errors found (stops at first failure)
"""

import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent
EN_DIR = SCRIPTS_DIR.parent / 'en'


def run(script, args=None, label=''):
    """Run a validator script. Exit with its code if it fails."""
    cmd = [sys.executable, str(SCRIPTS_DIR / script)] + (args or [])
    result = subprocess.run(cmd, text=True)
    if result.returncode != 0:
        lbl = label or script
        print(f"\n❌ {lbl} failed.")
        sys.exit(result.returncode)


# ── Phase 1: Discovery studies — translation/JSON/index ──────────────────────
print("=" * 30)
print("PHASE 1: DISCOVERY STUDIES VALIDATION")
print("=" * 30)
run("validate_translations.py", label="Discovery translation/JSON validation")

# ── Phase 2: Discovery studies — schema drift ────────────────────────────────
print("=" * 30)
print("PHASE 2: DISCOVERY BULK STRUCTURE VALIDATION")
print("=" * 30)

base_files = sorted(EN_DIR.glob("*_en_*.json"))
if not base_files:
    print(f"❌ No English base files found in {EN_DIR}")
    sys.exit(1)

for base_file in base_files:
    print(f"\n--- {base_file.name} ---")
    run("validate_structure_bulk.py", [str(base_file)], label=base_file.name)

print("\n✅ All discovery studies passed bulk structure validation.\n")

# ── Phase 3: Encounters ───────────────────────────────────────────────────────
print("=" * 30)
print("PHASE 3: ENCOUNTERS VALIDATION")
print("=" * 30)
run("validate_encounters.py", label="Encounters validation")

print("\n✅ ALL PHASES PASSED\n")
