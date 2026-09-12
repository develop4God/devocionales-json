"""Precompute multilingual sentence embeddings for the devotional corpus.

Reads every Devocional_year_{year}_{lang}_{version}.json file, embeds
versiculo + reflexion + para_meditar per entry with intfloat/multilingual-e5-small,
and writes:
  - editorial/semantic_search/embeddings.bin   (little-endian float32, unit-normalized,
                                                 row-major, one row per entry)
  - editorial/semantic_search/manifest.json    (parallel list of {id, language, version,
                                                 date} in the same row order)

--exclude-reflexion embeds only versiculo + para_meditar (dropping the long
free-form reflexion commentary) — an experiment to check whether reflexion's
variable, often-long length was diluting the verse's weight in the pooled
embedding (suspected contributor to the Arabic/German ranking gaps found in
testing). --out-dir writes to an alternate location instead of overwriting
the committed baseline, for side-by-side comparison.
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


def load_entries(include_reflexion=True, include_para_meditar=True):
    entries = []
    for path in sorted(ROOT.glob("Devocional_year_*.json")):
        match = FILE_PATTERN.match(path.name)
        if not match:
            continue
        lang, version = match.groups()
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
    parser.add_argument("--out-dir", default=None)
    args = parser.parse_args()

    out_dir = Path(args.out_dir) if args.out_dir else ROOT / "editorial" / "semantic_search"

    entries = load_entries(
        include_reflexion=not args.exclude_reflexion,
        include_para_meditar=not args.exclude_para_meditar,
    )
    print(f"Loaded {len(entries)} devotional entries")

    model = SentenceTransformer(MODEL_NAME, device="cpu")
    passages = [f"passage: {e['text']}" for e in entries]
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
