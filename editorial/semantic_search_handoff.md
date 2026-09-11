# Semantic Search — Handoff Plan

**Branch:** `feature/semantic-search-embeddings`
**Status:** Not started — planning only, no code written yet.

## Goal

Let a user type a free-form phrase (e.g. "I'm depressed, I need something") and get back
the most relevant devotional by *meaning*, not exact tag/keyword match. Sits **alongside**
existing tags — does not replace them.

## Approach

Offline/precomputed embedding layer, not a live LLM call per search:

1. Precompute one embedding vector per devotional entry (offline, one-time + incremental for new content).
2. Store vectors alongside the existing JSON content.
3. At search time, embed the user's query with the same model and find nearest vectors
   (cosine/dot-product similarity) against the stored set.

Model: `sentence-transformers/all-MiniLM-L6-v2` (Hugging Face) — 384-dim, small/fast, good default
for short-text semantic similarity. Runs locally, no API key/cost.

## Environment check (done 2026-09-11)

Checked before assuming anything was missing, since an unrelated fine-tuning effort may already
overlap on tooling:

- Project venv (`.venv`) and global pip: only `numpy` present. No `sentence-transformers`, `torch`,
  `transformers`, `huggingface_hub`, `faiss`, or `scikit-learn` installed.
- `uv` (0.12.3) is installed on the machine and should be used for this work instead of raw
  pip/venv — the existing `.venv` was pip-managed; next session should confirm whether to let
  `uv` adopt/recreate it or keep them separate before running `uv add`.
- No cached Hugging Face models found under the home directory.
- `pyproject.toml` has an empty `dependencies = []` list; `dev` extras are just `ruff`/`pytest`.

**Conclusion:** nothing reusable exists yet — this needs a fresh install. Worth re-checking the
fine-tuning effort's environment/requirements before installing, in case it already pins a
compatible `torch`/`sentence-transformers` version (avoid duplicate/conflicting installs).

## Install command (hand to Claude Code agent, not run in this session)

Project uses `uv`, not raw venv/pip — `uv` is already installed (`uv 0.12.3`) and the project
has a `pyproject.toml`, so add the dependency and sync:

```bash
uv add sentence-transformers
```

This pulls in `torch` and `transformers` as dependencies automatically and updates
`pyproject.toml` + the lockfile. If the fine-tuning work already pins a specific `torch`
build (e.g. CUDA-specific) in its own environment, check that first — `uv add torch==<version>`
before `uv add sentence-transformers` to pin it, so `uv` doesn't resolve a mismatched build.

## Suggested implementation steps (next session)

1. Confirm/resolve the `torch` version question above with the fine-tuning setup.
2. `uv add sentence-transformers` (adds to `pyproject.toml` dependencies + lockfile directly).
3. Write an offline script to:
   - Load all devotional JSON entries (~2 years × 365 = ~730 entries).
   - Build embedding input text per entry (likely title + body + tags — needs a decision).
   - Encode with `all-MiniLM-L6-v2`, save vectors (e.g. `.npy` or per-entry field) keyed by entry id.
4. Write a query-time function: embed query, compute similarity against stored vectors, return top-N.
5. Decide storage location/format for vectors (separate file vs. embedded in JSON) — keep tags untouched.
6. Add incremental update path for new devotionals going forward (don't require full re-embed every time).
7. No UI/app integration scoped yet — confirm with Giovanni where results should surface.

## Open questions for Giovanni

- What text exactly should be embedded per devotional (full body? title+summary? tags included)?
- Where do vectors live — new file per year, single index file, or inside existing JSON structure?
- Any constraint from the parallel fine-tuning effort on `torch`/CUDA vs CPU-only?
