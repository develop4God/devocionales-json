# shared_validation

Internal library shared by the `encounters` and `discovery` validator pipelines. It exists because
both pipelines independently converged on near-identical solutions for several concerns — this
package is the single implementation of those concerns, extracted after both originals were read
in full and diffed line-by-line to confirm the logic was actually identical, not just similar.

**Nobody runs this package directly.** It has no CLI and no `__main__`. It is imported by validator
scripts and does nothing on its own.

## Status

Two parallel entry-point scripts prove this library is a safe substrate, by reproducing their
originals' output byte-for-byte on real repo content:

| Original (unchanged, still the one anyone runs) | Parallel build on `shared_validation` |
|---|---|
| `encounters/encounters_scripts/validate_encounters.py` | `encounters/encounters_scripts/validate_encounters_v2.py` |
| `discovery/discovery_scripts/validate_discovery.py` | `discovery/discovery_scripts/validate_discovery_v2.py` |

Both `_v2` scripts are **not wired into CI, git hooks, or any documented workflow.** They exist
side-by-side with the originals for comparison only. No decision has been made yet to ever swap
one in for the other — that is future, separate work.

## What's shared vs. what stays custom per pipeline

The boundary was drawn by reading both 900+-line validator scripts in full and classifying every
piece of overlapping logic into one of three tiers — not by guessing from similar-looking code.

### Shared (this package) — genuinely identical logic, safe to extract

| Module | What it does | Why it's safe to share |
|---|---|---|
| `bible_sot.py` | `load_bible_versions(cache_name)` — fetches Bible version/language config from the live remote SOT (`develop4God/bible_versions`), with retry and a temp-dir-only offline fallback cache. | Byte-identical fetch/retry/cache logic in both originals. `cache_name` namespaces the temp file per caller so two pipelines running concurrently never collide. Improves on the originals: raises an explicit `RuntimeError` on total cache-miss instead of an unhandled `FileNotFoundError`. |
| `text_checks.py` | `check_quote_anomalies()`, `is_verse_continuation_close()`, `iter_strings()`, `is_cognate()` + the Romance-cognate word table. | Identical quote/punctuation-anomaly detection logic in both originals (doubled quote chars, unbalanced guillemets, odd straight-quote counts, verse-continuation exception). Cognate table is the union of both pipelines' tables. |
| `lint.py` | `lint_json_files(directory, report, exclude_dir_part, severity)` — JSON indent=2 / tab / trailing-newline checks, returns a parsed-JSON cache. | Same algorithm in both originals; only *severity* differed (encounters treats findings as errors, discovery as warnings) — the shared function takes `severity` as an explicit parameter instead of hardcoding either pipeline's choice, so migrating never silently changes a pipeline's gating behavior. |
| `report.py` | `Report` class (`E`/`W`/`I` methods, phase-scoped, prints a formatted report) + a `ReportLike` `typing.Protocol` documenting that contract. | Based on encounters' `Report` (cleaner than discovery's `ValidationReport`). The `Protocol` exists because discovery's own report class uses different method names (`add_error`/`add_warning`/`add_info`) — see below, this is a real interface mismatch, not folklore. |

### Custom per pipeline — deliberately NOT shared

Each `validate_*_v2.py` keeps a full local copy of its pipeline's own rules, unchanged from the
original. These were evaluated and rejected as extraction candidates because they encode
genuinely different structure or policy, not just different field names:

- **Card/type-specific schema validation** — encounters' `CARD_REQUIRED_KEYS` dispatch table
  (`cinematic_scene`, `scripture_moment`, `discovery_activation`, etc.) has no discovery
  equivalent; discovery's `greek_words` / `timeline` / `scripture_anchor` checks have no
  encounters equivalent. Different content types, different schemas — sharing this would mean one
  module serving two unrelated vocabularies.
- **English-leakage heuristics** — discovery's CJK-vowel detection and exact-English-category
  blocklist (`validate_no_english_in_translation`, `validate_discovery_question_categories`) exist
  only in discovery. Encounters has no equivalent check.
- **Phase A index-structure validation** — both pipelines validate their `index.json` (required
  fields → duplicate ID → language coverage → filename convention → file existence), but on
  different field vocabularies (`encounters` array vs. `studies` array, different required-field
  lists). Same *shape*, different *fields*, and only two consumers exist — abstracting this now
  would be speculative generality for no real reuse benefit.
- **Cross-translation / key-parity checking** — encounters' `validate_cross_translation` and
  discovery's `_check_key_parity` do structurally similar recursive walks, but encode **different
  editorial policies**: encounters flags identical-to-English text as a translation-quality
  warning; discovery deliberately does not (by design — see discovery's own docstring, it has a
  separate review pipeline for translation quality). A shared walker with a quality-check flag
  would hide that policy difference behind a boolean, which is worse than two small, honest,
  separate functions.

### One real interface gap this surfaced

`shared_validation.lint` and `shared_validation.text_checks.check_quote_anomalies` call
`report.E(...)` / `report.W(...)`. Encounters' own `Report` already has those exact method names.
Discovery's `ValidationReport` does not — it uses `add_error` / `add_warning` / `add_info`, plus
tracks run statistics (`stats['total_files']`, etc.) and a different `print_report()` format that
the original discovery output depends on.

Rather than rewrite discovery's report class (which would change its output), `validate_discovery_v2.py`
keeps `ValidationReport` exactly as it is and adds three one-line aliases:

```python
E = add_error
W = add_warning
I = add_info
```

This satisfies `shared_validation`'s `ReportLike` protocol without touching discovery's existing
behavior or output format. It's a real Interface Segregation gap between the two pipelines'
reporting conventions — noted here rather than papered over, in case it matters for any future
decision to reconcile the two `Report` implementations into one.

## Verification performed

Both `_v2` scripts were run against real repository content and diffed against their originals'
output, more than once across this work (including a fresh re-run at the end to catch any drift):

- `validate_encounters_v2.py` output is byte-identical to `validate_encounters.py`, exit code 0.
- `validate_discovery_v2.py` output is byte-identical to `validate_discovery.py`, exit code 0
  (after fixing the `E`/`W`/`I` alias gap above, which a first run caught as an `AttributeError`).
- `bible_sot.load_bible_versions`'s cache-miss `RuntimeError` path was exercised directly (network
  fetch mocked to fail, no cache present) and confirmed to raise cleanly instead of leaking an
  unhandled `FileNotFoundError`.
- Confirmed via `git diff --stat` that neither original script, nor either
  `*_master_validator.py` wrapper, was modified — only new files exist.

## If a future migration is ever decided

This package and the two `_v2` scripts are not a commitment to swap anything. If that's decided
later: migrate one pipeline at a time (encounters first, since its `Report` already matches the
shared `ReportLike` protocol with no adapter needed), keep it timeboxed, and reconcile discovery's
`ValidationReport` vs. shared `Report` gap as part of that work rather than leaving the alias
workaround in place indefinitely.
