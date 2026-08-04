#!/usr/bin/env python3
"""
master_validator.py — Encounters pipeline entry point.

Runs validate_encounters.py, which owns the full phased pipeline (lint,
index, bible-versions SOT, encounter files, image URLs). This wrapper
exists as a stable, memorable entry point; all phase logic lives in
validate_encounters.py.

Run from encounters/encounters_scripts/ or anywhere.

Exit codes: 0 = all passed, 1 = errors found
"""

import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent


def run(script, args=None, label=""):
    cmd = [sys.executable, str(SCRIPTS_DIR / script)] + (args or [])
    result = subprocess.run(cmd, text=True, check=False)
    if result.returncode != 0:
        print(f"\n❌ {label or script} failed.")
        sys.exit(result.returncode)


print("=" * 30)
print("ENCOUNTERS VALIDATION")
print("=" * 30)
run("validate_encounters.py", label="Encounters validation")

print("\n✅ ALL ENCOUNTERS PASSED\n")
