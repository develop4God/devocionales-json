"""Tests for the auto devocionales index-date bump tool, using isolated
temp git repos so real repo history/index.json state is never touched."""

import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).parent.parent / "devocionales_scripts"))
import bump_devocionales_date as bdd


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


def _write_index(
    root: Path, files_section: dict, updated_at: str = "2026-01-01"
) -> None:
    (root / "index.json").write_text(
        json.dumps(
            {"schema_version": 1, "updated_at": updated_at, "files": files_section},
            indent=2,
        ),
        encoding="utf-8",
    )


class BumpDevocionalesDateTests(unittest.TestCase):
    def setUp(self):
        self._tmp = TemporaryDirectory()
        self.root = Path(self._tmp.name)
        _init_repo(self.root)
        self._orig_root = bdd.REPO_ROOT
        self._orig_index_path = bdd.INDEX_PATH
        bdd.REPO_ROOT = self.root
        bdd.INDEX_PATH = self.root / "index.json"

    def tearDown(self):
        bdd.REPO_ROOT = self._orig_root
        bdd.INDEX_PATH = self._orig_index_path
        self._tmp.cleanup()

    def test_bumps_combo_date_when_file_changed_without_manual_update(self):
        files_section = {
            "en": {
                "NIV": {
                    "2026": "2026-04-24",
                    "files": {"2026": "Devocional_year_2026_en_NIV.json"},
                }
            }
        }
        _write_index(self.root, files_section)
        (self.root / "Devocional_year_2026_en_NIV.json").write_text(
            '{"data": {}}', encoding="utf-8"
        )
        base_sha = _commit(self.root, "base")

        (self.root / "Devocional_year_2026_en_NIV.json").write_text(
            '{"data": {"x": 1}}', encoding="utf-8"
        )
        head_sha = _commit(self.root, "content change, no index bump")

        total = bdd.apply_bumps(base_sha, head_sha, dry_run=False, today="2026-08-15")

        self.assertEqual(total, 1)
        new_index = json.loads(bdd.INDEX_PATH.read_text(encoding="utf-8"))
        self.assertEqual(new_index["files"]["en"]["NIV"]["2026"], "2026-08-15")
        self.assertEqual(new_index["updated_at"], "2026-08-15")

    def test_skips_combo_already_manually_updated_in_same_diff(self):
        files_section = {
            "en": {
                "NIV": {
                    "2026": "2026-04-24",
                    "files": {"2026": "Devocional_year_2026_en_NIV.json"},
                }
            }
        }
        _write_index(self.root, files_section)
        (self.root / "Devocional_year_2026_en_NIV.json").write_text(
            '{"data": {}}', encoding="utf-8"
        )
        base_sha = _commit(self.root, "base")

        (self.root / "Devocional_year_2026_en_NIV.json").write_text(
            '{"data": {"x": 1}}', encoding="utf-8"
        )
        files_section["en"]["NIV"]["2026"] = "2026-08-10"
        _write_index(self.root, files_section)
        head_sha = _commit(self.root, "content change with manual date update")

        total = bdd.apply_bumps(base_sha, head_sha, dry_run=False, today="2026-08-15")

        self.assertEqual(total, 0)
        new_index = json.loads(bdd.INDEX_PATH.read_text(encoding="utf-8"))
        self.assertEqual(new_index["files"]["en"]["NIV"]["2026"], "2026-08-10")

    def test_skips_brand_new_combo_not_present_at_base(self):
        _write_index(self.root, {})
        base_sha = _commit(self.root, "base, no combos yet")

        files_section = {
            "en": {
                "NIV": {
                    "2026": "2026-08-15",
                    "files": {"2026": "Devocional_year_2026_en_NIV.json"},
                }
            }
        }
        _write_index(self.root, files_section)
        (self.root / "Devocional_year_2026_en_NIV.json").write_text(
            '{"data": {}}', encoding="utf-8"
        )
        head_sha = _commit(self.root, "add brand new combo")

        total = bdd.apply_bumps(base_sha, head_sha, dry_run=False, today="2026-08-15")

        self.assertEqual(total, 0)
        new_index = json.loads(bdd.INDEX_PATH.read_text(encoding="utf-8"))
        self.assertEqual(new_index["files"]["en"]["NIV"]["2026"], "2026-08-15")

    def test_dry_run_does_not_write_file(self):
        files_section = {
            "en": {
                "NIV": {
                    "2026": "2026-04-24",
                    "files": {"2026": "Devocional_year_2026_en_NIV.json"},
                }
            }
        }
        _write_index(self.root, files_section)
        (self.root / "Devocional_year_2026_en_NIV.json").write_text(
            '{"data": {}}', encoding="utf-8"
        )
        base_sha = _commit(self.root, "base")

        (self.root / "Devocional_year_2026_en_NIV.json").write_text(
            '{"data": {"x": 1}}', encoding="utf-8"
        )
        head_sha = _commit(self.root, "content change, no bump")

        total = bdd.apply_bumps(base_sha, head_sha, dry_run=True, today="2026-08-15")

        self.assertEqual(total, 1)
        new_index = json.loads(bdd.INDEX_PATH.read_text(encoding="utf-8"))
        self.assertEqual(new_index["files"]["en"]["NIV"]["2026"], "2026-04-24")

    def test_unrelated_file_change_does_not_bump_anything(self):
        files_section = {
            "en": {
                "NIV": {
                    "2026": "2026-04-24",
                    "files": {"2026": "Devocional_year_2026_en_NIV.json"},
                }
            }
        }
        _write_index(self.root, files_section)
        (self.root / "Devocional_year_2026_en_NIV.json").write_text(
            '{"data": {}}', encoding="utf-8"
        )
        (self.root / "README.md").write_text("hello", encoding="utf-8")
        base_sha = _commit(self.root, "base")

        (self.root / "README.md").write_text("hello world", encoding="utf-8")
        head_sha = _commit(self.root, "unrelated readme change")

        total = bdd.apply_bumps(base_sha, head_sha, dry_run=False, today="2026-08-15")

        self.assertEqual(total, 0)
        new_index = json.loads(bdd.INDEX_PATH.read_text(encoding="utf-8"))
        self.assertEqual(new_index["files"]["en"]["NIV"]["2026"], "2026-04-24")


if __name__ == "__main__":
    unittest.main()
