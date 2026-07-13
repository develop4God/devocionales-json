#!/usr/bin/env python3
"""
Convert Encounters JSON files to human-readable Markdown, and back.

Every JSON value is wrapped in an explicit field marker so the Markdown
can be parsed back into an identical dict. This is not prose-friendly
Markdown for publishing -- it's a lossless, greppable view for editors
to read JSON content without wading through braces.

Usage:
    python3 json_to_md.py encode <file.json> [output.md]
    python3 json_to_md.py encode-dir <dir> [output_dir]
    python3 json_to_md.py decode <file.md> [output.json]
    python3 json_to_md.py verify <file.json>
        Round-trips file.json -> md -> json in memory and diffs the
        result against the original. Exits non-zero on any mismatch.
    python3 json_to_md.py verify-dir <dir>
        Runs verify on every .json file in a directory.
    python3 json_to_md.py read <file.json> [output.md]
        Reader-friendly Markdown: plain prose, no field markers, not
        reversible. For humans reviewing/reading content, not for
        editing-and-decoding back to JSON. Encode/decode/verify above
        are unaffected -- use those for the lossless editorial pipeline.
    python3 json_to_md.py read-dir <dir> [output_dir]
        Runs `read` on every .json file in a directory.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "shared_validation"))
from json_md_converter import (  # noqa: E402
    is_scalar,
    json_to_md,
    md_to_json,
    encode_file,
    decode_file,
    diff_json,
    verify_file,
)


def _quote_block(text, reference, version=None):
    lines = [f'> "{text}"']
    tail = f"> — {reference}" + (f" ({version})" if version else "")
    lines.append(tail)
    return lines


def json_to_reader_md(data, source_name=""):
    """Plain-prose Markdown for humans: no field markers, not reversible.

    Renders every key actually present in the file -- nothing is assumed
    or hardcoded to a single content type -- so encounters, discovery
    studies, or any future schema all render without data loss. Unknown
    scalar/dict/list shapes fall back to a generic labeled rendering so
    no field is ever silently dropped.
    """
    out = []
    meta = data.get("meta", {}) if isinstance(data.get("meta"), dict) else {}

    title = meta.get("character") or data.get("title") or source_name
    out.append(f"# {title}")
    out.append("")

    header_bits = []
    if meta.get("scripture_reference"):
        header_bits.append(f"**Referencia:** {meta['scripture_reference']}")
    if data.get("estimated_reading_minutes"):
        header_bits.append(f"**Tiempo estimado de lectura:** {data['estimated_reading_minutes']} min")
    if header_bits:
        out.append("  \n".join(header_bits))
        out.append("")

    kv = data.get("key_verse")
    if isinstance(kv, dict) and kv.get("text"):
        out.extend(_quote_block(kv["text"], kv.get("reference", ""), kv.get("bible_version")))
        out.append("")

    out.append("---")
    out.append("")

    cards = data.get("cards", [])
    for c in cards:
        if not isinstance(c, dict):
            continue
        order = c.get("order", "")
        out.append(f"## Card {order}")
        if c.get("title"):
            out.append(f"### {c['title']}")
        if c.get("subtitle"):
            out.append(f"*{c['subtitle']}*")
        out.append("")

        for text_field in ("narrative", "reflection", "content"):
            if c.get(text_field):
                out.append(c[text_field])
                out.append("")

        if c.get("verse_reference") and c.get("verse_text"):
            out.extend(_quote_block(c["verse_text"], c["verse_reference"]))
            out.append("")

        vo = c.get("verse_overlay")
        if isinstance(vo, dict) and vo.get("text"):
            out.extend(_quote_block(vo["text"], vo.get("reference", "")))
            out.append("")

        sc = c.get("scripture_connections")
        if isinstance(sc, list):
            for item in sc:
                if isinstance(item, dict):
                    out.append(f"**Conexión:** {item.get('reference','')} — \"{item.get('text','')}\"")
            if sc:
                out.append("")

        dq = c.get("discovery_questions")
        if isinstance(dq, list) and dq:
            out.append("**Preguntas para reflexionar:**")
            for q in dq:
                if isinstance(q, dict):
                    out.append(f"- ({q.get('category','')}) {q.get('question','')}")
            out.append("")

        prayer = c.get("prayer")
        if isinstance(prayer, dict) and prayer.get("content"):
            if prayer.get("title"):
                out.append(f"**{prayer['title']}**")
                out.append("")
            out.append(prayer["content"])
            out.append("")

        cv = c.get("completion_verse")
        if isinstance(cv, dict) and cv.get("text"):
            out.extend(_quote_block(cv["text"], cv.get("reference", ""), cv.get("bible_version")))
            out.append("")

        if c.get("reflection_prompt"):
            out.append(f"*{c['reflection_prompt']}*")
            out.append("")

        if c.get("revelation_key"):
            out.append(f"💡 {c['revelation_key']}")
            out.append("")

        # Catch-all: any scalar field not already rendered above, so no
        # data is ever silently omitted from the reader view.
        _rendered = {
            "order", "type", "mood", "image_url", "title", "subtitle",
            "narrative", "reflection", "content", "verse_reference",
            "verse_text", "verse_overlay", "scripture_connections",
            "discovery_questions", "prayer", "completion_verse",
            "reflection_prompt", "revelation_key", "ambient_sound", "haptic",
            "celebration_type", "icon",
        }
        for key, value in c.items():
            if key in _rendered or value in (None, "", [], {}):
                continue
            if is_scalar(value):
                out.append(f"**{key}:** {value}")
                out.append("")

        out.append("---")
        out.append("")

    return "\n".join(out).rstrip() + "\n"


def read_file(src_path, dst_path=None):
    src_path = Path(src_path)
    data = json.loads(src_path.read_text(encoding="utf-8"))
    md = json_to_reader_md(data, source_name=src_path.stem)
    dst_path = Path(dst_path) if dst_path else src_path.with_name(src_path.stem + "_LECTURA.md")
    dst_path.write_text(md, encoding="utf-8")
    return dst_path


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "encode":
        out = encode_file(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
        print(f"Wrote {out}")

    elif cmd == "decode":
        out = decode_file(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
        print(f"Wrote {out}")

    elif cmd == "verify":
        problems = verify_file(sys.argv[2])
        if problems:
            print(f"FAIL: {sys.argv[2]}")
            for p in problems:
                print(f"  - {p}")
            sys.exit(1)
        print(f"OK: {sys.argv[2]}")

    elif cmd == "encode-dir":
        src_dir = Path(sys.argv[2])
        dst_dir = Path(sys.argv[3]) if len(sys.argv) > 3 else src_dir
        dst_dir.mkdir(parents=True, exist_ok=True)
        for f in sorted(src_dir.glob("*.json")):
            out = encode_file(f, dst_dir / f.with_suffix(".md").name)
            print(f"Wrote {out}")

    elif cmd == "verify-dir":
        src_dir = Path(sys.argv[2])
        failures = 0
        for f in sorted(src_dir.glob("*.json")):
            problems = verify_file(f)
            if problems:
                failures += 1
                print(f"FAIL: {f}")
                for p in problems:
                    print(f"  - {p}")
            else:
                print(f"OK: {f}")
        if failures:
            print(f"\n{failures} file(s) failed round-trip verification.")
            sys.exit(1)
        print("\nAll files round-trip cleanly.")

    elif cmd == "read":
        out = read_file(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
        print(f"Wrote {out}")

    elif cmd == "read-dir":
        src_dir = Path(sys.argv[2])
        dst_dir = Path(sys.argv[3]) if len(sys.argv) > 3 else src_dir
        dst_dir.mkdir(parents=True, exist_ok=True)
        for f in sorted(src_dir.glob("*.json")):
            out = read_file(f, dst_dir / (f.stem + "_LECTURA.md"))
            print(f"Wrote {out}")

    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()