"""Tests for the semantic search embeddings (devocionales_scripts/build_semantic_embeddings.py
output) — validates the committed artifacts in editorial/semantic_search/ and, separately,
that the embedding pipeline produces semantically meaningful matches, not just well-formed
binary output.
"""

import json
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "devocionales_scripts"))

EMBEDDINGS_PATH = ROOT / "editorial" / "semantic_search" / "embeddings.bin"
MANIFEST_PATH = ROOT / "editorial" / "semantic_search" / "manifest.json"
DIM = 384


class TestEmbeddingArtifactIntegrity(unittest.TestCase):
    """Structural checks on the committed embeddings.bin + manifest.json —
    catches a broken/truncated regeneration without needing the model."""

    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        cls.vectors = np.fromfile(EMBEDDINGS_PATH, dtype="<f4")

    def test_binary_size_matches_manifest_row_count(self):
        expected_floats = len(self.manifest) * DIM
        self.assertEqual(
            self.vectors.size,
            expected_floats,
            "embeddings.bin float count must equal len(manifest) * 384 — "
            "a mismatch means the two files are out of sync.",
        )

    def test_manifest_entries_have_required_fields(self):
        for entry in self.manifest:
            for field in ("id", "language", "version", "date"):
                self.assertIn(field, entry)
                self.assertTrue(entry[field], f"empty {field} in manifest entry {entry}")

    def test_manifest_ids_are_unique(self):
        ids = [e["id"] for e in self.manifest]
        self.assertEqual(len(ids), len(set(ids)), "duplicate ids found in manifest")

    def test_vectors_are_unit_normalized(self):
        rows = self.vectors.reshape(-1, DIM)
        norms = np.linalg.norm(rows, axis=1)
        # sampled, not every row, to keep this test fast
        sample = norms[:: max(1, len(norms) // 200)]
        np.testing.assert_allclose(sample, 1.0, atol=1e-4)

    def test_no_nan_or_inf(self):
        self.assertTrue(np.isfinite(self.vectors).all())


class TestSemanticRelevance(unittest.TestCase):
    """Loads the real model and confirms a query actually surfaces thematically
    relevant devotionals — guards against a wrong-model or wrong-field regression
    that would still pass the structural checks above."""

    @classmethod
    def setUpClass(cls):
        from sentence_transformers import SentenceTransformer

        cls.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        cls.vectors = np.fromfile(EMBEDDINGS_PATH, dtype="<f4").reshape(len(cls.manifest), DIM)
        cls.model = SentenceTransformer("intfloat/multilingual-e5-small")

    def _search(self, query_text, top_n=5):
        query_vec = self.model.encode([f"query: {query_text}"], normalize_embeddings=True)[0]
        scores = self.vectors @ query_vec
        top_indices = np.argsort(-scores)[:top_n]
        return [(float(scores[i]), self.manifest[i]) for i in top_indices]

    def test_comfort_query_returns_thematically_relevant_passages(self):
        """Raw cosine score magnitude is not a reliable relevant/irrelevant signal
        for this model on this corpus (verified: nonsense queries like 'random
        gibberish xkqz' score ~0.82, same range as real queries) — all-MiniLM/e5
        family scores run uniformly high on short devotional-style text regardless
        of relevance. So this checks actual content instead of score thresholds:
        a comfort-themed query's top results should be drawn from the small set
        of books/entries actually about comfort/hope/repentance, not arbitrary."""
        results = self._search("I feel depressed and hopeless, I need comfort", top_n=5)
        comfort_keywords = (
            "heb",  # Hebrews (hold fast to hope)
            "philippians4",  # Phil 4:7, peace that surpasses understanding
            "peter",  # 2 Peter
            "rev21",  # Revelation 21:4, no more tears
            "psalm",
            "isaiah",
        )
        matching = [
            entry for _, entry in results if any(k in entry["id"].lower() for k in comfort_keywords)
        ]
        self.assertGreaterEqual(
            len(matching),
            3,
            f"expected at least 3 of top 5 results to be comfort/hope-themed passages, "
            f"got {[e['id'] for _, e in results]}",
        )

    def test_cross_language_queries_find_same_target_entry(self):
        """Each language has its own independent devotional calendar — the same
        calendar date is NOT the same verse/content across languages (verified:
        2025-08-01 is Luke 5:32 in en, 1 Thess 5:11 in es, Ephesians 1:7 in pt,
        Hebrews 4:12 in fr — four unrelated passages). So there is no ground
        truth pairing by date to test against.

        Instead: anchor on one verse (Luke 5:32, "I have not come to call the
        righteous, but sinners to repentance") and hand-translate its meaning
        into Spanish, Portuguese, and French, single-line and multi-line. Each
        query — regardless of language or phrasing — should retrieve an entry
        for THAT SAME VERSE (id containing "lucas532"/"luke532", any language's
        recurrence of it across different years) near the top of its own
        results. This is the real test of whether the shared multilingual
        vector space aligns languages on meaning, not whether two unrelated
        queries happen to overlap.

        Confirmed while building this test: a Spanish phrasing of this verse's
        meaning correctly retrieves "lucas532NVI..." entries (the same verse,
        in Spanish) — matching by language-appropriate id, not by a single
        fixed id, is the correct check."""
        target_markers = ("luke532", "lucas532")
        queries = {
            "en_single": "I have not come to call the righteous, but sinners to repentance",
            "en_multi": (
                "Jesus did not come for those who think they are already righteous.\n"
                "He came for sinners.\n"
                "He calls them to repentance."
            ),
            "es_single": "No he venido a llamar a justos, sino a pecadores al arrepentimiento",
            "es_multi": (
                "Jesús no vino por los que se creen justos.\n"
                "Vino por los pecadores.\n"
                "Los llama al arrepentimiento."
            ),
            "pt_single": "Não vim chamar justos, mas pecadores ao arrependimento",
            "fr_single": "Je ne suis pas venu appeler des justes, mais des pécheurs à la repentance",
        }

        for label, text in queries.items():
            results = self._search(text, top_n=10)
            result_ids = [entry["id"].lower() for _, entry in results]
            matched = any(
                marker in rid for rid in result_ids for marker in target_markers
            )
            self.assertTrue(
                matched,
                f"{label} query did not retrieve a Luke 5:32 entry in its top 10 "
                f"({result_ids}) — cross-lingual alignment may be broken",
            )


if __name__ == "__main__":
    unittest.main()
