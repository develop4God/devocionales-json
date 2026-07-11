# shared_validation

Internal library shared by the `encounters` and `discovery` validator pipelines. It exists because
both pipelines independently converged on near-identical solutions for several concerns — this
package is the single implementation of those concerns, extracted after both originals were read
in full and diffed line-by-line to confirm the logic was actually identical, not just similar.

**Nobody runs this package directly.** It has no CLI and no `__main__`. It is imported by validator
scripts and does nothing on its own.

## Status

**This is now a load-bearing dependency of both live validators**, promoted 2026-07-11 after a
period of parallel comparison (`_v2` scripts proven byte-identical to their originals) and an
independent SOLID review. `encounters_master_validator.py` and `discovery_master_validator.py`
invoke these directly:

| Live validator (built on `shared_validation`) |
|---|
| `encounters/encounters_scripts/validate_encounters.py` |
| `discovery/discovery_scripts/validate_discovery.py` |

The pre-migration originals are not kept in the tree. They're recoverable via:

```
git checkout pre-shared-validation -- encounters/encounters_scripts discovery/discovery_scripts
```

`pre-shared-validation` is a git tag pointing at the last commit before this migration.

A durable smoke-test gate (`tests/test_promoted_validators.py`) shells out to the real master
validators against real repo content on every test run, so this promotion's correctness is a
maintained property, not a one-time verification claim.

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

Each live validator keeps a full local copy of its pipeline's own rules, unchanged from the
pre-migration original. These were evaluated and rejected as extraction candidates because they
encode genuinely different structure or policy, not just different field names:

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

### Schema-templating — considered again, still rejected (2026-07-11)

After this migration shipped, a further idea was floated: since both pipelines' Phase A/B structure
checks are mostly "does this field exist, is it the right type," could that be pulled one layer
further into a generic schema-driven core, with `discovery_template` / `encounters_template` as
the only per-pipeline difference?

The field-presence/type-checking slice of this is real and would be a legitimate future extraction
— it's genuinely mechanical. But it doesn't shrink the list above, because none of those four
items are schema-shape differences to begin with:

- `CARD_REQUIRED_KEYS` isn't a flat schema — it's conditional dispatch keyed on a card's own `type`
  field. Expressible in a schema language (`oneOf`/`if-then-else`), but that's the hardest part to
  get right, not the boilerplate part — a template wouldn't make it safer to share, just differently
  shaped.
- The English-leakage and cross-translation checks are editorial policy running on top of
  similar-looking shapes, not schema. Templating the shape doesn't remove the policy divergence
  (see "different editorial policies" above) — it would just relocate the same boolean-flag problem
  one layer deeper.
- Phase A's "missing language" handling differs in *meaning*, not just field names: encounters'
  `status: coming_soon` changes what a missing translation means for that content unit; discovery
  has no such status concept. A shared template still needs per-pipeline logic to interpret this.

Conclusion: this migration's actual win — encounters' bug fixes automatically reaching discovery —
was already captured by the Tier-1 extraction above (`bible_sot`, `lint`, `text_checks`). The
remaining duplication is not unrealized shared logic; it's the two pipelines correctly diverging.
Not revisiting this again without a concrete new case of duplicated *mechanical* logic (not policy)
showing up.

### One real interface gap this surfaced

`shared_validation.lint` and `shared_validation.text_checks.check_quote_anomalies` call
`report.E(...)` / `report.W(...)`. Encounters' own `Report` already has those exact method names.
Discovery's `ValidationReport` does not — it uses `add_error` / `add_warning` / `add_info`, plus
tracks run statistics (`stats['total_files']`, etc.) and a different `print_report()` format that
the original discovery output depends on.

Rather than rewrite discovery's report class (which would change its output), `validate_discovery.py`
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

Before promotion, both live validators (then `_v2`) were run against real repository content and
diffed against the pre-migration originals' output, more than once across this work:

- `validate_encounters.py` (post-migration) output is byte-identical to the pre-migration original,
  exit code 0.
- `validate_discovery.py` (post-migration) output is byte-identical to the pre-migration original,
  exit code 0 (after fixing the `E`/`W`/`I` alias gap above, which a first run caught as an
  `AttributeError`).
- `bible_sot.load_bible_versions`'s cache-miss `RuntimeError` path was exercised directly (network
  fetch mocked to fail, no cache present) and confirmed to raise cleanly instead of leaking an
  unhandled `FileNotFoundError`.
- Promotion initially archived the pre-migration originals in a `legacy/` folder rather than a git
  tag. That approach was short-lived: moving the files one directory level deeper immediately broke
  a hardcoded depth assumption (`SCRIPTS_DIR`/`script_dir` resolution), and encounters' archived
  copy needed its own frozen `verify_image_urls.py` to avoid an import-shadowing risk. Both were
  fixable, but a "frozen" archive that needs its own bugfix the moment it's created is the wrong
  shape — a git tag has neither problem, so `legacy/` was removed in favor of `pre-shared-validation`
  above.
- `tests/test_promoted_validators.py` shells out to both real master validators on every test run,
  so byte-identical correctness is now a maintained property, not just a one-time verification.

## Remaining known gaps

- Discovery's `ValidationReport` vs. shared `Report` interface gap (the alias bridge above) is
  unresolved — reconciling the two into one report class is future work, not required for
  `shared_validation` to be the live dependency it is today.
- Discovery's `RunReport` phase table is coarse (2 rows) vs. encounters' (5 rows), since discovery's
  `main()` doesn't have per-phase report objects the way encounters does.
