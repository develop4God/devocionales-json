#!/usr/bin/env python3
"""
validate_encounters.py — Validator for the encounters content type.

This is the live validator, invoked by encounters_master_validator.py. Built
on shared_validation/ — Tier-1 concerns (identical logic shared with the
discovery pipeline) are delegated there: SOT fetch/cache, quote-anomaly
checks, lint, and the Report/RunReport contract. Tier-3 concerns
(card-schema dispatch, index structure, cross-translation policy) stay
local, since they encode encounters-specific rules that must not be shared
with discovery.

The prior validator (pre-shared_validation) is archived at
legacy/validate_encounters_legacy.py for reference — it is not executed by
any pipeline and receives no further changes.

  PHASE 1:   Lint — verify all JSON files use indent=2 formatting
  PHASE A:   Validate encounters/index.json
  PHASE SOT: Confirm bible_version codes resolved from the live remote SOT
  PHASE B:   Validate encounter files (published only) using EN as base — GATE
  PHASE C:   Verify image_url references resolve on the Devocionales-assets
             CDN — warnings only, runs last, never fails the build

Exit codes: 0 = all passed (Phase C warnings do not affect this), 1 = errors found in 1/A/SOT/B
"""

import re
import sys
from pathlib import Path
from typing import Optional


def _find_repo_root(start: Path) -> Path:
    """Walk upward from `start` looking for the shared_validation/ package,
    rather than assuming a fixed directory depth (which silently breaks if
    this script is ever moved). Raises clearly instead of resolving to the
    wrong place."""
    for candidate in [start, *start.parents]:
        if (candidate / 'shared_validation').is_dir():
            return candidate
    raise RuntimeError(
        f"Could not find shared_validation/ above {start} — "
        "is this script still inside the devocionales-json repo?"
    )


sys.path.insert(0, str(_find_repo_root(Path(__file__).resolve().parent)))
from shared_validation.report import Report
from shared_validation.run_report import RunReport
from shared_validation.bible_sot import load_bible_versions, REMOTE_INDEX_URL
from shared_validation.text_checks import (
    iter_strings, check_quote_anomalies, is_cognate,
)
from shared_validation.lint import lint_json_files

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


def validate_sot_source(report: Report, bible_versions: dict, used_remote_sot: bool,
                         last_fetch_error: Optional[Exception]) -> bool:
    """Report whether this run resolved bible_version codes from the live
    remote SOT or fell back to the temp-dir bible_versions cache.
    """
    if used_remote_sot:
        report.I(f"✓ bible_version codes resolved live from remote SOT ({REMOTE_INDEX_URL}) for all {len(bible_versions)} languages")
        return True
    reason = f" ({last_fetch_error})" if last_fetch_error else ""
    report.W(
        f"Could not reach remote SOT ({REMOTE_INDEX_URL}){reason} — fell back to the "
        f"temp-dir bible_versions cache. Results reflect the LOCAL CACHE, not confirmed "
        f"live data; re-run once network access is available before merging."
    )
    return True


def load_json(path: Path, report: Report) -> Optional[dict]:
    import json
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
    Delegates to shared_validation.lint with severity='error' to reproduce
    validate_encounters.py's existing gating behavior exactly.
    """
    report.I("=" * 60)
    report.I("PHASE 1: Lint — checking JSON formatting (indent=2)")
    report.I("=" * 60)

    cache = lint_json_files(ENCOUNTERS_DIR, report, 'encounters_scripts', severity='error')

    report.I(f"✓ Checked {len(cache)} JSON files")
    return cache


# ── Phase A: Index validation ─────────────────────────────────────────────────

def validate_index(report: Report, expected_languages: list) -> Optional[dict]:
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
            missing = set(expected_languages) - langs
            if missing:
                missing_by_field[obj_key] = missing

        if missing_by_field:
            all_same = len(set(map(frozenset, missing_by_field.values()))) == 1
            have = sorted(present_langs) if present_langs else []
            if all_same:
                missing_langs = sorted(next(iter(missing_by_field.values())))
                summary = f"missing {len(missing_langs)}/{len(expected_languages)} languages {missing_langs} across all fields (has: {have})"
            else:
                parts = ", ".join(f"{k}: {sorted(v)}" for k, v in missing_by_field.items())
                summary = f"uneven language coverage — {parts}"

            if status == 'coming_soon':
                report.W(f"Encounter {enc_id}: {summary} — coming_soon, translation pending")
            else:
                report.W(f"Encounter {enc_id}: {summary} — encounter is published, translations should be complete")

        # File existence — checked regardless of status: a listed file must exist
        if 'files' in enc:
            for lang, fname in enc['files'].items():
                fpath = ENCOUNTERS_DIR / lang / fname
                if not fpath.exists():
                    report.E(f"Encounter {enc_id}: listed file {lang}/{fname} does not exist")

        # coming_soon reminder — must be flipped to 'published' before shipping
        if status == 'coming_soon':
            report.W(f"Encounter {enc_id}: status is 'coming_soon' — flip to 'published' before release")

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
                             bible_versions: dict,
                             index_entry: Optional[dict] = None):
    """Validate a single encounter file."""

    # Quote / stray-punctuation anomaly scan across all text fields
    for path, text in iter_strings(data):
        check_quote_anomalies(text, f"{filename}:{path}", report)

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
    allowed = bible_versions.get(lang, {}).get('allowed_versions', [])
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
                    if en_val.strip() == tr_val.strip() and not is_cognate(tr_val, lang):
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
                    if eq_val == tq_val and not is_cognate(tq_val, lang):
                        report.W(f"{ctx} question[{j+1}]: '{field}' appears untranslated")

        # scripture_connections count
        en_sc = ec.get('scripture_connections', [])
        tr_sc = tc.get('scripture_connections', [])
        if len(en_sc) != len(tr_sc):
            report.E(f"{ctx}: scripture_connections count mismatch EN={len(en_sc)}, {lang.upper()}={len(tr_sc)}")


def validate_encounter_files(report: Report, index_data: dict, lint_cache: dict,
                              bible_versions: dict, expected_languages: list) -> None:
    """Phase B: load and validate every encounter's files (regardless of
    status), then cross-validate every non-EN language against the EN base."""
    report.I("=" * 60)
    report.I("PHASE B: Validating encounter files using EN as base")
    report.I("=" * 60)

    encounters = index_data['encounters']
    published = [e for e in encounters if e.get('status') == 'published']
    coming_soon = [e for e in encounters if e.get('status') == 'coming_soon']

    report.I(f"Published: {len(published)} | Coming soon: {len(coming_soon)}")

    all_loaded = {}  # {lang: {enc_id: data}}

    for enc in encounters:
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
            validate_encounter_file(data, lang, fname, enc_id, report, bible_versions, index_entry=enc)

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

    for lang in expected_languages:
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
    report.I("Verifying all index file references exist...")
    for enc in encounters:
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

def main():
    print("🔍 Starting Encounters Validation...")
    print(f"📁 Encounters directory: {ENCOUNTERS_DIR}")
    print()

    run_report = RunReport("ENCOUNTERS VALIDATION")

    bible_versions, used_remote_sot, last_fetch_error = load_bible_versions('encounters')
    expected_languages = list(bible_versions.keys())

    lint_cache = run_report.wrap("PHASE 1: LINT", validate_lint)
    index_data = run_report.wrap("PHASE A: INDEX", validate_index, expected_languages)

    if index_data is None:
        print("\n❌ PHASE A FAILED - Stopping validation")
        run_report.print_summary()
        sys.exit(1)

    run_report.wrap("PHASE SOT: BIBLE VERSIONS SOURCE", validate_sot_source, bible_versions, used_remote_sot, last_fetch_error)
    run_report.wrap("PHASE B: ENCOUNTER FILES", validate_encounter_files, index_data, lint_cache,
                     bible_versions, expected_languages)

    # Phase C runs last, after the real gate (Phase B) has passed. Its
    # findings are warnings only (see validate_image_urls); gate=False means
    # an unreachable image doesn't stop later phases from running, but any
    # warning it produces still fails the overall run via print_summary().
    run_report.wrap("PHASE C: IMAGE URLS", validate_image_urls, gate=False, final=True)

    encounters = index_data['encounters']
    published = [e for e in encounters if e.get('status') == 'published']
    coming_soon = [e for e in encounters if e.get('status') == 'coming_soon']
    run_report.add_coverage(
        content_units=len(encounters),
        published=len(published),
        coming_soon=len(coming_soon),
        files_scanned=len(lint_cache),
        languages_present=expected_languages,
        expected_languages=len(expected_languages),
        sot_live=used_remote_sot,
    )
    run_report.print_summary()

    sys.exit(run_report.exit_code)


if __name__ == '__main__':
    main()
