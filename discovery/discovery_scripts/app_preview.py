#!/usr/bin/env python3
"""
Render a Discovery study JSON as static HTML that mirrors how
devocional_nuevo's DiscoveryDetailPage actually displays it.

Not a Dart-to-HTML transpiler: the layout/styling below is hand-translated
from discovery_detail_page.dart's _buildCardContent and its _build*Tile
helpers. What IS read live from the Dart source on every run is the set of
`card.xxx` fields that _buildCardContent actually renders (scraped from its
`if (card.xxx != null)` guards) -- if that list drifts from FIELDS_RENDERED
below, this script prints a loud warning instead of silently going stale.

Usage:
    python3 app_preview.py <study.json> [--out out.html] [--dart-repo path]
"""

import argparse
import json
import re
import sys
import webbrowser
from pathlib import Path


def _find_repo_root(start: Path) -> Path:
    """Walk upward from `start` looking for the shared_preview/ package,
    rather than assuming a fixed directory depth (which silently breaks if
    this script is ever moved). Raises clearly instead of resolving to the
    wrong place."""
    for candidate in [start, *start.parents]:
        if (candidate / "shared_preview").is_dir():
            return candidate
    raise RuntimeError(
        f"Could not find shared_preview/ above {start} — "
        "is this script still inside the devocionales-json repo?"
    )


sys.path.insert(0, str(_find_repo_root(Path(__file__).resolve().parent)))
from shared_preview.markdown import escape, render_emphasis_markdown  # noqa: E402
from shared_preview.unrendered import TrackedDict, find_unrendered_keys  # noqa: E402

# Fields this script knows how to render, matching _buildCardContent in
# discovery_detail_page.dart as of the last time this script was synced.
# JSON keys are snake_case; the Dart guard names are camelCase -- this maps
# JSON key -> Dart field name for the drift check below.
FIELDS_RENDERED = {
    "content": "content",
    "revelation_key": "revelationKey",
    "scripture_anchor": "scriptureAnchor",
    "identity_statement": "identityStatement",
    "scripture_connections": "scriptureConnections",
    "scripture_references": "scriptureReferences",
    "greek_words": "greekWords",
    "hebrew_words": "hebrewWords",
    "discovery_questions": "discoveryQuestions",
    "prayer": "prayer",
}

DETAIL_PAGE_REL = "lib/pages/discovery_bible_studies/discovery_detail_page.dart"


def check_drift(dart_repo: Path):
    """Scrape _buildCardContent's `if (card.xxx != null)` guards from the
    live Dart source and compare against FIELDS_RENDERED. Returns a list of
    warning strings (empty if no drift detected)."""
    dart_file = dart_repo / DETAIL_PAGE_REL
    warnings = []
    if not dart_file.exists():
        warnings.append(
            f"Could not find {dart_file} -- skipping drift check against "
            "the live Dart source. Pass --dart-repo to point at a local "
            "devocional_nuevo checkout."
        )
        return warnings

    src = dart_file.read_text(encoding="utf-8")
    start = src.find("Widget _buildCardContent")
    if start == -1:
        warnings.append("_buildCardContent not found in discovery_detail_page.dart")
        return warnings
    body = src[start : start + 6000]  # generous slice past the method body

    dart_fields = set(re.findall(r"if\s*\(card\.(\w+)\s*!=\s*null\)", body))
    dart_fields -= {"icon", "title", "subtitle"}

    known_dart_fields = set(FIELDS_RENDERED.values())

    missing_in_script = dart_fields - known_dart_fields
    missing_in_dart = known_dart_fields - dart_fields

    if missing_in_script:
        warnings.append(
            "Dart now renders fields this script doesn't handle yet: "
            f"{sorted(missing_in_script)}. Update FIELDS_RENDERED and the "
            "renderer in app_preview.py."
        )
    if missing_in_dart:
        warnings.append(
            "This script expects fields no longer guarded in Dart (may be "
            f"stale): {sorted(missing_in_dart)}."
        )
    return warnings


CSS = """
:root {
  --bg: #f2f2f5; --card-bg: #fff; --text: rgba(0,0,0,0.9); --subtitle: rgba(80,60,180,0.7);
  --tile-bg: rgba(230,230,235,0.5); --tile-border: rgba(108,79,214,0.1);
  --anchor-bg: rgba(108,79,214,0.07); --anchor-border: rgba(108,79,214,0.25);
  --identity-bg: rgba(108,79,214,0.12); --identity-border: rgba(108,79,214,0.3);
  --greek-bg: rgba(230,225,250,0.4); --accent: #6c4fd6;
  --question-border: rgba(0,0,0,0.1); --shadow: rgba(0,0,0,0.08);
}
html[data-theme="dark"] {
  --bg: #16161a; --card-bg: #232228; --text: rgba(255,255,255,0.92); --subtitle: #b9a6ff;
  --tile-bg: rgba(255,255,255,0.06); --tile-border: rgba(180,150,255,0.2);
  --anchor-bg: rgba(180,150,255,0.1); --anchor-border: rgba(180,150,255,0.3);
  --identity-bg: rgba(180,150,255,0.14); --identity-border: rgba(180,150,255,0.35);
  --greek-bg: rgba(180,150,255,0.1); --accent: #a68fff;
  --question-border: rgba(255,255,255,0.15); --shadow: rgba(0,0,0,0.4);
}
body { font-family: -apple-system, Roboto, Arial, sans-serif; background:var(--bg); margin:0; padding:24px; }
.theme-toggle { position:fixed; top:16px; right:16px; z-index:100; padding:10px 16px; border-radius:20px;
                border:1px solid var(--tile-border); background:var(--card-bg); color:var(--text);
                font-size:14px; font-weight:700; cursor:pointer; box-shadow:0 2px 8px var(--shadow); }
.card { max-width:640px; margin:0 auto 32px; background:var(--card-bg); border-radius:32px;
        box-shadow:0 4px 15px var(--shadow); padding:28px; }
.icon { font-size:52px; }
.title { font-size:22px; font-weight:800; letter-spacing:-0.5px; margin:20px 0 0; color:var(--text); }
.subtitle { font-size:14px; font-weight:600; color:var(--subtitle); margin:6px 0 0; }
.content { font-size:16px; line-height:1.6; color:var(--text); margin-top:24px; }
.revelation { margin-top:32px; padding:20px; border-radius:20px; background:var(--accent);
              color:#fff; font-weight:700; font-size:16px; line-height:1.4;
              display:flex; gap:16px; align-items:flex-start; }
.revelation .bulb { font-size:22px; }
.tile { margin-top:16px; padding:20px; border-radius:20px; background:var(--tile-bg);
        border:1px solid var(--tile-border); }
.tile .ref { font-weight:900; color:var(--accent); }
.tile .body { margin-top:8px; line-height:1.5; color:var(--text); }
.anchor-tile { margin-top:16px; padding:20px; border-radius:20px; background:var(--anchor-bg);
               border:1px solid var(--anchor-border); }
.identity-tile { margin-top:16px; padding:20px; border-radius:20px; background:var(--identity-bg);
                  border:1px solid var(--identity-border); font-weight:700; font-size:16px;
                  line-height:1.4; display:flex; gap:16px; align-items:flex-start; color:var(--text); }
.identity-tile .sparkle { font-size:20px; }
.greek-tile { margin-top:16px; padding:20px; border-radius:20px; background:var(--greek-bg); color:var(--text); }
.greek-word { font-size:26px; font-weight:900; }
.greek-translit { font-size:16px; font-weight:600; color:var(--accent); margin-left:8px; }
.greek-strong { font-size:12px; font-weight:700; color:var(--accent); margin-left:8px; padding:3px 8px;
                background:var(--identity-bg); border-radius:8px; }
.greek-meaning { margin-top:12px; font-weight:800; font-size:15px; }
.greek-revelation { margin-top:8px; }
.greek-reference { margin-top:8px; }
.greek-application { margin-top:8px; }
.question-tile { margin-top:12px; padding:16px; border-radius:16px; border:1px solid var(--question-border); color:var(--text); }
.question-cat { font-size:10px; font-weight:900; color:var(--accent); letter-spacing:1px; }
.question-text { margin-top:4px; font-weight:600; }
.prayer-tile { margin-top:16px; padding:24px; border-radius:20px; background:var(--identity-bg); color:var(--text); }
.prayer-title { font-size:20px; font-weight:900; }
.prayer-content { margin-top:12px; line-height:1.6; }
h2.section { font-size:20px; font-weight:900; margin-top:32px; color:var(--text); }
.warning { max-width:640px; margin:0 auto 8px; padding:14px 20px; border-radius:12px;
           background:#ffe8e8; border:1px solid #e05555; color:#a02020; font-weight:600; }
.unrendered { max-width:640px; margin:16px auto 0; padding:14px 20px; border-radius:12px;
              background:#fff3cd; border:1px solid #d0a000; color:#7a5c00; font-weight:600; }
.key-verse-card { max-width:640px; margin:0 auto 32px; background:linear-gradient(135deg,#8b6fd9,#6c4fd6);
                   border-radius:20px; padding:32px; color:#fff; text-align:center; }
.key-verse-label { font-size:11px; font-weight:800; letter-spacing:1.8px; opacity:0.8; }
.key-verse-text { margin-top:20px; font-size:19px; font-weight:600; line-height:1.5; }
.key-verse-ref { margin-top:20px; font-size:14px; font-weight:900; letter-spacing:1px; }
.key-verse-version { margin-top:4px; font-size:11px; opacity:0.7; }
.card-number { max-width:640px; margin:0 auto; color:var(--accent); font-size:13px;
               font-weight:700; font-family:monospace; }
"""

THEME_SCRIPT = """
(function() {
  var saved = localStorage.getItem('discoveryPreviewTheme');
  var prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  var theme = saved || (prefersDark ? 'dark' : 'light');
  document.documentElement.setAttribute('data-theme', theme);
  document.addEventListener('DOMContentLoaded', function() {
    var btn = document.getElementById('theme-toggle-btn');
    function updateLabel() {
      var current = document.documentElement.getAttribute('data-theme');
      btn.textContent = current === 'dark' ? 'Light mode' : 'Dark mode';
    }
    updateLabel();
    btn.addEventListener('click', function() {
      var current = document.documentElement.getAttribute('data-theme');
      var next = current === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      localStorage.setItem('discoveryPreviewTheme', next);
      updateLabel();
    });
  });
})();
"""


def render_word_tile(w):
    """Shared tile markup for one greek_words[]/hebrew_words[] entry --
    both use the identical shape (word, transliteration, strong, meaning,
    revelation, reference, application), same as Dart's shared GreekWord
    class / _buildGreekWordTile widget."""
    translit = (
        f'<span class="greek-translit">({escape(w.get("transliteration", ""))})</span>'
        if w.get("transliteration")
        else ""
    )
    strong = (
        f'<span class="greek-strong">{escape(w.get("strong", ""))}</span>'
        if w.get("strong")
        else ""
    )
    extra = ""
    if w.get("reference"):
        extra += f'<div class="greek-reference">Reference: {escape(w["reference"])}</div>'
    if w.get("application"):
        extra += f'<div class="greek-application">Application: {escape(w["application"])}</div>'
    return (
        '<div class="greek-tile">'
        f'<span class="greek-word">{escape(w.get("word", ""))}</span>{translit}{strong}'
        f'<div class="greek-meaning">Meaning: {escape(w.get("meaning", ""))}</div>'
        f'<div class="greek-revelation">Revelation: {escape(w.get("revelation", ""))}</div>'
        f"{extra}"
        "</div>"
    )


def render_card(card, index=None, total=None):
    out = []
    if index is not None:
        ctype = card.get("type", "")
        out.append(f'<div class="card-number">CARD {index} of {total} · {escape(ctype)}</div>')
    out.append('<div class="card">')
    if card.get("icon"):
        out.append(f'<div class="icon">{escape(card["icon"])}</div>')
    if card.get("title"):
        out.append(f'<div class="title">{escape(card["title"])}</div>')
    if card.get("subtitle"):
        out.append(f'<div class="subtitle">{escape(card["subtitle"])}</div>')

    if card.get("content"):
        out.append(
            f'<div class="content">{render_emphasis_markdown(card["content"])}</div>'
        )

    if card.get("revelation_key"):
        out.append(
            '<div class="revelation"><span class="bulb">💡</span>'
            f"<span>{escape(card['revelation_key'])}</span></div>"
        )

    sa = card.get("scripture_anchor")
    if isinstance(sa, dict):
        out.append(
            '<div class="anchor-tile">'
            f'<div class="ref">{escape(sa.get("reference", ""))}</div>'
            f'<div class="body">{escape(sa.get("text", ""))}</div></div>'
        )

    if card.get("identity_statement"):
        out.append(
            '<div class="identity-tile"><span class="sparkle">✨</span>'
            f"<span>{escape(card['identity_statement'])}</span></div>"
        )

    for key in ("scripture_connections", "scripture_references"):
        items = card.get(key)
        if isinstance(items, list):
            for it in items:
                if isinstance(it, dict):
                    out.append(
                        '<div class="tile">'
                        f'<div class="ref">{escape(it.get("reference", ""))}</div>'
                        f'<div class="body">{escape(it.get("text", ""))}</div></div>'
                    )

    # hebrew_words reuses the exact same word-tile shape/widget as
    # greek_words (mirrors _buildGreekWordTile reuse in discovery_detail_page.dart).
    for words_key in ("greek_words", "hebrew_words"):
        words = card.get(words_key)
        if isinstance(words, list):
            for w in words:
                if isinstance(w, dict):
                    out.append(render_word_tile(w))

    dq = card.get("discovery_questions")
    if isinstance(dq, list) and dq:
        out.append('<h2 class="section">Reflection Questions</h2>')
        for q in dq:
            if isinstance(q, dict):
                out.append(
                    '<div class="question-tile">'
                    f'<div class="question-cat">{escape(q.get("category", "").upper())}</div>'
                    f'<div class="question-text">{escape(q.get("question", ""))}</div></div>'
                )

    prayer = card.get("prayer")
    if isinstance(prayer, dict) and prayer.get("content"):
        out.append('<div class="prayer-tile">')
        if prayer.get("title"):
            out.append(f'<div class="prayer-title">{escape(prayer["title"])}</div>')
        out.append(
            f'<div class="prayer-content">{escape(prayer["content"])}</div></div>'
        )

    # Automatic gate: compares keys this function actually READ from `card`
    # (tracked live by TrackedDict) against keys populated in the JSON --
    # no allowlist to keep in sync by hand.
    unrendered = find_unrendered_keys(card, ignored_keys=("order", "type"))
    if unrendered:
        out.append(
            '<div class="unrendered">⚠ NOT RENDERED IN APP -- these JSON fields exist on '
            f"this card but discovery_card_model.dart / discovery_detail_page.dart do not "
            f"parse or display them: {', '.join(sorted(unrendered))}</div>"
        )

    out.append("</div>")
    return "\n".join(out)


def render_key_verse(kv):
    return (
        '<div class="key-verse-card">'
        '<div class="key-verse-label">VERSÍCULO CLAVE</div>'
        f'<div class="key-verse-text">&ldquo;{escape(kv.get("text", ""))}&rdquo;</div>'
        f'<div class="key-verse-ref">{escape(kv.get("reference", "")).upper()}</div>'
        "</div>"
    )


# Study-level keys that are deliberately non-visual (authoring/search
# metadata never shown on any discovery screen) -- not a list of "what
# renders"; find_unrendered_keys() derives that automatically.
TOP_LEVEL_IGNORED = {
    "id",
    "type",
    "date",
    "title",
    "subtitle",
    "language",
    "version",
    "estimated_reading_minutes",
    "tags",
    "metadata",
}


def build_html(data, drift_warnings):
    """`data` must be a TrackedDict (see main()) so the unrendered-field
    check below reflects what render_key_verse/render_card actually read."""
    parts = [
        (
            f"<!doctype html><html><head><meta charset='utf-8'>"
            f"<title>{escape(data.get('title', ''))}</title><style>{CSS}</style>"
            f"<script>{THEME_SCRIPT}</script></head><body>"
            '<button id="theme-toggle-btn" class="theme-toggle">Dark mode</button>'
        )
    ]
    for w in drift_warnings:
        parts.append(f'<div class="warning">⚠ {escape(w)}</div>')

    kv = data.get("key_verse")
    if isinstance(kv, dict):
        parts.append(render_key_verse(kv))

    cards = data.get("cards", [])
    total = len(cards)
    for i, card in enumerate(cards, start=1):
        if isinstance(card, dict):
            parts.append(render_card(card, index=i, total=total))

    # Run last: by now every render_* call above has recorded which keys it
    # actually read off `data`, so this reflects real usage, not a guess.
    unrendered_top = find_unrendered_keys(data, ignored_keys=TOP_LEVEL_IGNORED)
    if unrendered_top:
        parts.append(
            '<div class="warning">⚠ NOT RENDERED IN PREVIEW -- these top-level JSON '
            f"fields exist but this script does not display them: "
            f"{', '.join(sorted(unrendered_top))}</div>"
        )

    parts.append("</body></html>")
    return "\n".join(parts)


def scan_unrendered(json_path: Path):
    """Run the same TrackedDict gate build_html() uses, without writing any
    HTML. Returns {field_name: count} for this one file."""
    data = TrackedDict(json.loads(json_path.read_text(encoding="utf-8")))
    build_html(data, drift_warnings=[])  # runs every render_* call to populate accessed_keys

    counts = {}
    for kv in find_unrendered_keys(data, ignored_keys=TOP_LEVEL_IGNORED):
        counts[kv] = counts.get(kv, 0) + 1
    for card in data.get("cards", []):
        if isinstance(card, dict):
            for k in find_unrendered_keys(card, ignored_keys=("order", "type")):
                counts[k] = counts.get(k, 0) + 1
    return counts


def run_report(root: Path):
    """Batch version of the per-card ⚠ NOT RENDERED warning: scans every
    *.json under `root` (skipping index.json) and prints one consolidated
    table instead of requiring each preview HTML to be opened by hand."""
    per_field = {}  # field -> list of (file, count)
    files_scanned = 0
    for json_path in sorted(root.rglob("*.json")):
        if json_path.name == "index.json":
            continue
        files_scanned += 1
        try:
            counts = scan_unrendered(json_path)
        except Exception as e:
            print(f"SKIP (parse/render error): {json_path}: {e}", file=sys.stderr)
            continue
        for field, n in counts.items():
            per_field.setdefault(field, []).append((json_path, n))

    if not per_field:
        print(f"Scanned {files_scanned} files -- 0 unrendered fields found.")
        return

    print(f"Scanned {files_scanned} files.\n")
    print(f"{'FIELD':<28} {'FILES':>6} {'OCCURRENCES':>12}")
    print("-" * 50)
    for field, hits in sorted(per_field.items(), key=lambda kv: -len(kv[1])):
        total_occurrences = sum(n for _, n in hits)
        print(f"{field:<28} {len(hits):>6} {total_occurrences:>12}")

    print()
    for field, hits in sorted(per_field.items(), key=lambda kv: -len(kv[1])):
        print(f"=== {field} ({len(hits)} files) ===")
        for path, n in hits:
            rel = path.relative_to(root.parent) if root.parent in path.parents else path
            print(f"  {rel} ({n})")
        print()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("json_file", nargs="?")
    ap.add_argument("--out", default=None)
    ap.add_argument(
        "--dart-repo",
        default=None,
        help="Path to a local devocional_nuevo checkout (default: ../devocional_nuevo)",
    )
    ap.add_argument(
        "--no-open", action="store_true", help="Don't auto-open the result in a browser"
    )
    ap.add_argument(
        "--report",
        nargs="?",
        const=".",
        default=None,
        metavar="DIR",
        help=(
            "Skip HTML generation; scan every *.json under DIR (default: "
            "current discovery/ tree) and print a consolidated unrendered-"
            "field report instead of opening each preview one by one."
        ),
    )
    args = ap.parse_args()

    if args.report is not None:
        root = Path(args.report)
        if str(root) == ".":
            root = Path(__file__).resolve().parent.parent
        run_report(root)
        return

    if not args.json_file:
        ap.error("json_file is required unless --report is given")

    json_path = Path(args.json_file)
    data = TrackedDict(json.loads(json_path.read_text(encoding="utf-8")))

    dart_repo = (
        Path(args.dart_repo)
        if args.dart_repo
        else (Path(__file__).resolve().parent.parent.parent.parent / "devocional_nuevo")
    )
    warnings = check_drift(dart_repo)
    for w in warnings:
        print(f"WARNING: {w}", file=sys.stderr)

    html = build_html(data, warnings)
    out_path = Path(args.out) if args.out else json_path.with_suffix(".preview.html")
    out_path.write_text(html, encoding="utf-8")
    print(f"Wrote {out_path}")

    if not args.no_open:
        webbrowser.open(out_path.resolve().as_uri())


if __name__ == "__main__":
    main()
