"""Benchmark Arabic diacritic stripping against the committed baseline, for
the 9 documented ranking gaps investigation on PR #118.

Community/literature research (see PR #118 discussion) flagged inconsistent
Arabic diacritization as a known, documented issue for embedding-based
Arabic semantic search — this corpus's biblical text is heavily diacritized
(harakat/tanwin/shadda), unlike the mostly-undiacritized web text most
multilingual embedding models are trained on.

Reuses the already-committed baseline vectors for the ar/single "anxiety"
comparison (no need to re-embed 13,870 entries just to test this) — only
newly embeds a diacritic-stripped Arabic-only subset (~1460 entries, fast)
via build_semantic_embeddings.strip_arabic_diacritics, and compares hit
rate against the same ground-truth queries used in
tests/test_semantic_embeddings.py's Arabic cases.

Usage:
    uv run python3 devocionales_scripts/benchmark_ar_diacritics.py
"""

import json
import sys
import unicodedata
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "devocionales_scripts"))
sys.path.insert(0, str(ROOT / "tests"))

from build_semantic_embeddings import MODEL_NAME, load_entries  # noqa: E402
from test_semantic_embeddings import TestSemanticRelevance  # noqa: E402

DIM = 384
BASELINE_DIR = ROOT / "editorial" / "semantic_search"


def nfc_set(ids):
    return {unicodedata.normalize("NFC", i) for i in ids}


def search(model, manifest, vectors, query_text, top_n=10):
    query_vec = model.encode([f"query: {query_text}"], normalize_embeddings=True)[0]
    scores = vectors @ query_vec
    top_indices = np.argsort(-scores)[:top_n]
    return [manifest[i]["id"] for i in top_indices]


def iter_ar_queries():
    topics = TestSemanticRelevance.MULTILINGUAL_TOPIC_GROUND_TRUTH["ar"]
    for topic, spec in topics.items():
        for style in ("single", "multi"):
            yield f"ar/{topic}/{style}", spec[style], spec["ids"]

    # Cross-language ar_single (Luke 5:32 exact-text self-retrieval),
    # excluded from strict assertion in the test suite (ranks ~503rd at
    # baseline) — the case that originally flagged Arabic as a concern.
    cross = TestSemanticRelevance
    yield (
        "ar/luke532/exact_text (cross-language)",
        "مَا جِئْتُ لأَدْعُوَ إِلَى التَّوْبَةِ أَبْرَاراً بَلْ خَاطِئِينَ",
        {
            "إِنْجِيلُلُوقَا532NAV20250927",
            "إِنْجِيلُلُوقَا532NAV20270611",
            "انجيللوقا532SVDA20250927",
            "انجيللوقا532SVDA20270611",
        },
    )


def main():
    print(f"Loading model {MODEL_NAME}...")
    model = SentenceTransformer(MODEL_NAME, device="cpu")

    print("Loading committed baseline (Arabic subset)...")
    baseline_manifest_full = json.loads((BASELINE_DIR / "manifest.json").read_text(encoding="utf-8"))
    baseline_vectors_full = np.fromfile(BASELINE_DIR / "embeddings.bin", dtype="<f4").reshape(
        len(baseline_manifest_full), DIM
    )
    ar_mask = [i for i, e in enumerate(baseline_manifest_full) if e["language"] == "ar"]
    baseline_manifest = [baseline_manifest_full[i] for i in ar_mask]
    baseline_vectors = baseline_vectors_full[ar_mask]
    print(f"  {len(baseline_manifest)} baseline Arabic entries")

    print("Building diacritic-stripped Arabic corpus...")
    stripped_entries = load_entries(languages={"ar"}, strip_arabic=True)
    stripped_manifest = [
        {"id": e["id"], "language": e["language"], "version": e["version"], "date": e["date"]}
        for e in stripped_entries
    ]
    stripped_passages = [f"passage: {e['text']}" for e in stripped_entries]
    stripped_vectors = model.encode(
        stripped_passages, normalize_embeddings=True, show_progress_bar=True, batch_size=64
    )
    print(f"  {len(stripped_manifest)} diacritic-stripped Arabic entries")

    print("\n=== RESULTS ===")
    baseline_hits = 0
    stripped_hits = 0
    total = 0
    for label, query_text, expected_ids in iter_ar_queries():
        total += 1
        expected_nfc = nfc_set(expected_ids)

        baseline_result_ids = nfc_set(search(model, baseline_manifest, baseline_vectors, query_text))
        stripped_result_ids = nfc_set(search(model, stripped_manifest, stripped_vectors, query_text))

        baseline_hit = bool(expected_nfc & baseline_result_ids)
        stripped_hit = bool(expected_nfc & stripped_result_ids)
        baseline_hits += baseline_hit
        stripped_hits += stripped_hit

        marker = "SAME" if baseline_hit == stripped_hit else "CHANGED"
        print(
            f"[{marker}] {label}: baseline={'HIT' if baseline_hit else 'MISS'} "
            f"stripped={'HIT' if stripped_hit else 'MISS'} — {query_text[:50]!r}"
        )

    print(f"\nBaseline:  {baseline_hits}/{total} ({baseline_hits/total:.1%})")
    print(f"Stripped:  {stripped_hits}/{total} ({stripped_hits/total:.1%})")


if __name__ == "__main__":
    main()
