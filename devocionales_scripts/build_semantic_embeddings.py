"""Precompute multilingual sentence embeddings for the devotional corpus.

Reads every Devocional_year_{year}_{lang}_{version}.json file — plus the
bare Devocional_year_{year}.json files, a legacy naming holdover that is
still the canonical es/RVR1960 source per index.json — embeds
versiculo + reflexion + para_meditar per entry, and writes:
  - <out-dir>/embeddings.bin   (little-endian float32, unit-normalized,
                                 row-major, one row per entry)
  - <out-dir>/manifest.json    (parallel list of {id, language, version,
                                 date} in the same row order)

--model selects the embedding model (default bge-m3, the committed
baseline as of PR #118, which replaced multilingual-e5-small after
benchmarking). --out-dir writes to an alternate location instead of
overwriting the committed baseline, for side-by-side comparison — always
pass it when trying a new model so the committed data dir (see
semantic_search_service/config.py's data_dir setting) is never touched
until a result is validated.

--exclude-reflexion embeds only versiculo + para_meditar (dropping the long
free-form reflexion commentary) — an experiment to check whether reflexion's
variable, often-long length was diluting the verse's weight in the pooled
embedding (suspected contributor to the Arabic/German ranking gaps found in
testing).

--device defaults to "auto" (cuda if torch.cuda.is_available(), else cpu).
A full 10-language corpus (~14,600 entries) takes multiple hours on CPU —
confirmed in practice on a 16-core machine and separately on GitHub Actions
runners (~4h per language there). A small/laptop GPU is not guaranteed to
be faster: bge-m3's ~2.3GB footprint plus batch activations can exceed
4GB VRAM even at --batch-size 4, and low-VRAM GPUs may show a similar or
worse wall-clock time than a many-core CPU despite 100% GPU utilization —
verify with a short --languages-limited run before committing to either
device for a full rebuild.
"""

import argparse
import json
import re
import struct
import sys
from pathlib import Path

from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from semantic_search_service.config import settings

# Matches both the standard Devocional_year_{year}_{lang}_{version}.json
# naming and the bare Devocional_year_{year}.json form — the latter is a
# legacy holdover (predates the _{lang}_{version} suffix convention) that
# is still index.json's canonical source for es/RVR1960. A prior version
# of this pattern required the suffix, which silently dropped RVR1960
# (730 entries) from every embedding build, e5-small and bge-m3 alike —
# language/version are now read from each entry's own fields (already
# present and correct in every file, suffixed or not) instead of being
# inferred from the filename, so this covers both forms without a
# special case.
FILE_PATTERN = re.compile(r"^Devocional_year_\d{4}(?:_[a-z]+_.+)?\.json$")
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


def load_entries(
    include_reflexion=True, include_para_meditar=True, languages=None, versions=None, strip_arabic=False
):
    entries = []
    for path in sorted(ROOT.glob("Devocional_year_*.json")):
        if not FILE_PATTERN.match(path.name):
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        for lang, day_map in data["data"].items():
            if languages is not None and lang not in languages:
                continue
            for date, day_entries in day_map.items():
                for entry in day_entries:
                    if versions is not None and entry["version"] not in versions:
                        continue
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
                            "language": entry["language"],
                            "version": entry["version"],
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
        "--versions",
        default=None,
        help="Comma-separated Bible version codes to embed (default: all). E.g. --versions RVR1960 "
        "to add just one missing version to an otherwise-complete corpus, without re-embedding "
        "sibling versions (e.g. es/NVI) that are already correct.",
    )
    parser.add_argument(
        "--strip-arabic-diacritics",
        action="store_true",
        help="Strip Arabic harakat/tanwin/sukun/shadda/tatweel from Arabic entries before embedding.",
    )
    parser.add_argument("--out-dir", default=None)
    parser.add_argument("--model", default="bge-m3", choices=MODELS.keys())
    parser.add_argument(
        "--device",
        default="auto",
        help="'auto' picks cuda when available (checked via torch.cuda.is_available()), "
        "else cpu. A full-corpus encode on CPU alone has taken multiple hours in practice "
        "(see PR #118); pass 'cpu' explicitly to force it anyway, or a specific device string.",
    )
    parser.add_argument("--batch-size", type=int, default=64)
    args = parser.parse_args()

    out_dir = Path(args.out_dir) if args.out_dir else settings.data_dir
    languages = set(args.languages.split(",")) if args.languages else None
    versions = set(args.versions.split(",")) if args.versions else None
    model_spec = MODELS[args.model]

    if args.device == "auto":
        import torch

        device = "cuda" if torch.cuda.is_available() else "cpu"
    else:
        device = args.device
    print(f"Using device: {device}")

    entries = load_entries(
        include_reflexion=not args.exclude_reflexion,
        include_para_meditar=not args.exclude_para_meditar,
        languages=languages,
        versions=versions,
        strip_arabic=args.strip_arabic_diacritics,
    )
    print(f"Loaded {len(entries)} devotional entries")

    model = SentenceTransformer(model_spec["name"], device=device, trust_remote_code=True)
    passages = [model_spec["passage_prefix"] + e["text"] for e in entries]
    vectors = model.encode(
        passages,
        normalize_embeddings=True,
        show_progress_bar=True,
        batch_size=args.batch_size,
    )

    out_dir.mkdir(parents=True, exist_ok=True)

    bin_path = out_dir / "embeddings.bin"
    with open(bin_path, "wb") as f:
        f.writelines(struct.pack(f"<{len(vector)}f", *vector) for vector in vectors)

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
