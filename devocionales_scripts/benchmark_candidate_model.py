"""Benchmark a candidate embedding model against the committed
multilingual-e5-small baseline, for one language at a time — continuation
of the PR #118 investigation after multilingual-e5-base gave a mixed,
language-dependent result (helped fil/zh, hurt ar badly, ~neutral for ja;
see benchmark_e5_base_model.py's docstring for that result in full).

Rather than accept a per-language hybrid model setup (real but nontrivial
extra deployment complexity — two models loaded, a language->model
routing table, an index-format change), this checks whether a single
newer model just handles all 4 affected languages well on its own:

  - Qwen3-Embedding-0.6B: currently tops multilingual MTEB among small
    open-weight models, including lower-resource language handling.
    Uses sentence-transformers' built-in prompt_name="query" mechanism
    for queries (applies the model's own trained instruction prefix);
    passages are encoded with no prompt. NOT the same convention as
    E5's manual "query: "/"passage: " string prefixes — verified via
    the model's own documentation before writing this, since getting
    an asymmetric-retrieval model's prompt convention wrong invalidates
    the whole comparison (this is exactly the class of mistake already
    found and fixed elsewhere in this investigation — the E5 prefix
    convention itself, applied correctly, was never the bug there, but
    it easily could be here with a different model that uses a
    different mechanism).
  - BGE-M3: explicit multilingual + hybrid dense/sparse/multi-vector
    design, no prefix needed for either query or passage (verified: BGE-M3's
    own documentation lists "-" for both). This benchmark only exercises
    its dense output (plain SentenceTransformer usage) — its sparse/
    multi-vector retrieval modes are a separate, larger evaluation this
    script does not attempt.

Usage:
    uv run python3 devocionales_scripts/benchmark_candidate_model.py --language zh --model qwen3
    uv run python3 devocionales_scripts/benchmark_candidate_model.py --language zh --model bge-m3
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

CANDIDATES = {
    "qwen3": "Qwen/Qwen3-Embedding-0.6B",
    "bge-m3": "BAAI/bge-m3",
}


def nfc_set(ids):
    return {unicodedata.normalize("NFC", i) for i in ids}


def encode_passages(model, model_key, texts):
    if model_key == "small":
        texts = [f"passage: {t}" for t in texts]
        return model.encode(texts, normalize_embeddings=True, show_progress_bar=True, batch_size=32)
    # Qwen3 and BGE-M3 both take passages/documents with no prefix or prompt.
    return model.encode(texts, normalize_embeddings=True, show_progress_bar=True, batch_size=32)


def encode_query(model, model_key, text):
    if model_key == "small":
        return model.encode([f"query: {text}"], normalize_embeddings=True)[0]
    if model_key == "qwen3":
        return model.encode([text], prompt_name="query", normalize_embeddings=True)[0]
    # bge-m3: no prompt needed for queries either.
    return model.encode([text], normalize_embeddings=True)[0]


def rank_all(model, model_key, manifest, vectors, query_text):
    query_vec = encode_query(model, model_key, query_text)
    scores = vectors @ query_vec
    order = np.argsort(-scores)
    return order, scores


def describe_expected(manifest, order, scores, expected_nfc):
    id_to_row = {unicodedata.normalize("NFC", e["id"]): i for i, e in enumerate(manifest)}
    rank_of_row = {row: rank + 1 for rank, row in enumerate(order)}
    found = []
    for eid in expected_nfc:
        row = id_to_row.get(eid)
        if row is None:
            found.append((eid, None, None))
        else:
            found.append((eid, rank_of_row[row], float(scores[row])))
    found.sort(key=lambda x: (x[1] is None, x[1] if x[1] is not None else 0))
    return found


def iter_language_queries(language):
    topics = TestSemanticRelevance.MULTILINGUAL_TOPIC_GROUND_TRUTH.get(language, {})
    for topic, spec in topics.items():
        for style in ("single", "multi"):
            if style in spec:
                yield f"{language}/{topic}/{style}", spec[style], spec["ids"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--language", required=True, help="Single language code, e.g. zh")
    parser.add_argument("--model", required=True, choices=CANDIDATES.keys())
    args = parser.parse_args()
    language = args.language
    candidate_key = args.model
    candidate_name = CANDIDATES[candidate_key]

    print(f"Loading corpus subset for language={language}...")
    entries = load_entries(languages={language})
    print(f"  {len(entries)} entries")
    texts = [e["text"] for e in entries]

    queries = list(iter_language_queries(language))
    print(f"  {len(queries)} ground-truth query combos for {language}")

    results = {}
    for model_name, label in ((SMALL_MODEL, "small"), (candidate_name, candidate_key)):
        print(f"\nLoading {model_name}...")
        model = SentenceTransformer(model_name, device="cpu", trust_remote_code=True)
        print(f"Embedding {len(entries)} {language} entries with {label}...")
        vectors = encode_passages(model, label, texts)
        manifest = [
            {"id": e["id"], "language": e["language"], "version": e["version"], "date": e["date"]}
            for e in entries
        ]

        hits = 0
        rows = []
        for q_label, query_text, expected_ids in queries:
            expected_nfc = nfc_set(expected_ids)
            order, scores = rank_all(model, label, manifest, vectors, query_text)
            top10_ids = nfc_set(manifest[i]["id"] for i in order[:10])
            hit = bool(expected_nfc & top10_ids)
            hits += hit
            best_expected = describe_expected(manifest, order, scores, expected_nfc)[0]
            top10_preview = [(manifest[i]["id"], round(float(scores[i]), 4)) for i in order[:3]]
            rows.append((q_label, hit, query_text, best_expected, top10_preview))
        results[label] = {"hits": hits, "total": len(queries), "rows": rows}

    print("\n=== RESULTS ===")
    for small_row, cand_row in zip(results["small"]["rows"], results[candidate_key]["rows"]):
        q_label, small_hit, query_text, small_best, small_top3 = small_row
        _, cand_hit, _, cand_best, cand_top3 = cand_row
        marker = "SAME" if small_hit == cand_hit else "CHANGED"
        print(f"[{marker}] {q_label} — {query_text[:50]!r}")
        print(
            f"    small:      {'HIT ' if small_hit else 'MISS'} "
            f"best-expected-id rank={small_best[1]} score={small_best[2]} "
            f"top3={small_top3}"
        )
        print(
            f"    {candidate_key + ':':<12}{'HIT ' if cand_hit else 'MISS'} "
            f"best-expected-id rank={cand_best[1]} score={cand_best[2]} "
            f"top3={cand_top3}"
        )

    for label in ("small", candidate_key):
        r = results[label]
        print(f"\n{label}: {r['hits']}/{r['total']} ({r['hits']/r['total']:.1%})")


if __name__ == "__main__":
    main()
