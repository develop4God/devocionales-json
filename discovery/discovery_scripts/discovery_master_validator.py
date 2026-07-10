#!/usr/bin/env python3
"""
discovery_master_validator.py — orchestrates all validation for the discovery
content type.
1. validate_discovery.py      — global translation/JSON/structure/index validation
2. validate_structure_bulk.py — schema drift check per study (EN as base)

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


# ── Phase 1: Global translation / JSON / index validation ────────────────────
print("=" * 30)
print("GLOBAL TRANSLATION/JSON VALIDATION")
print("=" * 30)
run("validate_discovery.py", label="Translation/JSON validation")

# ── Phase 2: Schema drift check per study ────────────────────────────────────
print("=" * 30)
print("BULK STRUCTURE VALIDATION FOR ALL STUDIES")
print("=" * 30)

base_files = sorted(EN_DIR.glob("*_en_*.json"))
if not base_files:
    print(f"❌ No English base files found in {EN_DIR}")
    sys.exit(1)

for base_file in base_files:
    print(f"\n--- {base_file.name} ---")
    run("validate_structure_bulk.py", [str(base_file)], label=base_file.name)

print("\n✅ All studies passed bulk structure validation.\n")
