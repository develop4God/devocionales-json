"""Precompute multilingual sentence embeddings for the devotional corpus.

Reads every Devocional_year_{year}_{lang}_{version}.json file, embeds
versiculo + reflexion + para_meditar per entry, and writes:
  - <out-dir>/embeddings.bin   (little-endian float32, unit-normalized,
                                 row-major, one row per entry)
  - <out-dir>/manifest.json    (parallel list of {id, language, version,
                                 date} in the same row order)

--model selects the embedding model (default e5-small, the current
committed baseline; bge-m3 is the PR #118-recommended replacement — see
benchmark_candidate_model.py for the full comparison). --out-dir writes to
an alternate location instead of overwriting the committed baseline, for
side-by-side comparison — always pass it when trying a new model so the
committed editorial/semantic_search/ files are never touched until a
result is validated.

--exclude-reflexion embeds only versiculo + para_meditar (dropping the long
free-form reflexion commentary) — an experiment to check whether reflexion's
variable, often-long length was diluting the verse's weight in the pooled
embedding (suspected contributor to the Arabic/German ranking gaps found in
testing).
"""

import argparse
import glob
import json
import re
import struct
from pathlib import Path

from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parent.parent
FILE_PATTERN = re.compile(r"^Devocional_year_\d{4}_([a-z]+)_(.+)\.json$")
MODEL_NAME = "intfloat/multilingual-e5-small"

# bge-m3 needs no "passage: " prefix (unlike e5-small/e5-base) — see PR #118's
# benchmark_candidate_model.py investigation, which found it beats e5-small
# on every one of the 4 languages with documented ranking gaps (ar/fil/ja/zh:
# 15/24 -> 19/24 combined hit rate, no per-language regression) with qwen3
# only tying it at ~4x the embedding cost.
MODELS = {
    "e5-small": {"name": "intfloat/multilingual-e5-small", "passage_prefix": "passage: "},
    "bge-m3": {"name": "BAAI/bge-m3", "passage_prefix": ""},
}

# Arabic combining marks (harakat/tanwin/sukun/shadda/quranic annotation
# marks) plus tatweel — stripped by --strip-arabic-diacritics to test
# whether the heavily-diacritized biblical text in this corpus (vs. the
# largely undiacritized web text most embedding models are trained on)
# is hurting Arabic ranking quality (see PR #118 investigation).
ARABIC_DIACRITICS_RE = re.compile(
    "[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06DC\u06DF-\u06E8\u06EA-\u06ED\u0640]"
)


def strip_arabic_diacritics(text):
    return ARABIC_DIACRITICS_RE.sub("", text)


def load_entries(include_reflexion=True, include_para_meditar=True, languages=None, strip_arabic=False):
    entries = []
    for path in sorted(ROOT.glob("Devocional_year_*.json")):
        match = FILE_PATTERN.match(path.name)
        if not match:
            continue
        lang, version = match.groups()
        if languages is not None and lang not in languages:
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        for date, day_entries in data["data"][lang].items():
            for entry in day_entries:
                fields = ("versiculo", "reflexion") if include_reflexion else ("versiculo",)
                parts = [entry[field] for field in fields if entry.get(field)]
                if include_para_meditar:
                    for meditar in entry.get("para_meditar") or []:
                        if meditar.get("texto"):
                            parts.append(meditar["texto"])
                text = " ".join(parts)
                if strip_arabic and lang == "ar":
                    text = strip_arabic_diacritics(text)
                entries.append(
                    {
                        "id": entry["id"],
                        "language": lang,
                        "version": version,
                        "date": date,
                        "text": text,
                    }
                )
    return entries


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--exclude-reflexion", action="store_true")
    parser.add_argument("--exclude-para-meditar", action="store_true")
    parser.add_argument(
        "--languages",
        default=None,
        help="Comma-separated language codes to embed (default: all). E.g. --languages ar",
    )
    parser.add_argument(
        "--strip-arabic-diacritics",
        action="store_true",
        help="Strip Arabic harakat/tanwin/sukun/shadda/tatweel from Arabic entries before embedding.",
    )
    parser.add_argument("--out-dir", default=None)
    parser.add_argument("--model", default="e5-small", choices=MODELS.keys())
    args = parser.parse_args()

    out_dir = Path(args.out_dir) if args.out_dir else ROOT / "editorial" / "semantic_search"
    languages = set(args.languages.split(",")) if args.languages else None
    model_spec = MODELS[args.model]

    entries = load_entries(
        include_reflexion=not args.exclude_reflexion,
        include_para_meditar=not args.exclude_para_meditar,
        languages=languages,
        strip_arabic=args.strip_arabic_diacritics,
    )
    print(f"Loaded {len(entries)} devotional entries")

    model = SentenceTransformer(model_spec["name"], device="cpu", trust_remote_code=True)
    passages = [model_spec["passage_prefix"] + e["text"] for e in entries]
    vectors = model.encode(
        passages,
        normalize_embeddings=True,
        show_progress_bar=True,
        batch_size=64,
    )

    out_dir.mkdir(parents=True, exist_ok=True)

    bin_path = out_dir / "embeddings.bin"
    with open(bin_path, "wb") as f:
        for vector in vectors:
            f.write(struct.pack(f"<{len(vector)}f", *vector))

    manifest_path = out_dir / "manifest.json"
    manifest = [
        {"id": e["id"], "language": e["language"], "version": e["version"], "date": e["date"]}
        for e in entries
    ]
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"Wrote {len(entries)} vectors ({vectors.shape[1]}-dim) to {bin_path}")
    print(f"Wrote manifest to {manifest_path}")


if __name__ == "__main__":
    main()
