"""Deeper accuracy check for the 4 languages bge-m3 already improved in
the single-query-per-topic check (ar/fil/ja/zh — see
benchmark_candidate_model.py's docstring). That check used exactly ONE
single-word query and ONE multi-sentence query per topic, same limitation
as the fr/de regression check in benchmark_fr_de_deep_dive.py — a win on
one specific phrasing isn't proof the model is broadly better for the
language.

Runs several independently-worded queries per topic (multiple single-word
synonyms, multiple multi-sentence phrasings) against the same expected
verse ids, for both models, broken down by single-word vs multi-word, so
the "bge-m3 fixed these languages" conclusion rests on more than 6 data
points per language.

Usage:
    uv run python3 devocionales_scripts/benchmark_gap_languages_deep_dive.py --language ar
    uv run python3 devocionales_scripts/benchmark_gap_languages_deep_dive.py --language fil
    uv run python3 devocionales_scripts/benchmark_gap_languages_deep_dive.py --language ja
    uv run python3 devocionales_scripts/benchmark_gap_languages_deep_dive.py --language zh
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

# Note: ar/fil/ja/zh ground truth topic keys are "anxiety" (not
# "anxiety_fear" as in es/pt/fr/de/hi) — matched against
# MULTILINGUAL_TOPIC_GROUND_TRUTH accordingly below.
EXTRA_QUERIES = {
    "ar": {
        "anxiety": {
            "single": ["توتر", "خوف", "هم"],
            "multi": [
                "أنا قلق جداً بشأن المستقبل.\nلا أستطيع التوقف عن التفكير في المشاكل.\nأشعر بالخوف باستمرار.",
                "الخوف يسيطر علي طوال الوقت.\nأقلق بشأن كل شيء.\nلا أجد راحة من هذا التوتر.",
            ],
        },
        "comfort": {
            "single": ["سلوى", "طمأنينة"],
            "multi": [
                "أمر بوقت صعب جداً الآن.\nقلبي مكسور.\nأحتاج من يواسيني.",
                "أنا أعاني كثيراً هذه الأيام.\nأشعر بالانكسار الداخلي.\nأبحث عن العزاء.",
            ],
        },
        "rest": {
            "single": ["استراحة", "سكينة"],
            "multi": [
                "أنا متعب جداً ومنهك تماماً.\nلم أتوقف عن العمل منذ أسابيع.\nأحتاج إلى راحة حقيقية.",
                "طاقتي انتهت تماماً.\nأعمل بدون توقف.\nأبحث عن راحة فعلية.",
            ],
        },
    },
    "fil": {
        "anxiety": {
            "single": ["Pangamba", "Takot", "Alalahanin"],
            "multi": [
                "Sobrang alala ko sa hinaharap.\nHindi ko mapigil ang pag-iisip ng masama.\nParati akong natatakot.",
                "Puno ako ng pangamba ngayon.\nNag-aalala ako sa lahat.\nHindi ako mapakali.",
            ],
        },
        "comfort": {
            "single": ["Aliw", "Ginhawa"],
            "multi": [
                "Nahihirapan ako ngayon.\nParang wasak ang puso ko.\nKailangan ko ng kaaliwan.",
                "Mahirap ang buhay ko ngayon.\nNasira ang loob ko.\nHinahanap ko ang kaginhawaan.",
            ],
        },
        "rest": {
            "single": ["Kapahingahan", "Kalmado"],
            "multi": [
                "Sobrang pagod na ako.\nWala akong tigil sa trabaho sa loob ng ilang linggo.\nKailangan ko ng tunay na pahinga.",
                "Naubusan na ako ng lakas.\nParati akong nagtatrabaho nang walang tigil.\nHinahanap ko ang tunay na kapahingahan.",
            ],
        },
    },
    "ja": {
        "anxiety": {
            "single": ["不安", "心配", "恐怖"],
            "multi": [
                "将来のことがとても心配です。\n悪いことばかり考えてしまいます。\nいつも怖い気持ちがあります。",
                "不安でいっぱいです。\nすべてのことが心配です。\nこの緊張から逃れられません。",
            ],
        },
        "comfort": {
            "single": ["癒し", "励まし"],
            "multi": [
                "今とても辛い時を過ごしています。\n心が壊れそうです。\n誰かに慰めてほしいです。",
                "最近本当に苦しいです。\n内側から崩れそうです。\n慰めを探しています。",
            ],
        },
        "rest": {
            "single": ["休養", "平安"],
            "multi": [
                "とても疲れていて完全に燃え尽きています。\n何週間も休まず働いています。\n本当の休息が必要です。",
                "力が尽きてしまいました。\n休まずに働き続けています。\n本当の休みを探しています。",
            ],
        },
    },
    "zh": {
        "anxiety": {
            "single": ["担忧", "紧张", "恐惧"],
            "multi": [
                "我对未来非常担忧。\n我无法停止想坏事。\n我一直感到害怕。",
                "焦虑充满了我的内心。\n我对一切都感到担心。\n我无法摆脱这种紧张。",
            ],
        },
        "comfort": {
            "single": ["慰藉", "宽慰"],
            "multi": [
                "我现在正经历非常艰难的时期。\n我的心感觉破碎了。\n我需要有人安慰我。",
                "最近我真的很痛苦。\n内心感觉快要崩溃了。\n我在寻找安慰。",
            ],
        },
        "rest": {
            "single": ["休养", "平静"],
            "multi": [
                "我非常疲惫,完全精疲力竭。\n我已经好几个星期没有停下来休息了。\n我需要真正的休息。",
                "我的力气已经用尽了。\n我一直不停地工作。\n我在寻找真正的休息。",
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
    topics = TestSemanticRelevance.MULTILINGUAL_TOPIC_GROUND_TRUTH[language]
    extra = EXTRA_QUERIES[language]
    for topic, spec in topics.items():
        if topic not in extra:
            continue
        expected_ids = spec["ids"]
        yield f"{topic}/single/original", spec["single"], expected_ids, "single"
        yield f"{topic}/multi/original", spec["multi"], expected_ids, "multi"
        for i, q in enumerate(extra[topic]["single"]):
            yield f"{topic}/single/extra{i+1}", q, expected_ids, "single"
        for i, q in enumerate(extra[topic]["multi"]):
            yield f"{topic}/multi/extra{i+1}", q, expected_ids, "multi"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--language", required=True, choices=["ar", "fil", "ja", "zh"])
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
