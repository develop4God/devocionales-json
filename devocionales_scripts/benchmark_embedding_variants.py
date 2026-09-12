"""Benchmark 3 embedding-text compositions against the same ground-truth
queries from tests/test_semantic_embeddings.py, without modifying that file.

Variants compared:
  A: baseline    - editorial/semantic_search/            (versiculo + reflexion + para_meditar)
  B: verses_only - .experiments/verses_only/              (versiculo + para_meditar)
  C: verse_reflexion_only - .experiments/verse_reflexion_only/  (versiculo + reflexion)

For each variant, runs every query in TOPIC_GROUND_TRUTH and
MULTILINGUAL_TOPIC_GROUND_TRUTH (English topic queries + the 9-language
common-word/multi-sentence topic queries), applying the same language
filter the tests use, and records hit/miss per query plus a hit-rate
summary per variant. Writes a timestamped log file under
.experiments/benchmark_logs/ and prints a summary table.

Usage:
    uv run python3 devocionales_scripts/benchmark_embedding_variants.py
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))

from test_semantic_embeddings import TestSemanticRelevance  # noqa: E402

MODEL_NAME = "intfloat/multilingual-e5-small"
DIM = 384

VARIANTS = {
    "A_baseline_verse+reflexion+meditar": ROOT / "editorial" / "semantic_search",
    "B_verses_only_verse+meditar": ROOT / ".experiments" / "verses_only",
    "C_verse+reflexion_only": ROOT / ".experiments" / "verse_reflexion_only",
}


def load_variant(out_dir):
    manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    vectors = np.fromfile(out_dir / "embeddings.bin", dtype="<f4").reshape(len(manifest), DIM)
    return manifest, vectors


def search(model, manifest, vectors, query_text, top_n=10, language=None):
    query_vec = model.encode([f"query: {query_text}"], normalize_embeddings=True)[0]
    scores = vectors @ query_vec
    if language is not None:
        mask = np.array([e["language"] == language for e in manifest])
        scores = np.where(mask, scores, -np.inf)
    top_indices = np.argsort(-scores)[:top_n]
    return [manifest[i]["id"] for i in top_indices]


def iter_english_topic_queries():
    for topic, spec in TestSemanticRelevance.TOPIC_GROUND_TRUTH.items():
        for style, query_text in spec["queries"].items():
            yield f"en/{topic}/{style}", "en", query_text, spec["ids"]


def iter_multilingual_topic_queries():
    for lang, topics in TestSemanticRelevance.MULTILINGUAL_TOPIC_GROUND_TRUTH.items():
        for topic, spec in topics.items():
            for style in ("single", "multi"):
                if style not in spec:
                    continue
                yield f"{lang}/{topic}/{style}", lang, spec[style], spec["ids"]


def main():
    model = SentenceTransformer(MODEL_NAME, device="cpu")

    queries = list(iter_english_topic_queries()) + list(iter_multilingual_topic_queries())
    print(f"Loaded {len(queries)} ground-truth queries")

    results_by_variant = {}
    for variant_name, out_dir in VARIANTS.items():
        if not (out_dir / "embeddings.bin").exists():
            print(f"SKIP {variant_name}: {out_dir} not built yet")
            continue
        manifest, vectors = load_variant(out_dir)
        print(f"\n=== {variant_name} ({len(manifest)} vectors) ===")

        rows = []
        hits = 0
        for label, lang, query_text, expected_ids in queries:
            result_ids = search(model, manifest, vectors, query_text, top_n=10, language=lang)
            hit = bool(expected_ids & set(result_ids))
            hits += hit
            rows.append(
                {
                    "query_label": label,
                    "language": lang,
                    "query_text": query_text,
                    "hit": hit,
                    "expected_ids": sorted(expected_ids),
                    "result_ids": result_ids,
                }
            )
            status = "HIT " if hit else "MISS"
            print(f"  [{status}] {label}: {query_text[:60]!r}")

        hit_rate = hits / len(queries) if queries else 0.0
        results_by_variant[variant_name] = {"hit_rate": hit_rate, "hits": hits, "total": len(queries), "rows": rows}
        print(f"  --> {variant_name}: {hits}/{len(queries)} ({hit_rate:.1%})")

    print("\n=== SUMMARY ===")
    for variant_name, r in results_by_variant.items():
        print(f"{variant_name}: {r['hits']}/{r['total']} ({r['hit_rate']:.1%})")

    log_dir = ROOT / ".experiments" / "benchmark_logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_path = log_dir / f"benchmark_{timestamp}.json"
    log_path.write_text(
        json.dumps(
            {
                "timestamp": timestamp,
                "model": MODEL_NAME,
                "query_count": len(queries),
                "variants": results_by_variant,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nFull log written to {log_path}")


if __name__ == "__main__":
    main()
