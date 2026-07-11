#!/usr/bin/env python3
"""
validate_encounters.py — Validator for the encounters content type.

Phased validation, one Report per phase, same reporting contract throughout.
Phases 1/A/SOT/B are gates — an ERROR in any of them stops the run and fails
the exit code. Phase C always runs last, after B (the real data-integrity
gate) has passed, and only ever reports WARNINGs: an unreachable image is a
content-completeness gap, not a structural defect, and never blocks a merge.

  PHASE 1:   Lint — verify all JSON files use indent=2 formatting
  PHASE A:   Validate encounters/index.json
  PHASE SOT: Confirm bible_version codes resolved from the live remote SOT
  PHASE B:   Validate encounter files (published only) using EN as base — GATE
  PHASE C:   Verify image_url references resolve on the Devocionales-assets
             CDN — warnings only, runs last, never fails the build

Exit codes: 0 = all passed (Phase C warnings do not affect this), 1 = errors found in 1/A/SOT/B
"""

import atexit
import json
import re
import sys
import tempfile
from pathlib import Path
from typing import List, Optional

from verify_image_urls import (
    EncounterIndexReader as ImageIndexReader,
    ImageReferenceExtractor,
    GitHubAssetChecker,
    MAX_CONCURRENT_REQUESTS,
)
from concurrent.futures import ThreadPoolExecutor

# ── Config ────────────────────────────────────────────────────────────────────

SCRIPTS_DIR = Path(__file__).parent
ENCOUNTERS_DIR = SCRIPTS_DIR.parent
INDEX_PATH = ENCOUNTERS_DIR / 'index.json'

SCHEMA_VERSION = 'encounters_v1'
VALID_STATUSES = {'published', 'coming_soon'}
VALID_TESTAMENT = {'old', 'new'}

REMOTE_INDEX_URL = "https://raw.githubusercontent.com/develop4God/bible_versions/refs/heads/main/index.json"
REMOTE_FETCH_ATTEMPTS = 3
REMOTE_FETCH_TIMEOUT = 15  # seconds, per attempt

# Set by _fetch_remote_index on the last failed attempt; None if the fetch
# succeeded or hasn't been tried yet. Surfaced by validate_sot_source.
_LAST_REMOTE_FETCH_ERROR: Optional[Exception] = None

# bible_versions.json is a CACHE of the remote SOT, used only as a fallback
# within a single run when the live fetch fails. It lives in the system temp
# dir (never inside the repo) and is deleted when the process exits, so the
# SOT is always fetched fresh on the next run rather than persisted locally.
_LOCAL_CACHE_PATH = Path(tempfile.gettempdir()) / 'encounters_bible_versions_cache.json'


def _cleanup_local_cache() -> None:
    try:
        _LOCAL_CACHE_PATH.unlink(missing_ok=True)
    except OSError:
        pass


atexit.register(_cleanup_local_cache)


def _local_cache_languages() -> dict:
    """Read the temp-dir cache file (used only as an offline fallback)."""
    return json.loads(_LOCAL_CACHE_PATH.read_text(encoding='utf-8'))['languages']


def _remote_to_local_shape(remote_entry: dict) -> dict:
    """Adapt a remote SOT language entry to this validator's expected shape."""
    primary = remote_entry['primary_version']
    fallback = remote_entry['fallback_version']
    return {
        'name': remote_entry['name'],
        'script': remote_entry['script'],
        'primary_version': primary,
        'fallback_version': fallback,
        'allowed_versions': [primary, fallback],
        'reading_speed': remote_entry['reading_speed'],
    }


def _fetch_remote_index(attempts: int = REMOTE_FETCH_ATTEMPTS) -> Optional[dict]:
    """Fetch the remote bible_versions SOT index, retrying transient failures
    a few times before giving up (a single flaky network blip shouldn't be
    indistinguishable from genuine unreachability). Records the last error
    on the module so validate_sot_source can report *why* it fell back to
    the local cache, not just that it did."""
    import time
    import urllib.request
    import urllib.error

    global _LAST_REMOTE_FETCH_ERROR
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(REMOTE_INDEX_URL, timeout=REMOTE_FETCH_TIMEOUT) as resp:
                return json.loads(resp.read())
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as e:
            _LAST_REMOTE_FETCH_ERROR = e
            if attempt < attempts:
                time.sleep(min(2 ** attempt, 8))  # 2s, 4s, ...
    return None


def _write_local_cache(remote_langs: dict) -> None:
    """Refresh the temp-dir bible_versions cache from a successful live
    fetch, so the offline fallback is always recent rather than a
    hand-maintained file that can silently go stale between fetches.
    Written outside the repo so it's never an untracked/committed file."""
    payload = {
        'meta': {
            'version': '1.0.0',
            'source': f'Cached from {REMOTE_INDEX_URL} on last successful validator run',
            'note': 'Offline fallback only. Lives in the system temp dir — never hand-edit, never commit.',
        },
        'languages': {
            lang: _remote_to_local_shape(entry) for lang, entry in remote_langs.items()
        },
    }
    try:
        _LOCAL_CACHE_PATH.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + '\n', encoding='utf-8'
        )
    except OSError:
        pass  # best-effort — a read-only filesystem shouldn't fail validation


def _load_bible_versions() -> tuple[dict, bool]:
    """Load bible version config for every language the remote SOT defines.

    Tries the live remote SOT first (source of truth, with retries); only
    falls back to the temp-dir bible_versions cache if the network is
    unreachable after all attempts. On a successful fetch, refreshes the
    cache file so the fallback path is always recent.
    Returns (languages_dict, used_remote: bool).
    """
    remote = _fetch_remote_index()
    if remote is not None:
        remote_langs = remote.get('languages', {})
        _write_local_cache(remote_langs)
        return {lang: _remote_to_local_shape(entry) for lang, entry in remote_langs.items()}, True

    return _local_cache_languages(), False


_BIBLE_VERSIONS, _USED_REMOTE_SOT = _load_bible_versions()
EXPECTED_LANGUAGES = list(_BIBLE_VERSIONS.keys())

# Required card keys by type
CARD_REQUIRED_KEYS = {
    'cinematic_scene':    ['order', 'type', 'image_url', 'title', 'narrative', 'revelation_key'],
    'scripture_moment':   ['order', 'type', 'image_url', 'verse_reference', 'verse_text', 'reflection', 'revelation_key'],
    'character_moment':   ['order', 'type', 'image_url', 'title', 'content', 'revelation_key'],
    'theological_depth':  ['order', 'type', 'image_url', 'title', 'content', 'revelation_key'],
    'interactive_moment': ['order', 'type', 'image_url', 'title', 'reflection_prompt'],
    'discovery_activation': ['order', 'type', 'image_url', 'title', 'discovery_questions', 'prayer'],
    'completion':         ['order', 'type', 'image_url', 'completion_verse', 'reflection_prompt', 'celebration_type'],
}

# English Bible book name pattern (for non-EN reference checks)
EN_BIBLE_BOOK_PATTERN = re.compile(
    r'\b(Genesis|Exodus|Leviticus|Numbers|Deuteronomy|Joshua|Judges|Ruth|'
    r'Samuel|Kings|Chronicles|Ezra|Nehemiah|Esther|Job|Psalm|Psalms|'
    r'Proverbs|Ecclesiastes|Song|Isaiah|Jeremiah|Lamentations|Ezekiel|'
    r'Daniel|Hosea|Joel|Amos|Obadiah|Jonah|Micah|Nahum|Habakkuk|'
    r'Zephaniah|Haggai|Zechariah|Malachi|Matthew|Mark|Luke|John|Acts|'
    r'Romans|Corinthians|Galatians|Ephesians|Philippians|Colossians|'
    r'Thessalonians|Timothy|Titus|Philemon|Hebrews|James|Peter|Jude|'
    r'Revelation)\s+\d', re.IGNORECASE)

# Book names that are identical (or near-identical) in German and English —
# the EN pattern would falsely flag these as untranslated in DE files.
_DE_SHARED_BOOK_NAMES = {
    'psalm', 'psalms', 'daniel', 'hosea', 'joel', 'amos', 'nahum', 'ezra',
    'job', 'ruth',
}

# Book names used in the Magandang Balita Biblia (MBB05) Filipino Bible that
# retain the English/transliterated form — same-name false positives for FIL.
_FIL_SHARED_BOOK_NAMES = {
    'genesis', 'ruth', 'samuel', 'ezra', 'job', 'ezekiel', 'daniel',
    'hosea', 'joel', 'amos', 'nahum',
}

# Words identical (or near-identical) across English and Romance languages —
# valid cognate translations, not untranslated leftovers. Per translator skill
# § "Cognates (FR, PT, ES)": these are correct and should not be flagged.
_ROMANCE_COGNATES = {
    'fr': {'courage', 'grace', 'grâce'},
    'pt': {'coragem', 'graça'},
    'es': {'coraje', 'gracia'},
    # 'Legion' is spelled identically in German (from Latin legio) and is the
    # word used in the LU17 Bible text itself (Mark 5:9) — not a missed translation.
    'de': {'legion'},
}


def _is_cognate(value: str, lang: str) -> bool:
    """Return True if value is a known valid cognate word for lang."""
    return value.strip().lower() in _ROMANCE_COGNATES.get(lang, set())


def _has_english_book_name(reference: str, lang: str) -> bool:
    """Return True if reference contains an English-only book name for lang."""
    m = EN_BIBLE_BOOK_PATTERN.search(reference)
    if not m:
        return False
    if lang == 'de' and m.group(1).lower() in _DE_SHARED_BOOK_NAMES:
        return False
    if lang == 'fil' and m.group(1).lower() in _FIL_SHARED_BOOK_NAMES:
        return False
    return True


# Quote-like characters whose accidental back-to-back doubling indicates a
# stray-punctuation typo (e.g. »» , "" , '')
_DOUBLE_CHECK_CHARS = {'"', "'", '«', '»', '“', '”', '‘', '’'}

# Paired quote characters that should appear in balanced counts within a field.
# Note: curly double quotes (“ ” „) are intentionally NOT balance-checked here —
# this corpus mixes „...“ and „...” conventions across different German
# encounters, so a fixed pair produces false positives. Guillemets « » are
# checked for all languages (used in AR/FR/etc.) since their usage is consistent.


def _iter_strings(obj, path: str = ""):
    """Recursively yield (path, value) for every string leaf in obj."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _iter_strings(v, f"{path}.{k}" if path else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _iter_strings(v, f"{path}[{i}]")
    elif isinstance(obj, str):
        yield path, obj


def _is_verse_continuation_close(text: str, mark_chars: str) -> bool:
    """True if `text` looks like the tail fragment of a multi-verse quotation:
    it carries exactly one quote-like mark from `mark_chars`, sitting at the
    very end of the field (only trailing punctuation/whitespace after it).
    This corpus stores consecutive Bible verses as separate string fields, so
    a quotation that began in an earlier verse legitimately closes here with
    no opener of its own — not a stray-punctuation typo.
    """
    positions = [i for i, c in enumerate(text) if c in mark_chars]
    if len(positions) != 1:
        return False
    idx = positions[0]
    return bool(re.match(r'^[\s.!?,;:]*$', text[idx + 1:]))


def _check_quote_anomalies(text: str, ctx: str, lang: str, report: 'Report'):
    """Flag stray/duplicated/unbalanced quote-like punctuation in a text field."""
    # Doubled identical quote-like characters back-to-back (e.g. »», "", '')
    for i in range(len(text) - 1):
        c = text[i]
        if c in _DOUBLE_CHECK_CHARS and text[i + 1] == c:
            report.E(f"{ctx}: contains doubled '{c}{c}' — likely stray punctuation")

    # Balanced guillemets (used in AR/FR/etc.). Skip fields that are the
    # trailing fragment of a quotation opened in a preceding verse — see
    # _is_verse_continuation_close.
    oc, cc = text.count('«'), text.count('»')
    if oc != cc and not (oc + cc == 1 and _is_verse_continuation_close(text, '«»')):
        report.W(f"{ctx}: unbalanced '«'/'»' — {oc} open vs {cc} close")

    # Straight double quotes should appear in pairs, with the same
    # verse-continuation exception as guillemets above.
    if text.count('"') % 2 != 0 and not (text.count('"') == 1 and _is_verse_continuation_close(text, '"')):
        report.W(f"{ctx}: odd number of straight double quotes (\") — possible stray quote")


def validate_sot_source(report: 'Report') -> bool:
    """Report whether this run resolved bible_version codes from the live
    remote SOT or fell back to the temp-dir bible_versions cache.

    _BIBLE_VERSIONS is populated at import time by fetching the remote SOT
    first — this function only surfaces which source was actually used, so
    a validation run that silently fell back to a stale local cache (e.g. in
    a sandboxed/offline CI runner) is visible in the report rather than
    indistinguishable from a fully live run.
    """
    if _USED_REMOTE_SOT:
        report.I(f"✓ bible_version codes resolved live from remote SOT ({REMOTE_INDEX_URL}) for all {len(_BIBLE_VERSIONS)} languages")
        return True
    reason = f" ({_LAST_REMOTE_FETCH_ERROR})" if _LAST_REMOTE_FETCH_ERROR else ""
    report.W(
        f"Could not reach remote SOT ({REMOTE_INDEX_URL}){reason} — fell back to the "
        f"temp-dir bible_versions cache. Results reflect the LOCAL CACHE, not confirmed "
        f"live data; re-run once network access is available before merging."
    )
    return True


# ── Report ────────────────────────────────────────────────────────────────────

class Report:
    def __init__(self, phase: str):
        self.phase = phase
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []

    def E(self, msg): self.errors.append(f"❌ ERROR: {msg}")
    def W(self, msg): self.warnings.append(f"⚠️  WARNING: {msg}")
    def I(self, msg): self.info.append(f"ℹ️  INFO: {msg}")

    def print(self, final=True) -> bool:
        print(f"\n{'='*80}")
        print(f"{self.phase} VALIDATION REPORT")
        print('='*80)
        if self.info:
            print(f"\nℹ️  INFORMATION ({len(self.info)}):")
            for m in self.info: print(f"  {m}")
        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for m in self.warnings: print(f"  {m}")
        if self.errors:
            print(f"\n❌ ERRORS ({len(self.errors)}):")
            for m in self.errors: print(f"  {m}")
            print('='*80)
            return False
        msg = "✅ ALL VALIDATIONS PASSED!" if final else "✅ PHASE PASSED - Proceeding to next phase"
        print(f"\n{msg}")
        print('='*80)
        return True


def load_json(path: Path, report: Report) -> Optional[dict]:
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as e:
        report.E(f"Invalid JSON in {path.name}: {e}")
        return None
    except Exception as e:
        report.E(f"Cannot read {path.name}: {e}")
        return None


# ── Phase 1: Lint ────────────────────────────────────────────────────────────

def validate_lint(report: Report) -> dict:
    """Check that all JSON files use indent=2 formatting and end with newline.

    Returns a cache mapping absolute Path -> parsed dict for valid files.
    """
    report.I("=" * 60)
    report.I("PHASE 1: Lint — checking JSON formatting (indent=2)")
    report.I("=" * 60)

    cache: dict = {}
    json_files = sorted(ENCOUNTERS_DIR.rglob('*.json'))
    json_files = [f for f in json_files if f.is_file()
                  and 'encounters_scripts' not in f.parts]
    checked = 0
    for fpath in json_files:
        raw = fpath.read_text(encoding='utf-8')
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            report.E(f"{fpath.name}: invalid JSON")
            continue
        rel = fpath.relative_to(ENCOUNTERS_DIR)
        for line_no, line in enumerate(raw.splitlines(), 1):
            stripped = line.lstrip(' ')
            indent = len(line) - len(stripped)
            if indent > 0 and indent % 2 != 0:
                report.E(f"{rel}:{line_no}: odd indentation ({indent} spaces), expected multiples of 2")
                break
            if '\t' in line:
                report.E(f"{rel}:{line_no}: contains tab character, use 2-space indent")
                break
        if not raw.endswith('\n'):
            report.W(f"{rel}: missing trailing newline")
        cache[fpath] = data
        checked += 1

    report.I(f"✓ Checked {checked} JSON files")
    return cache


# ── Phase A: Index validation ─────────────────────────────────────────────────

def validate_index(report: Report) -> Optional[dict]:
    report.I("=" * 60)
    report.I("PHASE A: Validating encounters/index.json")
    report.I("=" * 60)

    if not INDEX_PATH.exists():
        report.E(f"index.json not found at {INDEX_PATH}")
        return None

    data = load_json(INDEX_PATH, report)
    if data is None:
        return None

    report.I("✓ index.json is valid JSON")

    if 'encounters' not in data:
        report.E("index.json missing required 'encounters' array")
        return None

    encounters = data['encounters']
    if not isinstance(encounters, list) or len(encounters) == 0:
        report.E("index.json 'encounters' must be a non-empty array")
        return None

    report.I(f"✓ Found {len(encounters)} encounters in index.json")

    seen_ids = set()
    for i, enc in enumerate(encounters):
        num = i + 1
        enc_id = enc.get('id', f'unknown_{num}')

        # Duplicate ID check
        if enc_id in seen_ids:
            report.E(f"Duplicate encounter ID: {enc_id}")
        seen_ids.add(enc_id)

        # Required index fields
        required = ['id', 'version', 'image_version', 'emoji', 'status', 'files',
                    'titles', 'subtitles', 'scripture_reference',
                    'estimated_reading_minutes', 'has_interactive',
                    'testament', 'character']
        for field in required:
            if field not in enc:
                report.E(f"Encounter {enc_id}: missing required field '{field}'")

        # Status
        status = enc.get('status', '')
        if status not in VALID_STATUSES:
            report.E(f"Encounter {enc_id}: invalid status '{status}', must be one of {VALID_STATUSES}")

        # Testament
        testament = enc.get('testament', '')
        if testament not in VALID_TESTAMENT:
            report.E(f"Encounter {enc_id}: invalid testament '{testament}', must be 'old' or 'new'")

        # Version format validation
        version = enc.get('version', '')
        if not re.match(r'^\d+\.\d+(\.\d+)?$', version):
            report.W(f"Encounter {enc_id}: version '{version}' should follow semantic versioning (e.g., '1.0' or '1.0.0')")

        # Image version format validation
        image_version = enc.get('image_version', '')
        if not re.match(r'^\d+\.\d+(\.\d+)?$', image_version):
            report.W(f"Encounter {enc_id}: image_version '{image_version}' should follow semantic versioning (e.g., '1.0' or '1.0.0')")

        # Language coverage for all language objects. Report once per encounter
        # (not once per field) so a Spanish-only draft doesn't produce five
        # near-identical warnings — and frame it by status: a coming_soon
        # encounter missing languages is expected (translation is a follow-up
        # step), a published one missing languages is a real gap.
        lang_objects = ['files', 'titles', 'subtitles', 'scripture_reference', 'estimated_reading_minutes']
        missing_by_field = {}
        present_langs = None
        for obj_key in lang_objects:
            obj = enc.get(obj_key, {})
            if not isinstance(obj, dict):
                report.E(f"Encounter {enc_id}: '{obj_key}' must be an object")
                continue
            langs = set(obj.keys())
            if present_langs is None:
                present_langs = langs
            missing = set(EXPECTED_LANGUAGES) - langs
            if missing:
                missing_by_field[obj_key] = missing

        if missing_by_field:
            all_same = len(set(map(frozenset, missing_by_field.values()))) == 1
            have = sorted(present_langs) if present_langs else []
            if all_same:
                missing_langs = sorted(next(iter(missing_by_field.values())))
                summary = f"missing {len(missing_langs)}/{len(EXPECTED_LANGUAGES)} languages {missing_langs} across all fields (has: {have})"
            else:
                parts = ", ".join(f"{k}: {sorted(v)}" for k, v in missing_by_field.items())
                summary = f"uneven language coverage — {parts}"

            if status == 'coming_soon':
                report.W(f"Encounter {enc_id}: {summary} — coming_soon, translation pending")
            else:
                report.W(f"Encounter {enc_id}: {summary} — encounter is published, translations should be complete")

        # File existence — only for published
        if status == 'published' and 'files' in enc:
            for lang, fname in enc['files'].items():
                fpath = ENCOUNTERS_DIR / lang / fname
                if not fpath.exists():
                    report.E(f"Encounter {enc_id}: listed file {lang}/{fname} does not exist")

        # Filename convention check
        if 'files' in enc:
            for lang, fname in enc['files'].items():
                expected = f"{enc_id.replace('_001', '')}_{lang}_001.json"
                if fname != expected:
                    report.W(f"Encounter {enc_id}: filename '{fname}' expected '{expected}'")

    report.I("✓ index.json structure validation complete")
    return data


# ── Phase B: File validation ──────────────────────────────────────────────────

def validate_encounter_file(data: dict, lang: str, filename: str,
                             enc_id: str, report: Report,
                             index_entry: Optional[dict] = None):
    """Validate a single encounter file."""

    # Quote / stray-punctuation anomaly scan across all text fields
    for path, text in _iter_strings(data):
        _check_quote_anomalies(text, f"{filename}:{path}", lang, report)

    # Required top-level fields
    required = ['id', 'type', 'schema_version', 'language', 'bible_version',
                'version', 'estimated_reading_minutes', 'meta', 'key_verse', 'cards']
    for field in required:
        if field not in data:
            report.E(f"{filename}: missing required field '{field}'")

    # id must match index
    internal_id = data.get('id', '')
    if not internal_id:
        report.E(f"{filename}: missing internal 'id' field")
    elif internal_id != enc_id:
        report.E(f"{filename}: internal 'id' field '{internal_id}' does not match index id '{enc_id}'")

    # schema_version
    if data.get('schema_version') != SCHEMA_VERSION:
        report.E(f"{filename}: schema_version must be '{SCHEMA_VERSION}', got '{data.get('schema_version')}'")

    # type
    if data.get('type') != 'encounter':
        report.E(f"{filename}: type must be 'encounter', got '{data.get('type')}'")

    # language field matches folder
    if data.get('language') != lang:
        report.E(f"{filename}: language field '{data.get('language')}' does not match folder '{lang}'")

    # bible_version
    allowed = _BIBLE_VERSIONS.get(lang, {}).get('allowed_versions', [])
    if data.get('bible_version') not in allowed:
        report.E(f"{filename}: bible_version '{data.get('bible_version')}' not valid for '{lang}', expected one of {allowed}")

    # meta block
    meta = data.get('meta', {})
    if not isinstance(meta, dict):
        report.E(f"{filename}: 'meta' must be an object")
    else:
        for field in ['character', 'testament', 'scripture_reference', 'mood_primary',
                      'accent_color', 'emoji', 'tags']:
            if field not in meta:
                report.E(f"{filename}: meta missing field '{field}'")
        if 'tags' in meta and not isinstance(meta['tags'], list):
            report.E(f"{filename}: meta.tags must be an array")
        if 'accent_color' in meta:
            if not re.match(r'^#[0-9a-fA-F]{6}$', meta.get('accent_color', '')):
                report.W(f"{filename}: meta.accent_color '{meta['accent_color']}' is not a valid hex color")
        if index_entry:
            for meta_key, index_key in [('emoji', 'emoji'), ('testament', 'testament')]:
                meta_val = meta.get(meta_key, '')
                index_val = index_entry.get(index_key, '')
                if meta_val and index_val and meta_val != index_val:
                    report.E(f"{filename}: meta.{meta_key} '{meta_val}' does not match index '{index_val}'")

    # key_verse
    kv = data.get('key_verse', {})
    if not isinstance(kv, dict):
        report.E(f"{filename}: 'key_verse' must be an object")
    else:
        for field in ['reference', 'text', 'bible_version']:
            if not kv.get(field):
                report.E(f"{filename}: key_verse missing or empty '{field}'")
        # bible_version inside key_verse must also match
        if kv.get('bible_version') not in allowed:
            report.E(f"{filename}: key_verse.bible_version '{kv.get('bible_version')}' not valid for '{lang}'")
        # Non-EN: reference should not use English book names
        if lang != 'en' and kv.get('reference'):
            if _has_english_book_name(kv['reference'], lang):
                report.E(f"{filename}: key_verse.reference has English book name: {kv['reference']}")

    # cards
    cards = data.get('cards', [])
    if not isinstance(cards, list) or len(cards) == 0:
        report.E(f"{filename}: 'cards' must be a non-empty array")
        return

    # Must end with completion card
    if cards[-1].get('type') != 'completion':
        report.E(f"{filename}: last card must be type 'completion', got '{cards[-1].get('type')}'")

    # Must have discovery_activation card
    card_types = [c.get('type') for c in cards]
    if 'discovery_activation' not in card_types:
        report.E(f"{filename}: missing required 'discovery_activation' card")

    # Order must be sequential
    for i, card in enumerate(cards):
        if card.get('order') != i + 1:
            report.W(f"{filename}: card {i+1} has order={card.get('order')}, expected {i+1}")

    # Per-card validation
    for card in cards:
        ctype = card.get('type', 'unknown')
        cidx = card.get('order', '?')
        ctx = f"{filename} card[{cidx}]({ctype})"

        # Unknown card type
        if ctype not in CARD_REQUIRED_KEYS:
            report.W(f"{ctx}: unknown card type '{ctype}'")

        # Required keys per card type
        required_keys = CARD_REQUIRED_KEYS.get(ctype, ['order', 'type', 'image_url'])
        for key in required_keys:
            if key not in card:
                report.E(f"{ctx}: missing required key '{key}'")
            elif isinstance(card[key], str) and not card[key].strip():
                report.E(f"{ctx}: field '{key}' is empty")

        # discovery_activation specific
        if ctype == 'discovery_activation':
            dqs = card.get('discovery_questions', [])
            if not dqs:
                report.E(f"{ctx}: discovery_questions is empty")
            else:
                for j, dq in enumerate(dqs):
                    for field in ['category', 'question']:
                        if not dq.get(field, '').strip():
                            report.E(f"{ctx} question[{j+1}]: '{field}' is empty")
            prayer = card.get('prayer', {})
            if not prayer.get('title', '').strip():
                report.E(f"{ctx}: prayer.title is empty")
            if not prayer.get('content', '').strip():
                report.E(f"{ctx}: prayer.content is empty")

        # verse_overlay validation
        vo = card.get('verse_overlay')
        if vo is not None:
            if not isinstance(vo, dict):
                report.E(f"{ctx}: verse_overlay must be an object")
            else:
                for field in ['reference', 'text']:
                    if not vo.get(field, '').strip():
                        report.E(f"{ctx}: verse_overlay.{field} is empty")
                if lang != 'en' and vo.get('reference'):
                    if _has_english_book_name(vo['reference'], lang):
                        report.E(f"{ctx}: verse_overlay.reference has English book name: {vo['reference']}")

        # completion specific
        if ctype == 'completion':
            cv = card.get('completion_verse', {})
            for field in ['reference', 'text', 'bible_version']:
                if not cv.get(field, '').strip():
                    report.E(f"{ctx}: completion_verse.{field} is empty")
            if cv.get('bible_version') not in allowed:
                report.E(f"{ctx}: completion_verse.bible_version '{cv.get('bible_version')}' not valid for '{lang}'")

        # scripture_moment specific
        if ctype == 'scripture_moment':
            for field in ['verse_reference', 'verse_text']:
                if not card.get(field, '').strip():
                    report.E(f"{ctx}: '{field}' is empty")
            if lang != 'en' and card.get('verse_reference'):
                if _has_english_book_name(card['verse_reference'], lang):
                    report.E(f"{ctx}: verse_reference has English book name: {card['verse_reference']}")

        # scripture_connections check
        for j, sc in enumerate(card.get('scripture_connections', [])):
            for field in ['reference', 'text']:
                if not sc.get(field, '').strip():
                    report.E(f"{ctx} scripture_connections[{j+1}]: '{field}' is empty")
            if lang != 'en' and sc.get('reference'):
                if _has_english_book_name(sc['reference'], lang):
                    report.E(f"{ctx} scripture_connections[{j+1}]: reference has English book name")


def validate_cross_translation(en_data: dict, trans_data: dict, lang: str,
                                filename: str, report: Report):
    """Validate translation against EN base: structure, counts, content."""
    en_cards = en_data.get('cards', [])
    tr_cards = trans_data.get('cards', [])

    # Card count
    if len(en_cards) != len(tr_cards):
        report.E(f"{filename}: card count mismatch — EN={len(en_cards)}, {lang.upper()}={len(tr_cards)}")

    for i, (ec, tc) in enumerate(zip(en_cards, tr_cards)):
        ctx = f"{filename} card[{ec.get('order','?')}]({ec.get('type','?')})"

        # type and order must match
        if ec.get('type') != tc.get('type'):
            report.E(f"{ctx}: type mismatch — EN='{ec.get('type')}', {lang.upper()}='{tc.get('type')}'")
        if ec.get('order') != tc.get('order'):
            report.E(f"{ctx}: order mismatch")

        # Key parity — no source key missing in translation
        for key in ec:
            if key not in tc:
                report.E(f"{ctx}: key '{key}' present in EN but missing in {lang.upper()}")

        # Reverse key parity — no extra/stray key in translation absent from EN
        for key in tc:
            if key not in ec:
                report.W(f"{ctx}: key '{key}' present in {lang.upper()} but missing in EN (possible extra/stray field)")

        # Text fields must be translated (non-empty, differ from EN)
        for field in ('title', 'subtitle', 'narrative', 'content', 'reflection',
                      'revelation_key', 'reflection_prompt'):
            if field in ec and field in tc:
                en_val = ec.get(field, '')
                tr_val = tc.get(field, '')
                if not tr_val or not str(tr_val).strip():
                    report.E(f"{ctx}: field '{field}' is empty in {lang.upper()}")
                elif isinstance(en_val, str) and isinstance(tr_val, str):
                    if en_val.strip() == tr_val.strip() and not _is_cognate(tr_val, lang):
                        report.W(f"{ctx}: field '{field}' appears untranslated")

        # discovery_questions count
        if ec.get('type') == 'discovery_activation':
            en_qs = ec.get('discovery_questions', [])
            tr_qs = tc.get('discovery_questions', [])
            if len(en_qs) != len(tr_qs):
                report.E(f"{ctx}: discovery_questions count mismatch EN={len(en_qs)}, {lang.upper()}={len(tr_qs)}")
            for j, (eq, tq) in enumerate(zip(en_qs, tr_qs)):
                for field in ('category', 'question'):
                    eq_val = eq.get(field, '').strip()
                    tq_val = tq.get(field, '').strip()
                    if eq_val == tq_val and not _is_cognate(tq_val, lang):
                        report.W(f"{ctx} question[{j+1}]: '{field}' appears untranslated")

        # scripture_connections count
        en_sc = ec.get('scripture_connections', [])
        tr_sc = tc.get('scripture_connections', [])
        if len(en_sc) != len(tr_sc):
            report.E(f"{ctx}: scripture_connections count mismatch EN={len(en_sc)}, {lang.upper()}={len(tr_sc)}")


def validate_encounter_files(report: Report, index_data: dict, lint_cache: dict) -> None:
    """Phase B: load and validate every published encounter's files, then
    cross-validate every non-EN language against the EN base."""
    report.I("=" * 60)
    report.I("PHASE B: Validating encounter files using EN as base")
    report.I("=" * 60)

    encounters = index_data['encounters']
    published = [e for e in encounters if e.get('status') == 'published']
    coming_soon = [e for e in encounters if e.get('status') == 'coming_soon']

    report.I(f"Published: {len(published)} | Coming soon: {len(coming_soon)} (skipped)")

    all_loaded = {}  # {lang: {enc_id: data}}

    for enc in published:
        enc_id = enc['id']
        files = enc.get('files', {})

        for lang, fname in files.items():
            fpath = ENCOUNTERS_DIR / lang / fname
            if not fpath.exists():
                continue  # already caught in Phase A

            data = lint_cache.get(fpath) or load_json(fpath, report)
            if data is None:
                continue

            # Individual file validation
            validate_encounter_file(data, lang, fname, enc_id, report, index_entry=enc)

            # has_interactive cross-check
            has_interactive_in_file = any(
                c.get('type') == 'interactive_moment'
                for c in data.get('cards', [])
            )
            index_has_interactive = enc.get('has_interactive', False)
            if has_interactive_in_file != index_has_interactive:
                report.E(
                    f"{fname}: index has_interactive={index_has_interactive} "
                    f"but file {'has' if has_interactive_in_file else 'does not have'} "
                    f"an interactive_moment card"
                )

            # Store for cross-validation
            if lang not in all_loaded:
                all_loaded[lang] = {}
            all_loaded[lang][enc_id] = data

    # Cross-validate all languages against EN
    report.I("Cross-validating all languages against EN base...")
    en_studies = all_loaded.get('en', {})

    for lang in EXPECTED_LANGUAGES:
        if lang == 'en':
            continue
        if lang not in all_loaded:
            continue
        for enc_id, en_data in en_studies.items():
            if enc_id in all_loaded[lang]:
                fname = f"{enc_id.replace('_001', '')}_{lang}_001.json"
                validate_cross_translation(
                    en_data, all_loaded[lang][enc_id],
                    lang, fname, report
                )

    # Verify all index file references exist
    report.I("Verifying all published index file references exist...")
    for enc in published:
        enc_id = enc['id']
        for lang, fname in enc.get('files', {}).items():
            fpath = ENCOUNTERS_DIR / lang / fname
            if not fpath.exists():
                report.E(f"index.json: encounter {enc_id} lists {lang}/{fname} but file does not exist")


# ── Phase C: Image URL verification ─────────────────────────────────────────
#
# Runs last, after Phase B (data integrity — the real gate). A broken or
# unreachable image is a content-completeness problem, not a structural one:
# it never blocks the release the way a malformed card or a translation gap
# does, so findings here are WARNINGs, not ERRORs, and never fail the run.

def validate_image_urls(report: Report) -> None:
    """Verify every image_url referenced in an encounter card resolves on the
    Devocionales-assets GitHub CDN. Reuses the reference-extraction and
    HTTP-checking classes from verify_image_urls.py — this phase is a thin
    adapter that feeds their results into the shared Report, it does not
    reimplement the checking logic."""
    report.I("=" * 60)
    report.I("PHASE C: Verifying image_url references resolve on the asset CDN")
    report.I("=" * 60)

    index_reader = ImageIndexReader(ENCOUNTERS_DIR)
    file_to_encounter_id = index_reader.build_file_to_encounter_id()

    extractor = ImageReferenceExtractor(ENCOUNTERS_DIR, file_to_encounter_id)
    references = extractor.extract()

    checker = GitHubAssetChecker()
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_REQUESTS) as pool:
        results = list(pool.map(checker.check, references))

    files_checked = len({r.reference.source_file for r in results})
    report.I(f"✓ Scanned {files_checked} encounter card files, {len(results)} unique images")

    failures = [r for r in results if not r.ok]
    for r in failures:
        report.W(
            f"{r.reference.encounter_id}/{r.reference.filename} "
            f"(referenced in {r.reference.source_file}): {r.status} "
            f"— {r.reference.url}"
        )

    if not failures:
        report.I(f"✓ All {len(results)} image references resolved")


# ── Main ──────────────────────────────────────────────────────────────────────

def run_phase(name: str, fn, *args, gate: bool = True, final: bool = False):
    """Run one validation phase: build its Report, call fn(report, *args),
    print the report, and (for gating phases) exit(1) on failure.

    fn may optionally return a value (e.g. Phase 1 returns a lint cache,
    Phase A returns parsed index data) — that return value is passed back
    to the caller unchanged so downstream phases can use it.

    gate=False (Phase C) prints the report but never exits on failure —
    used for phases whose findings are warnings-only by design.
    """
    report = Report(name)
    result = fn(report, *args)
    passed = report.print(final=final)

    if gate and not passed:
        print(f"\n❌ {name} FAILED - Stopping validation")
        sys.exit(1)

    return result


def main():
    print("🔍 Starting Encounters Validation...")
    print(f"📁 Encounters directory: {ENCOUNTERS_DIR}")
    print()

    lint_cache = run_phase("PHASE 1: LINT", validate_lint)
    index_data = run_phase("PHASE A: INDEX", validate_index)

    if index_data is None:
        print("\n❌ PHASE A FAILED - Stopping validation")
        sys.exit(1)

    run_phase("PHASE SOT: BIBLE VERSIONS SOURCE", validate_sot_source)
    run_phase("PHASE B: ENCOUNTER FILES", validate_encounter_files, index_data, lint_cache)

    # Phase C runs last, after the real gate (Phase B) has passed. Its
    # findings are warnings only (see validate_image_urls) — an unreachable
    # image never fails the run, so gate=False and it's always final.
    run_phase("PHASE C: IMAGE URLS", validate_image_urls, gate=False, final=True)

    sys.exit(0)


if __name__ == '__main__':
    main()
