#!/usr/bin/env python3
"""Regenerates the stats blocks in README.md from index.json (devocionales)
and discovery/encounters index.json, so numbers never silently drift out of
sync with what's actually registered.

Usage:
    python3 devocionales_scripts/generate_stats.py

Run from anywhere; paths are resolved relative to the repo root.
"""

import argparse
import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
README_PATH = REPO_ROOT / "README.md"


def devocionales_stats():
    idx = json.loads((REPO_ROOT / "index.json").read_text())
    rows = []
    total_files = 0
    total_entries = 0
    total_versions = 0
    for lang, versions in idx["files"].items():
        version_codes = sorted(versions)
        total_versions += len(version_codes)
        file_count = sum(len(v["files"]) for v in versions.values())
        total_files += file_count

        entries = 0
        for version, meta in versions.items():
            for year, filename in meta["files"].items():
                path = REPO_ROOT / filename
                data = json.loads(path.read_text())
                entries += sum(len(v) for v in data["data"][lang].values())
        total_entries += entries

        rows.append((lang, ", ".join(version_codes), file_count, entries))

    return {
        "rows": sorted(rows),
        "total_files": total_files,
        "total_entries": total_entries,
        "languages": sorted(idx["files"]),
        "total_versions": total_versions,
    }


def corpus_stats(root: Path, index_key: str):
    """Counts, per language, how many of the index's registered content files
    actually exist on disk under root/<lang>/. Driven by index.json rather
    than a directory glob so stray non-content JSON (e.g. image-prompt
    sidecar files) never gets miscounted as a study/encounter."""
    idx = json.loads((root / "index.json").read_text())
    items = idx[index_key]
    languages = sorted({lang for item in items for lang in item.get("files", {})})
    return {"languages": languages, "item_count": len(items)}


def replace_marked_block(content: str, marker: str, new_inner: str) -> str:
    start = f"<!-- README-STATS:{marker} -->"
    end = f"<!-- /README-STATS:{marker} -->"
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.DOTALL)
    if not pattern.search(content):
        raise RuntimeError(f"Marker not found: {marker}")
    replacement = f"{start}\n{new_inner}\n{end}"
    return pattern.sub(lambda _: replacement, content)


def build_devocionales_block(stats: dict) -> str:
    lines = ["| Lang | Versions | Files (2025 + 2026) | Entries |", "|---|---|---|---|"]
    for lang, versions, file_count, entries in stats["rows"]:
        lines.append(f"| {lang} | {versions} | {file_count} | {entries:,} |")
    lines.append("")
    lines.append(
        f"**Total: {stats['total_files']} files · {stats['total_entries']:,} entries · "
        f"{len(stats['languages'])} languages · {stats['total_versions']} Bible versions**"
    )
    return "\n".join(lines)


def build_corpus_block(name: str, stats: dict) -> str:
    langs = ", ".join(stats["languages"])
    file_count = stats["item_count"] * len(stats["languages"])
    return (
        f"**{name}** — {stats['item_count']} {'studies' if name == 'Discovery' else 'encounters'} "
        f"× {len(stats['languages'])} languages ({langs}) — {file_count} files."
    )


def build_directory_structure_block() -> str:
    """Lists top-level directories only, skipping hidden/build dirs, so this
    block never has to be hand-updated when a directory is added or removed."""
    dirs = sorted(
        d.name for d in REPO_ROOT.iterdir()
        if d.is_dir() and not d.name.startswith(".") and not d.name.startswith("__")
    )
    lines = ["```", "devocionales-json/"]
    for i, name in enumerate(dirs):
        connector = "└──" if i == len(dirs) - 1 else "├──"
        lines.append(f"{connector} {name}/")
    lines.append("```")
    return "\n".join(lines)


def extract_links(content: str) -> list[tuple[str, str]]:
    """Returns (text, target) pairs for every markdown link and bare URL in
    the README. Badge images (![...](...)) are skipped — their link target
    is the badge SVG service, not a doc/page worth validating here."""
    links = []
    for m in re.finditer(r"(?<!!)\[([^\]]*)\]\(([^)]+)\)", content):
        links.append((m.group(1), m.group(2)))
    for m in re.finditer(r"(?<![(\[])https?://[^\s)]+", content):
        links.append((m.group(0), m.group(0)))
    for m in re.finditer(r"(?<![\w/.\-])www\.[a-zA-Z0-9\-]+\.[a-zA-Z]{2,}\b", content):
        links.append((m.group(0), "https://" + m.group(0)))
    return links


def github_slugify(heading: str) -> str:
    """Mimics GitHub's markdown heading-anchor algorithm: lowercase, drop
    emoji glyphs but keep variation-selector characters, strip remaining
    punctuation, spaces to hyphens."""
    s = heading.lower()
    s = "".join(
        "" if (0x1F000 <= ord(c) <= 0x1FFFF or 0x2600 <= ord(c) <= 0x27BF)
        else c
        for c in s
    )
    s = re.sub(r"[^\w\s\-︀-️]", "", s)
    s = re.sub(r"\s+", "-", s.strip())
    return s


def check_links(content: str) -> list[str]:
    """Validates every link in the README: internal paths must exist on
    disk, anchors must match a real heading, external URLs must resolve
    with a live HTTP request. Returns a list of human-readable problems;
    empty means everything checked out."""
    import urllib.error
    import urllib.parse
    import urllib.request

    problems = []
    headings = set()
    for m in re.finditer(r"^#{1,6}\s+(.+)$", content, re.MULTILINE):
        headings.add(github_slugify(m.group(1)))

    seen = set()
    for text, target in extract_links(content):
        if target in seen:
            continue
        seen.add(target)

        if target.startswith("#"):
            anchor = target[1:].lower()
            if anchor not in headings:
                problems.append(f"Broken anchor [{text}]({target}) — no matching heading")
        elif target.startswith("http://") or target.startswith("https://"):
            if urllib.parse.urlparse(target).hostname == "img.shields.io":
                continue  # badge service, not a doc link
            try:
                req = urllib.request.Request(target, method="HEAD",
                                              headers={"User-Agent": "Mozilla/5.0"})
                urllib.request.urlopen(req, timeout=10)
            except urllib.error.HTTPError as e:
                if e.code in (403, 405):
                    continue  # some hosts block HEAD; not a real 404
                problems.append(f"Broken link [{text}]({target}) — HTTP {e.code}")
            except Exception as e:
                problems.append(f"Broken link [{text}]({target}) — {e}")
        else:
            clean_target = target.split("#")[0]
            local_path = (README_PATH.parent / clean_target).resolve()
            if not local_path.exists():
                problems.append(f"Broken local link [{text}]({target}) — path does not exist")

    return problems


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check-links",
        action="store_true",
        help="Validate every link in README.md (internal paths, anchors, "
             "external URLs) and exit non-zero if any are broken. Does not "
             "modify the file.",
    )
    args = parser.parse_args()

    if args.check_links:
        problems = check_links(README_PATH.read_text())
        if problems:
            print(f"❌ {len(problems)} broken link(s) found in README.md:\n")
            for p in problems:
                print(f"  - {p}")
            raise SystemExit(1)
        print("✅ All README.md links are valid.")
        return

    devo = devocionales_stats()
    discovery = corpus_stats(REPO_ROOT / "discovery", "studies")
    encounters = corpus_stats(REPO_ROOT / "encounters", "encounters")

    content = README_PATH.read_text()
    content = replace_marked_block(content, "devocionales", build_devocionales_block(devo))
    content = replace_marked_block(content, "discovery", build_corpus_block("Discovery", discovery))
    content = replace_marked_block(content, "encounters", build_corpus_block("Encounters", encounters))
    content = replace_marked_block(content, "directory-structure", build_directory_structure_block())

    # Reverse validation: check the generated content BEFORE writing it to
    # disk. A bug in any substitution above (stray broken link, wrong path)
    # should never silently ship — fail loudly here instead.
    problems = check_links(content)
    if problems:
        print(f"❌ Refusing to write README.md — {len(problems)} broken link(s) "
              f"in the generated content:\n")
        for p in problems:
            print(f"  - {p}")
        raise SystemExit(1)

    README_PATH.write_text(content)
    print(f"Devocionales: {devo['total_files']} files, {devo['total_entries']:,} entries, "
          f"{len(devo['languages'])} languages, {devo['total_versions']} versions")
    print(f"Discovery: {discovery['item_count']} studies, {len(discovery['languages'])} languages")
    print(f"Encounters: {encounters['item_count']} encounters, {len(encounters['languages'])} languages")
    print("README.md stats updated.")
    print("✅ Reverse validation passed — no broken links in generated content.")


if __name__ == "__main__":
    main()
