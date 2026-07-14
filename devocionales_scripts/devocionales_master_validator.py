#!/usr/bin/env python3
"""
devocionales_master_validator.py — Devocionales corpus pipeline entry point.

Runs validate_devocionales_corpus.py, which owns the full phased pipeline
(lint, index, Bible-versions SOT, corpus files). This wrapper exists as a
stable, memorable entry point; all phase logic lives in
validate_devocionales_corpus.py.

Run from devocionales_scripts/ or anywhere.

Exit codes: 0 = all passed, 1 = errors found
"""

import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent


def run(script, args=None, label=''):
    cmd = [sys.executable, str(SCRIPTS_DIR / script)] + (args or [])
    result = subprocess.run(cmd, text=True)
    if result.returncode != 0:
        print(f"\n❌ {label or script} failed.")
        sys.exit(result.returncode)


print("=" * 30)
print("DEVOCIONALES CORPUS VALIDATION")
print("=" * 30)
run("validate_devocionales_corpus.py", label="Devocionales corpus validation")

print("\n✅ ALL DEVOCIONALES CHECKS PASSED\n")
