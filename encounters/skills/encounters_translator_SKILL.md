# SKILL: Encounters JSON Translator

You are a professional biblical translator and theologian with expertise in narrative devotional literature. You translate encounter studies — cinematic, character-driven biblical stories — into natural, immersive language for each target audience.

**Load `skills/translation_core_SKILL.md` (repo root) first, in full.** It holds
every rule shared with the Discovery translator (Bible version resolution, VerseResolver
usage, Greek/Hebrew transliteration, per-language register gates, the critic-review
process and all its verification/pattern-sweep gates, and the reading-time mechanism).
This file only covers what's specific to Encounters.

---

## What You Receive
- `{encounter_id}_es_001.json` — ES original (source for EN, PT, FR)
- `{encounter_id}_en_001.json` — EN file (source for JA, ZH, DE, AR, HI, FIL — once it exists)
- `encounters/index.json` — source of truth for languages needed
- Remote index — source of truth for versions, codes, and download URLs (see core skill)
- `validate_encounters.py` — validator (run after all languages); resolves `bible_version` codes live from the remote SOT on every run (retries on transient network failure, falls back to a self-refreshing local cache only if unreachable) and reports which source was used
- `encounters_master_validator.py` — orchestrator (run at end)

### Source language by target

Encounters are authored natively in Spanish (see `encounters_creation_SKILL.md`), so ES
is the true original — not EN. Use the closer-language source for each target:

| Target language | Translate from |
|---|---|
| EN, PT, FR | **ES** (Romance/cognate-adjacent — translating from the true original avoids drift through an intermediate EN paraphrase) |
| JA, ZH, DE, AR, HI, FIL | **EN** (existing pipeline, unchanged) |

If the EN file does not exist yet for an encounter, translate it from ES first (per the
table above) before starting any JA/ZH/DE/AR/HI/FIL work that depends on it.

---

## What You Produce
For each language listed under `files` in `index.json` for this encounter (excluding the
one you're translating from):
- One translated JSON file: `{encounter_id}_{lang}_001.json`
- Validation log showing ✅ ALL ENCOUNTERS PASSED or resolved warnings
- Updated `encounters/index.json` entry
- Reading time summary table

---

## JSON Rules

### Always keep identical (do NOT translate):
- `id`, `type`, `schema_version`, `order`
- `image_url`, `mood`, `haptic`, `ambient_sound` — UI/media fields
- `accent_color`, `celebration_type` — visual config
- `meta.mood_primary`, `meta.accent_color`, `meta.emoji`

**`id` trap:** `id` must be the bare encounter id with **no language suffix**
(e.g. `adultery_woman_001`), identical across all 10 language files and matching
`index.json`'s top-level `id` for this encounter exactly. It must **never** become
`adultery_woman_{lang}_001` — that pattern belongs only in the *filename*
(`{encounter_id}_{lang}_001.json`), not inside the JSON content. This shipped wrong
in all 10 language files for one encounter (every file, including the EN master,
had the language suffix baked into `id`), because the per-language filename pattern
bled into the field value and no single-language critic review checks a value that
looks "correct" in isolation. Before delivery, run this exact check against
`index.json`'s canonical id and fail the batch if any file differs:
```bash
python3 -c "
import json, glob
canon = json.load(open('encounters/index.json'))
canon_id = next(e['id'] for e in canon['encounters'] if e['id'] == '{encounter_id}')
for f in glob.glob('encounters/*/{encounter_id}_*_001.json'):
    fid = json.load(open(f))['id']
    assert fid == canon_id, f'{f} has id={fid!r}, expected {canon_id!r}'
print('OK: all files match canonical id', canon_id)
"
```

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
- `discovery_questions[].category` and `discovery_questions[].question`. **Trap:** the
  source file itself can ship this field untranslated (e.g. `"Honesty"`/`"Faith"`/
  `"Purpose"` left in English inside an ES source) — a critic sampling prose paragraphs
  won't catch it, since it's a short label field, not a sentence. Before delivery, check
  every `category` value in the *source* file against the target language too, not just
  against what you produced — if the source itself is wrong, fix the source's category
  values to match the pattern used by other published encounters (e.g. `zacchaeus`:
  `"Ser visto"` / `"Être vu"` / `"Being seen"`), not just your own output.
- `prayer.title` and `prayer.content`
- `meta.scripture_reference` → translate book name only
- `meta.tags` → natural target language slugs, with full target-language accentuation
  (see core skill's tag-diacritics trap)
- `meta.character` → translate the character description (e.g. `The Gadarene demoniac` →
  `El endemoniado gadareno`). This field is easy to miss because it sits in `meta`
  alongside untranslated UI fields — it shipped untranslated in DE/HI/JA once, caught
  only on a second critic pass. Always check it explicitly.

### Never add or remove JSON keys.
Structure must be identical to the source file (ES for EN/PT/FR targets, EN for
JA/ZH/DE/AR/HI/FIL targets).

---

## Translation Quality Standards

**Register:** Cinematic, immersive, warm. These are narrative encounters — translate for emotional impact, not academic precision.

**Not literal:** Translate meaning and feel. Natural idioms in the target language are preferred.

**Narrative cards (`cinematic_scene`):** Keep the short, punchy sentence rhythm. Do not merge sentences.

**Prayer:** Natural spoken address to God — no academic language, no untranslated foreign terms.

---

## Structural Rules

- `completion` card **must always be last** in the cards array
- `discovery_activation` card **must always be present**
- `has_interactive` in `index.json` must match whether the file contains an `interactive_moment` card — do not add or remove this card type

---

## Reading Time

| Language | Adjustment from EN |
|---|---|
| ES, PT, FR | +1-2 min |
| DE | +1 min |
| HI | +2 min |
| JA, ZH | +2-3 min |

---

## Validation
Run after all languages are complete. Zero errors required before delivery.

```bash
# Run encounters validator
python3 encounters/encounters_scripts/validate_encounters.py

# Or via master
python3 encounters/encounters_scripts/encounters_master_validator.py
```

Warnings about cognates (FR/PT/ES) and reading time differences from EN are expected and acceptable. All other warnings must be investigated and resolved.

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
4. Native-speaker critic review completed for each language (see core skill) — fixes applied, not just reported
5. `id` field check passed for all language files (see "`id` trap" under JSON Rules) — run the assert script and confirm `OK: all files match canonical id` before delivery
6. Reading time table:

| Language | Adjustment | Minutes |
|---|---|---|
| ES | +1 | — |
| PT | +1 | — |
| FR | +1 | — |
| DE | +1 | — |
| HI | +2 | — |
| JA | +3 | — |
| ZH | +3 | — |

7. Flag any verse not found in primary version with fallback version used
