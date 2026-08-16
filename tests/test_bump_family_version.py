"""Tests for the auto family-version bump tool, using isolated temp git repos
so real repo history/index.json state is never touched."""

import json
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from shared_validation.tools import bump_family_version as bfv


def _run(*args, cwd):
    subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)


def _init_repo(root: Path) -> None:
    _run("git", "init", "-q", cwd=root)
    _run("git", "config", "user.email", "test@test.com", cwd=root)
    _run("git", "config", "user.name", "test", cwd=root)


def _commit(root: Path, message: str) -> str:
    _run("git", "add", "-A", cwd=root)
    _run("git", "commit", "-q", "-m", message, cwd=root)
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _write_index(root: Path, studies: list[dict]) -> None:
    (root / "discovery").mkdir(exist_ok=True)
    (root / "discovery" / "en").mkdir(exist_ok=True)
    (root / "encounters").mkdir(exist_ok=True)
    (root / "discovery" / "index.json").write_text(
        json.dumps({"studies": studies}, indent=2), encoding="utf-8"
    )
    if not (root / "encounters" / "index.json").exists():
        (root / "encounters" / "index.json").write_text(
            json.dumps({"encounters": []}, indent=2), encoding="utf-8"
        )


class BumpFamilyVersionTests(unittest.TestCase):
    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.root = Path(self._tmp.name)
        _init_repo(self.root)
        self._orig_root = bfv.REPO_ROOT
        self._orig_content_types = bfv.CONTENT_TYPES
        bfv.REPO_ROOT = self.root
        bfv.CONTENT_TYPES = {
            "discovery": (self.root / "discovery", "studies"),
            "encounters": (self.root / "encounters", "encounters"),
        }

    def tearDown(self):
        bfv.REPO_ROOT = self._orig_root
        bfv.CONTENT_TYPES = self._orig_content_types
        self._tmp.cleanup()

    def test_bumps_family_when_language_file_changed_without_manual_bump(self):
        study = {
            "id": "foo_001",
            "version": "1.1",
            "files": {"en": "foo_en_001.json"},
        }
        _write_index(self.root, [study])
        (self.root / "discovery" / "en" / "foo_en_001.json").write_text(
            '{"title": "a"}', encoding="utf-8"
        )
        base_sha = _commit(self.root, "base")

        (self.root / "discovery" / "en" / "foo_en_001.json").write_text(
            '{"title": "b"}', encoding="utf-8"
        )
        head_sha = _commit(self.root, "content change, no bump")

        total = bfv.apply_bumps(base_sha, head_sha, dry_run=False)

        self.assertEqual(total, 1)
        new_index = json.loads(
            (self.root / "discovery" / "index.json").read_text(encoding="utf-8")
        )
        self.assertEqual(new_index["studies"][0]["version"], "1.2")

    def test_skips_family_already_manually_bumped_in_same_diff(self):
        study = {
            "id": "foo_001",
            "version": "1.1",
            "files": {"en": "foo_en_001.json"},
        }
        _write_index(self.root, [study])
        (self.root / "discovery" / "en" / "foo_en_001.json").write_text(
            '{"title": "a"}', encoding="utf-8"
        )
        base_sha = _commit(self.root, "base")

        (self.root / "discovery" / "en" / "foo_en_001.json").write_text(
            '{"title": "b"}', encoding="utf-8"
        )
        _write_index(self.root, [{**study, "version": "1.5"}])
        head_sha = _commit(self.root, "content change with manual bump")

        total = bfv.apply_bumps(base_sha, head_sha, dry_run=False)

        self.assertEqual(total, 0)
        new_index = json.loads(
            (self.root / "discovery" / "index.json").read_text(encoding="utf-8")
        )
        self.assertEqual(new_index["studies"][0]["version"], "1.5")

    def test_skips_brand_new_family_not_present_at_base(self):
        _write_index(self.root, [])
        base_sha = _commit(self.root, "base, no families yet")

        new_study = {
            "id": "brand_new_001",
            "version": "1.0",
            "files": {"en": "brand_new_en_001.json"},
        }
        _write_index(self.root, [new_study])
        (self.root / "discovery" / "en" / "brand_new_en_001.json").write_text(
            '{"title": "new"}', encoding="utf-8"
        )
        head_sha = _commit(self.root, "add brand new family")

        total = bfv.apply_bumps(base_sha, head_sha, dry_run=False)

        self.assertEqual(total, 0)
        new_index = json.loads(
            (self.root / "discovery" / "index.json").read_text(encoding="utf-8")
        )
        self.assertEqual(new_index["studies"][0]["version"], "1.0")

    def test_dry_run_does_not_write_file(self):
        study = {
            "id": "foo_001",
            "version": "1.1",
            "files": {"en": "foo_en_001.json"},
        }
        _write_index(self.root, [study])
        (self.root / "discovery" / "en" / "foo_en_001.json").write_text(
            '{"title": "a"}', encoding="utf-8"
        )
        base_sha = _commit(self.root, "base")

        (self.root / "discovery" / "en" / "foo_en_001.json").write_text(
            '{"title": "b"}', encoding="utf-8"
        )
        head_sha = _commit(self.root, "content change, no bump")

        total = bfv.apply_bumps(base_sha, head_sha, dry_run=True)

        self.assertEqual(total, 1)
        new_index = json.loads(
            (self.root / "discovery" / "index.json").read_text(encoding="utf-8")
        )
        self.assertEqual(new_index["studies"][0]["version"], "1.1")


if __name__ == "__main__":
    unittest.main()
