"""Benchmark intfloat/multilingual-e5-base against the committed
multilingual-e5-small baseline, for one language at a time, as part of the
PR #118 ranking-gap investigation.

multilingual-e5-small compresses 100+ languages into a small model; the
base/large tiers trade memory/speed for more per-language depth (documented
community pattern — see PR #118 discussion). This tests whether the base
model actually closes the ranking gaps found for a given language, without
paying to re-embed the full 13,870-entry corpus or every affected language
at once (each language is ~1460 entries; the base model is slower per
passage than small, so one language per run keeps this tractable).

Both the baseline and the base-model side embed with their OWN model (a
model's query and passage embeddings must come from the same model — this
does not mix multilingual-e5-small passage vectors with e5-base query
vectors). The baseline side re-embeds the language subset with
multilingual-e5-small rather than reusing the committed vectors, so the
comparison is apples-to-apples on identical text if the corpus subset
happens to differ slightly (it shouldn't, but this stays correct either
way rather than assuming the committed file matches current corpus JSON).

Usage:
    uv run python3 devocionales_scripts/benchmark_e5_base_model.py --language zh
"""

import argparse
import sys
import unicodedata
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "devocionales_scripts"))
sys.path.insert(0, str(ROOT / "tests"))

from build_semantic_embeddings import load_entries  # noqa: E402
from test_semantic_embeddings import TestSemanticRelevance  # noqa: E402

SMALL_MODEL = "intfloat/multilingual-e5-small"
BASE_MODEL = "intfloat/multilingual-e5-base"


def nfc_set(ids):
    return {unicodedata.normalize("NFC", i) for i in ids}


def embed_corpus(model, entries):
    passages = [f"passage: {e['text']}" for e in entries]
    vectors = model.encode(passages, normalize_embeddings=True, show_progress_bar=True, batch_size=32)
    manifest = [
        {"id": e["id"], "language": e["language"], "version": e["version"], "date": e["date"]}
        for e in entries
    ]
    return manifest, vectors


def search(model, manifest, vectors, query_text, top_n=10):
    query_vec = model.encode([f"query: {query_text}"], normalize_embeddings=True)[0]
    scores = vectors @ query_vec
    top_indices = np.argsort(-scores)[:top_n]
    return [manifest[i]["id"] for i in top_indices]


def iter_language_queries(language):
    topics = TestSemanticRelevance.MULTILINGUAL_TOPIC_GROUND_TRUTH.get(language, {})
    for topic, spec in topics.items():
        for style in ("single", "multi"):
            if style in spec:
                yield f"{language}/{topic}/{style}", spec[style], spec["ids"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--language", required=True, help="Single language code, e.g. zh")
    args = parser.parse_args()
    language = args.language

    print(f"Loading corpus subset for language={language}...")
    entries = load_entries(languages={language})
    print(f"  {len(entries)} entries")

    queries = list(iter_language_queries(language))
    print(f"  {len(queries)} ground-truth query combos for {language}")

    results = {}
    for model_name, label in ((SMALL_MODEL, "small"), (BASE_MODEL, "base")):
        print(f"\nLoading {model_name}...")
        model = SentenceTransformer(model_name, device="cpu")
        print(f"Embedding {len(entries)} {language} entries with {label}...")
        manifest, vectors = embed_corpus(model, entries)

        hits = 0
        rows = []
        for q_label, query_text, expected_ids in queries:
            expected_nfc = nfc_set(expected_ids)
            result_ids = nfc_set(search(model, manifest, vectors, query_text))
            hit = bool(expected_nfc & result_ids)
            hits += hit
            rows.append((q_label, hit, query_text))
        results[label] = {"hits": hits, "total": len(queries), "rows": rows}

    print("\n=== RESULTS ===")
    for q_label, small_hit, query_text in results["small"]["rows"]:
        base_hit = next(h for lbl, h, _ in results["base"]["rows"] if lbl == q_label)
        marker = "SAME" if small_hit == base_hit else "CHANGED"
        print(
            f"[{marker}] {q_label}: small={'HIT' if small_hit else 'MISS'} "
            f"base={'HIT' if base_hit else 'MISS'} — {query_text[:50]!r}"
        )

    for label in ("small", "base"):
        r = results[label]
        print(f"\n{label}: {r['hits']}/{r['total']} ({r['hits']/r['total']:.1%})")


if __name__ == "__main__":
    main()
