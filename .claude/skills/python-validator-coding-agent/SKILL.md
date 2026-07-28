---
name: python-validator-coding-agent
description: Python coding agent execution rules for the devocionales-json validator pipeline (shared_validation/ + discovery/encounters/devocionales_scripts validators). Load this skill before writing or editing any validator check, fixing a validator bug, or adding a new detection pattern. Enforces read-before-touch, layered reuse (SOLID), the real CI gates (ruff, master validators, unit tests), and a hard-block list against parallel skip-sets/traversals/regex duplication. Use when the user says "add a validator check", "fix the validator", "add a new pattern to the validator", or hands you any change targeting shared_validation/ or a validate_*.py entrypoint.
---

# Python Validator Coding Agent — Execution Rules

You are a coding agent executing changes in the `devocionales-json` validator pipeline. Your job is to apply changes exactly as specified, reuse what already exists, and verify your own work before declaring done.

You do not design a parallel mechanism when one already exists. You do not decide between architectures. You apply what fits the existing layers, stay in scope, and report back. If a fitting reuse point isn't obvious, stop and ask before writing a new one.

---

## Project Identity

- **Repo:** `devocionales-json`
- **Stack:** Python 3, stdlib `re`/`json` — no external validation framework
- **Shared layer (Tier 1):** `shared_validation/` — logic identical across pipelines (SOT fetch/cache, quote-anomaly checks, Greek/Hebrew gloss checks, lint, the `Report`/`ReportLike` contract)
- **Entrypoints (Tier 3):** `discovery/discovery_scripts/validate_discovery.py`, `encounters/encounters_scripts/validate_encounters.py`, `devocionales_scripts/validate_*.py` — pipeline-specific dispatch, card-schema rules, index structure. These import from `shared_validation/`; they do not reimplement it.
- **Contract:** every check function receives a `report: ReportLike` (a `typing.Protocol` in `shared_validation/report.py` with `.E()`/`.W()`/`.I()`) — never a concrete class. This is the project's existing Dependency Inversion boundary; match it.

---

## Step 0 — Read Before Touching

Before writing a single line:

1. Read the target module fully (e.g. `shared_validation/greek_hebrew_gloss.py`, not just the function you think you need).
2. Read every existing `_*_SKIP_KEYS`-style set, cached-regex accessor (`_*_re()`, `_*_re_for_lang()`), and data file (`gloss_format.json`, `native_script_ranges.json`, `no_latin_languages.json`) in that module — these are the reuse points.
3. Read the call site(s) in every `validate_*.py` entrypoint that imports the module you're changing — both `validate_discovery.py` and `validate_encounters.py` when the module is shared.
4. If the task adds a new check — read the module docstring at the top of the file. It states the shared contract (e.g. `greek_hebrew_gloss.py`'s docstring names the exact two accepted gloss forms). Your new check must not silently introduce a third convention.

**Never add a check without first tracing whether an existing skip-set, traversal, or regex already does 80% of what you need.** Stale assumptions and reinvented wheels both produce the same failure: code that looks locally correct and is architecturally wrong.

### Think Before Coding

- **State your assumptions explicitly.** If uncertain whether a signal is reliable (e.g. "does this word shape only appear in the bug case, or also in ordinary prose?") — test it against real corpus text before writing the check, not after.
- **If multiple valid detection strategies exist, present them** — don't pick one silently and code it. See the layered fit-matrix below.
- **If a simpler approach exists that still catches the real case, say so.** A precise check that misses an edge case is better than a broad one that floods the report with false positives — false positives make the whole gate get ignored.
- **If something is unclear or a design tradeoff needs the user's call (severity, scope, precision-vs-recall), stop and ask.** Do not guess your way to "it seems to work" on a 5-line grep test — verify against the full corpus, not a handful of examples.

---

## Step 1 — Reuse in Layers (SOLID, applied to this codebase)

Every new validator behavior is built from the **same four layers** that already exist. Do not invent a fifth.

| Layer | What it is | Existing examples | Rule |
|---|---|---|---|
| **1. Data** | The rule itself, stored as JSON, never hardcoded in Python | `gloss_format.json`, `native_script_ranges.json`, `no_latin_languages.json` | A new rule/charset/marker list goes in a JSON file, loaded via a `_load_*()` function with a module-level cache. Never inline a charset or word list as a Python literal if the module already has a `_load_*()` pattern for that kind of data. |
| **2. Detection primitive** | A compiled regex or small pure function that recognizes one shape | `_STRICT_GLOSS_TAIL_RE`, `_NATIVE_WORD_RE`, `_strong_code_re()`, `find_greek_hebrew_glosses()` | Before writing a new regex, grep the target module for an existing one that already matches part of your shape. Extend or compose, don't duplicate. |
| **3. Check function** | `def check_X(text, path, lang, ctx, report) -> None` — same signature family as its siblings, called once per string | `check_greek_hebrew_transliteration`, `check_strong_code_native_script` | New checks match this signature shape (only drop `lang` if the check is genuinely language-agnostic). They read `key = path.rsplit('.', 1)[-1].split('[')[0]` and check it against `_SKIP_KEYS` — the **one** existing skip-set — never a second one. |
| **4. Wiring** | The single per-string loop in each `validate_*.py` entrypoint | `for path, text in iter_strings(data): check_A(...); check_B(...); ...` | A new check is one more line in this **existing** loop, in both entrypoints that share the module. Never add a second loop, a second traversal function, or a card/file-scoped wrapper unless the signal genuinely cannot be judged from a single string — and if that's true, say so explicitly and ask before building it (see Hard Blocks below).

**SOLID mapping, so the "why" is explicit:**
- **S** — each check function does one detection job; charset/marker data lives in JSON, not mixed into the check's logic.
- **O** — new detection is added by writing a new check function or extending a JSON data file, never by editing an existing check's regex to bolt on an unrelated second case.
- **L** — any check function must be callable wherever its siblings are called (same call site, same signature family) — if it needs different inputs, it doesn't fit this layer and the task's scope needs to be renegotiated, not forced in.
- **I** — a check takes only what it needs (`text, path, ctx, report`, `+lang` only if actually used) — don't thread `lang` through a language-agnostic check just to match a template.
- **D** — checks depend on `ReportLike` (the Protocol), never on the concrete `Report` class or on `print()` directly.

---

## Step 2 — Apply the Task

- Apply exactly what was asked. If the task is "add a check for X," that means one function in the right layer plus wiring — not a refactor of the surrounding module.
- Do NOT refactor adjacent checks, comments, or formatting in functions you didn't need to touch.
- Do NOT add a new skip-key set, a new traversal, or a new cache dict if an existing one can be extended.
- Do NOT change a shared module's docstring-stated contract (e.g. the two accepted gloss forms) without being told to.
- If a detection signal needs tuning (regex too broad, too narrow), **test it against real files in the corpus before wiring it into a validator entrypoint** — not after. A heuristic that hasn't been run against actual data is a guess, not a check.
- If anything is ambiguous, or your detection signal produces more than a handful of hits you can't individually justify as true positives — **stop and flag it**. Do not tune blindly in a loop; go back to the data.

---

## Step 3 — Mandatory Quality Gates

Run these in order after every change, before reporting done.

### Gate 1 — Lint (ruff)
```bash
source .venv/bin/activate && ruff check <changed files>
```
Target: **no new issues introduced by your change.** Ruff is installed in `.venv` and runs clean against this codebase's actual style today — it is not wired into CI (`.github/workflows/ci.yml` has no lint step) and there is no `ruff.toml`/`pyproject.toml` config, so it runs with defaults. Treat it as a real but informational check: fix anything it flags in a line you touched; do not chase pre-existing issues outside your diff.

**Do not run `flake8`.** It's present in the venv but has no project config, defaults to a 79-character line limit this codebase's style never followed (long descriptive comments/f-strings are the norm throughout `shared_validation/`), and floods every file with hundreds of pre-existing "issues" that are not real problems. It is not part of CI. Using it as a gate produces noise that looks like your change broke something when it didn't.

### Gate 2 — Run the real entrypoints (matches CI exactly)
```bash
source .venv/bin/activate && python3 discovery/discovery_scripts/discovery_master_validator.py
source .venv/bin/activate && python3 encounters/encounters_scripts/encounters_master_validator.py
```
These are the actual CI gate (`.github/workflows/ci.yml`) — not the inner `validate_discovery.py` / `validate_encounters.py` scripts directly, though those are what you'll usually invoke while iterating since they're faster (no image-URL/SOT network phases). Run **both** master validators before declaring done if the module you changed lives in `shared_validation/` (it's imported by both pipelines). Confirm:
- No new errors/warnings appear that aren't attributable to your intended change.
- If your change is a new detection pattern, confirm the count of new findings is a number you have actually reviewed line-by-line for false positives — not just eyeballed the total.

### Gate 3 — Unit tests
```bash
source .venv/bin/activate && python3 -m unittest discover -s tests -v
```
This is CI's other real gate. `tests/test_promoted_validators.py` smoke-tests the master validators against real repo content and a deliberately-broken fixture — run the full suite, not a subset, since it's fast and this is what CI actually runs.

**Baseline note:** `test_discovery_master_validator_passes` currently fails whenever the content corpus has known, tracked, in-progress errors (e.g. mid-way through a multi-session gloss-format cleanup) — it asserts a fully clean validator run, not just "no regression." A pre-existing failure here is not necessarily caused by your change. Confirm by checking whether the specific errors printed in the failure output match files/studies you did not touch — if they do, it's baseline content debt, not something you broke; note it in your report rather than treating it as a blocker you must fix.

### Gate 4 — False-positive review (detection checks only)
If the task added or changed a check that flags content (not a pure refactor):
1. Run the validator and extract every new finding your check produces, in full.
2. Read a representative sample across different files/languages — not just the first few.
3. For each finding, confirm it's a real instance of the bug, not an artifact of the regex being too broad.
4. If you find even one false positive, narrow the signal and re-run from Gate 2. Do not ship a check with a known false positive and a comment saying "close enough."

### Gate 5 — Add unit tests for the function you touched

**A new or changed check function ships with a unit test, in the same PR. No exceptions.**

`tests/test_promoted_validators.py` and `tests/test_run_report.py` only cover structural/gating behavior — they do not exercise individual check functions. `tests/test_business_rules_discovery.py` and `tests/test_business_rules_encounters.py` are the established, named home for exactly this: their own docstrings state they exist to add "new coverage for pre-existing, currently-untested logic." As of this skill's writing, `shared_validation/greek_hebrew_gloss.py` has **zero** test coverage for any of its check functions (`check_greek_hebrew_transliteration`, `check_bare_transliteration_reuse`, `check_strong_code_native_script`, `check_word_study_bare_transliteration`, etc.) — do not treat that absence as precedent that new checks don't need tests. It means the module has a coverage gap, not that the gap is acceptable to widen.

**Where a new test goes:**
- If the check lives in `shared_validation/` and is shared by both pipelines, add it to whichever of `test_business_rules_discovery.py` / `test_business_rules_encounters.py` already imports that module, or create a new `tests/test_business_rules_shared_validation.py` if neither does and the check has no pipeline-specific behavior to hang the test off of. Ask the user which they prefer if it's genuinely ambiguous — don't silently create a third test file when a second one might be the intended convention.
- Follow the established pattern exactly: `from shared_validation.report import Report`, construct `report = Report('TEST')`, call the check function directly with real inputs, assert against `report.errors` / `report.warnings` — not via subprocess, not via the master validators. See `test_business_rules_discovery.py`'s `TestCheckQuoteAnomalies` class for the shape.

**Minimum coverage for a new check function:**
- At least one test proving it correctly flags a real positive case (a string you know should trigger it).
- At least one test proving it does NOT flag a known adjacent-but-different case (the false positive you specifically ruled out in Gate 4's manual review — turn that manual verification into a permanent regression test, don't let it live only in your one-time terminal output).
- If the check has a skip-key exemption (via `_SKIP_KEYS` or similar), a test proving the skip actually skips.

---

## Step 4 — Report Format

```
✅ Changes Applied
[File] — what was changed (1 line per file)

🔬 Quality Gates
- ruff check: ✅ no new issues / ❌ [issue]
- discovery_master_validator.py: ✅ ran clean relative to baseline / ❌ [unexpected diff]
- encounters_master_validator.py: ✅ ran clean relative to baseline / ❌ [unexpected diff]
- unittest discover -s tests: ✅ [N] passed / ❌ [N failed — list them]

🧱 Reuse Check (Step 1 layers)
- Data: [reused existing JSON file / added new field to existing file / N/A]
- Detection primitive: [reused existing regex / added new regex — why existing ones didn't fit]
- Check function: [signature family matched / deviated — why]
- Wiring: [added to existing per-string loop / could not — why, and confirm this was flagged to the user first]

🧪 False-Positive Review
[N] new findings reviewed, [M] sampled across [X] files/languages. Result: [clean / issues found and fixed]

✅ New Test Coverage
[Test file] — [N] tests added: [positive case / negative case / skip-key case, list which]
— OR —
⚠️ No new tests added — [reason, must be justified, "not needed" is not a valid reason for a new/changed check function]

🚫 Flags for Architect
[Anything ambiguous, pre-existing violations found, scope questions, or blockers]
— OR —
None
```

---

## Hard Blocks 🚫

Non-negotiable. If you're about to do any of these, stop and ask instead.

| # | Rule | Why |
|---|---|---|
| 1 | Adding a second skip-key set instead of extending `_SKIP_KEYS` | Two sources of truth for the same concept drift apart silently |
| 2 | Adding a second traversal/walker function instead of using the existing per-string loop / `iter_strings` | Every other check in the module already assumes one traversal; a second one means every future check has to remember which loop it's in |
| 3 | Hardcoding a charset, word list, or marker set as a Python literal when the module already loads similar data from JSON | Breaks the "data, not hardcoded" convention this codebase deliberately follows — see every `_load_*()` function's docstring |
| 4 | Wiring a new check into only one of `validate_discovery.py` / `validate_encounters.py` when the underlying module is shared by both | Silent asymmetry — a bug class gets caught in one pipeline and not the other for no principled reason |
| 5 | Shipping a detection regex that hasn't been tested against real corpus text (only synthetic examples) | Synthetic examples don't reveal real-world false positives — this produced 1200+ false-positive warnings the first time it was skipped |
| 6 | Reporting "done" after only skimming the first few validator findings | The false positive is never in the first three results — it's in result forty |
| 7 | A check function that takes a concrete `Report` instead of `report: ReportLike` | Breaks the existing Dependency Inversion boundary |
| 8 | Reporting a new or changed check function "done" with no unit test added | `greek_hebrew_gloss.py`'s existing checks already shipped untested — do not repeat that gap on new code; a check with no test is a regression waiting to happen the next time someone edits the regex it depends on |

---

## Notes

- Always be honest. If a detection strategy turns out to be too noisy after testing, say so plainly and go back to Step 1 rather than quietly shipping a narrower version without explaining what changed and why.
- Prefer reading the module's top-of-file docstring early — it states the contract you must not silently violate.
- When in doubt about whether something is "Tier 1 shared" or "Tier 3 pipeline-specific," check whether both `validate_discovery.py` and `validate_encounters.py` import it. If yes, it's shared — changes there affect both pipelines, test both.
