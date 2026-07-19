#!/usr/bin/env python3
"""
verify_image_urls.py — Verify encounter image_url references resolve to real
files in the Devocionales-assets GitHub repo (SOT).

image_url in card JSON is a bare filename (e.g. "zacchaeus_in_tree.png").
The asset host maps it to:
  https://raw.githubusercontent.com/develop4God/Devocionales-assets/main/images/encounters/<encounter_id>/<filename>
where <encounter_id> is the encounter's "id" in index.json (== its asset folder name).

Each image is uploaded in two formats (PNG + AVIF) with the same stem, so for
every image_url reference this script cross-checks BOTH extensions — the one
declared in the JSON and its AVIF counterpart — even though only the declared
one is what the app actually requests.

With --validate-format, each resolved URL is also range-fetched (first 32
bytes) and its magic-number signature is checked against the extension it
was requested under, catching a file that exists but isn't a real PNG/AVIF
(e.g. an HTML error page saved with the wrong extension, or a swapped file).

Exit codes: 0 = all images resolved in both formats, 1 = one or more missing/unreachable.
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from pathlib import Path

from asset_urls import EncounterIndexReader, ImageReference as _BaseImageReference

RETRY_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 2
REQUEST_TIMEOUT_SECONDS = 10
MAX_CONCURRENT_REQUESTS = 16
CROSS_CHECK_EXTENSIONS = ("png", "avif")
MAGIC_BYTES_FETCH_SIZE = 32


@dataclass(frozen=True)
class ImageReference(_BaseImageReference):
    source_file: str = ""
    ext: str = ""  # which of CROSS_CHECK_EXTENSIONS this reference checks

    @property
    def url(self) -> str:
        return _BaseImageReference.url(self, ext=self.ext)


@dataclass
class CheckResult:
    reference: ImageReference
    ok: bool
    status: str
    format_ok: bool = None
    format_status: str = ""


class ImageReferenceExtractor:
    """Extracts image_url references from encounter card files, deduplicated
    per (encounter_id, filename) since the same asset is reused across languages.
    Each unique image_url expands into one ImageReference per cross-check
    extension (PNG + AVIF), since both are uploaded for every image."""

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
        references = []
        for base in seen.values():
            for ext in CROSS_CHECK_EXTENSIONS:
                references.append(replace(base, ext=ext))
        return references

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


class ImageFormatValidator:
    """Range-fetches the first bytes of a resolved image URL and checks its
    magic-number signature matches the extension it was requested under.
    One check method per format, dispatched by extension (open/closed: add a
    format by adding a method + registering it in CHECKERS)."""

    def _is_png(self, header: bytes) -> bool:
        return header.startswith(b"\x89PNG\r\n\x1a\n")

    def _is_avif(self, header: bytes) -> bool:
        # ISOBMFF box: 4-byte size, b"ftyp", then a major brand of avif/avis.
        return header[4:8] == b"ftyp" and header[8:12] in (b"avif", b"avis")

    CHECKERS = {"png": _is_png, "avif": _is_avif}

    def validate(self, reference: ImageReference) -> tuple:
        checker = self.CHECKERS.get(reference.ext)
        if checker is None:
            return None, f"No format checker registered for .{reference.ext}"

        request = urllib.request.Request(
            reference.url,
            headers={"Range": f"bytes=0-{MAGIC_BYTES_FETCH_SIZE - 1}"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                header = response.read(MAGIC_BYTES_FETCH_SIZE)
        except (urllib.error.URLError, TimeoutError) as e:
            return False, f"Format check network error: {e}"

        if checker(self, header):
            return True, f"Valid {reference.ext.upper()} signature"
        return False, f"Bytes at {reference.url} do not match {reference.ext.upper()} signature"


class VerificationReport:
    """Formats and prints the verification results; owns the exit code decision."""

    def __init__(self, results: list, files_checked: int):
        self._results = results
        self._files_checked = files_checked

    def print(self) -> None:
        unique_images = len({(r.reference.encounter_id, r.reference.filename) for r in self._results})

        print("=" * 80)
        print("IMAGE URL VERIFICATION REPORT (SOT: Devocionales-assets on GitHub)")
        print("=" * 80)
        print()
        print(f"Encounter card files scanned: {self._files_checked}")
        print(f"Unique images checked: {unique_images} (x{len(CROSS_CHECK_EXTENSIONS)} formats "
              f"{'/'.join(CROSS_CHECK_EXTENSIONS)} = {len(self._results)} checks)")
        print()

        failures = [r for r in self._results if not r.ok]
        format_failures = [r for r in self._results if r.ok and r.format_ok is False]

        if failures:
            print(f"MISSING/UNREACHABLE FILES ({len(failures)}):")
            for r in failures:
                print(f"   - {r.reference.encounter_id}/{r.reference.filename} [{r.reference.ext.upper()}]")
                print(f"     Referenced in: {r.reference.source_file}")
                print(f"     Status: {r.status}")
                print(f"     URL: {r.reference.url}")
            print()
        else:
            print(f"All images resolved successfully in both formats ({'/'.join(CROSS_CHECK_EXTENSIONS)}).")
            print()

        if format_failures:
            print(f"FORMAT MISMATCHES ({len(format_failures)}):")
            for r in format_failures:
                print(f"   - {r.reference.encounter_id}/{r.reference.filename} [{r.reference.ext.upper()}]")
                print(f"     Referenced in: {r.reference.source_file}")
                print(f"     Status: {r.format_status}")
                print(f"     URL: {r.reference.url}")
            print()

        print("=" * 80)
        total_failed = len({(r.reference.encounter_id, r.reference.filename, r.reference.ext)
                             for r in failures + format_failures})
        print(f"Summary: {len(self._results) - total_failed}/{len(self._results)} checks OK, "
              f"{total_failed} failed")
        print("=" * 80)

    def exit_code(self) -> int:
        if not all(r.ok for r in self._results):
            return 1
        if any(r.format_ok is False for r in self._results):
            return 1
        return 0


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--validate-format",
        action="store_true",
        help="Also range-fetch each resolved image's first bytes and verify "
             "its magic-number signature matches its extension (slower: one "
             "extra network request per successfully-resolved image).",
    )
    return parser.parse_args(argv)


def main() -> int:
    args = parse_args()
    encounters_dir = Path(__file__).parent.parent

    index_reader = EncounterIndexReader(encounters_dir)
    file_to_encounter_id = index_reader.build_file_to_encounter_id()

    extractor = ImageReferenceExtractor(encounters_dir, file_to_encounter_id)
    references = extractor.extract()

    checker = GitHubAssetChecker()
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_REQUESTS) as pool:
        results = list(pool.map(checker.check, references))

    if args.validate_format:
        validator = ImageFormatValidator()

        def add_format_check(result: CheckResult) -> CheckResult:
            if not result.ok:
                return result
            format_ok, format_status = validator.validate(result.reference)
            result.format_ok = format_ok
            result.format_status = format_status
            return result

        with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_REQUESTS) as pool:
            results = list(pool.map(add_format_check, results))

    files_checked = len({r.reference.source_file for r in results})
    report = VerificationReport(results, files_checked)
    report.print()
    return report.exit_code()


if __name__ == "__main__":
    sys.exit(main())
