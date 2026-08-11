#!/usr/bin/env python3
"""
Render an Encounter study JSON as static HTML that mirrors how
devocional_nuevo's encounter_card_widgets.dart actually displays it.

Not a Dart-to-HTML transpiler: the layout/styling below is hand-translated
from encounter_card_widgets.dart's per-type card widgets (CinematicSceneCard,
ScriptureMomentCard, CharacterMomentCard, TheologicalDepthCard,
DiscoveryActivationCard, CompletionCard, InteractiveMomentCard).

What IS read live from the Dart source on every run is
kEncounterCardRenderedFields in encounter_card_contract.dart -- the
project's own authoritative map of which fields each card type renders.
If a card type's field set there drifts from RENDERED_FIELDS_BY_TYPE below,
this script prints a loud warning instead of silently going stale.

Usage:
    python3 app_preview.py <study.json> [--out out.html] [--dart-repo path]
"""

import argparse
import base64
import json
import re
import sys
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

from asset_urls import EncounterIndexReader, ImageReference

IMAGE_EXT = "avif"
IMAGE_MIME = "image/avif"
REQUEST_TIMEOUT_SECONDS = 10

# JSON key -> Dart field name, so this script's field checks can be compared
# against kEncounterCardRenderedFields (which uses Dart camelCase names).
JSON_TO_DART_FIELD = {
    "mood": "mood",
    "image_url": "imageUrl",
    "title": "title",
    "narrative": "narrative",
    "verse_overlay": "verseOverlay",
    "revelation_key": "revelationKey",
    "icon": "icon",
    "subtitle": "subtitle",
    "content": "content",
    "verse_reference": "verseReference",
    "verse_text": "verseText",
    "reflection": "reflection",
    "discovery_questions": "discoveryQuestions",
    "prayer": "prayer",
    "completion_verse": "completionVerse",
    "reflection_prompt": "reflectionPrompt",
    "scripture_connections": "scriptureConnections",
    "ambient_sound": "ambientSound",
    "haptic": "haptic",
    "celebration_type": "celebrationType",
}

# Mirrors kEncounterCardRenderedFields in encounter_card_contract.dart as of
# the last time this script was synced with the Dart source.
RENDERED_FIELDS_BY_TYPE = {
    "cinematic_scene": {
        "mood",
        "imageUrl",
        "title",
        "narrative",
        "verseOverlay",
        "scriptureConnections",
        "revelationKey",
    },
    "scripture_moment": {
        "mood",
        "imageUrl",
        "title",
        "subtitle",
        "verseReference",
        "verseText",
        "reflection",
        "scriptureConnections",
        "revelationKey",
    },
    "character_moment": {
        "mood",
        "imageUrl",
        "icon",
        "title",
        "subtitle",
        "content",
        "verseOverlay",
        "scriptureConnections",
        "revelationKey",
    },
    "theological_depth": {
        "mood",
        "imageUrl",
        "icon",
        "title",
        "subtitle",
        "content",
        "verseOverlay",
        "scriptureConnections",
        "revelationKey",
    },
    "discovery_activation": {
        "mood",
        "imageUrl",
        "title",
        "subtitle",
        "discoveryQuestions",
        "prayer",
    },
    "completion": {"mood", "imageUrl", "completionVerse", "reflectionPrompt"},
    "interactive_moment": {
        "mood",
        "imageUrl",
        "icon",
        "title",
        "subtitle",
        "reflectionPrompt",
        "revelationKey",
    },
}

DEFERRED_FIELDS = {"ambientSound", "haptic", "celebrationType"}

CONTRACT_FILE_REL = "lib/models/encounter_card_contract.dart"

MOOD_COLORS = {
    "storm": "#0d1a2e",
    "tense": "#0f1828",
    "mysterious": "#0a0e1a",
    "awe": "#0a1220",
    "falling": "#040810",
    "grace": "#12100a",
    "peace": "#0a120e",
    "intense": "#1a0a0e",
}
DEFAULT_MOOD_COLOR = "#0a0e1a"


def check_drift(dart_repo: Path):
    """Parse the live kEncounterCardRenderedFields map literal out of
    encounter_card_contract.dart and diff it against RENDERED_FIELDS_BY_TYPE.
    Returns a list of warning strings (empty if no drift detected)."""
    contract_file = dart_repo / CONTRACT_FILE_REL
    warnings = []
    if not contract_file.exists():
        warnings.append(
            f"Could not find {contract_file} -- skipping drift check. Pass "
            "--dart-repo to point at a local devocional_nuevo checkout."
        )
        return warnings

    src = contract_file.read_text(encoding="utf-8")
    start = src.find("kEncounterCardRenderedFields = {")
    if start == -1:
        warnings.append(
            "kEncounterCardRenderedFields not found in encounter_card_contract.dart"
        )
        return warnings
    end = src.find("\n};", start)
    body = src[start:end]

    live = {}
    for type_match in re.finditer(r"'(\w+)':\s*\{([^}]*)\}", body):
        type_name = type_match.group(1)
        fields = set(re.findall(r"'(\w+)'", type_match.group(2)))
        live[type_name] = fields

    known_types = set(RENDERED_FIELDS_BY_TYPE.keys())
    live_types = set(live.keys())

    if live_types - known_types:
        warnings.append(
            f"Dart contract has new card type(s) this script doesn't handle: {sorted(live_types - known_types)}"
        )
    if known_types - live_types:
        warnings.append(
            f"This script expects card type(s) no longer in the Dart contract: {sorted(known_types - live_types)}"
        )

    for t in known_types & live_types:
        if live[t] != RENDERED_FIELDS_BY_TYPE[t]:
            warnings.append(
                f"Field mismatch for type '{t}': Dart contract has {sorted(live[t])}, "
                f"script has {sorted(RENDERED_FIELDS_BY_TYPE[t])}"
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


CSS = """
body { font-family: -apple-system, Roboto, Arial, sans-serif; background:#1a1a1a; margin:0; padding:24px; }
.card { max-width:480px; margin:0 auto 32px; border-radius:28px; overflow:hidden;
        box-shadow:0 8px 30px rgba(0,0,0,0.4); }
.header { height:160px; display:flex; align-items:center; justify-content:center;
          background-size:cover; background-position:center;
          background:linear-gradient(to bottom, rgba(0,0,0,0.2), rgba(0,0,0,0.8)); }
.header .icon-badge { background:rgba(255,255,255,0.1); border-radius:50%; padding:16px; font-size:48px; }
.body { padding:24px 24px 32px; }
.title { color:#fff; font-size:26px; font-weight:900; letter-spacing:-0.5px; }
.title.center { text-align:center; }
.title.upper { text-transform:uppercase; }
.subtitle { color:rgba(255,193,7,0.8); font-size:12px; font-weight:800; letter-spacing:1px;
            text-transform:uppercase; margin-top:8px; }
.subtitle.center { text-align:center; }
.narrative, .content { color:rgba(255,255,255,0.8); font-size:16px; line-height:1.7; margin-top:20px; white-space:pre-line; }
.content.strong { color:rgba(255,255,255,0.85); }
.reflection { color:rgba(255,255,255,0.75); font-size:15px; line-height:1.7; margin-top:24px; text-align:center; white-space:pre-line; }
.verse-badge { display:inline-block; margin-top:16px; padding:6px 12px; border-radius:20px;
               background:rgba(255,193,7,0.15); border:1px solid rgba(255,193,7,0.4);
               color:#ffc107; font-size:11px; font-weight:900; letter-spacing:1.5px; }
.verse-text { color:#fff; font-size:22px; font-weight:800; font-style:italic; line-height:1.5;
              margin-top:20px; text-align:center; }
.verse-overlay { margin-top:20px; padding:16px; border-radius:16px; background:rgba(255,255,255,0.05);
                  border:1px solid rgba(255,255,255,0.15); }
.verse-overlay .text { color:#fff; font-size:14px; font-style:italic; }
.verse-overlay .ref { color:rgba(255,255,255,0.7); font-size:12px; font-weight:700; margin-top:8px; }
.revelation { margin-top:20px; padding:20px; border-radius:20px; background:rgba(255,193,7,0.1);
              border:1px solid rgba(255,193,7,0.3); display:flex; gap:16px; align-items:flex-start; }
.revelation .icon { color:#ffc107; }
.revelation .text { color:#ffc107; font-size:15px; font-weight:700; line-height:1.4; }
.connections-label { color:rgba(255,255,255,0.6); font-size:11px; font-weight:900;
                      letter-spacing:2px; text-transform:uppercase; margin-top:32px; }
.connection-tile { margin-top:12px; padding:16px; border-radius:16px; background:rgba(255,255,255,0.05); }
.connection-tile .ref { color:#ffc107; font-weight:800; font-size:12px; }
.connection-tile .text { color:rgba(255,255,255,0.7); font-size:13px; margin-top:4px; line-height:1.5; }
.question-tile { margin-top:16px; padding:20px; border-radius:24px; background:rgba(255,255,255,0.05);
                  border:1px solid rgba(255,255,255,0.1); }
.question-tile .cat { color:#ffc107; font-size:11px; font-weight:900; letter-spacing:1.5px; }
.question-tile .q { color:#fff; font-size:16px; margin-top:8px; line-height:1.5; }
.prayer-box { margin-top:24px; padding:24px; border-radius:28px; background:rgba(156,39,176,0.1);
              border:1px solid rgba(156,39,176,0.25); }
.prayer-box .title { color:#ffeb3b; font-weight:900; font-size:14px; text-transform:uppercase; }
.prayer-box .content { color:#fff; font-size:16px; font-style:italic; line-height:1.7; margin-top:16px; }
.completion-verse { color:rgba(255,255,255,0.7); font-size:16px; font-style:italic; text-align:center; margin-top:20px; }
.completion-ref { color:rgba(255,255,255,0.6); font-size:13px; font-weight:600; text-align:center; margin-top:8px; }
.reflection-prompt { color:rgba(255,255,255,0.7); font-size:18px; line-height:1.5; text-align:center; margin-top:20px; }
.big-icon { font-size:64px; text-align:center; }
.warning { max-width:480px; margin:0 auto 8px; padding:14px 20px; border-radius:12px;
           background:#ffe8e8; border:1px solid #e05555; color:#a02020; font-weight:600; }
.unrendered { max-width:480px; margin:16px auto 0; padding:14px 20px; border-radius:12px;
              background:#fff3cd; border:1px solid #d0a000; color:#7a5c00; font-weight:600; }
.pending { max-width:480px; margin:8px auto 0; padding:10px 20px; border-radius:12px;
           background:#e8f0ff; border:1px solid #5580d0; color:#1a3a7a; font-weight:600; font-size:14px; }
.card-number { max-width:480px; margin:0 auto; color:#ffc107; font-size:13px;
               font-weight:700; font-family:monospace; }
"""


class AssetImageFetcher:
    """Downloads encounter images from the Devocionales-assets repo and hands
    back a data: URI, so the preview HTML stays a single self-contained file
    and nothing is left on disk once it's deleted. Caches per-process so a
    single preview run never fetches the same image twice."""

    def __init__(self, encounter_id: str, ext: str = IMAGE_EXT, mime: str = IMAGE_MIME):
        self._encounter_id = encounter_id
        self._ext = ext
        self._mime = mime
        self._cache = {}

    def data_uri(self, filename: str):
        if filename in self._cache:
            return self._cache[filename]
        ref = ImageReference(encounter_id=self._encounter_id, filename=filename)
        url = ref.url(ext=self._ext)
        try:
            with urllib.request.urlopen(
                url, timeout=REQUEST_TIMEOUT_SECONDS
            ) as response:
                raw = response.read()
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            print(f"WARNING: could not fetch {url}: {e}", file=sys.stderr)
            self._cache[filename] = None
            return None
        encoded = base64.b64encode(raw).decode("ascii")
        uri = f"data:{self._mime};base64,{encoded}"
        self._cache[filename] = uri
        return uri


def header_html(card, image_fetcher=None):
    mood_color = MOOD_COLORS.get(card.get("mood"), DEFAULT_MOOD_COLOR)
    icon = card.get("icon")
    icon_html = f'<div class="icon-badge">{escape(icon)}</div>' if icon else ""
    filename = card.get("image_url")
    image_note = ""
    style = f"background:{mood_color}"
    if filename:
        uri = image_fetcher.data_uri(filename) if image_fetcher else None
        if uri:
            style = f"background:{mood_color} url('{uri}') center/cover no-repeat"
        else:
            image_note = (
                f"<!-- image_url: {escape(filename)} (not fetched in this preview) -->"
            )
    return f'<div class="header" style="{style}">{icon_html}{image_note}</div>'


def verse_overlay_html(vo):
    if not isinstance(vo, dict):
        return ""
    return (
        '<div class="verse-overlay">'
        f'<div class="text">"{escape(vo.get("text", ""))}"</div>'
        f'<div class="ref">— {escape(vo.get("reference", ""))}</div></div>'
    )


def revelation_html(text):
    return (
        '<div class="revelation"><span class="icon">⚡</span>'
        f'<span class="text">{escape(text)}</span></div>'
    )


def connections_html(items):
    if not isinstance(items, list) or not items:
        return ""
    out = ['<div class="connections-label">Deeper Connections</div>']
    for c in items:
        if isinstance(c, dict):
            out.append(
                '<div class="connection-tile">'
                f'<div class="ref">{escape(c.get("reference", ""))}</div>'
                f'<div class="text">{escape(c.get("text", ""))}</div></div>'
            )
    return "\n".join(out)


def render_card(card, image_fetcher=None):
    ctype = card.get("type", "unknown")
    order = card.get("order")
    body = []
    if order is not None:
        body.append(
            f'<div class="card-number">CARD {escape(order)} · {escape(ctype)}</div>'
        )
    body += [
        '<div class="card">',
        header_html(card, image_fetcher),
        '<div class="body">',
    ]

    if ctype == "cinematic_scene":
        if card.get("title"):
            body.append(f'<div class="title upper">{escape(card["title"])}</div>')
        if card.get("narrative"):
            body.append(f'<div class="narrative">{escape(card["narrative"])}</div>')
        if card.get("verse_overlay"):
            body.append(verse_overlay_html(card["verse_overlay"]))
        body.append(connections_html(card.get("scripture_connections")))
        if card.get("revelation_key"):
            body.append(revelation_html(card["revelation_key"]))

    elif ctype == "scripture_moment":
        if card.get("title"):
            body.append(f'<div class="title center">{escape(card["title"])}</div>')
        if card.get("subtitle"):
            body.append(
                f'<div class="subtitle center">{escape(card["subtitle"])}</div>'
            )
        if card.get("verse_reference"):
            body.append(
                f'<div style="text-align:center"><span class="verse-badge">{escape(card["verse_reference"].upper())}</span></div>'
            )
        if card.get("verse_text"):
            body.append(f'<div class="verse-text">"{escape(card["verse_text"])}"</div>')
        if card.get("reflection"):
            body.append(f'<div class="reflection">{escape(card["reflection"])}</div>')
        body.append(connections_html(card.get("scripture_connections")))
        if card.get("revelation_key"):
            body.append(revelation_html(card["revelation_key"]))

    elif ctype in ("character_moment", "theological_depth"):
        if card.get("title"):
            body.append(f'<div class="title">{escape(card["title"])}</div>')
        if card.get("subtitle"):
            body.append(f'<div class="subtitle">{escape(card["subtitle"])}</div>')
        if card.get("verse_overlay"):
            body.append(verse_overlay_html(card["verse_overlay"]))
        if card.get("content"):
            body.append(f'<div class="content strong">{escape(card["content"])}</div>')
        body.append(connections_html(card.get("scripture_connections")))
        if card.get("revelation_key"):
            body.append(revelation_html(card["revelation_key"]))

    elif ctype == "discovery_activation":
        if card.get("title"):
            body.append(f'<div class="title upper">{escape(card["title"])}</div>')
        if card.get("subtitle"):
            body.append(
                f'<div class="subtitle center">{escape(card["subtitle"])}</div>'
            )
        dq = card.get("discovery_questions")
        if isinstance(dq, list):
            for q in dq:
                if isinstance(q, dict):
                    body.append(
                        '<div class="question-tile">'
                        f'<div class="cat">{escape(q.get("category", "").upper())}</div>'
                        f'<div class="q">{escape(q.get("question", ""))}</div></div>'
                    )
        prayer = card.get("prayer")
        if isinstance(prayer, dict) and prayer.get("content"):
            title = prayer.get("title", "Prayer").upper()
            body.append(
                f'<div class="prayer-box"><div class="title">{escape(title)}</div>'
                f'<div class="content">{escape(prayer["content"])}</div></div>'
            )

    elif ctype == "completion":
        cv = card.get("completion_verse")
        if isinstance(cv, dict):
            body.append(
                f'<div class="completion-verse">"{escape(cv.get("text", ""))}"</div>'
            )
            body.append(
                f'<div class="completion-ref">— {escape(cv.get("reference", ""))}</div>'
            )
        if card.get("reflection_prompt"):
            body.append(
                f'<div class="reflection-prompt">{escape(card["reflection_prompt"])}</div>'
            )

    elif ctype == "interactive_moment":
        body.append(f'<div class="big-icon">{escape(card.get("icon", "🌊"))}</div>')
        if card.get("title"):
            body.append(f'<div class="title center">{escape(card["title"])}</div>')
        if card.get("subtitle"):
            body.append(
                f'<div class="subtitle center">{escape(card["subtitle"])}</div>'
            )
        if card.get("reflection_prompt"):
            body.append(
                f'<div class="reflection-prompt">{escape(card["reflection_prompt"])}</div>'
            )
        if card.get("revelation_key"):
            body.append(revelation_html(card["revelation_key"]))

    else:
        body.append(f'<div class="title">Unknown card type: {escape(ctype)}</div>')

    # Any populated field not in this type's rendered set is a schema drift
    # bug -- the app's own debug contract check would flag this at runtime.
    rendered_dart_fields = RENDERED_FIELDS_BY_TYPE.get(ctype, set())
    populated_json_keys = {
        k
        for k, v in card.items()
        if v not in (None, "", [], {}) and k not in ("order", "type")
    }
    orphaned = []
    pending = []
    for jkey in populated_json_keys:
        dart_field = JSON_TO_DART_FIELD.get(jkey, jkey)
        if dart_field in DEFERRED_FIELDS:
            pending.append(jkey)
        elif dart_field not in rendered_dart_fields:
            orphaned.append(jkey)
    if orphaned:
        body.append(
            '<div class="unrendered">⚠ NOT RENDERED IN APP for type '
            f'"{escape(ctype)}" -- fields present in JSON with no renderer in the '
            f"Dart contract: {', '.join(sorted(orphaned))}</div>"
        )
    if pending:
        body.append(
            '<div class="pending">⏳ PENDING (deferred, not yet wired in app): '
            f"{', '.join(sorted(pending))}</div>"
        )

    body.append("</div></div>")
    return "\n".join(body)


def build_html(data, drift_warnings, image_fetcher=None):
    title = data.get("title") or data.get("id") or "Encounter Preview"
    parts = [
        (
            f"<!doctype html><html><head><meta charset='utf-8'>"
            f"<title>{escape(title)}</title><style>{CSS}</style></head><body>"
        )
    ]
    for w in drift_warnings:
        parts.append(f'<div class="warning">⚠ {escape(w)}</div>')
    for card in data.get("cards", []):
        if isinstance(card, dict):
            parts.append(render_card(card, image_fetcher))
    parts.append("</body></html>")
    return "\n".join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("json_file")
    ap.add_argument("--out", default=None)
    ap.add_argument(
        "--dart-repo",
        default=None,
        help="Path to a local devocional_nuevo checkout (default: ../../devocional_nuevo)",
    )
    ap.add_argument(
        "--no-open", action="store_true", help="Don't auto-open the result in a browser"
    )
    ap.add_argument(
        "--no-images",
        action="store_true",
        help="Don't fetch real images from the assets repo",
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

    image_fetcher = None
    if not args.no_images:
        encounters_dir = Path(__file__).resolve().parent.parent
        index_reader = EncounterIndexReader(encounters_dir)
        encounter_id = index_reader.encounter_id_for(json_path.name)
        if encounter_id:
            image_fetcher = AssetImageFetcher(encounter_id)
        else:
            print(
                f"WARNING: {json_path.name} not found in index.json -- skipping image fetch",
                file=sys.stderr,
            )

    html = build_html(data, warnings, image_fetcher)
    out_path = Path(args.out) if args.out else json_path.with_suffix(".preview.html")
    out_path.write_text(html, encoding="utf-8")
    print(f"Wrote {out_path}")

    if not args.no_open:
        webbrowser.open(out_path.resolve().as_uri())


if __name__ == "__main__":
    main()
