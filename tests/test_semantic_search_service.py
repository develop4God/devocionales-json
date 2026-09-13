"""Tests for semantic_search_service/ — the shared search core (search.py),
query embedding (embed.py), and the FastAPI wrapper (api.py) that a web page
or the Flutter app calls into, instead of each client re-implementing
brute-force cosine search or shipping its own copy of the bge-m3 model.

Structural/index tests (no model download) run always. Tests that embed a
real query or hit the live /search and /related endpoints require
RUN_SEMANTIC_MODEL_TESTS=1, matching tests/test_semantic_embeddings.py's gate.
"""

import os
import subprocess
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from semantic_search_service.search import DATA_DIR, DIM, SearchIndex

RUN_MODEL_TESTS = os.environ.get("RUN_SEMANTIC_MODEL_TESTS") == "1"


class DataDirOverrideTests(unittest.TestCase):
    def test_semantic_search_data_dir_env_var_overrides_default(self):
        # A fresh interpreter is required: search.py resolves DATA_DIR at
        # import time, and this test's own process already imported it
        # with the real path above.
        result = subprocess.run(
            [sys.executable, "-c", "from semantic_search_service.search import DATA_DIR; print(DATA_DIR)"],
            cwd=ROOT,
            env={**os.environ, "SEMANTIC_SEARCH_DATA_DIR": "/tmp/some-other-dir"},
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertEqual(result.stdout.strip(), "/tmp/some-other-dir")


@unittest.skipUnless(DATA_DIR.exists(), f"committed embeddings not found at {DATA_DIR}")
class SearchIndexTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = SearchIndex()

    def test_loads_manifest_and_vectors_with_matching_row_count(self):
        self.assertEqual(len(self.index.manifest), self.index.vectors.shape[0])
        self.assertEqual(self.index.vectors.shape[1], DIM)

    def test_vectors_are_unit_normalized(self):
        norms = np.linalg.norm(self.index.vectors[:50], axis=1)
        np.testing.assert_allclose(norms, 1.0, atol=1e-3)

    def test_version_is_stable_across_instances(self):
        other = SearchIndex()
        self.assertEqual(self.index.version, other.version)
        self.assertEqual(len(self.index.version), 16)

    def test_related_excludes_the_source_entry_itself(self):
        sample_id = self.index.manifest[0]["id"]
        results = self.index.related(sample_id, top_n=5)
        result_ids = [rid for rid, _score in results]
        self.assertNotIn(sample_id, result_ids)
        self.assertEqual(len(results), 5)

    def test_related_same_language_filters_to_source_language(self):
        sample = self.index.manifest[0]
        results = self.index.related(sample["id"], top_n=5, same_language=True)
        for rid, _score in results:
            self.assertEqual(self.index.entry(rid)["language"], sample["language"])

    def test_related_unknown_id_raises_key_error(self):
        with self.assertRaises(KeyError):
            self.index.related("not-a-real-id", top_n=5)

    def test_search_with_self_vector_ranks_self_first(self):
        sample = self.index.manifest[0]
        query_vector = self.index.vectors[0]
        results = self.index.search(query_vector, top_n=3)
        self.assertEqual(results[0][0], sample["id"])
        self.assertAlmostEqual(results[0][1], 1.0, places=3)

    def test_search_language_filter_restricts_results(self):
        sample = self.index.manifest[0]
        query_vector = self.index.vectors[0]
        results = self.index.search(query_vector, top_n=10, language=sample["language"])
        for rid, _score in results:
            self.assertEqual(self.index.entry(rid)["language"], sample["language"])

    def test_entry_returns_none_for_unknown_id(self):
        self.assertIsNone(self.index.entry("not-a-real-id"))


@unittest.skipUnless(
    RUN_MODEL_TESTS,
    "requires RUN_SEMANTIC_MODEL_TESTS=1 — downloads BAAI/bge-m3 (~2GB) and runs live queries",
)
@unittest.skipUnless(DATA_DIR.exists(), f"committed embeddings not found at {DATA_DIR}")
class EmbedAndApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient

        import semantic_search_service.api as api_module

        cls.client = TestClient(api_module.app)

    def test_embed_returns_unit_normalized_vector(self):
        from semantic_search_service.embed import embed

        vector = embed("Dios es amor")
        self.assertEqual(vector.shape, (DIM,))
        self.assertAlmostEqual(float(np.linalg.norm(vector)), 1.0, places=3)

    def test_manifest_version_endpoint(self):
        response = self.client.get("/manifest/version")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("version", body)
        self.assertGreater(body["count"], 0)

    def test_search_endpoint_returns_relevant_spanish_result(self):
        response = self.client.post("/search", json={"query": "tengo miedo y ansiedad", "language": "es", "top_n": 5})
        self.assertEqual(response.status_code, 200)
        results = response.json()
        self.assertEqual(len(results), 5)
        for item in results:
            self.assertIn("id", item)
            self.assertIn("score", item)

    def test_related_endpoint_matches_search_core(self):
        from semantic_search_service.search import SearchIndex

        index = SearchIndex()
        sample_id = index.manifest[0]["id"]
        response = self.client.get(f"/related/{sample_id}", params={"top_n": 3})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body), 3)
        expected = index.related(sample_id, top_n=3)
        self.assertEqual([item["id"] for item in body], [rid for rid, _score in expected])

    def test_related_endpoint_404s_on_unknown_id(self):
        response = self.client.get("/related/not-a-real-id")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
