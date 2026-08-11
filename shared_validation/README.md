# shared_validation

Library shared by the `discovery` and `encounters` validator pipelines. No CLI, no
`__main__` on the package itself — imported by `validate_discovery.py` and
`validate_encounters.py`, and run via their master validators
(`discovery_master_validator.py`, `encounters_master_validator.py`).

Contract: every check function takes `report: ReportLike` (`report.py`'s Protocol —
`.E()`/`.W()`/`.I()`), never the concrete `Report` class.

## Wired into both validators (the gate)

| Module | What it checks |
|---|---|
| `bible_sot.py` | Loads Bible version/language config from the remote SOT, with a temp-dir offline cache fallback. |
| `lint.py` | JSON indent=2 / tab / trailing-newline formatting. |
| `text_checks.py` | Quote-anomaly detection, Latin-leak (untranslated text) detection, string traversal (`iter_strings`). |
| `greek_hebrew_gloss.py` | Structural well-formedness of inline Greek/Hebrew glosses and Strong's-code citations — comma placement, script boundaries, bare-transliteration-without-native-script detection. |
| `lexicon_check.py` | Lexical accuracy of a well-formed gloss against Strong's Concordance (real headword? correct transliteration?). |
| `lexicon_family_check.py` | Cross-language Strong's-citation balance checks, orchestrates `lexicon_check` + `greek_hebrew_gloss` per family. |
| `lexicon_source.py` | `StrongsLexiconSource` — loads and queries the Strong's lexicon data (the SOT lexicon lookups above depend on this). |
| `family_check.py` | Cross-language structural checks within a content family: filename/language match, key parity, field drift. |
| `scripture_check.py` | Scripture reference resolution and quote-accuracy validation against Bible text (SOT-gated, see `scripture_validation_enabled()`). |
| `report.py` | `Report` class + `ReportLike` Protocol — the shared error/warning/info contract. |
| `run_report.py` | `RunReport` — phase-scoped run summary used by both master validators. |

**Strong's coverage today:** format/citation correctness (`greek_hebrew_gloss.py`) and
lexical accuracy against Strong's (`lexicon_check.py` / `lexicon_family_check.py`) are
both already wired into every validator run — no gap here.

## Standalone tools (not part of the gate, run manually)

These have their own `__main__` / CLI and are explicitly **not** imported by either
`validate_*.py` entrypoint:

| Module | Purpose |
|---|---|
| `content_length_report.py` | Opt-in diagnostic comparing prose length across sibling-language files. Not a pass/fail check — see its own docstring for why. |
| `check_gitignore_pycache.py` | Repo-hygiene check: no `__pycache__` tracked or untracked. |
| `paren_balance.py` | Report-only parenthesis balance scan over a JSON file's text fields. |

The Strong's-citation repair toolchain (scanner/search/fixer/balance-fixer/applier/
pipeline CLI, plus the gloss-rewrite fixer) was removed 2026-08-11: it required a
human to run it and decide, had zero callers from either live validator, and its
one automated concern — citation *format* normalization — isn't something the gate
enforces in the first place (`gloss_format.json`'s `strong_code_prefixes` rule
already accepts multiple citation shapes). Strong's correctness itself is still
fully covered by the gate — see the table above.

## Tests

- `tests/test_business_rules_shared_validation.py` — unit tests for shared check
  functions not otherwise covered by a pipeline's own `test_business_rules_*.py`.
- `tests/test_family_check.py`, `test_lexicon_source.py`, `test_paren_balance.py`,
  `test_scripture_check.py`, `test_run_report.py`, `test_business_rules_report.py`
  — per-module coverage.
- `tests/test_promoted_validators.py` — smoke-shells both real master validators
  against real repo content on every run; the durable end-to-end gate.

## Known interface gap

Discovery's own `ValidationReport` (used inside `validate_discovery.py`) predates
`ReportLike` and uses `add_error`/`add_warning`/`add_info` instead of `E`/`W`/`I`.
It satisfies the Protocol via three one-line aliases rather than being rewritten, so
discovery's existing output format doesn't change. Reconciling the two report classes
into one is future work, not required for `shared_validation` to be the live
dependency it is today.
