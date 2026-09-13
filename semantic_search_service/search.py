"""Shared in-memory search core over the committed embeddings — the one
place brute-force cosine lookup is implemented, so the web API and any
future Dart client both go through this instead of each re-implementing
the same dot-product logic (see PR #118 discussion: query embedding stays
server-side too, so the client never needs the bge-m3 model itself).

No index, no vector DB: at ~14,600 rows, brute-force is sub-millisecond
and a vector DB would add a dependency for a scale problem this corpus
doesn't have (see editorial/semantic_search_plan.md's storage-format
decision).
"""

import hashlib
import json
from pathlib import Path

import numpy as np

from semantic_search_service.config import settings

DATA_DIR = settings.data_dir
DIM = 1024  # bge-m3, the committed baseline as of PR #118


class SearchIndex:
    """Loads the committed manifest + vectors once and serves lookups against them."""

    def __init__(self, data_dir=DATA_DIR):
        self.data_dir = Path(data_dir)
        manifest_path = self.data_dir / "manifest.json"
        vectors_path = self.data_dir / "embeddings.bin"

        self.manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.vectors = np.fromfile(vectors_path, dtype="<f4").reshape(len(self.manifest), DIM)
        self.id_to_row = {entry["id"]: i for i, entry in enumerate(self.manifest)}
        self.version = hashlib.sha256(vectors_path.read_bytes()).hexdigest()[:16]

    def __len__(self):
        return len(self.manifest)

    def search(self, query_vector, top_n=10, language=None):
        """Return top_n (id, score) pairs for a pre-embedded, unit-normalized query vector."""
        scores = self.vectors @ query_vector
        order = np.argsort(-scores)
        results = []
        for i in order:
            if language is not None and self.manifest[i]["language"] != language:
                continue
            results.append((self.manifest[i]["id"], float(scores[i])))
            if len(results) >= top_n:
                break
        return results

    def related(self, entry_id, top_n=5, same_language=False):
        """Return top_n (id, score) nearest neighbors of an existing corpus entry."""
        if entry_id not in self.id_to_row:
            raise KeyError(f"id not found in manifest: {entry_id}")
        row = self.id_to_row[entry_id]
        language = self.manifest[row]["language"] if same_language else None
        results = self.search(self.vectors[row], top_n=top_n + 1, language=language)
        return [(rid, score) for rid, score in results if rid != entry_id][:top_n]

    def entry(self, entry_id):
        row = self.id_to_row.get(entry_id)
        return self.manifest[row] if row is not None else None
