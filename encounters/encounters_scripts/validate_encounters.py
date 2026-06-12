#!/usr/bin/env python3
"""
validate_encounters.py — Validator for the encounters content type.

Two-phase validation:
  PHASE A: Validate encounters/index.json
  PHASE B: Validate encounter files (published only) using EN as base

Exit codes: 0 = all passed, 1 = errors found
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional

# ── Config ────────────────────────────────────────────────────────────────────

SCRIPTS_DIR = Path(__file__).parent
ENCOUNTERS_DIR = SCRIPTS_DIR.parent
INDEX_PATH = ENCOUNTERS_DIR / 'index.json'

SCHEMA_VERSION = 'encounters_v1'
VALID_STATUSES = {'published', 'coming_soon'}
VALID_TESTAMENT = {'old', 'new'}

# Load Bible versions from shared config
def _load_bible_versions() -> dict:
    path = SCRIPTS_DIR / 'bible_versions.json'
    return json.loads(path.read_text(encoding='utf-8'))['languages']

_BIBLE_VERSIONS = _load_bible_versions()
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


def _check_quote_anomalies(text: str, ctx: str, lang: str, report: 'Report'):
    """Flag stray/duplicated/unbalanced quote-like punctuation in a text field."""
    # Doubled identical quote-like characters back-to-back (e.g. »», "", '')
    for i in range(len(text) - 1):
        c = text[i]
        if c in _DOUBLE_CHECK_CHARS and text[i + 1] == c:
            report.E(f"{ctx}: contains doubled '{c}{c}' — likely stray punctuation")

    # Balanced guillemets (used in AR/FR/etc.)
    oc, cc = text.count('«'), text.count('»')
    if oc != cc:
        report.W(f"{ctx}: unbalanced '«'/'»' — {oc} open vs {cc} close")

    # Straight double quotes should appear in pairs
    if text.count('"') % 2 != 0:
        report.W(f"{ctx}: odd number of straight double quotes (\") — possible stray quote")


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

        # Language coverage for all language objects
        lang_objects = ['files', 'titles', 'subtitles', 'scripture_reference', 'estimated_reading_minutes']
        for obj_key in lang_objects:
            obj = enc.get(obj_key, {})
            if not isinstance(obj, dict):
                report.E(f"Encounter {enc_id}: '{obj_key}' must be an object")
                continue
            langs = set(obj.keys())
            missing = set(EXPECTED_LANGUAGES) - langs
            if missing:
                report.W(f"Encounter {enc_id}: '{obj_key}' missing languages: {sorted(missing)}")

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
                             enc_id: str, report: Report):
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

        # completion specific
        if ctype == 'completion':
            cv = card.get('completion_verse', {})
            for field in ['reference', 'text', 'bible_version']:
                if not cv.get(field, '').strip():
                    report.E(f"{ctx}: completion_verse.{field} is empty")

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
                    if en_val.strip() == tr_val.strip():
                        report.W(f"{ctx}: field '{field}' appears untranslated")

        # discovery_questions count
        if ec.get('type') == 'discovery_activation':
            en_qs = ec.get('discovery_questions', [])
            tr_qs = tc.get('discovery_questions', [])
            if len(en_qs) != len(tr_qs):
                report.E(f"{ctx}: discovery_questions count mismatch EN={len(en_qs)}, {lang.upper()}={len(tr_qs)}")
            for j, (eq, tq) in enumerate(zip(en_qs, tr_qs)):
                for field in ('category', 'question'):
                    if eq.get(field, '').strip() == tq.get(field, '').strip():
                        report.W(f"{ctx} question[{j+1}]: '{field}' appears untranslated")

        # scripture_connections count
        en_sc = ec.get('scripture_connections', [])
        tr_sc = tc.get('scripture_connections', [])
        if len(en_sc) != len(tr_sc):
            report.E(f"{ctx}: scripture_connections count mismatch EN={len(en_sc)}, {lang.upper()}={len(tr_sc)}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("🔍 Starting Encounters Validation...")
    print(f"📁 Encounters directory: {ENCOUNTERS_DIR}")
    print()

    # ── PHASE A ──
    report_a = Report("PHASE A: INDEX")
    index_data = validate_index(report_a)
    passed_a = report_a.print(final=False)

    if not passed_a or index_data is None:
        print("\n❌ PHASE A FAILED - Stopping validation")
        sys.exit(1)

    # ── PHASE B ──
    report_b = Report("PHASE B: ENCOUNTER FILES")
    report_b.I("=" * 60)
    report_b.I("PHASE B: Validating encounter files using EN as base")
    report_b.I("=" * 60)

    encounters = index_data['encounters']
    published = [e for e in encounters if e.get('status') == 'published']
    coming_soon = [e for e in encounters if e.get('status') == 'coming_soon']

    report_b.I(f"Published: {len(published)} | Coming soon: {len(coming_soon)} (skipped)")

    all_loaded = {}  # {lang: {enc_id: data}}

    for enc in published:
        enc_id = enc['id']
        files = enc.get('files', {})

        for lang, fname in files.items():
            fpath = ENCOUNTERS_DIR / lang / fname
            if not fpath.exists():
                continue  # already caught in Phase A

            data = load_json(fpath, report_b)
            if data is None:
                continue

            # Individual file validation
            validate_encounter_file(data, lang, fname, enc_id, report_b)

            # has_interactive cross-check
            has_interactive_in_file = any(
                c.get('type') == 'interactive_moment'
                for c in data.get('cards', [])
            )
            index_has_interactive = enc.get('has_interactive', False)
            if has_interactive_in_file != index_has_interactive:
                report_b.E(
                    f"{fname}: index has_interactive={index_has_interactive} "
                    f"but file {'has' if has_interactive_in_file else 'does not have'} "
                    f"an interactive_moment card"
                )

            # Store for cross-validation
            if lang not in all_loaded:
                all_loaded[lang] = {}
            all_loaded[lang][enc_id] = data

    # Cross-validate all languages against EN
    report_b.I("Cross-validating all languages against EN base...")
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
                    lang, fname, report_b
                )

    # Verify all index file references exist
    report_b.I("Verifying all published index file references exist...")
    for enc in published:
        enc_id = enc['id']
        for lang, fname in enc.get('files', {}).items():
            fpath = ENCOUNTERS_DIR / lang / fname
            if not fpath.exists():
                report_b.E(f"index.json: encounter {enc_id} lists {lang}/{fname} but file does not exist")

    passed_b = report_b.print(final=True)
    sys.exit(0 if passed_b else 1)


if __name__ == '__main__':
    main()
