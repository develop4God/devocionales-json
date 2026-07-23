#!/usr/bin/env python3
"""
validate_discovery.py — Validator for discovery study translations.

This is the live validator, invoked by discovery_master_validator.py. Built
on shared_validation/ — Tier-1 concerns (identical logic shared with the
encounters pipeline) are delegated there: SOT fetch/cache, quote-anomaly
checks, and lint. Tier-3 concerns (Phase A index structure, key-parity
policy) stay local, since they encode discovery-specific rules that must
not be shared with encounters.

Note: discovery's ValidationReport (stats-tracking, add_error/add_warning/
add_info naming, hand-reset phase state) is kept as-is here rather than
swapped for shared_validation.report.Report — the two have different output
formats, and reconciling them is a separate future decision, not required
for this script to be the live validator.

The prior validator (pre-shared_validation) is archived at
legacy/validate_discovery_legacy.py for reference — it is not executed by
any pipeline and receives no further changes.

PHASE A: Validate index.json (format, structure, data integrity)
PHASE B: Validate translation files using index.json as source of truth
"""

import json
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple, Set, Optional
from collections import Counter


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
from shared_validation.run_report import RunReport
from shared_validation.bible_sot import load_bible_versions, REMOTE_INDEX_URL
from shared_validation.text_checks import (
    iter_strings, check_quote_anomalies, check_halfwidth_colon_in_title,
    check_greek_hebrew_transliteration, is_cognate,
)
from shared_validation.lint import lint_json_files
from shared_validation.scripture_check import (
    ScriptureValidator, find_scripture_pairs, validate_pair, validate_translated_pair,
    scripture_validation_enabled,
)

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

    # E/W/I aliases satisfying shared_validation's ReportLike protocol
    # (check_quote_anomalies, lint_json_files) without changing this
    # class's own output format or existing add_* call sites.
    E = add_error
    W = add_warning
    I = add_info

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

        # On a fully clean pass, RunReport's rollup already covers what ran
        # and how it went — the full per-message INFO dump here is only
        # worth the noise when there's a warning/error to give context for.
        clean = not self.errors and not self.warnings
        if self.info and not clean:
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


def validate_structure(data: Dict, lang: str, filename: str, report: ValidationReport,
                        expected_languages: dict) -> bool:
    """Validate the structure of a discovery study file."""
    required_fields = ['id', 'type', 'date', 'title', 'subtitle', 'language',
                       'version', 'estimated_reading_minutes', 'key_verse',
                       'cards', 'tags', 'metadata']

    is_valid = True

    # Quote / stray-punctuation anomaly scan across all text fields
    for path, text in iter_strings(data):
        check_quote_anomalies(text, f"{filename}:{path}", report)
        check_halfwidth_colon_in_title(text, path, lang, f"{filename}:{path}", report)
        check_greek_hebrew_transliteration(text, path, f"{filename}:{path}", report)

    # Check required fields
    for field in required_fields:
        if field not in data:
            report.add_error(f"{filename}: Missing required field '{field}'")
            is_valid = False

    # Validate language and version
    if data.get('language') != lang:
        report.add_error(f"{filename}: Language mismatch - expected '{lang}', got '{data.get('language')}'")
        is_valid = False

    expected_versions = expected_languages.get(lang)
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
                             report: ValidationReport, bible_versions: dict):
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
    if bible_versions.get(lang, {}).get('script') == 'latin' and lang != 'en':
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


def validate_filename_format(filepath: Path, lang: str, report: ValidationReport,
                              expected_languages: dict) -> bool:
    """Validate that filename follows the correct naming convention."""
    filename = filepath.name

    # Expected pattern: {study_name}_{lang_code}_001.json
    # Examples: cana_wedding_en_001.json, gethsemane_agony_es_001.json, zechariah_14_return_en_001.json
    pattern = re.compile(r'^[a-z0-9_]+_(' + '|'.join(expected_languages.keys()) + r')_001\.json$')

    if not pattern.match(filename):
        report.add_error(f"{filename}: Invalid filename format. Expected pattern: {{study_name}}_{{lang}}_001.json")
        return False

    # Verify the language code in filename matches the directory
    lang_in_filename = filename.split('_')[-2]
    if lang_in_filename != lang:
        report.add_error(f"{filename}: Language code mismatch - file is in {lang}/ directory but filename contains '{lang_in_filename}'")
        return False

    return True


def validate_sot_source(report: ValidationReport, used_remote_sot: bool, bible_versions: dict) -> None:
    """Report whether this run resolved bible_version codes from the live
    remote SOT or fell back to the temp-dir bible_versions cache, so a run
    that silently used stale cached data (e.g. offline CI) is visible in
    the report instead of indistinguishable from a fully live run.
    """
    if used_remote_sot:
        report.add_info(f"✓ bible_version codes resolved live from remote SOT ({REMOTE_INDEX_URL}) for all {len(bible_versions)} languages")
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

    Delegates to shared_validation.lint with severity='warning' to
    reproduce validate_discovery.py's existing (non-gating) behavior.
    """
    report.add_info("=" * 60)
    report.add_info("PHASE 1: Lint — checking JSON formatting (indent=2)")
    report.add_info("=" * 60)

    cache = lint_json_files(discovery_dir, report, 'discovery_scripts', severity='warning')

    report.add_info(f"✓ Checked {len(cache)} JSON files")


def validate_index_json(discovery_dir: Path, report: ValidationReport,
                         expected_languages: dict) -> Optional[Dict]:
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
                expected_langs = set(expected_languages.keys())
                missing_langs = expected_langs - langs_in_study

                if missing_langs:
                    pending_studies.append({
                        'id': study_id,
                        'missing_languages': sorted(missing_langs)
                    })
                    report.add_warning(f"Study {study_id}: Missing translations for {sorted(missing_langs)}")

                # Validate filename format for each language
                for lang, filename in files.items():
                    if lang not in expected_languages:
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


# ── Phase: Scripture references ─────────────────────────────────────────────
#
# Verifies every {reference, verse_text}-shaped pair actually resolves
# against the Bible version cited for that file, and that the stored text
# matches the resolved text closely enough (fuzzy match — see
# shared_validation.scripture_check). WARNING-only for this initial
# rollout — see the issue's Rollout section. Runs after Phase B (the real
# gate) so scripture findings never block the release while the fuzzy-match
# threshold is being tuned. Shares shared_validation.scripture_check with
# encounters' equivalent phase — no corpus-specific duplication of the
# validation logic itself.

def validate_scripture_references(report: 'ValidationReport', all_studies: dict,
                                    bible_database_dir: Path, only_lang: Optional[str] = None) -> None:
    """Resolve every scripture reference found in every loaded study file
    and fuzzy-match its stored verse text against the resolved text.

    EN studies resolve directly (validate_pair). Non-EN studies never
    parse their own native-language reference string — cards align 1:1 by
    position with the EN study (guaranteed by Phase B's parity check), so
    each translated reference is validated against its EN sibling's
    reference via validate_translated_pair (see shared_validation.
    scripture_check module docstring for why).

    only_lang restricts the scan to a single language's studies (EN is
    still loaded as the sibling source for non-EN languages) — for fast
    local iteration on one language's findings without scanning the full
    10-language corpus."""
    report.add_info("=" * 60)
    report.add_info("PHASE: SCRIPTURE REFERENCES" + (f" ({only_lang})" if only_lang else ""))
    report.add_info("=" * 60)

    pairs_checked = 0
    resolution_failures = 0
    text_mismatches = 0
    warned_versions = set()
    en_studies = all_studies.get('en', {})

    with ScriptureValidator(bible_database_dir) as validator:
        for lang, lang_studies in all_studies.items():
            if only_lang and lang != only_lang:
                continue
            for study_id, data in lang_studies.items():
                bible_version = data.get('version')
                if not bible_version:
                    continue

                resolver = validator.get_resolver(bible_version, lang)
                if resolver is None:
                    if (lang, bible_version) not in warned_versions:
                        report.add_warning(
                            f"No local Bible DB found for bible_version '{bible_version}' "
                            f"(lang '{lang}', study '{study_id}') — skipping scripture checks for this version"
                        )
                        warned_versions.add((lang, bible_version))
                    continue

                if lang == 'en':
                    for ref in find_scripture_pairs(data):
                        pairs_checked += 1
                        finding = validate_pair(ref, resolver)
                        if finding is None:
                            continue
                        if finding.kind == "resolution_failed":
                            resolution_failures += 1
                        else:
                            text_mismatches += 1
                        report.add_warning(f"{study_id}: {finding.message}")
                    continue

                en_data = en_studies.get(study_id)
                if en_data is None:
                    report.add_warning(f"{study_id} ({lang}): no EN sibling study found — skipping scripture checks")
                    continue

                en_pairs = find_scripture_pairs(en_data)
                native_pairs = find_scripture_pairs(data)
                if len(native_pairs) != len(en_pairs):
                    report.add_warning(
                        f"{study_id} ({lang}): scripture pair count ({len(native_pairs)}) doesn't match "
                        f"EN sibling ({len(en_pairs)}) — skipping scripture checks (cards likely out of sync, see Phase B)"
                    )
                    continue

                for en_ref, native_ref in zip(en_pairs, native_pairs):
                    pairs_checked += 1
                    finding = validate_translated_pair(en_ref, native_ref, resolver, bible_version)
                    if finding is None:
                        continue
                    if finding.kind == "resolution_failed":
                        resolution_failures += 1
                    else:
                        text_mismatches += 1
                    report.add_warning(f"{study_id}: {finding.message}")

    report.add_info(
        f"✓ Checked {pairs_checked} scripture reference(s): "
        f"{resolution_failures} resolution failure(s), {text_mismatches} text mismatch(es)"
    )



def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--lang", help="Restrict PHASE D (scripture references) to one language "
                                        "and run it locally without needing CI=true")
    parser.add_argument("--scripture-only", action="store_true",
                         help="Only PHASE D (scripture references) counts toward the exit code "
                              "and summary; PHASE A/B still run internally since PHASE D depends "
                              "on their output, but their findings are not recorded/gating. "
                              "Implies scripture validation runs regardless of CI env var.")
    args = parser.parse_args()

    # Get discovery directory
    script_dir = Path(__file__).parent
    discovery_dir = script_dir.parent

    report = ValidationReport()
    run_report = RunReport("DISCOVERY VALIDATION")

    print("🔍 Starting Discovery Studies Validation...")
    print(f"📁 Discovery directory: {discovery_dir}")
    print()

    bible_versions, used_remote_sot, last_fetch_error = load_bible_versions('discovery')
    expected_languages = {
        lang: cfg['allowed_versions']
        for lang, cfg in bible_versions.items()
    }

    # ==========================================
    # PHASE A (coarse): Lint + SOT visibility + index.json structure
    #
    # Discovery's ValidationReport spans these three concerns in one
    # long-lived object (unlike encounters' one-Report-per-phase model),
    # so they're recorded here as a single coarse "phase" for RunReport's
    # summary table rather than split into three rows that don't reflect
    # how discovery's own report object actually accumulates.
    # ==========================================
    phase_a_start = time.monotonic()

    # PHASE 1: Lint — JSON formatting
    validate_lint(discovery_dir, report)

    # SOT source visibility — live remote vs. offline cache
    validate_sot_source(report, used_remote_sot, bible_versions)

    # PHASE A: Validate index.json
    index_data = validate_index_json(discovery_dir, report, expected_languages)

    # Print Phase A report
    phase_a_success = report.print_report(final=False)
    phase_a_elapsed = time.monotonic() - phase_a_start

    if not args.scripture_only:
        run_report.record_phase(
            "PHASE A: LINT + SOT + INDEX", report, phase_a_success, phase_a_elapsed, gate=True,
        )

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
    phase_b_start = time.monotonic()
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
    for lang, expected_versions in expected_languages.items():
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
            validate_filename_format(filepath, lang, report, expected_languages)

            # Load and validate JSON
            data = load_json_file(filepath, report)
            if data is None:
                continue

            # Validate structure
            validate_structure(data, lang, filename, report, expected_languages)

            # Store for cross-validation
            lang_studies[study_base] = data

            # Validate verse references are in correct language
            validate_verse_references(data, lang, filename, report, bible_versions)

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
        for lang in expected_languages:
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

    # Print Phase B report. final=False here — the 📊 STATISTICS block and
    # the final pass/fail banner now come from run_report.print_summary()
    # below, so discovery's coverage renders exactly once rather than
    # twice (once via ValidationReport's own stats block, once via
    # RunReport).
    phase_b_success = report.print_report(final=False)
    phase_b_elapsed = time.monotonic() - phase_b_start

    if not args.scripture_only:
        run_report.record_phase(
            "PHASE B: TRANSLATION FILES", report, phase_b_success, phase_b_elapsed, gate=True,
        )

    # ==========================================
    # PHASE: Scripture references — runs after Phase B (the real gate).
    # Its own ValidationReport instance/timing since it never gates the run
    # (gate=False) — findings are warnings only. Scans the ENTIRE corpus
    # (2000+ references across 10 languages) every run — too slow for
    # daily local editing, so it's CI-only (see scripture_validation_enabled).
    # ==========================================
    if scripture_validation_enabled() or args.lang or args.scripture_only:
        phase_scripture_start = time.monotonic()
        scripture_report = ValidationReport()
        scripture_report.phase = "PHASE_SCRIPTURE"
        validate_scripture_references(scripture_report, all_studies, discovery_dir.parent / 'bible_database', only_lang=args.lang)
        phase_scripture_success = scripture_report.print_report(final=False)
        phase_scripture_elapsed = time.monotonic() - phase_scripture_start

        run_report.record_phase(
            "PHASE D: SCRIPTURE REFERENCES", scripture_report, phase_scripture_success, phase_scripture_elapsed, gate=False,
        )
    else:
        print("ℹ️  PHASE D: SCRIPTURE REFERENCES — skipped (CI-only; set CI=true to run locally, or pass --lang)")

    run_report.add_coverage(
        studies_found=len(report.stats['studies_found']),
        files_scanned=report.stats['total_files'],
        languages_present=sorted(report.stats['languages_found']),
        expected_languages=len(expected_languages),
        sot_live=used_remote_sot,
    )
    run_report.print_summary()
    run_report.write_github_summary()

    return run_report.exit_code


if __name__ == '__main__':
    sys.exit(main())
