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

Usage:
    uv run python3 devocionales_scripts/benchmark_fr_de_deep_dive.py --language fr
    uv run python3 devocionales_scripts/benchmark_fr_de_deep_dive.py --language de
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
BGE_M3_MODEL = "BAAI/bge-m3"

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


def encode_passages(model, model_key, texts):
    if model_key == "small":
        texts = [f"passage: {t}" for t in texts]
    return model.encode(texts, normalize_embeddings=True, show_progress_bar=True, batch_size=32)


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
    args = parser.parse_args()
    language = args.language

    print(f"Loading corpus subset for language={language}...")
    entries = load_entries(languages={language})
    texts = [e["text"] for e in entries]
    manifest = [
        {"id": e["id"], "language": e["language"], "version": e["version"], "date": e["date"]}
        for e in entries
    ]
    print(f"  {len(entries)} entries")

    queries = list(iter_all_queries(language))
    print(f"  {len(queries)} total query variants ({sum(1 for _,_,_,s in queries if s=='single')} single-word, "
          f"{sum(1 for _,_,_,s in queries if s=='multi')} multi-sentence)")

    results = {}
    for model_name, label in ((SMALL_MODEL, "small"), (BGE_M3_MODEL, "bge-m3")):
        print(f"\nLoading {model_name}...")
        model = SentenceTransformer(model_name, device="cpu", trust_remote_code=True)
        print(f"Embedding {len(entries)} {language} entries with {label}...")
        vectors = encode_passages(model, label, texts)

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
