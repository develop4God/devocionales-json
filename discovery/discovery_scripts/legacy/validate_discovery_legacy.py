#!/usr/bin/env python3
"""
=========================== ARCHIVED — 2026-07-11 ===========================
This file is NOT executed by any pipeline or master validator. It is kept
as a frozen, standalone reference only.

The live validator is ../validate_discovery.py, invoked by
discovery_master_validator.py. Edits to this file have no effect on
production validation.
===============================================================================

validate_discovery_legacy.py (originally validate_discovery.py) —
Comprehensive validation script for discovery study translations,
pre-shared_validation.

This script validates in two phases:
PHASE A: Validate index.json (format, structure, data integrity)
PHASE B: Validate translation files using index.json as source of truth

1. JSON format validity
2. No mixed languages in content
3. Structural consistency across translations
4. Field completeness and accuracy
5. Proper language codes and Bible versions
"""

import atexit
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple, Set, Optional
from collections import Counter

# Bible versions are resolved live from the remote SOT (source of truth):
# https://github.com/develop4God/bible_versions. To add a language or
# version, edit that repo — not a local file here.
REMOTE_INDEX_URL = "https://raw.githubusercontent.com/develop4God/bible_versions/refs/heads/main/index.json"
REMOTE_FETCH_ATTEMPTS = 3
REMOTE_FETCH_TIMEOUT = 15  # seconds, per attempt

# Local cache is a fallback for this run only when the network is
# unreachable. It lives in the system temp dir (never inside the repo) and
# is deleted on exit, so the SOT is always fetched fresh on the next run.
_LOCAL_CACHE_PATH = Path(tempfile.gettempdir()) / 'discovery_bible_versions_cache.json'


def _cleanup_local_cache() -> None:
    try:
        _LOCAL_CACHE_PATH.unlink(missing_ok=True)
    except OSError:
        pass


atexit.register(_cleanup_local_cache)


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
    a few times before giving up."""
    import time
    import urllib.request
    import urllib.error

    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(REMOTE_INDEX_URL, timeout=REMOTE_FETCH_TIMEOUT) as resp:
                return json.loads(resp.read())
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
            if attempt < attempts:
                time.sleep(min(2 ** attempt, 8))  # 2s, 4s, ...
    return None


def _write_local_cache(remote_langs: dict) -> None:
    payload = {
        'meta': {
            'source': f'Cached from {REMOTE_INDEX_URL} on last successful validator run',
            'note': 'Offline fallback only, valid for this run — never hand-edit.',
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


def _load_bible_versions() -> Tuple[dict, bool]:
    """Load bible version config for every language the remote SOT defines.

    Tries the live remote SOT first (source of truth, with retries); only
    falls back to the local temp cache if the network is unreachable after
    all attempts and a cache from earlier in this run exists.
    Returns (languages_dict, used_remote: bool) so callers can surface
    whether this run actually hit the live SOT or fell back to a cache.
    """
    remote = _fetch_remote_index()
    if remote is not None:
        remote_langs = remote.get('languages', {})
        _write_local_cache(remote_langs)
        return {lang: _remote_to_local_shape(entry) for lang, entry in remote_langs.items()}, True

    if _LOCAL_CACHE_PATH.exists():
        return json.loads(_LOCAL_CACHE_PATH.read_text(encoding='utf-8'))['languages'], False

    raise RuntimeError(
        f"Could not reach the Bible versions SOT at {REMOTE_INDEX_URL} "
        "and no local fallback cache is available. Check network connectivity."
    )

_BIBLE_VERSIONS, _USED_REMOTE_SOT = _load_bible_versions()

# Build EXPECTED_LANGUAGES directly from the SOT
EXPECTED_LANGUAGES = {
    lang: cfg['allowed_versions']
    for lang, cfg in _BIBLE_VERSIONS.items()
}

# Character patterns keyed by script (not language code) \u2014 the SOT's
# per-language 'script' field (see _BIBLE_VERSIONS) already identifies which
# writing system each language uses, so detection is driven by that instead
# of a hand-maintained language-code list that silently misses new languages.
SCRIPT_PATTERNS = {
    'latin': re.compile(r'[a-zA-Z]{3,}'),
    'cjk': re.compile(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]+'),
    'devanagari': re.compile(r'[\u0900-\u097F]+'),
    'arabic': re.compile(r'[\u0600-\u06FF]+'),
}

# Backward-compatible alias kept for the ja/zh-specific CJK check below,
# which needs the two individual language patterns rather than the
# unified 'cjk' script pattern.
LANGUAGE_PATTERNS = {
    'ja': re.compile(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]+'),  # Japanese
    'zh': re.compile(r'[\u4E00-\u9FFF]+'),  # Chinese
}


class ValidationReport:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.info = []
        self.stats = {
            'total_files': 0,
            'valid_json': 0,
            'invalid_json': 0,
            'languages_found': set(),
            'studies_found': set(),
            'pending_translations': []
        }
        self.phase = "INIT"

    def add_error(self, message: str):
        self.errors.append(f"❌ ERROR: {message}")

    def add_warning(self, message: str):
        self.warnings.append(f"⚠️  WARNING: {message}")

    def add_info(self, message: str):
        self.info.append(f"ℹ️  INFO: {message}")

    def print_report(self, final: bool = True):
        print("\n" + "=" * 80)
        if self.phase == "PHASE_A":
            print("PHASE A: INDEX VALIDATION REPORT")
        elif self.phase == "PHASE_B":
            print("PHASE B: TRANSLATION FILES VALIDATION REPORT")
        else:
            print("VALIDATION REPORT")
        print("=" * 80)
        
        if final:
            print(f"\n📊 STATISTICS:")
            print(f"  Total files checked: {self.stats['total_files']}")
            print(f"  Valid JSON files: {self.stats['valid_json']}")
            print(f"  Invalid JSON files: {self.stats['invalid_json']}")
            print(f"  Languages found: {', '.join(sorted(self.stats['languages_found']))}")
            print(f"  Studies found: {len(self.stats['studies_found'])}")
            if self.stats['pending_translations']:
                print(f"  Studies with pending translations: {len(self.stats['pending_translations'])}")

        if self.info:
            print(f"\nℹ️  INFORMATION ({len(self.info)}):")
            for msg in self.info:
                print(f"  {msg}")

        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for msg in self.warnings:
                print(f"  {msg}")

        if self.errors:
            print(f"\n❌ ERRORS ({len(self.errors)}):")
            for msg in self.errors:
                print(f"  {msg}")
            print("\n" + "=" * 80)
            return False
        else:
            if final:
                print(f"\n✅ ALL VALIDATIONS PASSED!")
            else:
                print(f"\n✅ PHASE PASSED - Proceeding to next phase")
            print("=" * 80)
            return True


def load_json_file(filepath: Path, report: ValidationReport) -> Dict:
    """Load and validate JSON file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            report.stats['valid_json'] += 1
            return data
    except json.JSONDecodeError as e:
        report.add_error(f"Invalid JSON in {filepath.name}: {e}")
        report.stats['invalid_json'] += 1
        return None
    except Exception as e:
        report.add_error(f"Error reading {filepath.name}: {e}")
        report.stats['invalid_json'] += 1
        return None


def detect_language_mix(text: str, expected_lang: str, report: ValidationReport, context: str) -> bool:
    """Detect if text contains mixed languages, driven by the SOT's per-language
    'script' field (latin/cjk/devanagari/arabic) rather than a hardcoded list of
    language codes, so every language the SOT defines is covered automatically.
    """
    if not text or len(text.strip()) < 3:
        return True

    script = _BIBLE_VERSIONS.get(expected_lang, {}).get('script')

    # For non-Latin scripts, check the expected script's characters are present
    if script and script != 'latin':
        pattern = SCRIPT_PATTERNS.get(script)
        if pattern and not pattern.search(text):
            report.add_warning(f"{context}: Expected {expected_lang} ({script}) characters but found none in: {text[:50]}...")
            return False

    # For Latin-script languages, check for unexpected CJK characters
    elif script == 'latin':
        if LANGUAGE_PATTERNS['ja'].search(text) or LANGUAGE_PATTERNS['zh'].search(text):
            report.add_error(f"{context}: Found Asian characters in {expected_lang} text: {text[:50]}...")
            return False

    return True


# Words identical (or near-identical) across English and Romance languages —
# valid cognate translations, not untranslated leftovers. Per translator skill
# § "Cognates (FR, PT, ES)": these are correct and should not be flagged.
_ROMANCE_COGNATES = {
    'fr': {'courage', 'grace', 'grâce'},
    'pt': {'coragem', 'graça'},
    'es': {'coraje', 'gracia'},
}


def _is_cognate(value: str, lang: str) -> bool:
    """Return True if value is a known valid cognate word for lang."""
    return value.strip().lower() in _ROMANCE_COGNATES.get(lang, set())


# Quote-like characters whose accidental back-to-back doubling indicates a
# stray-punctuation typo (e.g. »» , "" , '')
_DOUBLE_CHECK_CHARS = {'"', "'", '«', '»', '“', '”', '‘', '’'}

# Paired quote characters that should appear in balanced counts within a field.
# Note: curly double quotes (“ ” „) are intentionally NOT balance-checked here —
# this corpus mixes „...“ and „...” conventions across different German
# studies, so a fixed pair produces false positives. Guillemets « » are
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


def _check_quote_anomalies(text: str, ctx: str, lang: str, report: ValidationReport):
    """Flag stray/duplicated/unbalanced quote-like punctuation in a text field."""
    # Doubled identical quote-like characters back-to-back (e.g. »», "", '')
    for i in range(len(text) - 1):
        c = text[i]
        if c in _DOUBLE_CHECK_CHARS and text[i + 1] == c:
            report.add_error(f"{ctx}: contains doubled '{c}{c}' — likely stray punctuation")

    # Balanced guillemets (used in AR/FR/etc.). Skip fields that are the
    # trailing fragment of a quotation opened in a preceding verse — see
    # _is_verse_continuation_close.
    oc, cc = text.count('«'), text.count('»')
    if oc != cc and not (oc + cc == 1 and _is_verse_continuation_close(text, '«»')):
        report.add_warning(f"{ctx}: unbalanced '«'/'»' — {oc} open vs {cc} close")

    # Straight double quotes should appear in pairs, with the same
    # verse-continuation exception as guillemets above.
    if text.count('"') % 2 != 0 and not (text.count('"') == 1 and _is_verse_continuation_close(text, '"')):
        report.add_warning(f"{ctx}: odd number of straight double quotes (\") — possible stray quote")


def validate_structure(data: Dict, lang: str, filename: str, report: ValidationReport) -> bool:
    """Validate the structure of a discovery study file."""
    required_fields = ['id', 'type', 'date', 'title', 'subtitle', 'language',
                       'version', 'estimated_reading_minutes', 'key_verse',
                       'cards', 'tags', 'metadata']

    is_valid = True

    # Quote / stray-punctuation anomaly scan across all text fields
    for path, text in _iter_strings(data):
        _check_quote_anomalies(text, f"{filename}:{path}", lang, report)

    # Check required fields
    for field in required_fields:
        if field not in data:
            report.add_error(f"{filename}: Missing required field '{field}'")
            is_valid = False
    
    # Validate language and version
    if data.get('language') != lang:
        report.add_error(f"{filename}: Language mismatch - expected '{lang}', got '{data.get('language')}'")
        is_valid = False
    
    expected_versions = EXPECTED_LANGUAGES.get(lang)
    if expected_versions:
        if isinstance(expected_versions, list):
            if data.get('version') not in expected_versions:
                report.add_error(f"{filename}: Bible version mismatch - expected one of {expected_versions}, got '{data.get('version')}'")
                is_valid = False
        else:
            if data.get('version') != expected_versions:
                report.add_error(f"{filename}: Bible version mismatch - expected '{expected_versions}', got '{data.get('version')}'")
                is_valid = False
    
    # Validate cards array
    if 'cards' in data:
        if not isinstance(data['cards'], list):
            report.add_error(f"{filename}: 'cards' should be an array")
            is_valid = False
        elif len(data['cards']) == 0:
            report.add_error(f"{filename}: 'cards' array is empty")
            is_valid = False
    
    # Validate tags array
    if 'tags' in data:
        if not isinstance(data['tags'], list):
            report.add_error(f"{filename}: 'tags' should be an array")
            is_valid = False
        elif len(data['tags']) == 0:
            report.add_warning(f"{filename}: 'tags' array is empty")
    
    # Validate metadata
    if 'metadata' in data:
        if 'themes' not in data['metadata']:
            report.add_warning(f"{filename}: Missing 'themes' in metadata")
    
    return is_valid


def _check_key_parity(en_obj, trans_obj, path: str, filename: str, lang: str, report: ValidationReport):
    """Recursively diff en_obj vs trans_obj for data-integrity only — key
    presence and list length, not text content/quality. Generic over any
    field name and nesting depth so it covers discovery's 50+ free-form
    card types without a hand-maintained field list:
      - dict: every key EN has must exist in the translation (error); any
        key the translation has that EN lacks is reported once (warning —
        likely a stray/leftover field).
      - list: length mismatch is reported once (error) rather than walking
        past the shorter list and reporting per-missing-item noise.
    """
    if isinstance(en_obj, dict):
        trans_dict = trans_obj if isinstance(trans_obj, dict) else {}
        if not isinstance(trans_obj, dict):
            report.add_error(f"{filename}: '{path}' is an object in EN but not in {lang.upper()}")
            return
        for k in en_obj:
            child_path = f"{path}.{k}" if path else k
            if k not in trans_dict:
                report.add_error(f"{filename}: '{child_path}' present in EN but missing in {lang.upper()}")
            else:
                _check_key_parity(en_obj[k], trans_dict[k], child_path, filename, lang, report)
        for k in trans_dict:
            if k not in en_obj:
                report.add_warning(f"{filename}: '{path}.{k}' present in {lang.upper()} but missing in EN (possible extra/stray field)")

    elif isinstance(en_obj, list):
        trans_list = trans_obj if isinstance(trans_obj, list) else []
        if not isinstance(trans_obj, list):
            report.add_error(f"{filename}: '{path}' is an array in EN but not in {lang.upper()}")
            return
        if len(en_obj) != len(trans_list):
            report.add_error(
                f"{filename}: '{path}' length mismatch - EN has {len(en_obj)}, {lang.upper()} has {len(trans_list)}"
            )
            return
        for i, (ev, tv) in enumerate(zip(en_obj, trans_list)):
            _check_key_parity(ev, tv, f"{path}[{i}]", filename, lang, report)

    elif isinstance(en_obj, str):
        if not en_obj.strip():
            return
        if trans_obj is None or (isinstance(trans_obj, str) and not trans_obj.strip()):
            report.add_error(f"{filename}: '{path}' is empty in {lang.upper()}")


def validate_content_translation(en_data: Dict, trans_data: Dict, lang: str,
                                  filename: str, report: ValidationReport):
    """Validate translation has the same data shape as EN: same fields,
    same list lengths, no empty text where EN has content. Deliberately
    does not judge translation quality (identical-to-EN text is not
    flagged) — that's out of scope, this corpus has its own review
    pipeline for translation quality.
    """
    _check_key_parity(en_data, trans_data, "", filename, lang, report)

    # Validate each card structure
    for i, (en_card, trans_card) in enumerate(zip(en_data.get('cards', []),
                                                   trans_data.get('cards', []))):
        if en_card.get('type') != trans_card.get('type'):
            report.add_error(f"{filename}: Card {i+1} type mismatch")

        if en_card.get('order') != trans_card.get('order'):
            report.add_error(f"{filename}: Card {i+1} order mismatch")


def validate_verse_references(data: Dict, lang: str, filename: str,
                             report: ValidationReport):
    """Validate that verse references are in the correct language."""
    if lang == 'en':
        return  # English is the base language
    
    # Books that are the same or very similar across Romance languages
    # (Spanish, Portuguese, French) - these should not trigger errors
    common_books_romance = ['Job', 'Joel', 'Amos', 'Daniel', 'Ruth', 'Rut', 'Rute']

    # Books that are identical in German and English — must not be flagged as untranslated
    # (Psalm, Daniel, Hosea, Joel, Amos, Nahum, Ezra, Job, Ruth are the same in LU17/German)
    _DE_SHARED_BOOK_NAMES = {'Psalm', 'Psalms', 'Daniel', 'Hosea', 'Joel', 'Amos', 'Nahum',
                              'Ezra', 'Job', 'Ruth'}

    # Books that are identical in Filipino and English — must not be flagged as untranslated
    # (confirmed against bible_database/MBB05_fil.SQLite3 books.long_name: Genesis and Ezekiel
    # are spelled the same in Filipino Bible translations)
    _FIL_SHARED_BOOK_NAMES = {'Genesis', 'Ezekiel'}

    def _has_english_book_name(ref: str, pattern, lang: str) -> bool:
        """Return True only if ref contains an English book name that should be translated."""
        if not pattern.search(ref):
            return False
        if lang == 'de':
            # Psalm etc. are identical in German — not a false positive
            for shared in _DE_SHARED_BOOK_NAMES:
                if re.match(rf'\b{re.escape(shared)}\b', ref, re.IGNORECASE):
                    return False
        if lang == 'fil':
            # Genesis and Ezekiel are identical in Filipino — not a false positive
            for shared in _FIL_SHARED_BOOK_NAMES:
                if re.match(rf'\b{re.escape(shared)}\b', ref, re.IGNORECASE):
                    return False
        return True

    # Pattern to detect English Bible book names that SHOULD be translated
    # Exclude books that are commonly the same across languages
    if _BIBLE_VERSIONS.get(lang, {}).get('script') == 'latin' and lang != 'en':
        # For Romance/German languages, be less strict about common names
        english_bible_pattern = re.compile(
            r'\b(Genesis|Exodus|Leviticus|Numbers|Deuteronomy|Joshua|Judges|'
            r'Samuel|Kings|Chronicles|Ezra|Nehemiah|Esther|Psalm|Psalms|'
            r'Proverbs|Ecclesiastes|Song|Isaiah|Jeremiah|Lamentations|Ezekiel|'
            r'Hosea|Obadiah|Jonah|Micah|Nahum|Habakkuk|'
            r'Zephaniah|Haggai|Zechariah|Malachi|Matthew|Mark|Luke|John|Acts|'
            r'Romans|Corinthians|Galatians|Ephesians|Philippians|Colossians|'
            r'Thessalonians|Timothy|Titus|Philemon|Hebrews|James|Peter|Jude|'
            r'Revelation)\s+\d', re.IGNORECASE)
    else:
        # For non-Latin languages (CJK, Devanagari), all English names should be translated
        english_bible_pattern = re.compile(
            r'\b(Genesis|Exodus|Leviticus|Numbers|Deuteronomy|Joshua|Judges|Ruth|'
            r'Samuel|Kings|Chronicles|Ezra|Nehemiah|Esther|Job|Psalm|Psalms|'
            r'Proverbs|Ecclesiastes|Song|Isaiah|Jeremiah|Lamentations|Ezekiel|'
            r'Daniel|Hosea|Joel|Amos|Obadiah|Jonah|Micah|Nahum|Habakkuk|'
            r'Zephaniah|Haggai|Zechariah|Malachi|Matthew|Mark|Luke|John|Acts|'
            r'Romans|Corinthians|Galatians|Ephesians|Philippians|Colossians|'
            r'Thessalonians|Timothy|Titus|Philemon|Hebrews|James|Peter|Jude|'
            r'Revelation)\s+\d', re.IGNORECASE)
    
    # Check key_verse reference
    if 'key_verse' in data and 'reference' in data['key_verse']:
        ref = data['key_verse']['reference']
        if _has_english_book_name(ref, english_bible_pattern, lang):
            report.add_error(f"{filename}: key_verse reference has English book name: {ref}")
    
    # Check all card references
    for card_idx, card in enumerate(data.get('cards', [])):
        # Check greek_words references
        for gw_idx, gw in enumerate(card.get('greek_words', [])):
            if 'reference' in gw:
                ref = gw['reference']
                if _has_english_book_name(ref, english_bible_pattern, lang):
                    report.add_error(f"{filename}: card {card_idx+1} greek_word {gw_idx+1} reference has English: {ref}")
        
        # Check timeline event references
        for event_idx, event in enumerate(card.get('timeline', [])):
            if 'event' in event:
                ref = event['event']
                if _has_english_book_name(ref, english_bible_pattern, lang):
                    report.add_error(f"{filename}: card {card_idx+1} timeline {event_idx+1} has English reference: {ref}")
        
        # Check scripture_connections
        for sc_idx, sc in enumerate(card.get('scripture_connections', [])):
            if 'reference' in sc:
                ref = sc['reference']
                if _has_english_book_name(ref, english_bible_pattern, lang):
                    report.add_error(f"{filename}: card {card_idx+1} scripture_connection {sc_idx+1} has English: {ref}")
        
        # Check scripture_anchor
        if 'scripture_anchor' in card and 'reference' in card['scripture_anchor']:
            ref = card['scripture_anchor']['reference']
            if _has_english_book_name(ref, english_bible_pattern, lang):
                report.add_error(f"{filename}: card {card_idx+1} scripture_anchor has English: {ref}")


def validate_discovery_question_categories(data: Dict, lang: str, filename: str,
                                           report: ValidationReport):
    """Validate that discovery question categories are in the correct language."""
    if lang == 'en':
        return  # English is the base language
    
    # For Asian languages (ja, zh), categories should contain Asian characters
    if _BIBLE_VERSIONS.get(lang, {}).get('script') == 'cjk':
        # Pattern to detect English category names (capitalized English words)
        english_category_pattern = re.compile(r'^[A-Z][a-z]+(\s+[a-z]+)*$')
        
        for card_idx, card in enumerate(data.get('cards', [])):
            for dq_idx, dq in enumerate(card.get('discovery_questions', [])):
                category = dq.get('category', '')
                if category and english_category_pattern.match(category):
                    # For Asian languages, capitalized English-looking text is wrong
                    report.add_error(f"{filename}: card {card_idx+1} discovery_question {dq_idx+1} category is in English: '{category}'")
    
    # For Romance languages (es, pt, fr), we can't use simple pattern matching
    # because their category names look similar to English (capitalized words)
    # Instead, we check for exact matches of known English categories
    elif _BIBLE_VERSIONS.get(lang, {}).get('script') == 'latin' and lang != 'en':
        # EXACT English categories that should never appear in translations
        # Note: Excludes cognates that are spelled the same in French/Spanish/Portuguese
        # (e.g., "Transformation", "Gratitude", "Mission" are valid in French)
        exact_english_cats = {
            'Self-evaluation', 'Evidence', 'Surrender', 'Freedom', 
            'Identity', 'Knowledge', 'Voice', 'Trust',
            'Shame', 'Obedience', 'Creation',
            'Light vs Darkness', 'Veiled Glory', 'Listening', 'Presence',
            'Hope', 'Personal', 'Revelation', 'Worship',
            'Intimacy', 'Protection', 'Provision', 'Confidence',
            'Separation', 'Access', 'Security', 'Victory', 'Promise'
            # Note: 'Transformation', 'Gratitude', and 'Mission' are cognates (same in French)
        }
        
        for card_idx, card in enumerate(data.get('cards', [])):
            for dq_idx, dq in enumerate(card.get('discovery_questions', [])):
                category = dq.get('category', '')
                # Only flag if it's an EXACT match to English
                if category in exact_english_cats:
                    report.add_error(f"{filename}: card {card_idx+1} discovery_question {dq_idx+1} category is in English: '{category}'")


def validate_no_english_in_translation(data: Dict, lang: str, filename: str, 
                                       report: ValidationReport):
    """Check that non-English files don't contain English content."""
    if lang == 'en':
        return
    
    # For JA and ZH, tags should be translated (not in English)
    # Detect English tags by checking for vowels (a,e,i,o,u)
    if _BIBLE_VERSIONS.get(lang, {}).get('script') == 'cjk':
        tags = data.get('tags', [])
        english_tags = []
        for tag in tags:
            tag_str = str(tag).lower()
            # If tag contains English vowels, it's likely English
            # Exception: Greek transliterations may contain vowels
            if any(char in tag_str for char in 'aeiou'):
                # Allow Greek word transliterations (typically end with 'ō' or contain Greek patterns)
                # Examples: emphysaō, tarassō, agapaō_phileō
                if not (tag_str.endswith('ō') or 'ō' in tag_str):
                    english_tags.append(tag)
        
        if english_tags:
            report.add_error(f"{filename}: Found English tags in {lang.upper()} (should be translated): {', '.join(english_tags[:5])}")
    
    # Check themes for English
    themes = data.get('metadata', {}).get('themes', [])
    if _BIBLE_VERSIONS.get(lang, {}).get('script') == 'cjk':
        for theme in themes:
            if not LANGUAGE_PATTERNS[lang].search(str(theme)):
                # Check if it looks like English
                if re.search(r'\b[A-Z][a-z]+(\s+[a-z]+){2,}\b', str(theme)):
                    report.add_warning(f"{filename}: Theme may be in English: {theme[:50]}")


def validate_filename_format(filepath: Path, lang: str, report: ValidationReport) -> bool:
    """Validate that filename follows the correct naming convention."""
    filename = filepath.name
    
    # Expected pattern: {study_name}_{lang_code}_001.json
    # Examples: cana_wedding_en_001.json, gethsemane_agony_es_001.json, zechariah_14_return_en_001.json
    pattern = re.compile(r'^[a-z0-9_]+_(' + '|'.join(EXPECTED_LANGUAGES.keys()) + r')_001\.json$')
    
    if not pattern.match(filename):
        report.add_error(f"{filename}: Invalid filename format. Expected pattern: {{study_name}}_{{lang}}_001.json")
        return False
    
    # Verify the language code in filename matches the directory
    lang_in_filename = filename.split('_')[-2]
    if lang_in_filename != lang:
        report.add_error(f"{filename}: Language code mismatch - file is in {lang}/ directory but filename contains '{lang_in_filename}'")
        return False
    
    return True


def validate_sot_source(report: ValidationReport) -> None:
    """Report whether this run resolved bible_version codes from the live
    remote SOT or fell back to the temp-dir bible_versions cache, so a run
    that silently used stale cached data (e.g. offline CI) is visible in
    the report instead of indistinguishable from a fully live run.
    """
    if _USED_REMOTE_SOT:
        report.add_info(f"✓ bible_version codes resolved live from remote SOT ({REMOTE_INDEX_URL}) for all {len(_BIBLE_VERSIONS)} languages")
    else:
        report.add_warning(
            f"Could not reach remote SOT ({REMOTE_INDEX_URL}) — fell back to the "
            f"temp-dir bible_versions cache. Results reflect the LOCAL CACHE, not confirmed "
            f"live data; re-run once network access is available before merging."
        )


def validate_lint(discovery_dir: Path, report: ValidationReport) -> None:
    """Check that all JSON files use indent=2 formatting and end with a
    trailing newline. Formatting issues are warnings, not errors — they
    don't affect JSON validity, just diff/lint hygiene.
    """
    report.add_info("=" * 60)
    report.add_info("PHASE 1: Lint — checking JSON formatting (indent=2)")
    report.add_info("=" * 60)

    json_files = sorted(f for f in discovery_dir.rglob('*.json')
                         if f.is_file() and 'discovery_scripts' not in f.parts)
    checked = 0
    for fpath in json_files:
        raw = fpath.read_text(encoding='utf-8')
        try:
            json.loads(raw)
        except json.JSONDecodeError:
            continue  # invalid JSON is reported elsewhere with full detail
        rel = fpath.relative_to(discovery_dir)
        for line_no, line in enumerate(raw.splitlines(), 1):
            stripped = line.lstrip(' ')
            indent = len(line) - len(stripped)
            if indent > 0 and indent % 2 != 0:
                report.add_warning(f"{rel}:{line_no}: odd indentation ({indent} spaces), expected multiples of 2")
                break
            if '\t' in line:
                report.add_warning(f"{rel}:{line_no}: contains tab character, use 2-space indent")
                break
        if not raw.endswith('\n'):
            report.add_warning(f"{rel}: missing trailing newline")
        checked += 1

    report.add_info(f"✓ Checked {checked} JSON files")


def validate_index_json(discovery_dir: Path, report: ValidationReport) -> Optional[Dict]:
    """
    PHASE A: Validate index.json format, structure, and data integrity.
    Returns the index data if valid, None if errors found.
    """
    report.phase = "PHASE_A"
    report.add_info("=" * 60)
    report.add_info("PHASE A: Validating index.json")
    report.add_info("=" * 60)
    
    index_path = discovery_dir / 'index.json'
    
    # Check if index.json exists
    if not index_path.exists():
        report.add_error("index.json not found in discovery directory")
        return None
    
    # Load and validate JSON format
    try:
        with open(index_path, 'r', encoding='utf-8') as f:
            index_data = json.load(f)
            report.stats['valid_json'] += 1
            report.add_info("✓ index.json is valid JSON")
    except json.JSONDecodeError as e:
        report.add_error(f"index.json has invalid JSON syntax: {e}")
        report.stats['invalid_json'] += 1
        return None
    except Exception as e:
        report.add_error(f"Error reading index.json: {e}")
        return None
    
    # Validate required top-level structure
    if 'studies' not in index_data:
        report.add_error("index.json missing required 'studies' array")
        return None
    
    if not isinstance(index_data['studies'], list):
        report.add_error("index.json 'studies' must be an array")
        return None
    
    if len(index_data['studies']) == 0:
        report.add_error("index.json 'studies' array is empty")
        return None
    
    report.add_info(f"✓ Found {len(index_data['studies'])} studies in index.json")
    
    # Validate each study entry
    study_ids = set()
    pending_studies = []
    
    for idx, study in enumerate(index_data['studies']):
        study_num = idx + 1
        
        # Check required fields
        required_fields = ['id', 'version', 'emoji', 'files', 'titles', 'subtitles', 'estimated_reading_minutes']
        for field in required_fields:
            if field not in study:
                report.add_error(f"Study #{study_num}: Missing required field '{field}'")
                continue
        
        study_id = study.get('id', f'unknown_{study_num}')
        
        # Check for duplicate IDs
        if study_id in study_ids:
            report.add_error(f"Duplicate study ID: {study_id}")
        study_ids.add(study_id)
        
        # Validate files object
        if 'files' in study:
            if not isinstance(study['files'], dict):
                report.add_error(f"Study {study_id}: 'files' must be an object")
            else:
                files = study['files']
                langs_in_study = set(files.keys())
                
                # Check if all expected languages are present
                expected_langs = set(EXPECTED_LANGUAGES.keys())
                missing_langs = expected_langs - langs_in_study
                
                if missing_langs:
                    pending_studies.append({
                        'id': study_id,
                        'missing_languages': sorted(missing_langs)
                    })
                    report.add_warning(f"Study {study_id}: Missing translations for {sorted(missing_langs)}")
                
                # Validate filename format for each language
                for lang, filename in files.items():
                    if lang not in EXPECTED_LANGUAGES:
                        report.add_error(f"Study {study_id}: Unknown language code '{lang}'")
                    
                    # Check filename format
                    expected_filename = f"{study_id.replace('_001', '')}_{lang}_001.json"
                    if filename != expected_filename:
                        report.add_warning(f"Study {study_id}: File for {lang} is '{filename}', expected '{expected_filename}'")
        
        # Validate titles object
        if 'titles' in study:
            if not isinstance(study['titles'], dict):
                report.add_error(f"Study {study_id}: 'titles' must be an object")
            else:
                # Check that titles match the files languages
                if 'files' in study:
                    title_langs = set(study['titles'].keys())
                    file_langs = set(study['files'].keys())
                    if title_langs != file_langs:
                        report.add_warning(f"Study {study_id}: Title languages {sorted(title_langs)} don't match file languages {sorted(file_langs)}")
        
        # Validate subtitles object
        if 'subtitles' in study:
            if not isinstance(study['subtitles'], dict):
                report.add_error(f"Study {study_id}: 'subtitles' must be an object")
            else:
                # Check that subtitles match the files languages
                if 'files' in study:
                    subtitle_langs = set(study['subtitles'].keys())
                    file_langs = set(study['files'].keys())
                    if subtitle_langs != file_langs:
                        report.add_warning(f"Study {study_id}: Subtitle languages {sorted(subtitle_langs)} don't match file languages {sorted(file_langs)}")
        
        # Validate estimated_reading_minutes
        if 'estimated_reading_minutes' in study:
            if not isinstance(study['estimated_reading_minutes'], dict):
                report.add_error(f"Study {study_id}: 'estimated_reading_minutes' must be an object")
    
    # Store pending translations info
    report.stats['pending_translations'] = pending_studies
    
    if pending_studies:
        report.add_info(f"Found {len(pending_studies)} studies with incomplete translations")
        for pending in pending_studies:
            report.add_info(f"  - {pending['id']}: PENDING {', '.join(pending['missing_languages'])}")
    
    report.add_info(f"✓ index.json structure validation complete")
    
    return index_data


def main():
    # Get discovery directory. legacy/ lives one level below the original
    # discovery_scripts/ location, so an extra .parent is needed here.
    script_dir = Path(__file__).parent.parent
    discovery_dir = script_dir.parent
    
    report = ValidationReport()
    
    print("🔍 Starting Discovery Studies Validation...")
    print(f"📁 Discovery directory: {discovery_dir}")
    print()
    
    # ==========================================
    # PHASE 1: Lint — JSON formatting
    # ==========================================
    validate_lint(discovery_dir, report)

    # ==========================================
    # SOT source visibility — live remote vs. offline cache
    # ==========================================
    validate_sot_source(report)

    # ==========================================
    # PHASE A: Validate index.json
    # ==========================================
    index_data = validate_index_json(discovery_dir, report)
    
    # Print Phase A report
    phase_a_success = report.print_report(final=False)
    
    if not phase_a_success or index_data is None:
        print("\n❌ PHASE A FAILED - Stopping validation")
        print("Please fix index.json errors before validating translation files")
        return 1
    
    # Extract study IDs from index.json to use as source of truth
    index_studies = {}
    for study in index_data['studies']:
        study_id = study['id']
        index_studies[study_id] = study
    
    # ==========================================
    # PHASE B: Validate translation files
    # ==========================================
    report.phase = "PHASE_B"
    report.errors = []  # Reset errors for Phase B
    report.warnings = []  # Reset warnings for Phase B
    report.info = []  # Reset info for Phase B
    
    report.add_info("=" * 60)
    report.add_info("PHASE B: Validating translation files using index.json")
    report.add_info("=" * 60)
    
    # Store all loaded data for cross-validation
    all_studies = {}
    
    # Validate each language folder
    for lang, expected_versions in EXPECTED_LANGUAGES.items():
        lang_dir = discovery_dir / lang
        
        if not lang_dir.exists():
            report.add_warning(f"Missing language folder: {lang}")
            continue
        
        report.stats['languages_found'].add(lang)
        if isinstance(expected_versions, list):
            report.add_info(f"Checking {lang.upper()} folder with versions: {', '.join(expected_versions)}")
        else:
            report.add_info(f"Checking {lang.upper()} folder with {expected_versions}")
        
        # Load all files for this language
        lang_studies = {}
        
        # Get all JSON files in this language directory
        for filepath in lang_dir.glob('*_001.json'):
            filename = filepath.name
            # Extract study_id from filename (e.g., "born_again_en_001.json" -> "born_again_001")
            study_base = filename.replace(f'_{lang}_001.json', '_001')
            
            report.stats['total_files'] += 1
            
            # Validate filename format
            validate_filename_format(filepath, lang, report)
            
            # Load and validate JSON
            data = load_json_file(filepath, report)
            if data is None:
                continue
            
            # Validate structure
            validate_structure(data, lang, filename, report)
            
            # Store for cross-validation
            lang_studies[study_base] = data
            
            # Validate no English in translations
            validate_no_english_in_translation(data, lang, filename, report)
            
            # Validate verse references are in correct language
            validate_verse_references(data, lang, filename, report)
            
            # Validate discovery question categories are translated
            validate_discovery_question_categories(data, lang, filename, report)
            
            # Track study IDs
            if data.get('id'):
                report.stats['studies_found'].add(data['id'])

            # Index integrity check
            # Verify internal id field matches index.json (single source of truth)
            internal_id = data.get('id', '')
            if not internal_id:
                report.add_error(f"{filename}: missing internal 'id' field")
            elif internal_id not in index_studies:
                report.add_error(
                    f"{filename}: internal 'id' field '{internal_id}' is not registered "
                    f"in index.json — file may be orphaned or have an incorrect id"
                )
            elif study_base != internal_id:
                report.add_error(
                    f"{filename}: internal 'id' field '{internal_id}' does not match "
                    f"filename-derived id '{study_base}' — must be consistent"
                )
        
        all_studies[lang] = lang_studies
    
    # Cross-validate translations against English using index.json as source
    if 'en' in all_studies:
        for lang in EXPECTED_LANGUAGES:
            if lang == 'en' or lang not in all_studies:
                continue
            
            # Use index_studies instead of EXPECTED_STUDIES
            for study_id in index_studies.keys():
                if study_id in all_studies['en'] and study_id in all_studies[lang]:
                    filename = f"{study_id.replace('_001', '')}_{lang}_001.json"
                    validate_content_translation(
                        all_studies['en'][study_id],
                        all_studies[lang][study_id],
                        lang,
                        filename,
                        report
                    )
    
    # Verify that files listed in index actually exist
    report.add_info("Verifying all index.json file references exist...")
    for study_id, study in index_studies.items():
        files = study.get('files', {})
        for lang, filename in files.items():
            filepath = discovery_dir / lang / filename
            if not filepath.exists():
                report.add_error(f"index.json: Study {study_id} lists {lang}/{filename} but file doesn't exist")
    
    # Print final report
    success = report.print_report(final=True)
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
