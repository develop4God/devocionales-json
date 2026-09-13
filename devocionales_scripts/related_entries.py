"""Nearest-neighbor "related entries" lookup using the already-committed
embeddings — the simplest, zero-new-infra idea from the post-PR#118
brainstorm of non-search uses for the corpus vectors.

No model call, no LLM, no re-embedding: this just does a cosine-similarity
lookup against editorial/semantic_search/embeddings.bin, which is already
built and committed. Given an entry id, returns its nearest neighbors
(optionally restricted to the same language, since cross-language
neighbors are only meaningful for a multilingual-linking feature, not a
"related reading" feature within one language's calendar).

Usage:
    uv run python3 devocionales_scripts/related_entries.py --id matthew11v2830CNV20260206 --top 5
    uv run python3 devocionales_scripts/related_entries.py --id matthew11v2830CNV20260206 --top 5 --same-language
"""

import argparse
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
BASELINE_DIR = ROOT / "editorial" / "semantic_search"
DIM = 1024  # bge-m3, the committed baseline as of PR #118


def load_baseline():
    manifest = json.loads((BASELINE_DIR / "manifest.json").read_text(encoding="utf-8"))
    vectors = np.fromfile(BASELINE_DIR / "embeddings.bin", dtype="<f4").reshape(len(manifest), DIM)
    return manifest, vectors


def related(manifest, vectors, entry_id, top_n=5, same_language=False):
    id_to_row = {e["id"]: i for i, e in enumerate(manifest)}
    if entry_id not in id_to_row:
        raise SystemExit(f"id not found in manifest: {entry_id}")
    row = id_to_row[entry_id]
    query_vec = vectors[row]
    scores = vectors @ query_vec

    order = np.argsort(-scores)
    results = []
    for i in order:
        if i == row:
            continue
        if same_language and manifest[i]["language"] != manifest[row]["language"]:
            continue
        results.append((manifest[i]["id"], float(scores[i])))
        if len(results) >= top_n:
            break
    return manifest[row], results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", required=True)
    parser.add_argument("--top", type=int, default=5)
    parser.add_argument("--same-language", action="store_true")
    args = parser.parse_args()

    manifest, vectors = load_baseline()
    source, results = related(manifest, vectors, args.id, args.top, args.same_language)

    print(f"Source: {source['id']} ({source['language']}, {source['version']}, {source['date']})")
    print(f"Top {len(results)} related entries:")
    for rid, score in results:
        entry = next(e for e in manifest if e["id"] == rid)
        print(f"  {score:.4f}  {rid}  ({entry['language']}, {entry['version']}, {entry['date']})")


if __name__ == "__main__":
    main()
