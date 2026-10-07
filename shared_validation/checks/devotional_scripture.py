"""devotional_scripture.py — validates the `versiculo` field and the
`para_meditar` verses of devotional-year entries against the Bible database for the file's own language and version.

Devotional-year entries store reference and verse text in ONE string
(`'John 3:16 NIV: "For God so loved..."'`), unlike encounters/discovery which
store them as separate keys, so scripture_check.find_scripture_pairs() cannot
see them. This module only adds what is missing: splitting that string,
mapping the native book title back to a book_number, and detecting empty
text. Fetching, cleaning and fuzzy-matching are reused from bible_resolver
and scripture_check (_compare_text) — nothing is re-implemented here.

Unlike encounters/discovery, year files are authored independently per
language (only some years line up with EN by date), so a native citation is
resolved against its own file's DB via the title map the generator itself
uses (bible_resolver.sanitize_book_name), not through an EN sibling.

Finding kinds: "empty_text" (a real shipped-content bug), "unparsed",
"unknown_book", "resolution_failed", plus scripture_check's "text_mismatch"
and "footnote_artifact". Callers decide severity.
"""

import re
import unicodedata
from dataclasses import dataclass

from bible_resolver import (
    VerseResolver,
    fetch_text,
    load_title_aliases,
    sanitize_book_name,
)

from shared_validation.checks.scripture_check import (
    Finding,
    ScriptureRef,
    _compare_text,
)

# "<book> <ch>:<v>[-<v>][ <version label>]: <text>" (CJK citations have no
# space before the chapter, hence `\s*`; the non-greedy book still splits
# "1 Corinthians 13:4" correctly). The label is free text
# ("NIV", "पवित्र बाइबल (HERV)", French "TOB :") but may not start with a comma,
# so a discontiguous citation ("Éphésiens 5:1-2, 18 LSG1910:") does not match
# and is reported as unparsed rather than half-compared.
_VERSICULO_RE = re.compile(
    r"^(?P<book>.+?)\s*(?P<chapter>\d+):(?P<start>\d+)(?:-(?P<end>\d+))?"
    r"(?:\s+[^\s,:\"“«][^:\"“«]*?)?\s*:\s*(?P<text>.*)$",
    re.DOTALL,
)
_QUOTE_CHARS = '"“”«»「」『』 \t\n'


@dataclass
class ParsedVersiculo:
    book: str
    chapter: int
    verse_start: int
    verse_end: int
    text: str


def parse_versiculo(versiculo: str) -> ParsedVersiculo | None:
    """Split a `versiculo` string into citation parts and verse text (outer
    quotes stripped). None if it doesn't have the expected shape."""
    match = _VERSICULO_RE.match(versiculo.strip())
    if match is None:
        return None
    start = int(match["start"])
    return ParsedVersiculo(
        book=match["book"].strip(),
        chapter=int(match["chapter"]),
        verse_start=start,
        verse_end=int(match["end"] or start),
        text=match["text"].strip(_QUOTE_CHARS),
    )


def build_native_book_map(resolver: VerseResolver, language: str) -> dict[str, int]:
    """Map each citation book title this DB produces (via the shared
    sanitize_book_name, the same function the seed generator writes titles
    with) to its book_number, plus the language's configured title aliases
    (load_title_aliases) — the same title map sanitize_seed_citations uses."""
    resolver.cursor.execute("SELECT book_number, long_name FROM books")
    book_map = {
        sanitize_book_name(long_name, book_number, language): book_number
        for book_number, long_name in resolver.cursor.fetchall()
    }
    for alias, canonical in load_title_aliases(language).items():
        if canonical in book_map:
            book_map[alias] = book_map[canonical]
    return book_map


def _invisible_character_hint(title: str) -> str:
    """Name what makes a title that *looks* right fail to match: a non-ASCII
    space (e.g. U+200A hair space) or a Cyrillic/Greek letter inside an
    otherwise Latin title. Empty string when the title has neither."""
    problems = []
    for ch in title:
        if ch != " " and unicodedata.category(ch) in ("Zs", "Cf"):
            problems.append(f"U+{ord(ch):04X} ({unicodedata.name(ch, 'unnamed')})")
    has_latin = any(unicodedata.name(c, "").startswith("LATIN") for c in title)
    if has_latin:
        for ch in title:
            name = unicodedata.name(ch, "")
            if name.startswith(("CYRILLIC", "GREEK")):
                problems.append(f"U+{ord(ch):04X} ({name})")
    return (
        f" — contains lookalike/invisible character(s): {', '.join(problems)}"
        if problems
        else ""
    )


def validate_versiculo(
    entry_id: str,
    versiculo: str,
    resolver: VerseResolver | None,
    book_map: dict[str, int] | None,
) -> Finding | None:
    """Validate one `versiculo`. With resolver=None only the DB-free checks
    (parseable, non-empty text) run — an empty verse is detectable without
    any Bible database."""
    ref = ScriptureRef(reference=versiculo[:40], verse_text=versiculo, path=entry_id)
    if not versiculo.strip():
        return Finding("empty_text", ref, f"'{entry_id}': versiculo is empty")
    parsed = parse_versiculo(versiculo)
    if parsed is None:
        return Finding(
            "unparsed",
            ref,
            f"'{entry_id}': unrecognised versiculo format: {versiculo[:80]!r}",
        )

    ref = ScriptureRef(
        reference=f"{parsed.book} {parsed.chapter}:{parsed.verse_start}"
        + (f"-{parsed.verse_end}" if parsed.verse_end != parsed.verse_start else ""),
        verse_text=parsed.text,
        path=entry_id,
    )
    if not parsed.text:
        return Finding(
            "empty_text", ref, f"'{entry_id}': empty verse text for '{ref.reference}'"
        )
    if resolver is None or book_map is None:
        return None

    book_number = book_map.get(parsed.book)
    if book_number is None:
        return Finding(
            "unknown_book",
            ref,
            f"'{entry_id}': book title '{parsed.book}' is not a title this language's book-name config produces{_invisible_character_hint(parsed.book)}",
        )

    resolved = fetch_text(
        resolver.cursor,
        book_number,
        parsed.chapter,
        parsed.verse_start,
        parsed.verse_end,
    )
    if resolved is None:
        return Finding(
            "resolution_failed",
            ref,
            f"'{entry_id}': verse not found for '{ref.reference}' in this file's Bible version",
        )
    return _compare_text(ref, resolved)


def validate_devotional_entries(
    entries: list[dict], resolver: VerseResolver | None, language: str
) -> list[Finding]:
    """Validate every entry's main `versiculo` and each `para_meditar` verse
    ({cita, texto}) in one file; returns the findings. A para_meditar item is
    rebuilt as 'cita: "texto"' so it goes through the same validate_versiculo
    path as the main verse."""
    book_map = build_native_book_map(resolver, language) if resolver else None
    findings = []
    for entry in entries:
        entry_id = entry.get("id", "?")
        checks = [(entry_id, entry.get("versiculo", ""))]
        for i, item in enumerate(entry.get("para_meditar", [])):
            checks.append(
                (
                    f"{entry_id}/para_meditar[{i}]",
                    f'{item.get("cita", "")}: "{item.get("texto", "")}"',
                )
            )
        for check_id, versiculo in checks:
            finding = validate_versiculo(check_id, versiculo, resolver, book_map)
            if finding is not None:
                findings.append(finding)
    return findings
