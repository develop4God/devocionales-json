"""test_promoted_validators.py — durable smoke-test gate for the promoted
validators (validate_encounters.py, validate_discovery.py) and their real
master-validator entry points.

Everything verified about the _v2 -> promoted migration so far (byte-identical
comparison against the pre-migration originals, golden-file RunReport tests)
was either a one-time manual act or tests RunReport in isolation. Neither
protects the promoted validators' actual pass/fail verdict against a future
edit that breaks them. This module is that durable gate: it shells out to the
real master validators — the actual production entry points — against real
repo content (clean-pass case) and against a tiny deliberately-broken fixture
in an isolated temp copy (failure case), so a future regression fails a test
instead of shipping silently.

Not a substitute for full business-rule test coverage (out of scope for this
migration) — just a smoke gate confirming the promoted scripts still run and
still gate correctly.
"""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
ENCOUNTERS_MASTER = REPO_ROOT / 'encounters' / 'encounters_scripts' / 'encounters_master_validator.py'
DISCOVERY_MASTER = REPO_ROOT / 'discovery' / 'discovery_scripts' / 'discovery_master_validator.py'


def _run(script_path: Path, timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=True, text=True, timeout=timeout,
    )


class TestPromotedValidatorsCleanPass(unittest.TestCase):
    """Runs the real master validators against real repo content. These are
    the actual production entry points post-promotion — if either of these
    fails, the real pipeline is broken, not just a test fixture."""

    def test_encounters_master_validator_passes(self):
        result = _run(ENCOUNTERS_MASTER)
        self.assertEqual(
            result.returncode, 0,
            f"encounters_master_validator.py failed unexpectedly.\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )
        # Confirm it's actually running the promoted (shared_validation-based)
        # script, not silently falling back to something else — the RunReport
        # summary block only the promoted script produces.
        self.assertIn("📊 COVERAGE", result.stdout)
        self.assertIn("RUN PASSED", result.stdout)

    def test_discovery_master_validator_passes(self):
        result = _run(DISCOVERY_MASTER)
        self.assertEqual(
            result.returncode, 0,
            f"discovery_master_validator.py failed unexpectedly.\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )
        self.assertIn("📊 COVERAGE", result.stdout)
        self.assertIn("RUN PASSED", result.stdout)


class TestPromotedValidatorsGateOnFailure(unittest.TestCase):
    """Builds an isolated temp copy of just enough of the real tree to run
    the promoted validator directly (not the master wrapper, to keep this
    fast), deliberately corrupts the copy's index.json, and confirms a real
    structural error actually gates the run — i.e. this is not a test that
    only ever sees the happy path.
    """

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="promoted_validator_gate_test_"))
        self.addCleanup(shutil.rmtree, self.tmpdir, ignore_errors=True)

    def _make_encounters_fixture(self) -> Path:
        """Copy encounters/ + encounters_scripts/ (needed because the
        validator locates its content directory relative to its own
        __file__, not cwd) plus shared_validation/ (its dependency) into an
        isolated temp tree, then corrupt the copy's index.json."""
        fixture_root = self.tmpdir / 'encounters_fixture'
        shutil.copytree(REPO_ROOT / 'encounters', fixture_root / 'encounters')
        shutil.copytree(REPO_ROOT / 'shared_validation', fixture_root / 'shared_validation')

        index_path = fixture_root / 'encounters' / 'index.json'
        data = json.loads(index_path.read_text(encoding='utf-8'))
        del data['encounters']  # required top-level key — Phase A must reject this
        index_path.write_text(json.dumps(data, indent=2), encoding='utf-8')

        return fixture_root / 'encounters' / 'encounters_scripts' / 'validate_encounters.py'

    def _make_discovery_fixture(self) -> Path:
        fixture_root = self.tmpdir / 'discovery_fixture'
        shutil.copytree(REPO_ROOT / 'discovery', fixture_root / 'discovery')
        shutil.copytree(REPO_ROOT / 'shared_validation', fixture_root / 'shared_validation')

        index_path = fixture_root / 'discovery' / 'index.json'
        data = json.loads(index_path.read_text(encoding='utf-8'))
        del data['studies']  # required top-level key — Phase A must reject this
        index_path.write_text(json.dumps(data, indent=2), encoding='utf-8')

        return fixture_root / 'discovery' / 'discovery_scripts' / 'validate_discovery.py'

    def test_encounters_validator_fails_on_broken_index(self):
        script = self._make_encounters_fixture()
        result = _run(script)
        self.assertNotEqual(
            result.returncode, 0,
            f"Expected a non-zero exit on a broken index.json, got 0.\n"
            f"stdout:\n{result.stdout}",
        )
        self.assertIn("missing required 'encounters' array", result.stdout)

    def test_discovery_validator_fails_on_broken_index(self):
        script = self._make_discovery_fixture()
        result = _run(script)
        self.assertNotEqual(
            result.returncode, 0,
            f"Expected a non-zero exit on a broken index.json, got 0.\n"
            f"stdout:\n{result.stdout}",
        )
        self.assertIn("missing required 'studies' array", result.stdout)


if __name__ == '__main__':
    unittest.main()
