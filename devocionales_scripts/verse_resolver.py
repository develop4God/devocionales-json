"""
verse_resolver.py
─────────────────
Agnostic verse resolver. Resolves English Bible references to
target-language citations and verse text from a SQLite Bible DB.

Reusable by any pipeline script — no content-type assumptions.

Usage:
    from verse_resolver import VerseResolver

    resolver = VerseResolver(
        sqlite_path="path/to/bible.db",
        book_map_path="path/to/book_map.json",
        target_lang="de",
    )

    cita, texto, error = resolver.resolve("1 Corinthians 13:4-7")
    # On success : ("1 Korinther 13:4-7", "Die Liebe ist...", None)
    # On failure : (None, None, "reason string")

    resolver.close()

    # Or use as a context manager:
    with VerseResolver(sqlite_path, book_map_path, "hi") as r:
        cita, texto, error = r.resolve("John 3:16")
"""

import json
import os
import re
import sqlite3

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

# Devanagari digit → ASCII digit (for Hindi references)
_DEVA = str.maketrans("०१२३४५६७८९", "0123456789")


# ─────────────────────────────────────────────────────────────────────────────
# LOW-LEVEL HELPERS  (module-level, usable without instantiation)
# ─────────────────────────────────────────────────────────────────────────────

def load_book_map(book_map_path: str) -> dict:
    """
    Load book_map.json.
    Returns flat dict: EN book name → {book_number, <lang>_name, ...}
    """
    if not os.path.exists(book_map_path):
        raise FileNotFoundError(
            f"book_map.json not found at: {book_map_path}\n"
            f"Place book_map.json next to the calling script."
        )
    with open(book_map_path, encoding="utf-8") as f:
        raw = json.load(f)
    flat = {}
    for testament in ("OT", "NT"):
        for en_name, entry in raw.get(testament, {}).items():
            flat[en_name] = entry
    return flat


def parse_en_ref(cita: str) -> tuple[str, int, int, int] | None:
    """
    Parse an English Bible reference string.

    Accepts:
      - "John 3:16"
      - "1 Corinthians 13:4-7"
      - References with trailing version codes ("John 3:16 KJV")
      - Devanagari digits

    Returns:
      (book_name, chapter, verse_start, verse_end)  on success
      None                                           on failure
    """
    cita = cita.strip().translate(_DEVA)
    cita = re.sub(r'\s+[A-Z0-9]{2,6}$', '', cita).strip()  # strip version code
    m = re.match(
        r'^((?:\d\s+)?[A-Za-z]+(?:\s+[A-Za-z]+)*)\s+(\d+):(\d+)(?:-(\d+))?$',
        cita,
    )
    if not m:
        return None
    return (
        m.group(1).strip(),
        int(m.group(2)),
        int(m.group(3)),
        int(m.group(4)) if m.group(4) else int(m.group(3)),
    )


def fetch_text(
    cursor: sqlite3.Cursor,
    book_number: int,
    chapter: int,
    v_start: int,
    v_end: int,
) -> str | None:
    """
    Fetch and clean verse text from a SQLite Bible DB.

    Expected schema:
      verses(book_number INTEGER, chapter INTEGER, verse INTEGER, text TEXT)

    Returns cleaned combined text, or None if not found.
    """
    cursor.execute(
        "SELECT text FROM verses "
        "WHERE book_number=? AND chapter=? AND verse>=? AND verse<=? "
        "ORDER BY verse",
        (book_number, chapter, v_start, v_end),
    )
    rows = cursor.fetchall()
    if not rows:
        return None
    combined = " ".join(r[0] for r in rows)
    combined = re.sub(r"<[^>]+>", "", combined)            # strip XML tags
    combined = re.sub(r"[\u2460-\u24FF]", "", combined)    # strip Unicode ref markers
    combined = re.sub(r"\s+", " ", combined).strip()
    return combined


# ─────────────────────────────────────────────────────────────────────────────
# VERSE RESOLVER CLASS
# ─────────────────────────────────────────────────────────────────────────────

class VerseResolver:
    """
    Stateful verse resolver. Holds an open SQLite connection and book_map
    so callers do not manage them directly.

    Parameters
    ----------
    sqlite_path   : path to SQLite Bible database
    book_map_path : path to book_map.json
    target_lang   : language code (e.g. "hi", "de", "ko")
                    Must match the <lang>_name keys in book_map.json

    Example
    -------
    resolver = VerseResolver("bible.db", "book_map.json", "de")
    cita, texto, error = resolver.resolve("1 Corinthians 13:4-7")
    resolver.close()
    """

    def __init__(
        self,
        sqlite_path: str,
        book_map_path: str,
        target_lang: str,
    ) -> None:
        self.target_lang = target_lang
        self.book_map    = load_book_map(book_map_path)
        self.conn        = sqlite3.connect(sqlite_path)
        self.cursor      = self.conn.cursor()

    # ── context manager support ───────────────────────────────────────────────

    def __enter__(self) -> "VerseResolver":
        return self

    def __exit__(self, *_) -> None:
        self.close()

    def close(self) -> None:
        """Close the SQLite connection."""
        if self.conn:
            self.conn.close()
            self.conn   = None
            self.cursor = None

    # ── public API ────────────────────────────────────────────────────────────

    def resolve(
        self,
        cita_en: str,
    ) -> tuple[str | None, str | None, str | None]:
        """
        Resolve an English Bible reference to target-language citation + text.

        Parameters
        ----------
        cita_en : English reference, e.g. "John 3:16" or "1 Corinthians 13:4-7"

        Returns
        -------
        (local_cita, texto, None)      on success
        (None,       None,  reason)    on failure

        Failure reasons:
          - "could not parse reference: '...'"
          - "unknown book: '...'"
          - "no '<lang>_name' in book_map for book '...' — add it before running"
          - "verse not found: '...' (chapter has N verses)"
        """
        parsed = parse_en_ref(cita_en)
        if parsed is None:
            return None, None, f"could not parse reference: '{cita_en}'"

        book_en, chapter, v_start, v_end = parsed

        entry = self.book_map.get(book_en)
        if not entry:
            return None, None, f"unknown book: '{book_en}'"

        book_number = entry["book_number"]
        name_key    = f"{self.target_lang}_name"

        if name_key not in entry:
            return None, None, (
                f"no '{name_key}' in book_map for book '{book_en}' — "
                f"add it before running lang='{self.target_lang}'"
            )

        local_name = entry[name_key]

        texto = fetch_text(self.cursor, book_number, chapter, v_start, v_end)
        if texto is None:
            self.cursor.execute(
                "SELECT MAX(verse) FROM verses WHERE book_number=? AND chapter=?",
                (book_number, chapter),
            )
            row       = self.cursor.fetchone()
            max_verse = row[0] if row and row[0] else "unknown"
            range_str = f"{v_start}-{v_end}" if v_start != v_end else str(v_start)
            return None, None, (
                f"verse not found: '{cita_en}' → {local_name} {chapter}:{range_str} "
                f"(chapter has {max_verse} verses)"
            )

        range_suffix = f"{v_start}-{v_end}" if v_start != v_end else str(v_start)
        local_cita   = f"{local_name} {chapter}:{range_suffix}"
        return local_cita, texto, None

    def resolve_many(
        self,
        refs: list[str],
    ) -> list[dict]:
        """
        Resolve a list of English references in one call.

        Returns list of dicts:
          {"ref": original, "cita": local_cita, "texto": texto, "error": None}
          {"ref": original, "cita": None,       "texto": None,  "error": reason}
        """
        results = []
        for ref in refs:
            cita, texto, error = self.resolve(ref)
            results.append({
                "ref":   ref,
                "cita":  cita,
                "texto": texto,
                "error": error,
            })
        return results

    def verse_count(self) -> int:
        """Return total number of verses in the connected DB."""
        self.cursor.execute("SELECT COUNT(*) FROM verses")
        return self.cursor.fetchone()[0]
