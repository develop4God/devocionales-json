"""Nearest-neighbor "related entries" lookup using the already-committed
embeddings — the simplest, zero-new-infra idea from the post-PR#118
brainstorm of non-search uses for the corpus vectors.

No model call, no LLM, no re-embedding: this is a thin CLI over
semantic_search_service.search.SearchIndex, the same brute-force
cosine-similarity core the HTTP API (semantic_search_service/api.py)
uses — one implementation, not a duplicate.

Usage:
    uv run python3 devocionales_scripts/related_entries.py --id matthew11v2830CNV20260206 --top 5
    uv run python3 devocionales_scripts/related_entries.py --id matthew11v2830CNV20260206 --top 5 --same-language
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from semantic_search_service.search import SearchIndex


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", required=True)
    parser.add_argument("--top", type=int, default=5)
    parser.add_argument("--same-language", action="store_true")
    args = parser.parse_args()

    index = SearchIndex()
    source = index.entry(args.id)
    if source is None:
        raise SystemExit(f"id not found in manifest: {args.id}")
    results = index.related(args.id, top_n=args.top, same_language=args.same_language)

    print(f"Source: {source['id']} ({source['language']}, {source['version']}, {source['date']})")
    print(f"Top {len(results)} related entries:")
    for rid, score in results:
        entry = index.entry(rid)
        print(f"  {score:.4f}  {rid}  ({entry['language']}, {entry['version']}, {entry['date']})")


if __name__ == "__main__":
    main()
