"""Manual end-to-end sanity check: a minimal terminal chat over the
committed semantic search corpus. Type a sentence, verse reference, or
word; get back the matching devotional's verse + reflection, the way a
real user's search would surface it — not just an id/score pair.

Usage:
    uv run python devocionales_scripts/search_chat.py
    uv run python devocionales_scripts/search_chat.py --language es
    uv run python devocionales_scripts/search_chat.py --top 3
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from semantic_search_service.embed import embed
from semantic_search_service.search import SearchIndex

_content_by_id = None


def _load_content_for_id(entry):
    """Devotional text lives in the source Devocional_year_*.json files,
    not the embeddings manifest (which only carries id/language/version/
    date) — look it up there. Indexed globally by id across every source
    file rather than partitioned by the entry's own `date` year: the
    legacy unsuffixed RVR1960 files (Devocional_year_2025/2026.json) mix
    content dated into a different calendar year than the filename
    implies (e.g. a 2026-03-08-dated entry physically stored in
    Devocional_year_2025.json), so filename-year and content-date-year
    cannot be assumed to match."""
    global _content_by_id
    if _content_by_id is None:
        _content_by_id = {}
        for path in ROOT.glob("Devocional_year_*.json"):
            data = json.loads(path.read_text(encoding="utf-8"))
            for day_map in data["data"].values():
                for day_entries in day_map.values():
                    for e in day_entries:
                        _content_by_id[e["id"]] = e

    return _content_by_id.get(entry["id"])


def format_result(rank, score, entry, content):
    lines = [f"  #{rank}  score={score:.4f}  {entry['id']}  ({entry['language']}, {entry['version']}, {entry['date']})"]
    if content is None:
        lines.append("      [content not found in source JSON]")
        return "\n".join(lines)
    if content.get("versiculo"):
        lines.append(f"      Verse: {content['versiculo']}")
    if content.get("reflexion"):
        reflexion = content["reflexion"]
        preview = reflexion if len(reflexion) <= 300 else reflexion[:300] + "…"
        lines.append(f"      Reflection: {preview}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--language", default=None, help="Restrict results to one language code, e.g. es")
    parser.add_argument("--top", type=int, default=5)
    args = parser.parse_args()

    print("Loading search index and model (bge-m3)...")
    index = SearchIndex()
    print(f"Ready — {len(index)} entries loaded. Type a query, or 'quit' to exit.\n")

    while True:
        try:
            query = input("search> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not query:
            continue
        if query.lower() in ("quit", "exit", "q"):
            break

        vector = embed(query)
        results = index.search(vector, top_n=args.top, language=args.language)

        if not results:
            print("  (no results)")
            continue

        for rank, (entry_id, score) in enumerate(results, start=1):
            entry = index.entry(entry_id)
            content = _load_content_for_id(entry)
            print(format_result(rank, score, entry, content))
        print()


if __name__ == "__main__":
    main()
