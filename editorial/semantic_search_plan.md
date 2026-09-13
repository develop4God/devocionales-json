# Semantic Search — Implementation Plan

**Branch:** `feature/semantic-search-embeddings`
**Status:** Planning complete, model download in progress. No embedding/search code written yet.

> **Update (2026-09-13, PR #118):** the committed model below (`intfloat/multilingual-e5-small`)
> was superseded by `BAAI/bge-m3` after benchmarking found it wins on every one of the 10
> languages, including the 4 (ar/fil/ja/zh) where e5-small had documented ranking gaps — see
> `devocionales_scripts/benchmark_candidate_model.py`, `benchmark_fr_de_deep_dive.py`, and
> `benchmark_gap_languages_deep_dive.py` for the investigation. `editorial/semantic_search/`
> now holds bge-m3 vectors (1024-dim), not e5-small (384-dim). The rest of this document is kept
> as a historical record of the original decision process; treat the "Model decision" section
> below as superseded, not current.

## Goal

Let a user type a free-form phrase (e.g. "I'm depressed, I need something") and get back the
devotional most relevant *by meaning*, across all 10 languages, in the production Flutter/Dart app.
Sits **alongside** existing tags — does not replace them.

## Corpus (confirmed from repo, 2026-09-11)

Flat JSON files at repo root, not per-language folders:
`Devocional_year_{2025,2026}_{lang}_{version}.json`

Languages/versions present: `ar` (NAV, SVDA), `de` (LU17, SCH2000), `en` (KJV, NIV), `es` (NVI),
`fil` (ASND, MBB05), `fr` (LSG1910, TOB), `hi` (HERV, HIOV), `ja` (リビングバイブル, 新改訳2003),
`pt` (ARC, NVI), `zh` (和合本1919, 新译本) — 10 languages, some with 2 Bible-version variants,
2 years each (2025, 2026).

Entry structure (confirmed via `Devocional_year_2025_es_NVI.json`):
```json
{
  "data": {
    "<lang>": {
      "<YYYY-MM-DD>": [
        {
          "id": "...", "date": "...", "language": "es", "version": "NVI",
          "versiculo": "...", "reflexion": "...", "para_meditar": "...",
          "oracion": "...", "tags": [...]
        }
      ]
    }
  }
}
```

**Decided:** embed `versiculo + reflexion + para_meditar`. `oracion` (prayer) excluded — more
formulaic/generic across entries, low distinguishing signal. `tags` excluded from the embedded
text — stays a separate/existing filter mechanism, not blended into the vector.

## Model decision

**Chosen: `intfloat/multilingual-e5-small`** (not `all-MiniLM-L6-v2`, which is English-only).

Validated 2026-09-11 against community practice:
- 384-dim output, ~118M params — same size/latency class as MiniLM, small enough for offline
  batch embedding of ~7,300 entries (730/year × 2 years × ~5 languages worth of unique content,
  more if each version-variant is embedded separately — see open question below) and for later
  on-device inference in Dart if desired.
- 100 languages supported (vs. 50 for the multilingual-MiniLM alternative) — confirmed to cover
  Arabic, Hindi, Japanese, Chinese, plus all Latin-script languages in the corpus.
- Independent tests show measurably better retrieval accuracy than
  `paraphrase-multilingual-MiniLM-L12-v2` at the same size/dim/latency cost.
- **Integration detail:** e5 models expect text prefixes — `"query: "` for the user's search
  input at query time, `"passage: "` for the devotional content at embed time. Must not be
  skipped or similarity scores degrade.

**Rejected:** `sentence-transformers/all-MiniLM-L6-v2` (English-only, wrong for 10-language
corpus). `paraphrase-multilingual-MiniLM-L12-v2` (legitimate alternative, weaker retrieval
accuracy per independent benchmarks, kept as fallback if e5-small underperforms in practice).

**Decided:** embed per `(language, version)` pair, not deduped per language. Verified 2026-09-11
by comparing `en_KJV` vs `en_NIV` for the same date — different verses and different `reflexion`
text entirely, not just a translation variant of the same content. Versions are not
interchangeable.

## Storage format decision

**Chosen: flat binary, little-endian `float32`, unit-normalized vectors + a JSON id-manifest.**

Validated 2026-09-11 against community/Flutter-Dart practice:
- Scale (~7,000-15,000 vectors depending on version-variant granularity, 384 dims) is far below
  the ~100k-vector threshold where ANN indexing (FAISS/sqlite-vec/ObjectBox vector DB) pays off.
  Brute-force cosine similarity in Dart is sub-millisecond at this scale — a vector database adds
  a native dependency and complexity for a scale problem this corpus doesn't have.
- Vectors pre-normalized to unit length at export time, so query-time similarity is a plain dot
  product (no per-query sqrt/division).
- Write explicitly little-endian from Python (`numpy.tofile()` is native-endian — pin it) to
  match Dart's default `ByteData` reads. Read in Dart via `ByteData.asFloat32List()` into a
  `Float32List`.
- Manifest (JSON, one entry per vector row in the same order as the binary file) carries
  `id`, `language`, `version`, `date` — whatever's needed to map a matched row back to content.

**Rejected:** JSON array of floats (5-8x larger, slower parse, fine only as a dev-time
intermediate, not the shipped asset). sqlite-vec / ObjectBox vector DB (real Dart packages exist,
but overkill until the corpus is an order of magnitude larger or needs metadata-filtered vector
queries). FAISS/Annoy/usearch/Parquet (no mature idiomatic Dart bindings, unused at this scale in
practice).

## Query-time embedding (Dart side) — not yet decided

Two paths, not yet chosen:
1. **On-device inference** via ONNX Runtime (the `fonnx` Flutter package supports this) using an
   ONNX export of `multilingual-e5-small`. No network call per search, works offline.
2. **Backend call** — send the query text to a small server-side endpoint that runs the same
   Python model, returns the embedding. Simpler to keep in sync with the Python-side model, but
   requires network + a backend endpoint that doesn't exist yet.

**Open question for Giovanni:** does the app have (or want) a backend endpoint at all, or is
fully offline/on-device required? This determines which path to build.

## Steps

1. ~~Validate model choice against community practice~~ — done 2026-09-11.
2. Download `intfloat/multilingual-e5-small` locally (in progress, `uv add sentence-transformers`
   then a one-time model fetch) so it's cached for the embedding script.
3. Resolve open questions above with Giovanni: embedded text fields, version-variant granularity,
   on-device vs. backend query embedding.
4. Write an offline Python script:
   - Load all devotional JSON entries across all language/version files, both years.
   - Build embed input text per entry: `"passage: " + <chosen fields>`.
   - Encode with `multilingual-e5-small`, normalize, write to one (or per-language) binary file
     in the confirmed layout + accompanying JSON manifest.
5. Write the Dart-side query path:
   - Load the binary + manifest as Flutter assets.
   - Embed the query (`"query: " + text`) via whichever path is chosen in step 3.
   - Brute-force dot product against all rows, return top-N by score.
6. Add an incremental update path for new devotionals added after initial embedding (avoid
   requiring a full re-embed of the whole corpus every time).
7. No UI integration scoped yet — confirm with Giovanni where results surface in the app.

## Follow-up (deferred, not in scope for this branch)

Giovanni raised a concern that existing `tags` per devotional may not reliably reflect content.
A quick spot-check (5 `es_NVI` entries, 2026-09-11) showed tags that did match content well
(e.g. "Comunidad, Edificación" for a verse about mutual encouragement), so this is not confirmed
as a corpus-wide problem. Deferred until after semantic search ships: a proper audit across the
full corpus, and only then decide whether an LLM-based re-tagging pass is warranted. Not part of
this embedding pipeline — tags stay untouched here.

## Environment status (2026-09-11)

- `.venv` was pip-only before this session; `uv` (0.12.3) is installed and now the tool of record
  for this project's dependencies — `sentence-transformers` added via `uv add`.
- Hugging Face cache before this session held only unrelated Gemma models
  (`unsloth/gemma-3-1b-it`, `unsloth/gemma-4-E4B-it`) from a parallel fine-tuning effort — no
  overlap/conflict with this work, no embedding model was cached.
- `multilingual-e5-small` download initiated this session.
