#!/usr/bin/env python3
"""
master_validator.py — Encounters pipeline orchestrator.

Phase 1: validate_encounters.py (JSON/content lint + cross-translation checks)
          and verify_image_urls.py (image_url references resolve on the
          Devocionales-assets CDN) run concurrently — one is disk/CPU-bound,
          the other network-bound, so there's no reason to serialize them.

Run from encounters/encounters_scripts/ or anywhere.

Exit codes: 0 = all passed, 1 = errors found in any phase
"""

import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent


def run(script, args=None, label=''):
    """Run a validator script, capturing output so concurrent runs don't
    interleave on stdout — printed sequentially once all jobs finish."""
    label = label or script
    cmd = [sys.executable, str(SCRIPTS_DIR / script)] + (args or [])
    result = subprocess.run(cmd, text=True, capture_output=True)
    return label, result.returncode, result.stdout, result.stderr


print("=" * 30)
print("ENCOUNTERS VALIDATION")
print("=" * 30)

jobs = [
    ("validate_encounters.py", None, "Encounters content validation"),
    ("verify_image_urls.py", None, "Image URL verification"),
]

with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
    results = list(pool.map(lambda j: run(*j), jobs))

for label, code, stdout, stderr in results:
    print(f"\n{'─' * 80}\n{label}\n{'─' * 80}")
    print(stdout, end='')
    if stderr:
        print(stderr, end='', file=sys.stderr)

failed = [label for label, code, _, _ in results if code != 0]

if failed:
    print(f"\n❌ Failed: {', '.join(failed)}")
    sys.exit(1)

print("\n✅ ALL ENCOUNTERS PASSED\n")
