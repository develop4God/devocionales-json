# SKILL: Translation Core (shared by Encounters & Discovery)

Shared rules for both content types. Content-specific skills load this file first, then
add only their own field lists/structure. Fix a rule here once — both pipelines get it.

---

## 1. Resolve Bible version + verse text

SOT for all version codes/names/reading-speed is the remote index — never hardcode or
keep a local copy of it:
`https://raw.githubusercontent.com/develop4God/bible_versions/refs/heads/main/index.json`

- [ ] `lang_entry = index["languages"][lang_code]` → use `primary_version`;
      `fallback_version` if primary lookup fails. Version field = that short code
      only, never `versions[code]["name"]` (display string, e.g. `"Reina-Valera 1960"`).
- [ ] Download `.gz` to `bible_database/` if missing — never decompress manually,
      `VerseResolver` takes the `.gz` path directly.
- [ ] Resolve every verse via `devocionales_scripts/verse_resolver.py`
      (`VerseResolver(path).resolve("John 3:16")`) — never hand-type/copy-paste verse
      text or references.
- [ ] Book names: always pass **English** book names into `resolve()` (e.g. `"John"`,
      not a native name) — `VerseResolver` looks that up in `bible_books.json` (English
      name → `book_number`) for you, then reads the native name back from the target
      language's own SQLite `books` table. Never hand-supply or hand-translate a native
      book name yourself.
- [ ] Before delivery: `assert data["bible_version"] in (primary_code, fallback_code)` —
      run it, don't eyeball it. Sibling files have shipped with the wrong value before.

---

## 2. Greek/Hebrew inline glosses

- [ ] Parenthetical after a Greek/Hebrew word (e.g. `μονογενής (monogenēs)`) is always
      **Latin-alphabet transliteration** — in every target language, including AR/ZH/HI/JA.
      Never respell it phonetically into the target script. Already checked mechanically
      by `shared_validation/text_checks.py::check_greek_hebrew_transliteration`, wired
      into both master validators — no separate action needed here beyond writing it
      correctly.

---

## 3. Per-language notes — load only the target language's file(s)

**ES/PT/FR/EN/DE:** no additional gate beyond this core file. Cognates (`Courage`,
`Grâce`) are valid translations, not errors.

**Every other target language:** before translating, load
`skills/language_notes/{lang}.json` (mechanically-checkable rules — forbidden
patterns, run by a validator script) and `skills/language_notes/{lang}.md` (judgment
rules the LLM must apply while writing) for the language you were invoked with — nothing
else. Do not read notes for languages you are not translating into; they don't apply and
only add irrelevant context.

---

## 4. Reading time

`estimated_reading_minutes` is editorial, not computed. Baseline = EN (or ES per the
content skill's source table) value, then apply that skill's per-language delta table.
Store in both the JSON file and `index.json`.

---

## 5. Critic review pipeline

Owned entirely by `translation_orchestrator_agent` / `~/.claude/skills/translate-batch/SKILL.md`
(Phases 3-4: two independent critic rounds, verify-before-apply, pattern sweep,
post-fix reverse validation). `translator_agent` does not run this — it translates,
runs its content-specific validator + `post_translate_checks.py`, and delivers; critic
review happens after, in a separate subagent the orchestrator spawns. If you are
`translator_agent` reading this, your job is done once delivery's mechanical checks
pass — do not attempt any part of this section yourself.

---

## 6. Known recurring mistakes — check explicitly, don't rely on critic sampling

- [ ] `meta.tags`/`tags` diacritics: check target-language spelling word-by-word against
      a sibling published file (shipped wrong before: `ressurreicao`→should be
      `ressurreição`, `esperance`→should be `espérance`). Tags aren't prose; a
      prose-sampling critic won't catch this.
- [ ] Third-party/external critic reports (pasted from elsewhere) get the same
      verify-before-apply treatment as your own spawned critics — several have been
      mostly false positives.
