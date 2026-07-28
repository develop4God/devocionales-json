"""bible_sot.py — load Bible version config from the remote SOT, with an
offline temp-dir cache fallback.

Merges the fetch/retry/cache logic that both validate_encounters.py and
validate_discovery.py implemented independently and near-identically.

Nothing in this module runs at import time — callers must explicitly call
load_bible_versions() from their own main().
"""

import json
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

REMOTE_INDEX_URL = "https://raw.githubusercontent.com/develop4God/bible_versions/refs/heads/main/index.json"
REMOTE_FETCH_ATTEMPTS = 3
REMOTE_FETCH_TIMEOUT = 15  # seconds, per attempt


def _remote_to_local_shape(remote_entry: dict) -> dict:
    """Adapt a remote SOT language entry to the validators' expected shape."""
    primary = remote_entry["primary_version"]
    fallback = remote_entry["fallback_version"]
    return {
        "name": remote_entry["name"],
        "script": remote_entry["script"],
        "primary_version": primary,
        "fallback_version": fallback,
        "allowed_versions": [primary, fallback],
        "reading_speed": remote_entry["reading_speed"],
    }


def _fetch_remote_index(attempts: int = REMOTE_FETCH_ATTEMPTS) -> Optional[dict]:
    """Fetch the remote bible_versions SOT index, retrying transient failures
    a few times before giving up (a single flaky network blip shouldn't be
    indistinguishable from genuine unreachability)."""
    last_err = None
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(
                REMOTE_INDEX_URL, timeout=REMOTE_FETCH_TIMEOUT
            ) as resp:
                return json.loads(resp.read())
        except (
            urllib.error.URLError,
            TimeoutError,
            OSError,
            json.JSONDecodeError,
        ) as e:
            last_err = e
            if attempt < attempts:
                time.sleep(min(2**attempt, 8))  # 2s, 4s, ...
    return None


def _write_local_cache(cache_path: Path, remote_langs: dict) -> None:
    """Refresh the temp-dir bible_versions cache from a successful live
    fetch, so the offline fallback is always recent. Written outside the
    repo so it's never an untracked/committed file."""
    payload = {
        "meta": {
            "version": "1.0.0",
            "source": f"Cached from {REMOTE_INDEX_URL} on last successful validator run",
            "note": "Offline fallback only. Lives in the system temp dir — never hand-edit, never commit.",
        },
        "languages": {
            lang: _remote_to_local_shape(entry) for lang, entry in remote_langs.items()
        },
    }
    try:
        cache_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    except OSError:
        pass  # best-effort — a read-only filesystem shouldn't fail validation


def load_bible_versions(cache_name: str) -> tuple[dict, bool, Optional[Exception]]:
    """Load bible version config for every language the remote SOT defines.

    Tries the live remote SOT first (source of truth, with retries); only
    falls back to a temp-dir cache file if the network is unreachable after
    all attempts. On a successful fetch, refreshes the cache so the fallback
    path is always recent.

    `cache_name` parameterizes the temp-dir cache filename
    (f'{cache_name}_bible_versions_cache.json') so two callers never collide.

    Returns (languages_dict, used_remote_sot, last_fetch_error).
    used_remote_sot is True only when the live fetch succeeded.
    last_fetch_error is the exception from the fetch attempt when it failed
    and a local cache was available (informational — the cache load itself
    did not raise).

    Raises RuntimeError if the network is unreachable AND no local cache
    exists — callers should not need to handle a bare FileNotFoundError.
    """
    cache_path = Path(tempfile.gettempdir()) / f"{cache_name}_bible_versions_cache.json"

    remote = _fetch_remote_index()
    if remote is not None:
        remote_langs = remote.get("languages", {})
        _write_local_cache(cache_path, remote_langs)
        return (
            {
                lang: _remote_to_local_shape(entry)
                for lang, entry in remote_langs.items()
            },
            True,
            None,
        )

    if cache_path.exists():
        try:
            languages = json.loads(cache_path.read_text(encoding="utf-8"))["languages"]
            return languages, False, None
        except (json.JSONDecodeError, KeyError, OSError) as e:
            raise RuntimeError(
                f"Could not reach the Bible versions SOT at {REMOTE_INDEX_URL} "
                f"and the local fallback cache at {cache_path} is unreadable: {e}"
            ) from e

    raise RuntimeError(
        f"Could not reach the Bible versions SOT at {REMOTE_INDEX_URL} "
        "and no local fallback cache is available. Check network connectivity."
    )
