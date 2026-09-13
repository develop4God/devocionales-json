---
name: translate-batch
description: Orchestrate a batch translation of an Encounters or Discovery JSON file into one or more target languages, in the devocionales-json project. Use when the user asks to translate an encounter/discovery file into new languages, says "translate the pending languages", "spawn translators for X", or references this project's standard translation batch process. Covers the full flow — two source-language phases, each with its own translate + two independent critic rounds + user confirmation before the next phase starts, verify-before-apply, fix with drift-check, re-validate, update index.json, propose new traps for confirmation, commit.
---

# Translation Batch Orchestration

You are the orchestrator, not the translator. Delegate all translation and critic work
to subagents; your job is sequencing, verification, gatekeeping, and — only with
explicit user confirmation — updating the shared skill/language-note files so future
runs inherit what this run learned.

**Each phase is self-contained: translate its files, run both critic rounds on THOSE
files, fix, get user confirmation that the phase is done — before starting the next
phase.** Phase 2 translates from Phase 1's EN output, so an uncaught error in EN would
propagate into six more files if Phase 2 started before Phase 1's critic rounds and
your confirmation were complete. Never batch both phases' files into one shared critic
pass.

## Phase 0 — Preflight

1. Confirm the source file is the approved, reviewed source of truth (check project
   memory for a review-status note on this specific encounter/discovery file; if
   none exists or it says review is still pending, stop and ask before translating).
2. Confirm `git status` is clean on the source file and on `index.json`.
3. Check `index.json`'s `files` map for this content id to see which languages are
   already done vs. pending.

## Phase 1 — ES → PT, FR, EN (translate, then 2 critic rounds, then confirm)

4. Spawn one `translator_agent` per language — PT, FR, EN — **in parallel**, each
   given: the content type (Encounters or Discovery — state this explicitly, don't
   rely on the translator inferring it from the file path, since its own profile says
   it will stop and ask if content type isn't plainly given), the source file path
   (ES), target language, and output file path. Do not restate its own skill/process
   to it; it loads that itself.
5. PT is **Brazilian** Portuguese (bare `pt` code, not `pt-BR`) — the translator loads
   this from `skills/language_notes/pt.md` itself; don't restate it in the delegation.
5b. Read each `translator_agent`'s report for a flagged assumption (e.g. "a language
    missing from a reading-time table," "register convention inferred from a sibling
    file") — don't let these pass silently. Fold each one into what you present to the
    user at this phase's confirmation step (11/13); an assumption the translator had
    to guess at is exactly the kind of thing a human should sign off on, not something
    that gets buried in a delivery report nobody re-reads.
6. **Critic Round 1** — for each of these 3 delivered files, spawn a separate, fresh
   `critic_reviewer_agent` (no shared context, single naive-reader prompt, in
   parallel). Don't restate its own instructions to it.
7. Triage every finding before touching a file: verify each claim against the actual
   file (grep the exact quoted string), reject claims that are not literally present,
   are intentional stylistic choices, or would reintroduce a problem already fixed
   elsewhere. Present surviving verified findings with your fix recommendation and
   wait for explicit go-ahead before editing — never apply-then-show.
8. For each approved fix, in this exact order: make the single edit, grep the file
   for the same pattern elsewhere and fix every occurrence, reread the full changed
   sentence in context to confirm no meaning drift, only then move to the next fix.
9. If a verified finding traces back to the **source file itself**, fix the source
   first, then check the other 2 files in this phase for the same inherited defect.
10. **Validate this phase's files now — do not defer to the end of the batch:**
    - Confirm valid JSON for all 3 files
      (`python3 -c "import json; json.load(open(path))"`).
    - Run the real corpus validator (`validate_encounters.py` for encounters,
      `discovery_master_validator.py` for discovery). **These validators always scan
      the whole corpus — neither takes a file-path argument to scope to just this
      batch.** `validate_encounters.py` at least implements real flag parsing
      (`--lang`, `--scripture-only`); **`discovery_master_validator.py` has no flag
      parsing at all — it silently ignores `--help`, typos, and any other argument, and
      always runs the identical full-corpus scan regardless of what you pass it.**
      Don't try to scope either validator via flags for this step; run it as-is, then
      read its output and check specifically for any error/warning that names one of
      this phase's 3 files. A hit on one of these 3 files is a real defect to fix
      now; a hit naming any other file (outside this batch) is not this phase's
      problem — don't let it block you, but also don't silently ignore it if it looks
      like a pre-existing corpus issue worth flagging to the user.
    - Run `validate_family.py {content_id}` (encounters or discovery, matching this
      batch's content type) — this one takes a single content id, not a file path,
      and cross-checks all of this item's language files against each other. As of
      Phase 1, ES/PT/FR/EN all exist by now, so this should have ≥2 files and run its
      real checks — a "fewer than 2 files" exit 1 at this point in Phase 1 is a
      genuine problem, not the expected mid-batch state.
    - Run `python3 skills/post_translate_checks.py <file>` on each of the 3 files
      individually — this one DOES take a single file path — zero violations.
    - If anything fails here, fix it and re-run before moving to step 11 — Round 2
      must start from files that already pass every check, not just "critic-clean."
11. **Confirm with the user that Phase 1's fixes look right** before Round 2 — surface
    what was found/fixed/rejected and wait for their go-ahead.
12. **Critic Round 2** — spawn a **new**, independent `critic_reviewer_agent` per file
    (not a repeat of Round 1's findings — a fresh read of the now-fixed file, since a
    Round 1 fix can itself introduce a new issue). Repeat steps 7-9 for Round 2's
    findings. Do not skip Round 2 because Round 1 found nothing.
    - **If Round 2 flags something that would undo a Round 1 fix** (oscillating
      finding), do not silently pick one — stop, present both findings and the
      conflict to the user, and let them decide which one is the real error. Two
      rounds are meant to converge, not fight each other in the file.
    - **If the user rejects a proposed fix**, drop it — don't re-propose the same
      fix from a later round's finding without new evidence. Note the rejection in
      what you report so it isn't silently re-litigated.
12b. **Re-validate again after Round 2's fixes** — same three checks as step 10 (JSON,
    corpus validator, `post_translate_checks.py`), zero errors/violations, on all 3
    files. A Round 2 fix is not "done" until it re-passes every check, not just until
    the critic finding is addressed.
13. **Confirm with the user that Phase 1 is fully done** (both rounds applied, both
    re-validated) before proceeding to Phase 2 — do not start Phase 2 on your own
    judgment that Phase 1 "looks fine," and do not start Phase 2 on a file that passed
    critic review but hasn't been re-validated since its last edit.

## Phase 2 — EN → the rest (same translate → 2 critic rounds → confirm shape)

14. Only after Phase 1's EN file has passed both critic rounds, both validation passes,
    and you've confirmed Phase 1 is done: re-check `index.json`'s `files` map now (not
    just what you recorded back in Phase 0 step 3) to get Phase 2's actual pending
    language list, then spawn one `translator_agent` per remaining target language —
    JA, ZH, DE, AR, HI, FIL, whichever are still pending — in parallel, each given the
    EN file as source. This re-check is intentional: `index.json` isn't updated with
    Phase 1's new languages until Phase 4, so Phase 0's original pending list is still
    accurate for what Phase 2 needs — but re-checking here rather than trusting
    Phase 0's now-stale snapshot is the safer habit if this skill is ever re-entered
    mid-run (e.g. resumed after an interruption).
15. Run the identical process from Phase 1 (steps 6-13) on Phase 2's files only —
    Round 1, triage/fix, **validate (JSON + corpus validator + post_translate_checks.py)**,
    confirm, Round 2, triage/fix, **validate again**, confirm. Do not mix Phase 1's
    already-approved files back into this round; they're done. Do not defer any of
    this phase's validation to the end-of-batch check in Phase 3 either.

## Phase 3 — Final full-corpus confirmation

16. This is a final cross-check, not the first time validation runs — every file from
    both phases should already be individually validator-clean from steps 10/12b/15.
    Run the corpus validator and `post_translate_checks.py` once more across the
    **whole corpus** (not just this batch's files) to confirm nothing outside this
    batch regressed and nothing was missed.
17. Pass criterion: **zero errors, always** — every language that exists must validate
    clean, no exceptions. The only acceptable warnings are ones explicitly about a
    language that is genuinely still pending/not yet translated (missing-file /
    `coming_soon` warnings for languages outside this batch's scope) — never a warning
    about a file this batch delivered. If this final run finds anything new, treat it
    as a gap in per-phase validation, fix it, and re-run.

## Phase 4 — index.json and commit

18. Add each new language to `index.json`: `files`, `titles`, `subtitles`,
    `scripture_reference`, `estimated_reading_minutes`. Pull these from what each
    translator agent reported, or read the delivered file's own title-bearing card
    directly if not reported.
19. Re-run the validator once more after the index update.
20. Ask how the user wants to commit (per-language as each is approved, or bundled
    at the end) — this has varied by request, don't assume. **For both content
    types: if committing/pushing per-language rather than bundled, do not add a
    content item's very first language file to `index.json`'s `files` map alone if
    `validate_family.py` would then see fewer than 2 files for it** (this applies to
    `encounters/encounters_scripts/validate_family.py` and
    `discovery/discovery_scripts/validate_family.py` identically) — that state is a
    real, hard failure (exit 1, not skippable) in both CI and any later run, by
    design: a content item caught mid-translation on a shared branch means something
    needs a human's attention, not a quiet pass. Either hold that language's
    `index.json` entry until a second language is ready to land alongside it, or
    confirm explicitly with the user that a red CI run on `main`/a shared branch for
    that window is expected and accepted — don't let it happen silently as a side
    effect of "commit as each language is approved."

## Phase 5 — Propose new traps, write back only on confirmation

21. If either phase's critic rounds surfaced a **durable, recurring** issue (not a
    one-off typo) — a grammar rule, a register convention, a mechanically-checkable
    forbidden pattern — propose it explicitly to the user: state the rule, which file
    it would go in (`skills/language_notes/{lang}.md` for judgment rules, `{lang}.json`
    `forbidden_patterns` for mechanically-checkable ones, or
    `.claude/skills/translation-core/SKILL.md` if it applies to every language), and wait for
    explicit confirmation.
22. **Never write to a skill or language-note file without that confirmation** — an
    unverified or one-off critic finding must not silently become a permanent rule
    that every future translation run inherits.
23. On confirmation, make the edit yourself (you have Read/Write/Edit) — don't
    delegate a skill-file edit to a translator or critic subagent, since neither is
    scoped to touch project skill files.

## Things that went wrong before, don't repeat

- Don't defer the corpus validator / `post_translate_checks.py` to a single end-of-batch
  run — run them after **each** critic round, on that phase's files, before moving on.
  A file that only passed critic review but was never re-validated after edits can carry
  a real structural/mechanical defect into the next phase (Phase 2 translates from
  Phase 1's EN file) or into a user confirmation that assumed it was already clean.
- Don't run one shared critic pass across both phases' files — each phase's files get
  their own two rounds, completed and confirmed, before the next phase starts.
  Phase 2 translates from Phase 1's EN output, so an uncaught Phase 1 error would
  otherwise propagate into every Phase 2 language.
- Don't skip a critic round because the other round already ran — they are
  independent passes that catch different things each time.
- Don't treat "no findings this pass" as proof the file is now error-free — critics
  sample, they don't exhaustively enumerate. Diminishing returns, not zero returns.
- When your own edit fixes one problem, re-scan the edited sentence as a whole for
  new grammar issues your edit may have introduced — don't just check the edit was
  internally consistent with itself.
- Third-party/external critic reports (e.g. pasted from another tool) get the same
  verification treatment as your own spawned critics — verify every quoted claim
  against the file before acting, several such passes have contained mostly false
  positives.
