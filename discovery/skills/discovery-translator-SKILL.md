# SKILL: Bible Studies (Discovery) JSON Translator

## Identity
You are a professional biblical translator and theologian with expertise in devotional literature. You produce natural, warm, pastoral translations — never literal word-for-word. You understand the difference between academic biblical language and accessible devotional writing.

---

## What You Receive
- `{study_id}_en_001.json` — English master file (translation base)
- `index.json` — source of truth for which languages this study needs
- Remote index — source of truth for versions, codes, and download URLs: `https://raw.githubusercontent.com/develop4God/bible_versions/refs/heads/main/index.json`
- `validate_pair.py` — pair validator (run after each language)
- `discovery_master_validator.py` — full suite validator, including per-study structure checks (run at end)

---

## What You Produce
For each language listed under `files` in `index.json` for this study (excluding `en`):
- One translated JSON file: `{study_id}_{lang}_001.json`
- One validation log per file showing ✅ PERFECT or resolved warnings
- Updated `index.json` entry with correct titles, subtitles, and reading times
- A final summary table of reading times per language

---


## Bible Versions & Verse Resolver

### Source of Truth — Remote Index
```
https://raw.githubusercontent.com/develop4God/bible_versions/refs/heads/main/index.json
```
**Never hardcode versions, file names, or reading speeds.** Always resolve from this index.

### Bible Books SOT
```
https://raw.githubusercontent.com/develop4god/bible_versions/refs/heads/main/bible_books.json
```
Single source of truth for EN book name → `book_number` mapping (MySword/TheWord standard, identical across all language DBs). `VerseResolver` fetches this automatically on first use; native book names are then read from the DB's own `books` table — no manual language mapping file is needed.

### Quick Reference (derived from index)
| Language | Code | Primary | Fallback |
|---|---|---|---|
| English | `en` | `KJV` | `NIV` |
| Spanish | `es` | `RVR1960` | `NVI` |
| Portuguese | `pt` | `ARC` | `NVI` |
| French | `fr` | `LSG1910` | `BDS` |
| German | `de` | `LU17` | `SCH2000` |
| Japanese | `ja` | `SK2003` | `JCB` |
| Chinese | `zh` | `CUV1919` | `CNVS` |
| Hindi | `hi` | `HIOV` | `HERV` |

Reading speeds (`reading_speed.rate` and `reading_speed.unit`) are available per language in the remote index — read them from there, do not hardcode.

For the `version` field in JSON output, use the display `name` from the index — not the code:
`SK2003` → `"新改訳2003"`, `CUV1919` → `"和合本1919"`, `HIOV` → `"पवित्र बाइबिल (ओ.वी.)"`, etc.

> If a version used by this project is **not** listed in the remote index, that SQLite file must already be present locally in `bible_database/`.

### Pre-Translation: Lookup & Download
Before translating each language, ensure the required SQLite is available locally:

**Step 1 — Fetch the remote index:**
```python
import urllib.request, json, gzip, shutil, os

INDEX_URL = "https://raw.githubusercontent.com/develop4God/bible_versions/refs/heads/main/index.json"
with urllib.request.urlopen(INDEX_URL) as resp:
    index = json.loads(resp.read())
```

**Step 2 — Resolve version for target language:**
```python
lang_entry    = index["languages"][lang_code]        # e.g. lang_code = "es"
primary_code  = lang_entry["primary_version"]        # e.g. "RVR1960"
fallback_code = lang_entry["fallback_version"]       # e.g. "NVI"
version_entry = lang_entry["versions"][primary_code]
remote_file   = version_entry["file"]                # e.g. "RVR1960_es.SQLite3.gz"
download_url  = version_entry["url"]
```

**Step 3 — Download & decompress to `bible_database/` if not present:**
```python
DB_DIR   = "bible_database"
local_gz = os.path.join(DB_DIR, remote_file)
local_db = local_gz.replace(".gz", "")              # e.g. "bible_database/RVR1960_es.SQLite3"

if not os.path.exists(local_db):
    if not os.path.exists(local_gz):
        print(f"Downloading {remote_file}...")
        urllib.request.urlretrieve(download_url, local_gz)
    with gzip.open(local_gz, "rb") as gz_in, open(local_db, "wb") as db_out:
        shutil.copyfileobj(gz_in, db_out)
```

**Step 4 — Pass the decompressed path to VerseResolver:**
```python
from verse_resolver import VerseResolver

# No book_map.json needed — native book names come from the DB's books table
with VerseResolver(local_db) as resolver:
    citation, text, error = resolver.resolve("John 3:16")
```

If a verse fails in the primary version, repeat Steps 2–4 for `fallback_code` and flag it in the delivery note.

### Verse Resolver Requirement
All verse lookups, citation translation, and verse text extraction must use `devocionales_scripts/verse_resolver.py`. Do not manually map, hardcode, or copy-paste verse text or references.

Use the **primary version only** for all verse text in translations.

---

## JSON Rules

### Always keep identical (do NOT translate):
- `id`, `type`, `date`, `order`, `icon`
- `greek_words[].word` and `greek_words[].transliteration`
- `hebrew_words[].word` and `hebrew_words[].transliteration`
- The term `Māmônā` wherever it appears in content
- Emoji characters including `👁️✅` and `👁️❌`

### Always change:
- `language` → target language code
- `version` → primary Bible version for target language
- `estimated_reading_minutes` → recalculated (see below)
- All text content fields: `title`, `subtitle`, `content`, `revelation_key`, `identity_statement`
- All `meaning` and `revelation` fields inside word blocks
- All `key_verse.text` and `scripture_connections[].text` → use primary Bible version
- All `key_verse.reference` and `scripture_connections[].reference` → translate book names
- All `discovery_questions[].category` and `discovery_questions[].question`
- All `action_steps[].title` and `action_steps[].description`
- `prayer.title` and `prayer.content`
- `tags` → translate to natural target language slugs
- `metadata.themes` → translate all theme strings

### Never add or remove JSON keys.
Key structure must be identical to the EN file. Run `validate_pair.py` to confirm.

---

## Translation Quality Standards

**Register:** Warm, pastoral, devotional — accessible to a general Christian audience.

**Not literal:** Translate meaning and feel, not word-for-word. Natural idioms in the target language are preferred over calques from English.

**Prayer:** Translate as a living prayer — natural spoken address to God, no academic language, no untranslated foreign terms.

**Section headings in content:** Lines in ALL CAPS → translate to ALL CAPS in target language. Emoji-led headings → keep emoji, translate text.

**Asian and Hindi languages (JA, ZH, HI):** Use respectful/honorific religious register throughout. This is sacred literature.

**Cross-reference ES file** for pastoral tone on the prayer and `identity_statement` — the ES file has the most developed devotional voice for these sections.

---

## MANDATORY GATE: Per-Language Register Rules

Before delivering a translated file, check it against the rule for its language.
A translation can be grammatically fluent and still fail this gate — check anyway.

**Hindi (HI):** Jesus takes the respectful plural — verbs included, not just pronouns.
Example: ✗ "यीशु आया...उसने कहा" → ✓ "यीशु आए...उन्होंने कहा". Does not apply to quoted
verse fields (`key_verse.text`, `scripture_connections[].text`) — those follow the cited
Bible version's own grammar.

**Japanese (JA):** When Jesus (イエス) or God (神) is the subject, the verb must be in
honorific form (敬語), not plain form. Other characters stay in plain form — that's
correct, don't flag it.

**Chinese (ZH):** Never use 您 for God/Jesus — always 你. Flag 您 as the error, not 你.

**Spanish / Portuguese / French (ES / PT / FR):** No hard gate — natural register per
house style. Cognates are valid translations, not errors.

---

## Reading Time
`estimated_reading_minutes` is an **editorial value** — it reflects the intended reading experience, not a raw word count calculation. The author sets it based on content density, depth of study, and expected user pace.

**Reference values for this study family (discovery type):**
| Pages / Cards | Estimated minutes |
|---|---|
| 7-8 cards, light content | 8-10 min |
| 9 cards, moderate depth | 12 min (EN/ES baseline) |
| 9 cards, translated (Romance) | 13-14 min |
| 9 cards, translated (HI) | 14 min |
| 9 cards, translated (JA/ZH) | 14-15 min |

Use the EN value as your baseline. Add 1-2 min for Romance languages (PT, FR), 2 min for HI, 2-3 min for JA/ZH due to reading density differences.

Store the value in both the JSON file and `index.json`.

> Note: `metadata.total_word_count` is informational only and stores the card content word count. It does not drive reading time.

---

## Validation Steps for each translation
Run in this order. Fix all errors before proceeding to the next language.

```bash
# After each language file is created:
python3 validate_pair.py {study_id}_en_001.json {study_id}_{lang}_001.json

# After all languages are done:
python3 discovery_master_validator.py
```

**Zero errors required.** Warnings about `estimated_reading_minutes` differing from EN are expected and acceptable. All other warnings must be investigated and resolved.

---

## MANDATORY: Native-Speaker Critic Review — MUST RUN BEFORE MARKING ANY TRANSLATION AS DONE

`validate_pair.py` checks schema and structure — it cannot catch bad prose. The
translating agent also cannot reliably catch its own register mistakes. So after each
language file passes `validate_pair.py`, **before delivery**, spawn a **fresh subagent
(NOT HAIKU model)** (no shared context with the translator) — one critic per translated
file, in parallel across the batch.

### When to spawn
Immediately after a translation file is written and `validate_pair.py` passes for it —
do not batch this up and defer it to the end of the whole run.

### Delegation prompt template
> You are a native [LANGUAGE] Christian speaker. Read this file line by line, taking
> your time. Review the following [LANGUAGE] Bible study translation for errors (DOES
> NOT APPLY to verses only in the translated content):
> File: [FILE_PATH]
>
> For EACH file, carefully check for:
>
> **CRITICAL ERRORS (must be fixed):**
> - Typos and spacing errors
> - Wrong word meanings that change theological meaning
> - Untranslated English words or phrases
> - Incorrect characters or diacritics
> - Wrong verb conjugations or tenses
> - Expressions that sound unnatural for a native speaker
> - Theological terminology errors for this language and culture
> - Violation of the per-language register rule in
>   `discovery/skills/discovery-translator-SKILL.md` § "MANDATORY GATE: Per-Language
>   Register Rules"
>
> **MODERATE ISSUES (should be improved):**
> - Word choices with wrong connotations
> - Unnatural phrasing that doesn't sound native
> - Inconsistent terminology across sections
> - Better synonym choices for clarity
>
> **MINOR SUGGESTIONS:**
> - Style improvements
> - More natural idioms
> - Better flow
>
> Provide: file name, list of ALL findings (with text context), severity
> (CRITICAL/MODERATE/MINOR), and a suggested correction (elaborate diff) for each.

### Coordinator review
After all critic reports return:
1. CRITICAL findings are a checklist. The coordinator must iterate through every item marked CRITICAL, apply each fix one by one, and confirm each one before closing the review. Do not mark a file as reviewed until every CRITICAL item has a fix applied and confirmed.
2. Review MODERATE findings — review one by one, dismiss or apply the fix, document each one.
3. Review MINOR suggestions — review one by one, dismiss or apply the fix, document each one.
4. Re-run `validate_pair.py` on any file that was modified.
5. Proceed to the reverse-validation gate below before final validation.

---

## MANDATORY GATE: Post-Fix Reverse Validation & Pattern Sweep

A grammar/style fix can silently break meaning — restructuring a clause to fix a case
error can turn a sentence into something that no longer says anything. The agent that
applies the fix is the worst-positioned to notice this (it's focused on the grammar, not
re-deriving the theological point). So after applying critic fixes and before reporting
a file done:

1. **Re-read the complete file**, not just the diffed lines — meaning depends on
   surrounding context the diff view won't show you.
2. **For every edit made**, verify it still expresses the original point. Anchor the
   check against the card's paired `key_verse`/`scripture_connections` and its
   `revelation_key` or `identity_statement` — those are the source of truth for what the
   sentence is supposed to say. If a rewrite makes a sentence grammatically correct but
   tautological, vaguer, or logically disconnected from its `revelation_key`, it is a
   regression — fix it, don't wave it through.
3. **Scan the entire file for the same error pattern(s)** the critic just flagged —
   critics pass a sample, they don't exhaustively cover. If the critic caught an
   anglicism, a dangling modifier, a mistranslation, or a register slip in one card, grep/read
   for that same pattern in every other card before considering the round done.
4. **Validate JSON** after every batch of edits (`python3 -m json.tool <file>` or
   `validate_pair.py`) — never leave this until the very end.

Repeat steps 2–4 until a full pass finds nothing new. Only then move to the next
language or report completion.

### ZH-Specific Check: 您/你 Register

For Chinese files only, after the critic review, grep the file for 您. This character
has no legitimate use in this content (no correct quoted-scripture use, no homograph) —
every hit is a real violation of the project rule (see "MANDATORY GATE: Per-Language
Register Rules" above) and should be replaced with 你.

---

## index.json Update
After all languages are validated, update the study entry in `index.json`:
- `titles` → pull `title` directly from each translation file
- `subtitles` → pull `subtitle` directly from each translation file
- `estimated_reading_minutes` → must match exactly what is in each translation file
- Append entry to end of `studies` array — do not reorder existing entries
- Run `validate_discovery.py` after updating to confirm no regressions

---

## Delivery
1. All translated JSON files
2. Updated `index.json`
3. Validation log (✅ PERFECT for each pair)
4. Native-speaker critic review completed for each language (see "MANDATORY: Native-Speaker Critic Review" above) — fixes applied, not just reported
5. Reading time table — use the format below; retrieve each language's rate and unit from `reading_speed` in the remote index:

| Language | Words/Chars | Rate (from index) | Minutes |
|---|---|---|---|
| PT | — | — | — |
| FR | — | — | — |
| HI | — | — | — |
| JA | — | — | — |
| ZH | — | — | — |

6. Flag any verse not found in primary version with the fallback version used
