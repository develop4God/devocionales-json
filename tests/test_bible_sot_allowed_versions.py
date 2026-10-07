"""bible_sot: allowed_versions comes from the SOT index when present, else primary + fallback."""

from shared_validation.checks.bible_sot import _remote_to_local_shape

BASE = {
    "name": "English",
    "script": "latin",
    "primary_version": "KJV",
    "fallback_version": "NIV",
    "reading_speed": {"unit": "wpm", "rate": 200},
}


def test_defaults_to_primary_and_fallback():
    assert _remote_to_local_shape(BASE)["allowed_versions"] == ["KJV", "NIV"]


def test_uses_the_sot_allowed_versions_when_present():
    entry = {**BASE, "allowed_versions": ["KJV", "NIV", "KJ2000"]}
    assert _remote_to_local_shape(entry)["allowed_versions"] == ["KJV", "NIV", "KJ2000"]
