"""duplication_check.py — cross-file/cross-character content duplication
detection, shared by both pipelines.

Two entry points, following the same shape as lint_json_files: one
comparison primitive, called separately per corpus/file-family with a
different extracted-text argument, rather than a single combined pass.

This module deliberately knows nothing about JSON structure or which
corpus is being scanned — extracting `{location_path: text}` (or
`{character: prompt}`) out of the source files is entirely the caller's
job. That keeps this module open to a third corpus later (a new
caller-side extraction function) without any change here.

Confirmed baseline (see issue #89): whole-field comparison across
unrelated real encounters stays under ~2% char-level ratio even with
heavy shared theological vocabulary — too coarse to catch real
duplication, which shows up as a shared sentence/phrase. So
find_prose_duplicates operates at sentence granularity; only
find_character_prompt_duplicates (single dense paragraphs, no natural
sentence boundaries worth splitting on for this purpose) compares whole
strings directly.
"""

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Dict, List


@dataclass
class Finding:
    """One suspected duplication between two locations."""
    location_a: str
    location_b: str
    ratio: float
    matched_text: str


# Splits on sentence-ending punctuation followed by whitespace, keeping the
# punctuation with the preceding sentence. Good enough for this corpus's
# prose (English/Romance/German/etc. declarative sentences) — not a full
# NLP sentence tokenizer, which would be overkill for a warning-only check.
_SENTENCE_SPLIT_RE = re.compile(r'(?<=[.!?])\s+')

# Below this length a chunk is too short for SequenceMatcher.ratio() to be
# meaningful (short common phrases score high by chance) — skip comparing it.
_MIN_CHUNK_LEN = 20

# A high ratio() alone is not enough evidence of real duplication: two short
# sentences with similar structure can clear the ratio threshold on the
# strength of a handful of shared filler words, with no actual shared
# phrase. Per issue #89's measured noise floor (longest contiguous match
# <=9 characters across unrelated real encounters), the longest_match must
# itself be a real phrase — comfortably above that floor — for a finding to
# be worth a human's time.
_MIN_MATCH_LEN = 15


def _split_sentences(text: str) -> List[str]:
    """Split text into sentence-ish chunks, dropping fragments too short
    to compare meaningfully."""
    chunks = [c.strip() for c in _SENTENCE_SPLIT_RE.split(text.strip()) if c.strip()]
    return [c for c in chunks if len(c) >= _MIN_CHUNK_LEN]


def _top_level_entry(location_path: str) -> str:
    """The top-level entry a location belongs to, used to exclude
    same-entry comparisons. Callers key locations as
    '{entry_id}::{rest_of_path}' — the entry id is everything before the
    first '::'."""
    return location_path.split('::', 1)[0]


def find_prose_duplicates(text_by_location: Dict[str, str], threshold: float = 0.65) -> List[Finding]:
    """Compare prose text across different top-level entries for
    near-duplicate sentences.

    `text_by_location` maps a location path to its text; the location path
    must be prefixed with '{entry_id}::' so entries can be told apart —
    two chunks from the same entry are never compared (intentional reuse
    within one encounter/study, e.g. a revelation_key echoed in its own
    completion card).

    Splits every text into sentence-ish chunks, then compares every chunk
    against every other chunk from a different entry using
    difflib.SequenceMatcher.ratio(). O(n^2) in chunk count — fine at
    current corpus size.
    """
    chunks: List[tuple] = []  # (location, entry_id, chunk_text)
    for location, text in text_by_location.items():
        entry_id = _top_level_entry(location)
        for chunk in _split_sentences(text):
            chunks.append((location, entry_id, chunk))

    findings: List[Finding] = []
    matcher = SequenceMatcher()
    for i in range(len(chunks)):
        loc_a, entry_a, text_a = chunks[i]
        matcher.set_seq2(text_a)
        for j in range(i + 1, len(chunks)):
            loc_b, entry_b, text_b = chunks[j]
            if entry_a == entry_b:
                continue
            matcher.set_seq1(text_b)
            ratio = matcher.ratio()
            if ratio >= threshold:
                match = matcher.find_longest_match(0, len(text_b), 0, len(text_a))
                if match.size < _MIN_MATCH_LEN:
                    continue
                matched_text = text_b[match.a:match.a + match.size]
                findings.append(Finding(loc_a, loc_b, ratio, matched_text))

    return findings


def find_character_prompt_duplicates(prompts_by_character: Dict[str, str], threshold: float = 0.7) -> List[Finding]:
    """Compare whole character-prompt strings character-against-character.

    No sentence-splitting — these are already single dense paragraphs, so
    the comparison primitive is applied directly to the full string.
    """
    characters = list(prompts_by_character.keys())
    findings: List[Finding] = []
    matcher = SequenceMatcher()
    for i in range(len(characters)):
        char_a = characters[i]
        text_a = prompts_by_character[char_a]
        matcher.set_seq2(text_a)
        for j in range(i + 1, len(characters)):
            char_b = characters[j]
            text_b = prompts_by_character[char_b]
            matcher.set_seq1(text_b)
            ratio = matcher.ratio()
            if ratio >= threshold:
                match = matcher.find_longest_match(0, len(text_b), 0, len(text_a))
                if match.size < _MIN_MATCH_LEN:
                    continue
                matched_text = text_b[match.a:match.a + match.size]
                findings.append(Finding(char_a, char_b, ratio, matched_text))

    return findings
