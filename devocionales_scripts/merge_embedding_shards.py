"""Merge per-language embedding shards (each produced by
build_semantic_embeddings.py --languages <lang> --out-dir <shard-dir>)
into a single embeddings.bin + manifest.json.

Used for the full-corpus bge-m3 re-embed: embedding all ~13,870 entries
with bge-m3 in one job would take several hours sequentially (ar alone
took ~2h42m for its ~1460-entry subset in CI — see
benchmark_candidate_model.py's docstring), so the CI workflow runs one
job per language in parallel, each writing its own shard, then this
script merges them in a fixed language order into the final committed
layout. Row order across languages doesn't matter for correctness (every
consumer looks up by id via the manifest), but a fixed order keeps output
deterministic across re-runs.

Usage:
    uv run python3 devocionales_scripts/merge_embedding_shards.py \
        --shards-dir /path/to/shards --languages ar,de,en,es,fil,fr,hi,ja,pt,zh \
        --out-dir editorial/semantic_search_bge_m3
"""

import argparse
import json
from pathlib import Path

import numpy as np

DIM = 1024  # bge-m3's native dense output dimension


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--shards-dir",
        required=True,
        help="Directory containing one subdirectory per language, e.g. <shards-dir>/ar/{embeddings.bin,manifest.json}",
    )
    parser.add_argument("--languages", required=True, help="Comma-separated language codes, in merge order")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--dim", type=int, default=DIM)
    args = parser.parse_args()

    shards_dir = Path(args.shards_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    all_manifest = []
    all_vectors = []
    for lang in args.languages.split(","):
        shard_dir = shards_dir / lang
        manifest = json.loads((shard_dir / "manifest.json").read_text(encoding="utf-8"))
        vectors = np.fromfile(shard_dir / "embeddings.bin", dtype="<f4").reshape(len(manifest), args.dim)
        print(f"  {lang}: {len(manifest)} entries")
        all_manifest.extend(manifest)
        all_vectors.append(vectors)

    merged_vectors = np.concatenate(all_vectors, axis=0)
    print(f"Merged {len(all_manifest)} entries, {merged_vectors.shape[1]}-dim")

    bin_path = out_dir / "embeddings.bin"
    with open(bin_path, "wb") as f:
        f.write(merged_vectors.astype("<f4").tobytes())

    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(all_manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Wrote {bin_path}")
    print(f"Wrote {manifest_path}")


if __name__ == "__main__":
    main()
