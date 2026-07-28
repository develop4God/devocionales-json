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

# Fields this script knows how to render, matching _buildCardContent in
# discovery_detail_page.dart as of the last time this script was synced.
# JSON keys are snake_case; the Dart guard names are camelCase -- this maps
# JSON key -> Dart field name for the drift check below.
FIELDS_RENDERED = {
    "content": "content",
    "revelation_key": "revelationKey",
    "scripture_anchor": "scriptureAnchor",
    "scripture_connections": "scriptureConnections",
    "scripture_references": "scriptureReferences",
    "greek_words": "greekWords",
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


def escape(text):
    if text is None:
        return ""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def render_bold_markdown(text):
    """Mirror _buildBoldMarkdownText: only **bold** is special-cased."""
    escaped = escape(text)
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escaped).replace("\n", "<br>")


CSS = """
body { font-family: -apple-system, Roboto, Arial, sans-serif; background:#f2f2f5; margin:0; padding:24px; }
.card { max-width:640px; margin:0 auto 32px; background:#fff; border-radius:32px;
        box-shadow:0 4px 15px rgba(0,0,0,0.08); padding:28px; }
.icon { font-size:52px; }
.title { font-size:22px; font-weight:800; letter-spacing:-0.5px; margin:20px 0 0; }
.subtitle { font-size:14px; font-weight:600; color:rgba(80,60,180,0.7); margin:6px 0 0; }
.content { font-size:16px; line-height:1.6; color:rgba(0,0,0,0.9); margin-top:24px; }
.revelation { margin-top:32px; padding:20px; border-radius:20px; background:#6c4fd6;
              color:#fff; font-weight:700; font-size:16px; line-height:1.4;
              display:flex; gap:16px; align-items:flex-start; }
.revelation .bulb { font-size:22px; }
.tile { margin-top:16px; padding:20px; border-radius:20px; background:rgba(230,230,235,0.5);
        border:1px solid rgba(108,79,214,0.1); }
.tile .ref { font-weight:900; color:#6c4fd6; }
.tile .body { margin-top:8px; line-height:1.5; }
.anchor-tile { margin-top:16px; padding:20px; border-radius:20px; background:rgba(108,79,214,0.07);
               border:1px solid rgba(108,79,214,0.25); }
.greek-tile { margin-top:16px; padding:20px; border-radius:20px; background:rgba(230,225,250,0.4); }
.greek-word { font-size:26px; font-weight:900; }
.greek-translit { font-size:16px; font-weight:600; color:#6c4fd6; margin-left:8px; }
.greek-meaning { margin-top:12px; font-weight:800; font-size:15px; }
.greek-revelation { margin-top:8px; }
.question-tile { margin-top:12px; padding:16px; border-radius:16px; border:1px solid rgba(0,0,0,0.1); }
.question-cat { font-size:10px; font-weight:900; color:#6c4fd6; letter-spacing:1px; }
.question-text { margin-top:4px; font-weight:600; }
.prayer-tile { margin-top:16px; padding:24px; border-radius:20px; background:rgba(108,79,214,0.12); }
.prayer-title { font-size:20px; font-weight:900; }
.prayer-content { margin-top:12px; line-height:1.6; }
h2.section { font-size:20px; font-weight:900; margin-top:32px; }
.warning { max-width:640px; margin:0 auto 8px; padding:14px 20px; border-radius:12px;
           background:#ffe8e8; border:1px solid #e05555; color:#a02020; font-weight:600; }
.unrendered { max-width:640px; margin:16px auto 0; padding:14px 20px; border-radius:12px;
              background:#fff3cd; border:1px solid #d0a000; color:#7a5c00; font-weight:600; }
"""


def render_card(card):
    out = ['<div class="card">']
    if card.get("icon"):
        out.append(f'<div class="icon">{escape(card["icon"])}</div>')
    if card.get("title"):
        out.append(f'<div class="title">{escape(card["title"])}</div>')
    if card.get("subtitle"):
        out.append(f'<div class="subtitle">{escape(card["subtitle"])}</div>')

    if card.get("content"):
        out.append(
            f'<div class="content">{render_bold_markdown(card["content"])}</div>'
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

    gw = card.get("greek_words")
    if isinstance(gw, list):
        for w in gw:
            if not isinstance(w, dict):
                continue
            translit = (
                f'<span class="greek-translit">({escape(w.get("transliteration", ""))})</span>'
                if w.get("transliteration")
                else ""
            )
            out.append(
                '<div class="greek-tile">'
                f'<span class="greek-word">{escape(w.get("word", ""))}</span>{translit}'
                f'<div class="greek-meaning">Meaning: {escape(w.get("meaning", ""))}</div>'
                f'<div class="greek-revelation">Revelation: {escape(w.get("revelation", ""))}</div>'
                "</div>"
            )

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

    # Anything present in the JSON but not in FIELDS_RENDERED is a schema
    # drift bug: the app silently ignores it today.
    unrendered = [
        k
        for k in card.keys()
        if k not in FIELDS_RENDERED
        and k not in ("order", "type", "icon", "title", "subtitle")
    ]
    if unrendered:
        out.append(
            '<div class="unrendered">⚠ NOT RENDERED IN APP -- these JSON fields exist on '
            f"this card but discovery_card_model.dart / discovery_detail_page.dart do not "
            f"parse or display them: {', '.join(sorted(unrendered))}</div>"
        )

    out.append("</div>")
    return "\n".join(out)


def build_html(data, drift_warnings):
    parts = [
        f"<!doctype html><html><head><meta charset='utf-8'>"
        f"<title>{escape(data.get('title', ''))}</title><style>{CSS}</style></head><body>"
    ]
    for w in drift_warnings:
        parts.append(f'<div class="warning">⚠ {escape(w)}</div>')
    for card in data.get("cards", []):
        if isinstance(card, dict):
            parts.append(render_card(card))
    parts.append("</body></html>")
    return "\n".join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("json_file")
    ap.add_argument("--out", default=None)
    ap.add_argument(
        "--dart-repo",
        default=None,
        help="Path to a local devocional_nuevo checkout (default: ../devocional_nuevo)",
    )
    ap.add_argument(
        "--no-open", action="store_true", help="Don't auto-open the result in a browser"
    )
    args = ap.parse_args()

    json_path = Path(args.json_file)
    data = json.loads(json_path.read_text(encoding="utf-8"))

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
