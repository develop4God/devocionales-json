#!/usr/bin/env python3
"""
discovery_master_validator.py — orchestrates all validation for the discovery
content type.
1. validate_discovery.py — global translation/JSON/structure/index validation

Exit codes: 0 = all passed, 1 = errors found
"""

import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent


def run(script, args=None, label=''):
    """Run a validator script. Exit with its code if it fails."""
    cmd = [sys.executable, str(SCRIPTS_DIR / script)] + (args or [])
    result = subprocess.run(cmd, text=True)
    if result.returncode != 0:
        lbl = label or script
        print(f"\n❌ {lbl} failed.")
        sys.exit(result.returncode)


print("=" * 30)
print("GLOBAL TRANSLATION/JSON VALIDATION")
print("=" * 30)
run("validate_discovery.py", label="Translation/JSON validation")
