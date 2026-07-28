#!/usr/bin/env python3
"""
Convert Discovery study JSON files to human-readable Markdown, and back.

Reuses the shared lossless JSON<->Markdown core (shared_validation) for
encode/decode/verify, and adds a Discovery-specific reader-friendly
renderer (plain prose, no field markers, not reversible).

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

sys.path.insert(
    0, str(Path(__file__).resolve().parent.parent.parent / "shared_validation")
)
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


def _word_study_block(label, words):
    out = []
    if not isinstance(words, list):
        return out
    for w in words:
        if not isinstance(w, dict):
            continue
        head = w.get("word", "")
        translit = w.get("transliteration", "")
        strong = w.get("strong")
        header = f"**{label}:** {head}"
        if translit:
            header += f" ({translit})"
        if strong:
            header += f" [{strong}]"
        out.append(header)
        out.append("")
        if w.get("meaning"):
            out.append(f"*{w['meaning']}*")
            out.append("")
        if w.get("revelation"):
            out.append(w["revelation"])
        out.append("")
    return out


def json_to_reader_md(data, source_name=""):
    """Plain-prose Markdown for humans: no field markers, not reversible.

    Renders every key actually present in the file -- nothing is assumed
    or hardcoded to a single card type -- so any Discovery card shape
    (greek_exegesis, hebrew word study, action steps, timeline, etc.)
    renders without data loss. Unknown scalar fields fall back to a
    generic labeled rendering so no field is ever silently dropped.
    """
    out = []
    title = data.get("title") or source_name
    out.append(f"# {title}")
    out.append("")

    header_bits = []
    if data.get("subtitle"):
        header_bits.append(f"*{data['subtitle']}*")
    if data.get("estimated_reading_minutes"):
        header_bits.append(
            f"**Estimated reading time:** {data['estimated_reading_minutes']} min"
        )
    if header_bits:
        out.append("  \n".join(header_bits))
        out.append("")

    kv = data.get("key_verse")
    if isinstance(kv, dict) and kv.get("text"):
        out.extend(
            _quote_block(kv["text"], kv.get("reference", ""), data.get("version"))
        )
        out.append("")

    out.append("---")
    out.append("")

    cards = data.get("cards", [])
    for c in cards:
        if not isinstance(c, dict):
            continue
        order = c.get("order", "")
        icon = c.get("icon", "")
        heading = f"## Card {order}"
        if icon:
            heading += f" {icon}"
        out.append(heading)
        if c.get("title"):
            out.append(f"### {c['title']}")
        if c.get("subtitle"):
            out.append(f"*{c['subtitle']}*")
        out.append("")

        if c.get("phase") is not None:
            out.append(f"**Phase:** {c['phase']}")
            out.append("")

        if c.get("content"):
            out.append(c["content"])
            out.append("")

        out.extend(_word_study_block("Greek", c.get("greek_words")))
        out.extend(_word_study_block("Hebrew", c.get("hebrew_words")))

        sa = c.get("scripture_anchor")
        if isinstance(sa, dict) and sa.get("text"):
            out.extend(_quote_block(sa["text"], sa.get("reference", "")))
            out.append("")

        sc = c.get("scripture_connections")
        if isinstance(sc, list):
            for item in sc:
                if isinstance(item, dict):
                    out.append(
                        f'**Connection:** {item.get("reference", "")} — "{item.get("text", "")}"'
                    )
            if sc:
                out.append("")

        sr = c.get("scripture_references")
        if isinstance(sr, list):
            for item in sr:
                if isinstance(item, dict):
                    out.append(
                        f'**Reference:** {item.get("reference", "")} — "{item.get("text", "")}"'
                    )
                    out.append("")
                elif isinstance(item, str):
                    out.append(f"**Reference:** {item}")
                    out.append("")

        tl = c.get("timeline")
        if isinstance(tl, list) and tl:
            out.append("**Timeline:**")
            for item in tl:
                if isinstance(item, dict):
                    out.append(
                        f"- **{item.get('event', '')}** — {item.get('description', '')}"
                    )
                    if item.get("revelation"):
                        out.append(f"  {item['revelation']}")
            out.append("")

        if c.get("identity_statement"):
            out.append(f"**Identity:** {c['identity_statement']}")
            out.append("")

        steps = c.get("action_steps")
        if isinstance(steps, list) and steps:
            out.append("**Action steps:**")
            for s in steps:
                if isinstance(s, dict):
                    out.append(
                        f"- **{s.get('title', '')}**: {s.get('description', '')}"
                    )
            out.append("")

        dq = c.get("discovery_questions")
        if isinstance(dq, list) and dq:
            out.append("**Questions for reflection:**")
            for q in dq:
                if isinstance(q, dict):
                    out.append(f"- ({q.get('category', '')}) {q.get('question', '')}")
            out.append("")

        prayer = c.get("prayer")
        if isinstance(prayer, dict) and prayer.get("content"):
            if prayer.get("title"):
                out.append(f"**{prayer['title']}**")
                out.append("")
            out.append(prayer["content"])
            out.append("")

        if c.get("revelation_key"):
            out.append(f"💡 {c['revelation_key']}")
            out.append("")

        # Catch-all: any scalar field not already rendered above, so no
        # data is ever silently omitted from the reader view.
        _rendered = {
            "order",
            "type",
            "icon",
            "title",
            "subtitle",
            "phase",
            "content",
            "greek_words",
            "hebrew_words",
            "scripture_anchor",
            "scripture_connections",
            "scripture_references",
            "timeline",
            "identity_statement",
            "action_steps",
            "discovery_questions",
            "prayer",
            "revelation_key",
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
    dst_path = (
        Path(dst_path)
        if dst_path
        else src_path.with_name(src_path.stem + "_LECTURA.md")
    )
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
