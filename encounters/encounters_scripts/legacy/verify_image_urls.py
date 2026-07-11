#!/usr/bin/env python3
"""
verify_image_urls.py — Verify encounter image_url references resolve to real
files in the Devocionales-assets GitHub repo (SOT).

image_url in card JSON is a bare filename (e.g. "zacchaeus_in_tree.png").
The asset host maps it to:
  https://raw.githubusercontent.com/develop4God/Devocionales-assets/main/images/encounters/<encounter_id>/<filename>
where <encounter_id> is the encounter's "id" in index.json (== its asset folder name).

Exit codes: 0 = all images resolved, 1 = one or more missing/unreachable.
"""

import json
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

ASSETS_REPO_RAW_BASE = (
    "https://raw.githubusercontent.com/develop4God/Devocionales-assets/main/images/encounters"
)
RETRY_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 2
REQUEST_TIMEOUT_SECONDS = 10
MAX_CONCURRENT_REQUESTS = 16


@dataclass(frozen=True)
class ImageReference:
    encounter_id: str
    filename: str
    source_file: str

    @property
    def url(self) -> str:
        return f"{ASSETS_REPO_RAW_BASE}/{self.encounter_id}/{self.filename}"


@dataclass
class CheckResult:
    reference: ImageReference
    ok: bool
    status: str


class EncounterIndexReader:
    """Reads index.json to map encounter file -> encounter_id (asset folder name)."""

    def __init__(self, encounters_dir: Path):
        self._encounters_dir = encounters_dir

    def build_file_to_encounter_id(self) -> dict:
        index_path = self._encounters_dir / "index.json"
        data = json.loads(index_path.read_text(encoding="utf-8"))

        file_to_id = {}
        for encounter in data["encounters"]:
            encounter_id = encounter["id"]
            if "intro_image" in encounter:
                file_to_id[("index.json", encounter["intro_image"])] = encounter_id
            for lang_file in encounter.get("files", {}).values():
                file_to_id[lang_file] = encounter_id
        return file_to_id


class ImageReferenceExtractor:
    """Extracts image_url references from encounter card files, deduplicated
    per (encounter_id, filename) since the same asset is reused across languages."""

    SKIP_DIRS = {
        "archive", "encounters_scripts", "discovery", "badges",
        "bible_database", "devocionales_scripts", "skills", "image_promts",
    }

    def __init__(self, encounters_dir: Path, file_to_encounter_id: dict):
        self._encounters_dir = encounters_dir
        self._file_to_encounter_id = file_to_encounter_id

    def extract(self) -> list:
        seen = {}
        for lang_dir in sorted(self._encounters_dir.iterdir()):
            if not lang_dir.is_dir() or lang_dir.name in self.SKIP_DIRS:
                continue
            for json_file in sorted(lang_dir.glob("*.json")):
                encounter_id = self._file_to_encounter_id.get(json_file.name)
                if encounter_id is None:
                    continue  # not referenced in index.json; not an encounter card file
                self._extract_from_file(json_file, encounter_id, seen)
        return list(seen.values())

    def _extract_from_file(self, json_file: Path, encounter_id: str, seen: dict) -> None:
        data = json.loads(json_file.read_text(encoding="utf-8"))
        for card in data.get("cards", []):
            filename = card.get("image_url")
            if not filename:
                continue
            key = (encounter_id, filename)
            if key not in seen:
                seen[key] = ImageReference(
                    encounter_id=encounter_id,
                    filename=filename,
                    source_file=json_file.name,
                )


class GitHubAssetChecker:
    """Checks whether an image reference resolves on the GitHub assets repo,
    retrying transient failures before giving up."""

    def __init__(self, attempts: int = RETRY_ATTEMPTS, backoff_seconds: int = RETRY_BACKOFF_SECONDS):
        self._attempts = attempts
        self._backoff_seconds = backoff_seconds

    def check(self, reference: ImageReference) -> CheckResult:
        last_status = "unknown error"
        for attempt in range(1, self._attempts + 1):
            ok, status, retryable = self._check_once(reference.url)
            if ok or not retryable:
                return CheckResult(reference=reference, ok=ok, status=status)
            last_status = status
            if attempt < self._attempts:
                time.sleep(self._backoff_seconds)
        return CheckResult(reference=reference, ok=False, status=last_status)

    def _check_once(self, url: str) -> tuple:
        request = urllib.request.Request(url, method="HEAD")
        try:
            with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                return True, f"HTTP {response.status}", False
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return False, "HTTP 404 Not Found", False  # not a transient error
            return False, f"HTTP {e.code}", True
        except (urllib.error.URLError, TimeoutError) as e:
            return False, f"Network error: {e}", True


class VerificationReport:
    """Formats and prints the verification results; owns the exit code decision."""

    def __init__(self, results: list, files_checked: int):
        self._results = results
        self._files_checked = files_checked

    def print(self) -> None:
        print("=" * 80)
        print("IMAGE URL VERIFICATION REPORT (SOT: Devocionales-assets on GitHub)")
        print("=" * 80)
        print()
        print(f"Encounter card files scanned: {self._files_checked}")
        print(f"Unique images checked: {len(self._results)}")
        print()

        failures = [r for r in self._results if not r.ok]

        if failures:
            print(f"MISSING/UNREACHABLE IMAGES ({len(failures)}):")
            for r in failures:
                print(f"   - {r.reference.encounter_id}/{r.reference.filename}")
                print(f"     Referenced in: {r.reference.source_file}")
                print(f"     Status: {r.status}")
                print(f"     URL: {r.reference.url}")
            print()
        else:
            print("All images resolved successfully.")
            print()

        print("=" * 80)
        print(f"Summary: {len(self._results) - len(failures)}/{len(self._results)} OK, {len(failures)} failed")
        print("=" * 80)

    def exit_code(self) -> int:
        return 0 if all(r.ok for r in self._results) else 1


def main() -> int:
    encounters_dir = Path(__file__).parent.parent

    index_reader = EncounterIndexReader(encounters_dir)
    file_to_encounter_id = index_reader.build_file_to_encounter_id()

    extractor = ImageReferenceExtractor(encounters_dir, file_to_encounter_id)
    references = extractor.extract()

    checker = GitHubAssetChecker()
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_REQUESTS) as pool:
        results = list(pool.map(checker.check, references))

    files_checked = len({r.reference.source_file for r in results})
    report = VerificationReport(results, files_checked)
    report.print()
    return report.exit_code()


if __name__ == "__main__":
    sys.exit(main())
