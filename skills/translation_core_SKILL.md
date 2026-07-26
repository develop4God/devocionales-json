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
      Never respell it phonetically into the target script. Per-target verification is a
      mechanical check — see `language_notes/{lang}.json`'s `required_ascii_transliteration`.

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

## 5. Critic review pipeline (run per language file, in this order)

1. [ ] File passes its content-specific validator.
2. [ ] Get a fresh, independent critic read with this exact prompt, `{language}`
       substituted, nothing else changed — **how** depends on who is running this step:
       - **Orchestrating conversation** (has the Agent tool): spawn `critic_reviewer_agent`
         as a real subagent — no shared context with the translator, not Haiku.
       - **`translator_agent` itself** (no Agent/Task tool in this environment — do not
         attempt to invoke one): run the same prompt via `claude -p "..."` through your
         Bash tool instead. Treat its output exactly as a spawned critic's report. This
         internal pass does NOT replace the orchestrating conversation's own later
         `critic_reviewer_agent` spawn (Phase 2 of the orchestration flow) — both are
         required, they catch different things because they run at different points
         with different context.
       > you are a native {language} speaker, read this file and tell me if you find:
       > Typos / Grammar Errors, Awkward / Non-native-sounding phrasing take your time
       > line by line, your comments in English. After complete the validation any error
       > you find, search broader in the file to see if you have a repeat pattern to
       > document and inform your findings.
3. [ ] Verify every claim before applying anything (critics hallucinate confidently):
   - String/typo claim → grep the exact quoted string; no match = discard, don't downgrade.
   - Count claim → verify with a script over string *values* only (not raw file — JSON
     indentation whitespace inflates naive counts).
   - Grammar-rule claim → confirm against a real reference, especially if it would *add*
     something (comma/word/article).
4. [ ] Apply only survived findings. Note why rejected ones were rejected (false /
       stylistic / rule-cited-wrong) so it isn't re-litigated later.
5. [ ] Pattern sweep — for every confirmed finding that's a *category* (calque,
       agent/patient inversion, mixed metaphor, category-mismatch verb), not a one-off:
   - Grep the same shape elsewhere in this file.
   - Check whether the same source sentence was mistranslated the same way in other
     already-delivered language files for this content — fix there too.
   - If it recurs across more than one encounter/study, add it as a named trap to the
     relevant content skill.
6. [ ] After applying fixes, before reporting done:
   - Re-read the full changed file, not just diffed lines.
   - For every edit, check it still says the same thing — anchor against the card's
     Bible reference and `revelation_key`/`identity_statement`. Grammatically fixed but
     now vague/tautological/disconnected = regression, not done.
   - Re-scan whole file for the same error pattern the critic flagged.
   - Re-run the validator.
   - Repeat 5-6 until a full pass finds nothing new.
7. [ ] Don't skip step 2 because an internal/self-critic already ran — they catch
       different things. "No findings" ≠ "file is clean," critics sample.

---

## 6. Known recurring mistakes — check explicitly, don't rely on critic sampling

- [ ] `meta.tags`/`tags` diacritics: check target-language spelling word-by-word against
      a sibling published file (shipped wrong before: `ressurreicao`→should be
      `ressurreição`, `esperance`→should be `espérance`). Tags aren't prose; a
      prose-sampling critic won't catch this.
- [ ] Third-party/external critic reports (pasted from elsewhere) get the same
      verify-before-apply treatment as your own spawned critics — several have been
      mostly false positives.
