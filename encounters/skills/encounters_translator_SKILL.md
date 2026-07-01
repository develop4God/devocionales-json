# SKILL: Encounters JSON Translator

You are a professional biblical translator and theologian with expertise in narrative devotional literature. You translate encounter studies — cinematic, character-driven biblical stories — into natural, immersive language for each target audience.

---

## What You Receive
- `{encounter_id}_en_001.json` — EN master (translation base)
- `encounters/index.json` — source of truth for languages needed
- Remote index — source of truth for versions, codes, and download URLs: `https://raw.githubusercontent.com/develop4God/bible_versions/refs/heads/main/index.json`
- `validate_encounters.py` — validator (run after all languages)
- `master_validator.py` — orchestrator (run at end)

---

## What You Produce
For each language listed under `files` in `index.json` for this encounter (excluding `en`):
- One translated JSON file: `{encounter_id}_{lang}_001.json`
- Validation log showing ✅ ALL ENCOUNTERS PASSED or resolved warnings
- Updated `encounters/index.json` entry
- Reading time summary table

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

For the `bible_version` field in JSON output:
- **Latin-script languages (EN, ES, PT, FR, DE)** — use the **code**, unchanged: `KJV`, `RVR1960`, `ARC`, `LSG1910`, `LU17`. Do **not** spell out the full name ("King James Version" is wrong — check existing sibling files in that language before writing this field if unsure).
- **Non-Latin-script languages (JA, ZH, HI, AR)** — use the display `name` from the index instead of the code, since the code alone means nothing to a native reader: `SK2003` → `"新改訳2003"`, `CUV1919` → `"和合本1919"`, `HIOV` → `"पवित्र बाइबिल (ओ.वी.)"`, `HERV` → `"पवित्र बाइबिल"`.

This applies to **all three** `bible_version` fields (top-level, `key_verse`, `completion_verse`) — keep all three the same form (code or name) for a given language, never mixed.

> If a version used by existing encounters is **not** listed in the remote index, that SQLite file must already be present locally in `bible_database/`.

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
display_name  = version_entry["name"]                # e.g. "Reina-Valera 1960"
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

---

## JSON Rules

### Always keep identical (do NOT translate):
- `id`, `type`, `schema_version`, `order`
- `image_url`, `mood`, `haptic`, `ambient_sound` — UI/media fields
- `accent_color`, `celebration_type` — visual config
- `meta.mood_primary`, `meta.accent_color`, `meta.emoji`

### Always translate:
- `language` → target language code
- `bible_version` — appears in **3 places**, translate ALL three consistently:
  1. Top-level `"bible_version"`
  2. Inside `key_verse.bible_version`
  3. Inside `completion_verse.bible_version`
- `estimated_reading_minutes` → recalculated (see Reading Time)
- `title`, `subtitle`, `narrative`, `content`, `reflection`, `revelation_key`, `reflection_prompt`
- `key_verse.text` → primary Bible version text
- `key_verse.reference` → translate book name (e.g. `Mark` → `Marcos`, `マルコ`, `मरकुस`)
- `verse_text` and `verse_reference` in `scripture_moment` cards
- `verse_overlay.text` and `verse_overlay.reference`
- `completion_verse.text`, `completion_verse.reference`
- `scripture_connections[].text` and `scripture_connections[].reference`
- `discovery_questions[].category` and `discovery_questions[].question`
- `prayer.title` and `prayer.content`
- `meta.scripture_reference` → translate book name only
- `meta.tags` → natural target language slugs

### Never add or remove JSON keys.
Structure must be identical to the EN file.

---

## Translation Quality Standards

**Register:** Cinematic, immersive, warm. These are narrative encounters — translate for emotional impact, not academic precision.

**Not literal:** Translate meaning and feel. Natural idioms in the target language are preferred.

**Narrative cards (`cinematic_scene`):** Keep the short, punchy sentence rhythm. Do not merge sentences.

**Prayer:** Natural spoken address to God — no academic language, no untranslated foreign terms.

**Cognates (FR, PT, ES):** Words identical or near-identical across languages (e.g. `Courage` in French, `Grâce`) are valid translations — do not change them. The validator may warn but these are correct.

---

## MANDATORY GATE: Per-Language Register Rules

Before delivering a translated file, check it against the rule for its language.
A translation can be grammatically fluent and still fail this gate — check anyway.

**Hindi (HI):** Jesus takes the respectful plural — verbs included, not just pronouns.
Example: ✗ "यीशु आया...उसने कहा" → ✓ "यीशु आए...उन्होंने कहा". Does not apply to quoted
verse fields (`verse_text`, `verse_overlay.text`, `completion_verse.text`,
`scripture_connections[].text`) — those follow the cited Bible version's own grammar.

**Japanese (JA) / Chinese (ZH):** Respectful/honorific register throughout — this is
sacred literature. Example: avoid casual だ/よ endings in Japanese narration about
Jesus; use 您 over 你 in Chinese devotional address.

**Spanish / Portuguese / French (ES / PT / FR):** No hard gate — natural register per
house style. Cognates are valid (see above).

---

## Structural Rules

- `completion` card **must always be last** in the cards array
- `discovery_activation` card **must always be present**
- `has_interactive` in `index.json` must match whether the file contains an `interactive_moment` card — do not add or remove this card type

---

## Reading Time
`estimated_reading_minutes` is an **editorial value** — not a formula. Use the EN value as baseline.

| Language | Adjustment from EN |
|---|---|
| ES, PT, FR | +1-2 min |
| DE | +1 min |
| HI | +2 min |
| JA, ZH | +2-3 min |

Store the value in both the JSON file and `index.json`.

---

## Validation
Run after all languages are complete. Zero errors required before delivery.

```bash
# Run encounters validator
python3 encounters/encounters_scripts/validate_encounters.py

# Or via master
python3 encounters/encounters_scripts/master_validator.py
```

Warnings about cognates (FR/PT/ES) and reading time differences from EN are expected and acceptable. All other warnings must be investigated and resolved.

---

## MANDATORY: Native-Speaker Critic Review

`validate_encounters.py` checks schema and structure — it cannot catch bad prose. The
translating agent also cannot reliably catch its own register mistakes (this is exactly
how the HI plural-Jesus error shipped). So after each language file passes validation,
before delivery, spawn a **fresh subagent (NOT HAIKU model)** (no shared context with the translator) with
this prompt, substituting the language and file path:

> You are a native {language} speaker. Read this file line by line, taking your time.
> Report: Typos / Grammar Errors, and Awkward / Non-native-sounding phrasing. For each
> issue found, propose the exact diff/fix. Also check it against the per-language
> register rule in `encounters/skills/encounters_translator_skill.md` § "MANDATORY GATE:
> Per-Language Register Rules".

Apply the fixes the critic finds, then re-run `validate_encounters.py` to confirm the
edits didn't break structure. Do this per language file — do not skip it for languages
that "usually don't have issues."

### MANDATORY GATE: Post-Fix Reverse Validation & Pattern Sweep

A grammar/style fix can silently break meaning — restructuring a clause to fix a case
error can turn "he walked toward danger with eyes open" into a circular sentence that no
longer says anything. The agent that applies the fix is the worst-positioned to notice
this (it's focused on the grammar, not re-deriving the theological point). So after
applying critic fixes and before reporting done:

1. **Re-read the complete file**, not just the diffed lines — meaning depends on
   surrounding context the diff view won't show you.
2. **For every edit made**, verify it still expresses the original point. Anchor the
   check against the card's paired Bible reference and its `revelation_key` — those are
   the source of truth for what the sentence is supposed to say. If a rewrite makes a
   sentence grammatically correct but tautological, vaguer, or logically disconnected
   from its `revelation_key`, it is a regression — fix it, don't wave it through.
3. **Scan the entire file for the same error pattern(s)** the critic just flagged —
   critic passes sample, they don't exhaustively cover. If the critic caught an
   anglicism, a dangling modifier, an aufstehen/auferstehen-type mistranslation, or a
   colon-capitalization slip in one card, grep/read for that same pattern in every other
   card before considering the round done.
4. **Validate JSON** after every batch of edits (`python3 -m json.tool <file>` or the
   project validator) — never leave this until the very end.

Repeat steps 2–4 until a full pass finds nothing new. Only then move to the next
language or report completion.

---

## index.json Update
- Update the existing entry in the `encounters` array — do not duplicate or reorder
- Pull `titles`, `subtitles`, `scripture_reference` directly from each translation file
- `estimated_reading_minutes` must match each translation file exactly
- `status` — do not change `published` or `coming_soon`
- Run `validate_encounters.py` after updating to confirm no regressions

---

## Delivery
1. All translated JSON files (one per language)
2. Updated `encounters/index.json`
3. Validation log showing ✅ ALL ENCOUNTERS PASSED
4. Native-speaker critic review completed for each language (see "MANDATORY: Native-Speaker Critic Review" above) — fixes applied, not just reported
5. Reading time table:

| Language | Adjustment | Minutes |
|---|---|---|
| ES | +1 | — |
| PT | +1 | — |
| FR | +1 | — |
| DE | +1 | — |
| HI | +2 | — |
| JA | +3 | — |
| ZH | +3 | — |

6. Flag any verse not found in primary version with fallback version used