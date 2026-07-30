# Session handoff — shared_validation Strong-code pipeline fixes

Branch: `apply-bare-latin-replacements`
Repo: `develop4God/devocionales-json`
Sparse-cloned path used this session: `shared_validation/`

## What's in this folder

- `strong_scanner.py`, `strong_fixer.py`, `strong_search.py`,
  `strong_balance_fixer.py`, `strong_pipeline.py`, `run_strong_search.py`
  — the 6 fixed files, ready to copy back over the repo's
  `shared_validation/` folder.
- `gap_check.py` — verification script used throughout. Not part of the
  repo. Diffs every fix action (Strong + balance) against the immutable
  scanner baseline across the whole corpus. Run from repo root with
  `shared_validation/` on the path. Currently reports 0 gaps across 542
  files.

## Bugs fixed this session, in order found

1. **`strong_fixer.preview_file` offset/text mismatch** — `FixAction.old`
   was built from `r.full_match.strip()` but `start`/`end` still pointed
   at the *unstripped* span, so the applier's `text[start:end] == old`
   check failed silently. Corpus-wide impact measured: **157 of 271**
   previewed Strong fixes were silently failing before this fix.

2. **`strong_pipeline.run_pipeline` dead SCAN stage + type-hedge** —
   called `scan_file()` and never used the result; also had a
   `hasattr(strong_result, 'applied')` hedge against a return type it
   fully controlled. Both removed.

3. **`strong_scanner.scan_file` silently dropped fields with escapes** —
   compared raw (still-escaped) file bytes against already-decoded
   field values, so any field containing `\n`, `\"`, etc. (i.e. every
   `content`/`narrative` field with line breaks) was never found, with
   zero error or warning. Fixed using `json.decoder.scanstring` to
   decode the raw literal before comparing. Verified: **52,267 of
   52,267** string fields now found across the full corpus (was
   silently missing an unmeasured but large fraction before).

4. **`strong_search._BROAD_RE` regex over-consumed trailing punctuation**
   — the trailing class `[\s\)\]:.\-]*` was unbounded, so when a Strong
   code sat right after another parenthetical (e.g.
   `(arrabon) - G728): pago`), the match ate past its own closing paren
   and swallowed a sentence colon, silently corrupting content on
   apply. Fixed by bounding the trailing class to `\s*[\)\]]?` — at most
   one closing wrapper. Verified: same 271/1187 fix/skip classification
   corpus-wide (no regression), colon no longer deleted in the repro
   case.

5. **`strong_applier`'s `failed` count was silently discarded** by both
   `strong_fixer.apply_fixes` and `strong_balance_fixer.apply_balance_fixes`
   (both returned bare `int` instead of the full `FixResult`). Fixed:
   both now return `FixResult`; updated the orchestrator
   (`strong_pipeline.py`) and all 6 CLI call sites in
   `run_strong_search.py` to read and print `.failed`.

6. **Sequential offset invalidation between strong-fix and balance-fix
   stages** — found immediately after fixing #5, because surfacing
   `failed` made it visible. Balance-fix offsets were computed once,
   before strong fixes were applied to the same file/field; strong
   fixes shift character offsets downstream of each edit, so the
   balance fixer's stale offsets pointed at the wrong text after strong
   fixes wrote. Corpus-wide impact measured: **63 silent failures
   across 27 files**. Fixed by re-running `preview_balance_fixes`
   against the file's current on-disk state after strong fixes are
   applied, instead of reusing the pre-fix preview.

## Full corpus verification (542 files, disposable copies, production mode)

```
Strong fixes applied:  271, failed: 0
Balance fixes applied: 224, failed: 0
Files valid after fix: 542 / 542
```

Gap-check (immutable-scan-vs-every-fix-action): **0 gaps, 552 actions
checked, 542 files.**

## NOT fixed — known, confirmed, deliberately out of scope so far

- **`strong_applier.apply_fixes`'s `json.dump` reformatting** drops
  whitespace-only lines and the file's trailing newline on every write.
  Confirmed via diff twice this session. Unrelated to bugs 1–6.
  Cosmetic/formatting, not data-loss, but worth a decision on whether
  it matters (git diffs will show noisy whitespace-only line removals
  on every applied fix).
- Dead import in `strong_fixer.py`: `from shared_validation.strong_scanner
  import scan_file, get_field_text` — neither is used in the file.
  Noticed, not removed (out of scope when found).

## How to resume

1. Sparse-clone `develop4God/devocionales-json` on
   `apply-bare-latin-replacements`, path `shared_validation` (see
   `sparse-clone` + `sparse-clone-devocionales-json` skills).
2. Copy these 6 files over the freshly-cloned `shared_validation/`.
3. Copy `gap_check.py` to repo root, run it to re-confirm 0 gaps before
   doing anything else — this is the safety net for the whole session's
   work.
4. Decide on the `json.dump` formatting issue, or move on.
