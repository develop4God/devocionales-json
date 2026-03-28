"""
bible_versions.py — Single source of truth for Bible version configuration.

Import this module in all validators and translation tools.
Never duplicate version data across files.

Usage:
    from bible_versions import PRIMARY_VERSION, ALLOWED_VERSIONS, LANGUAGES
"""

# ── Primary Bible version per language ───────────────────────────────────────
# Used by translation agents as the required version for all verse text.

PRIMARY_VERSION = {
    'en': 'KJV',
    'es': 'RVR1960',
    'pt': 'ARC',
    'fr': 'LSG1910',
    'de': 'LU17',
    'ja': '新改訳2003',
    'zh': '和合本1919',
    'hi': 'पवित्र बाइबिल (ओ.वी.)',
}

# ── Allowed versions per language ────────────────────────────────────────────
# Used by validators to accept both primary and secondary versions.
# Secondary versions are legacy or alternate accepted translations.

ALLOWED_VERSIONS = {
    'en': ['KJV', 'NIV'],
    'es': ['RVR1960', 'NVI'],
    'pt': ['ARC', 'NVI'],
    'fr': ['LSG1910', 'TOB'],
    'de': ['LU17', 'SCH2000'],
    'ja': ['新改訳2003', 'リビングバイブル'],
    'zh': ['和合本1919', '新译本'],
    'hi': ['पवित्र बाइबिल (ओ.वी.)', 'पवित्र बाइबिल'],
}

# ── Supported language codes ──────────────────────────────────────────────────
LANGUAGES = list(PRIMARY_VERSION.keys())

# ── Reading speed for estimated_reading_minutes calculation ───────────────────
# WPM = words per minute (Latin-script languages)
# CPM = characters per minute (CJK languages)

READING_SPEED = {
    'en': {'unit': 'wpm', 'rate': 200},
    'es': {'unit': 'wpm', 'rate': 200},
    'pt': {'unit': 'wpm', 'rate': 200},
    'fr': {'unit': 'wpm', 'rate': 200},
    'de': {'unit': 'wpm', 'rate': 200},
    'ja': {'unit': 'cpm', 'rate': 400},
    'zh': {'unit': 'cpm', 'rate': 400},
    'hi': {'unit': 'wpm', 'rate': 180},
}


def get_primary(lang: str) -> str:
    """Return the primary Bible version for a language code."""
    return PRIMARY_VERSION.get(lang, '')


def get_allowed(lang: str) -> list:
    """Return all allowed Bible versions for a language code."""
    return ALLOWED_VERSIONS.get(lang, [])


def is_valid_version(lang: str, version: str) -> bool:
    """Check if a Bible version is valid for a given language."""
    return version in ALLOWED_VERSIONS.get(lang, [])


def is_primary_version(lang: str, version: str) -> bool:
    """Check if a Bible version is the primary version for a language."""
    return version == PRIMARY_VERSION.get(lang)
