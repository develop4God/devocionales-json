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

import re
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


def _count(pattern, text):
    m = re.search(pattern, text)
    return m.group(1) if m else "?"


def summarize_content_validation(stdout: str) -> str:
    files = _count(r'Checked (\d+) JSON files', stdout)
    encounters = _count(r'Found (\d+) encounters', stdout)
    errors = len(re.findall(r'^\s*❌ ERROR:', stdout, re.MULTILINE))
    warnings = len(re.findall(r'^\s*⚠️\s*WARNING:', stdout, re.MULTILINE))
    return (f"{files} JSON files · {encounters} encounters indexed · "
            f"{errors} errors · {warnings} warnings")


def summarize_image_urls(stdout: str) -> str:
    checked = _count(r'Unique images checked: (\d+)', stdout)
    summary_line = re.search(r'Summary: (\d+)/(\d+) OK, (\d+) failed', stdout)
    if summary_line:
        ok, total, failed = summary_line.groups()
        return f"{checked} unique images · {ok}/{total} resolved · {failed} failed"
    return f"{checked} unique images checked (summary line not found)"


SUMMARIZERS = {
    "Encounters content validation": summarize_content_validation,
    "Image URL verification": summarize_image_urls,
}


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

# Final rollup — the per-phase reports above are long; pull the numbers that
# actually matter into one place so nothing (like image URL results) gets
# lost by scrolling past it.
print(f"\n{'=' * 30}")
print("SUMMARY")
print("=" * 30)
for label, code, stdout, _ in results:
    status = "✅" if code == 0 else "❌"
    summarizer = SUMMARIZERS.get(label)
    detail = summarizer(stdout) if summarizer else f"exit code {code}"
    print(f"{status} {label}: {detail}")

if failed:
    print(f"\n❌ Failed: {', '.join(failed)}")
    sys.exit(1)

print("\n✅ ALL ENCOUNTERS PASSED\n")
