"""Deeper accuracy check for the two languages that showed a bge-m3
regression in the single-query-per-topic regression check (see
benchmark_candidate_model.py's docstring: fr 6/6->5/6, de 5/6->4/6).

That check used exactly ONE single-word query and ONE multi-sentence query
per topic — not enough to tell "bge-m3 is worse at fr/de anxiety_fear" from
"this one specific phrasing happens to rank badly." This script runs
several independently-worded queries per topic (multiple single-word
synonyms, multiple multi-sentence phrasings) against the SAME expected
verse ids, for both models, and reports hit-rate broken down by
single-word vs multi-word so a narrow phrasing-specific miss doesn't get
mistaken for a systemic model regression.

Reuses ALREADY-COMPUTED passage vectors instead of re-embedding the
corpus: --small-dir defaults to the committed e5-small baseline
(editorial/semantic_search/), --bge-m3-dir points at a bge-m3 shard
directory (embeddings.bin + manifest.json for this language only, as
produced by build_semantic_embeddings.py --model bge-m3 --languages
<lang>, e.g. downloaded from the bge-m3-shard-<lang> CI artifact). Only
the query text gets encoded fresh per model — the expensive part
(embedding ~1460 passages) is skipped entirely, so this runs in seconds
per language instead of tens of minutes.

Usage:
    uv run python3 devocionales_scripts/benchmark_fr_de_deep_dive.py \
        --language fr --bge-m3-dir /path/to/bge-m3-shard-fr
"""

import argparse
import json
import sys
import unicodedata
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))

from test_semantic_embeddings import TestSemanticRelevance  # noqa: E402

SMALL_MODEL = "intfloat/multilingual-e5-small"
BGE_M3_MODEL = "BAAI/bge-m3"
SMALL_DIM = 384
BGE_M3_DIM = 1024


def load_precomputed(vec_dir, dim, language=None):
    """Loads a manifest.json + embeddings.bin pair. If `language` is given,
    filters to just that language's rows (for loading a subset out of the
    full committed baseline, which covers all 10 languages)."""
    manifest = json.loads((vec_dir / "manifest.json").read_text(encoding="utf-8"))
    vectors = np.fromfile(vec_dir / "embeddings.bin", dtype="<f4").reshape(len(manifest), dim)
    if language is not None:
        mask = [i for i, e in enumerate(manifest) if e["language"] == language]
        manifest = [manifest[i] for i in mask]
        vectors = vectors[mask]
    return manifest, vectors

# Extra single-word synonyms and multi-sentence rephrasings per topic, on
# top of the one query the original test suite already checks. Expected
# ids are reused from MULTILINGUAL_TOPIC_GROUND_TRUTH — same target
# verses, just approached with different wording, since a genuinely good
# embedding of "I'm anxious" content should surface the same verses
# regardless of which synonym or sentence structure the user typed.
EXTRA_QUERIES = {
    "fr": {
        "anxiety_fear": {
            "single": ["anxiété", "peur", "inquiétude", "angoisse"],
            "multi": [
                "Je suis rongé par l'inquiétude en ce moment.\nRien ne me rassure.\nJ'ai peur de ce qui va arriver.",
                "L'angoisse ne me quitte pas.\nJe m'inquiète pour tout.\nLa peur m'envahit sans cesse.",
            ],
        },
        "comfort": {
            "single": ["réconfort", "soulagement"],
            "multi": [
                "Tout est difficile en ce moment.\nJe me sens vraiment abattu.\nJ'aimerais tant être réconforté.",
                "Je traverse une épreuve douloureuse.\nMon cœur est brisé.\nJ'ai besoin d'être consolé.",
            ],
        },
        "rest": {
            "single": ["détente", "tranquillité"],
            "multi": [
                "Je n'en peux plus, je suis épuisé.\nCela fait des semaines que je n'arrête pas.\nJ'ai besoin de vrai repos.",
                "Je suis à bout de forces.\nJe travaille sans jamais m'arrêter.\nJe cherche un repos véritable.",
            ],
        },
    },
    "de": {
        "anxiety_fear": {
            "single": ["Furcht", "Sorge", "Nervosität", "Beklemmung"],
            "multi": [
                "Ich mache mir ständig Sorgen.\nNichts beruhigt mich.\nIch habe Angst vor der Zukunft.",
                "Die Angst lässt mich nicht los.\nIch sorge mich um alles.\nFurcht überwältigt mich immer wieder.",
            ],
        },
        "comfort": {
            "single": ["Tröstung", "Erleichterung"],
            "multi": [
                "Gerade ist alles sehr schwer.\nIch fühle mich niedergeschlagen.\nIch wünsche mir so sehr Trost.",
                "Ich gehe durch eine schmerzhafte Zeit.\nMein Herz ist gebrochen.\nIch brauche Tröstung.",
            ],
        },
        "rest": {
            "single": ["Entspannung", "Erholung"],
            "multi": [
                "Ich kann nicht mehr, ich bin völlig erschöpft.\nSeit Wochen komme ich nicht zur Ruhe.\nIch brauche echte Erholung.",
                "Ich bin am Ende meiner Kräfte.\nIch arbeite ohne Unterbrechung.\nIch suche wirkliche Ruhe.",
            ],
        },
    },
}


def nfc_set(ids):
    return {unicodedata.normalize("NFC", i) for i in ids}


def encode_query(model, model_key, text):
    if model_key == "small":
        return model.encode([f"query: {text}"], normalize_embeddings=True)[0]
    return model.encode([text], normalize_embeddings=True)[0]


def iter_all_queries(language):
    """Original ground-truth query (from the test suite) plus the extra
    synonym/rephrasing queries defined above, all mapped to the same
    expected ids per topic."""
    topics = TestSemanticRelevance.MULTILINGUAL_TOPIC_GROUND_TRUTH[language]
    extra = EXTRA_QUERIES[language]
    for topic, spec in topics.items():
        expected_ids = spec["ids"]
        yield f"{topic}/single/original", spec["single"], expected_ids, "single"
        yield f"{topic}/multi/original", spec["multi"], expected_ids, "multi"
        for i, q in enumerate(extra[topic]["single"]):
            yield f"{topic}/single/extra{i+1}", q, expected_ids, "single"
        for i, q in enumerate(extra[topic]["multi"]):
            yield f"{topic}/multi/extra{i+1}", q, expected_ids, "multi"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--language", required=True, choices=["fr", "de"])
    parser.add_argument(
        "--small-dir",
        default=str(ROOT / "editorial" / "semantic_search"),
        help="Directory with the committed e5-small embeddings.bin + manifest.json (full corpus; filtered by language)",
    )
    parser.add_argument(
        "--bge-m3-dir",
        required=True,
        help="Directory with a bge-m3 shard's embeddings.bin + manifest.json for this language only",
    )
    args = parser.parse_args()
    language = args.language

    queries = list(iter_all_queries(language))
    print(f"{len(queries)} total query variants ({sum(1 for _,_,_,s in queries if s=='single')} single-word, "
          f"{sum(1 for _,_,_,s in queries if s=='multi')} multi-sentence)")

    vec_sources = {
        "small": (SMALL_MODEL, "small", Path(args.small_dir), SMALL_DIM, True),
        "bge-m3": (BGE_M3_MODEL, "bge-m3", Path(args.bge_m3_dir), BGE_M3_DIM, False),
    }

    results = {}
    for label, (model_name, model_key, vec_dir, dim, filter_lang) in vec_sources.items():
        print(f"\nLoading precomputed {label} vectors from {vec_dir}...")
        manifest, vectors = load_precomputed(vec_dir, dim, language=language if filter_lang else None)
        print(f"  {len(manifest)} entries, {vectors.shape[1]}-dim")

        print(f"Loading {model_name} (for query encoding only)...")
        model = SentenceTransformer(model_name, device="cpu", trust_remote_code=True)

        rows = []
        for q_label, query_text, expected_ids, style in queries:
            expected_nfc = nfc_set(expected_ids)
            query_vec = encode_query(model, label, query_text)
            scores = vectors @ query_vec
            order = np.argsort(-scores)
            top10_ids = nfc_set(manifest[i]["id"] for i in order[:10])
            hit = bool(expected_nfc & top10_ids)
            rows.append((q_label, style, hit, query_text))
        results[label] = rows

    print("\n=== RESULTS ===")
    for small_row, bge_row in zip(results["small"], results["bge-m3"]):
        q_label, style, small_hit, query_text = small_row
        _, _, bge_hit, _ = bge_row
        marker = "SAME" if small_hit == bge_hit else "CHANGED"
        print(f"[{marker}] {language}/{q_label} ({style}) — {query_text[:40]!r}")
        print(f"    small: {'HIT ' if small_hit else 'MISS'}   bge-m3: {'HIT ' if bge_hit else 'MISS'}")

    for label in ("small", "bge-m3"):
        rows = results[label]
        total = len(rows)
        hits = sum(1 for _, _, hit, _ in rows if hit)
        single_rows = [r for r in rows if r[1] == "single"]
        multi_rows = [r for r in rows if r[1] == "multi"]
        single_hits = sum(1 for _, _, hit, _ in single_rows if hit)
        multi_hits = sum(1 for _, _, hit, _ in multi_rows if hit)
        print(f"\n{label}: {hits}/{total} overall ({hits/total:.1%})")
        print(f"  single-word: {single_hits}/{len(single_rows)} ({single_hits/len(single_rows):.1%})")
        print(f"  multi-word:  {multi_hits}/{len(multi_rows)} ({multi_hits/len(multi_rows):.1%})")


if __name__ == "__main__":
    main()
