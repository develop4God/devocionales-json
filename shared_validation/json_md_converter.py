#!/usr/bin/env python3
"""
Schema-agnostic JSON <-> Markdown lossless converter, shared across content types.

Every JSON value is wrapped in an explicit field marker so the Markdown
can be parsed back into an identical dict. This is not prose-friendly
Markdown for publishing -- it's a lossless, greppable view for editors
to read JSON content without wading through braces.

Domain-specific scripts (encounters, discovery, ...) import this module
for encode/decode/verify, and layer their own reader-friendly renderer
(schema-aware, one-way) on top.
"""
import json
from pathlib import Path

FIELD_START = "<!-- field:"
FIELD_END = "-->"


def is_scalar(value):
    return isinstance(value, (str, int, float, bool)) or value is None


def scalar_type_name(value):
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    return "str"


def encode_scalar(value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    text = str(value)
    # Escape any line that would otherwise look like a structural heading
    # marker to the decoder (headings only ever introduce list/object
    # fields in this format, never scalar text).
    return "\n".join(
        f"\\{line}" if line.startswith("#") else line
        for line in text.split("\n")
    )


def decode_scalar_text(text):
    return "\n".join(
        line[1:] if line.startswith("\\#") else line
        for line in text.split("\n")
    )


def decode_scalar(text, type_name):
    """Decode using the type recorded at encode time -- never guessed."""
    text = decode_scalar_text(text)
    if type_name == "null":
        return None
    if type_name == "bool":
        return text == "true"
    if type_name == "int":
        return int(text)
    if type_name == "float":
        return float(text)
    return text  # str: verbatim, including things like "1.0" or "#3b1f00"


def field_marker(path, type_name=None):
    if type_name is None:
        return f"{FIELD_START}{path}{FIELD_END}"
    return f"{FIELD_START}{path} type={type_name}{FIELD_END}"


def encode_value(path, value, lines, depth):
    """Recursively encode a JSON value under `path` into markdown lines."""
    heading = "#" * min(depth + 2, 6)

    if is_scalar(value):
        lines.append(field_marker(path, scalar_type_name(value)))
        lines.append(encode_scalar(value))
        lines.append("")
        return

    if isinstance(value, list):
        lines.append(field_marker(path))
        lines.append(f"<!-- list len={len(value)} -->")
        lines.append("")
        for i, item in enumerate(value):
            item_path = f"{path}[{i}]"
            lines.append(f"{heading} {item_path}")
            lines.append("")
            encode_value(item_path, item, lines, depth + 1)
        return

    if isinstance(value, dict):
        lines.append(field_marker(path))
        lines.append(f"<!-- object keys={len(value)} -->")
        lines.append("")
        for key, sub_value in value.items():
            sub_path = f"{path}.{key}"
            lines.append(f"{heading} {sub_path}")
            lines.append("")
            encode_value(sub_path, sub_value, lines, depth + 1)
        return

    raise TypeError(f"Unsupported type at {path}: {type(value)}")


def json_to_md(data, source_name=""):
    lines = [f"# {source_name}", ""]
    for key, value in data.items():
        lines.append(f"## {key}")
        lines.append("")
        encode_value(key, value, lines, 1)
    return "\n".join(lines).rstrip() + "\n"


def parse_field_line(line):
    """Parse '<!-- field:path type=str -->' into (path, type_name|None)."""
    inner = line[len(FIELD_START):-len(FIELD_END)]
    if " type=" in inner:
        path, type_name = inner.rsplit(" type=", 1)
        return path, type_name
    return inner, None


def parse_field_blocks(md_text):
    """Yield (path, kind, payload) for every field marker in document order.

    kind is 'scalar' (payload = (raw_text, type_name)), 'list' (payload =
    declared length), or 'object' (payload = declared key count).
    """
    lines = md_text.splitlines()
    i = 0
    blocks = []
    while i < len(lines):
        line = lines[i]
        if line.startswith(FIELD_START) and line.endswith(FIELD_END):
            path, type_name = parse_field_line(line)
            i += 1
            kind = "scalar"
            meta = None
            if i < len(lines) and lines[i].startswith("<!-- list "):
                kind = "list"
                meta = int(lines[i].split("len=")[1].split(" ")[0])
                i += 1
            elif i < len(lines) and lines[i].startswith("<!-- object "):
                kind = "object"
                meta = int(lines[i].split("keys=")[1].split(" ")[0])
                i += 1
            if kind == "scalar":
                # Skip the single blank separator line, then consume every
                # line up to (not including) the next structural boundary:
                # a field marker, or a heading line introducing the next
                # sibling field. Scalar text may legitimately contain blank
                # lines; any of its own lines starting with '#' were escaped
                # at encode time (see encode_scalar), so a bare '#' heading
                # here is always structural, never scalar content.
                if i < len(lines) and lines[i].strip() == "":
                    i += 1
                value_lines = []
                while i < len(lines):
                    nxt = lines[i]
                    if nxt.startswith(FIELD_START) and nxt.endswith(FIELD_END):
                        break
                    if nxt.startswith("#"):
                        break
                    value_lines.append(nxt)
                    i += 1
                # trim a single trailing blank line (the separator we emit
                # after every field), keep interior blank lines intact
                while value_lines and value_lines[-1] == "":
                    value_lines.pop()
                raw = "\n".join(value_lines)
                blocks.append((path, "scalar", (raw, type_name)))
            else:
                blocks.append((path, kind, meta))
        else:
            i += 1
    return blocks


def md_to_json(md_text):
    """Rebuild the original dict from field markers, ignoring heading text."""
    blocks = parse_field_blocks(md_text)
    root = {}
    containers = {"": root}

    def parent_path_and_key(path):
        if path.endswith("]"):
            base, idx = path.rsplit("[", 1)
            return base, int(idx[:-1])
        if "." in path:
            base, key = path.rsplit(".", 1)
            return base, key
        return "", path

    for path, kind, meta in blocks:
        if kind == "list":
            containers[path] = []
        elif kind == "object":
            containers[path] = {}

    for path, kind, meta in blocks:
        parent_path, key = parent_path_and_key(path)
        parent = containers.get(parent_path)
        if parent is None:
            raise ValueError(f"Missing parent container for {path}")

        if kind == "scalar":
            raw, type_name = meta
            value = decode_scalar(raw, type_name)
        else:
            value = containers[path]

        if isinstance(parent, list):
            parent.append(value)
        else:
            parent[key] = value

    return root


def encode_file(src_path, dst_path=None):
    src_path = Path(src_path)
    data = json.loads(src_path.read_text(encoding="utf-8"))
    md = json_to_md(data, source_name=src_path.stem)
    dst_path = Path(dst_path) if dst_path else src_path.with_suffix(".md")
    dst_path.write_text(md, encoding="utf-8")
    return dst_path


def decode_file(src_path, dst_path=None):
    src_path = Path(src_path)
    md = src_path.read_text(encoding="utf-8")
    data = md_to_json(md)
    dst_path = Path(dst_path) if dst_path else src_path.with_suffix(".json")
    dst_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return dst_path


def diff_json(original, rebuilt, path="root"):
    """Return a list of human-readable mismatch descriptions."""
    problems = []

    if type(original) != type(rebuilt):
        # int/float/bool distinctions from decode_scalar are the only
        # expected wrinkle; treat numeric equality as acceptable.
        if isinstance(original, (int, float)) and isinstance(rebuilt, (int, float)) \
                and not isinstance(original, bool) and not isinstance(rebuilt, bool) \
                and original == rebuilt:
            return problems
        problems.append(f"{path}: type mismatch {type(original).__name__} vs {type(rebuilt).__name__}")
        return problems

    if isinstance(original, dict):
        orig_keys = set(original.keys())
        rebuilt_keys = set(rebuilt.keys())
        for missing in orig_keys - rebuilt_keys:
            problems.append(f"{path}.{missing}: FIELD DROPPED in round-trip")
        for extra in rebuilt_keys - orig_keys:
            problems.append(f"{path}.{extra}: unexpected extra field appeared")
        for key in orig_keys & rebuilt_keys:
            problems.extend(diff_json(original[key], rebuilt[key], f"{path}.{key}"))
        return problems

    if isinstance(original, list):
        if len(original) != len(rebuilt):
            problems.append(f"{path}: list length {len(original)} vs {len(rebuilt)}")
        for i, (o_item, r_item) in enumerate(zip(original, rebuilt)):
            problems.extend(diff_json(o_item, r_item, f"{path}[{i}]"))
        return problems

    if original != rebuilt:
        problems.append(f"{path}: value mismatch {original!r} vs {rebuilt!r}")
    return problems


def verify_file(src_path):
    src_path = Path(src_path)
    original = json.loads(src_path.read_text(encoding="utf-8"))
    md = json_to_md(original, source_name=src_path.stem)
    rebuilt = md_to_json(md)
    problems = diff_json(original, rebuilt)
    return problems
