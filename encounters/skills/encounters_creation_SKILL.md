---
name: encounters-content-creator
description: "Use this skill whenever the user wants to create, draft, or generate a new Encounter — a biblical character study distributed as a structured JSON file for the Encounters devotional app series. Triggers include: \"create an encounter\", \"new encounter for [character]\", \"write the encounter about [biblical scene]\", \"draft [character] encounter\", or any request to produce Encounters-format content. Always load this skill before generating any encounter JSON or card content, even if the request seems simple."
---

---
name: encounters-content-creator
description: >
  Use this skill whenever the user wants to create, draft, or generate a new Encounter —
  a biblical character study distributed as a structured JSON file for the Encounters devotional
  app series. Triggers include: "create an encounter", "new encounter for [character]",
  "write the encounter about [biblical scene]", "draft [character] encounter", or any request
  to produce Encounters-format content. Always load this skill before generating any encounter
  JSON or card content, even if the request seems simple.
---

# Encounters Content Creator

## What this skill does

Guides Claude through generating a new Encounter JSON file from scratch: drafting in-chat first,
collecting user approval, then saving the final `.json` file. This avoids wasting tokens on
full file generation before the content is approved.

---

## Workflow

### 1. Gather inputs (if not already in context)
Ask only what's missing:
- **Character** — who is the encounter about?
- **Scripture passage** — book, chapter:verses
- **Language** — default is **Spanish (es)**; English (en) only after Spanish is approved
- **Bible version** — default Spanish: RVR1960; default English: KJV
- **Tone/mood seed** — optional, e.g. "shame → restoration", "darkness → sight"

If the user provides all of this upfront, skip to step 2 (pre-write checklist), then step 3.

---

### 2. Pre-write checklist — apply WHILE drafting, not after

These are the recurring failures that first drafts have shipped with in the past. Apply them
as you write each card, not as a post-hoc review pass — the goal is a first draft that doesn't
need a correction round for these specific issues:

- **No negation-based argument construction.** Never build a sentence on "No fue X. Fue Y." /
  "No dijo X, sino Y." / "sin epílogo" / "elige no ejercerlo" as a rhetorical contrast device.
  State what IS true directly. The only exception is direct or close-paraphrase quotation of
  the biblical text itself (e.g. "Ninguno, Señor" — the character's own words). See the
  "Affirmation over negation" rule below — this is the single most common defect flagged
  across review sessions, so catch it while writing, not after.
- **Never quote a full verse inline in prose.** `narrative`, `content`, and `reflection` fields
  must reference other passages as a bare parenthetical — e.g. "(Juan 1:17)" — never as an
  embedded full quotation. The complete verse text belongs only in `verse_overlay` or
  `scripture_connections`, each with its own `reference` field alongside it.
- **Distinguish the character's face from every previously published character.** Before
  writing the `master_character_prompt` (see Image Prompts section), check the age bracket,
  face shape, eye shape, build, hair treatment, and clothing palette used in every other
  `*_image_prompts.json` already in the language folder. Pick something that reads as a
  genuinely different person, not just different adjectives. Avoid defaulting to a young,
  conventionally beautiful face — but don't overcorrect into harsh or masculine-reading
  features either; aim for plain, ordinary, clearly adult, clearly the stated gender. State
  the distinction explicitly when presenting the character prompt so the user can catch
  overlap or overcorrection before the full card set is generated.

---

### 3. Draft the encounter IN-CHAT (no file yet)

Generate the full JSON structure directly in the chat as a code block.
Do NOT save a file until the user approves. This is the token-efficient path.

Use the envelope + card schema below.

---

### 4. User reviews → iterate in-chat

Make all edits to the in-chat JSON until the user approves. Only then proceed to step 5.

---

### 5. Save the approved JSON files

Once the user says it's approved, save **two files** to the encounter's language directory
(e.g. `encounters/es/`):

1. **Encounter file**: `<id>.json` — the full encounter JSON with cards.
2. **Image prompts file**: `<id_without_lang>_image_prompts.json` — a separate JSON containing:
   - `encounter_id` — matches the encounter's `id`
   - `character` — English character name
   - `master_character_prompt` — the character visual identity lock (English)
   - `intro_image` — `{ "filename": "...", "prompt": "..." }` for the index cover image
   - `card_prompts` — array of `{ "order", "image_url", "mood", "shot_type", "prompt" }` for each card

Image prompts are always in English regardless of encounter language. Each card prompt must be
self-contained (include character description inline, never reference "see master prompt").

Also update `index.json` with `intro_image` and `intro_image_prompt` fields for the encounter.

---

## Known encounter queue

Encounters series as of April 2026. Published: Pedro, Bartimeo, Mujer del Pozo. Next in queue:

| Character | Scripture | index id | Status |
|-----------|-----------|----------|--------|
| Zaqueo | Lucas 19:1-10 | `zacchaeus_001` | `coming_soon` — **next** |
| María Magdalena | Juan 20:1-18 | `mary_garden_001` | `coming_soon` |

When starting a new encounter, check this table so `id` and filenames align with the index.

---

## JSON Schema

### Encounter file envelope (top-level)

```json
{
  "id": "<character_slug>_<NNN>",
  "type": "encounter",
  "schema_version": "encounters_v1",
  "language": "es",
  "bible_version": "RVR1960",
  "version": "1.0",
  "image_version": "1.0",
  "estimated_reading_minutes": 10,
  "meta": {
    "character": "string",
    "testament": "old | new",
    "scripture_reference": "Book chapter:verses",
    "mood_primary": "string (e.g. darkness, midday, storm, crowd, grief, fire)",
    "accent_color": "#hexcolor",
    "emoji": "single emoji",
    "tags": ["array", "of", "theme", "strings"]
  },
  "key_verse": {
    "reference": "Book chapter:verse",
    "text": "Full verse text. Never truncated.",
    "bible_version": "RVR1960"
  },
  "cards": []
}
```

**ID file name convention:** `<character_snake_case>_<lang>_<NNN>` — e.g. `zacchaeus_es_001 always in English

### index.json entry (update after each approved encounter)

When a new encounter is approved, also draft the index.json entry for it:

```json
{
  "id": "<character>_001",
  "version": "1.0",
  "image_version": "1.0",
  "emoji": "emoji",
  "status": "coming_soon",
  "intro_image": "<character>_intro.png",
  "intro_image_prompt": "AI image prompt for the cover/intro image. Same style rules as card images.",
  "mood_primary": "string",
  "accent_color": "#hexcolor",
  "has_interactive": false,
  "testament": "new | old",
  "character": "Full character name",
  "files": { "es": "<id>_es_001.json", "en": "...", "pt": "...", "fr": "...", "de": "...", "ja": "...", "zh": "...", "hi": "...", "ar": "..." },
  "titles": { "es": "...", "en": "..." },
  "subtitles": { "es": "...", "en": "..." },
  "scripture_reference": { "es": "...", "en": "..." },
  "estimated_reading_minutes": { "es": 10, "en": 9 }
}
```

**`has_interactive`**: set to `true` only if the encounter contains an `interactive_moment` card.
**`intro_image_prompt`**: write this alongside the encounter, same image prompt rules as cards.

---

### Card types

All cards share these base fields:
- `order` (integer, 1-based)
- `type` (string, see types below)
- `mood` (string, optional on some types)
- `image_url` (string — filename, see Image Prompt section)
- `revelation_key` (string — the one-sentence theological insight, optional on some types)

> **Note:** `image_prompt` is NOT stored in the card JSON. Image prompts are managed separately (see Image Prompts section).

### What a `revelation_key` is (and isn't)

A `revelation_key` is not a summary of the card's `content`/`narrative`, not a poetic flourish, and not a place to cram extra biblical content just because it's available. It is the single sharpened "aha" specific to *this card's moment* — distinct from what the narrative already said, and without spoiling what a later card will reveal.

Before writing one, answer explicitly: **what is this specific card trying to make the reader take away, and is that different from what neighboring cards already carry or will carry?** Don't write text "a lo loco" (recklessly, without this analysis) — if a card already has heavy theological weight assigned to it (e.g. a following card that unpacks the full symbolism), the current card's `revelation_key` doesn't need to carry that weight too; it should capture only what belongs to its own moment.

**Concrete case (2026-07-16, Emmaus, "Al partir el pan" card):** first draft closed with "no en una señal espectacular" — technically accurate but (1) a negation pattern already banned above, and (2) it flattened everything already established about the theological weight of bread-breaking (same verb pattern as the Last Supper and the feeding of the 5,000 — see the following card, which owns that weight). The real "aha" for *this specific card* was narrower: recognition came through something intimate Cleofas already knew of Jesus, not through a new miracle. Final: "Cleofas no reconoce a Jesús por un milagro ante sus ojos, sino por algo íntimo que ya conocía de él."

---

#### `cinematic_scene`
Opens or transitions a narrative beat. Immersive, present-tense prose.
```json
{
  "order": 1,
  "type": "cinematic_scene",
  "mood": "string",
  "image_url": "filename.png",
  "title": "Short evocative title.",
  "narrative": "Prose paragraph(s). No em dashes. Pastoral tone.",
  "ambient_sound": "crowd_distant | wind | water | silence | fire | etc.",
  "haptic": null,
  "verse_overlay": {
    "reference": "Book ch:v",
    "text": "Full verse text in same Bible version and language"
  },
  "revelation_key": "One sentence."
}
```
> **`verse_overlay`** is optional but common — use it when the scene has a verse anchor.
> **`haptic`** is optional — omit or set to `null`.

#### `scripture_moment`
Presents a passage + reflection. Verse must be complete — no truncation.

**`scripture_connections`** (optional array): Add this field at the bottom of any `scripture_moment`
card when the reflection references other Bible passages that the reader would benefit from seeing.
Each connection is `{ "reference": "...", "text": "..." }` with the full verse text in the same
Bible version and language as the card. Use this whenever the reflection explicitly mentions or
contrasts another passage — the dart code will resolve these for display automatically.

```json
{
  "order": 2,
  "type": "scripture_moment",
  "mood": "string",
  "image_url": "filename.png",
  "verse_reference": "Book chapter:verses",
  "verse_text": "Full verse(s) from RVR1960 — exact text, correct capitalization",
  "reflection": "Paragraph(s) unpacking the verse. No jargon. Pastoral.",
  "revelation_key": "One sentence.",
  "scripture_connections": [
    { "reference": "Book ch:v", "text": "Full verse text in same Bible version and language" }
  ]
}
```

> **Rule:** `scripture_connections` is optional but REQUIRED when the reflection explicitly cites
> or contrasts another passage by reference (e.g. "unlike the rich young ruler in Luke 18:18–23…"
> or "exceeding what the law required in Leviticus 5:16"). The reader must be able to see those
> verses inline without leaving the card.

#### `character_moment`
Psychological/emotional deep-dive into the biblical character.
```json
{
  "order": 3,
  "type": "character_moment",
  "mood": "string",
  "image_url": "filename.png",
  "title": "string",
  "subtitle": "string",
  "content": "Prose. May include emphasis markers like 🔑 or ⚠️ for key phrases.",
  "revelation_key": "One sentence.",
  "verse_overlay": {
    "reference": "Book ch:v",
    "text": "Full verse text"
  },
  "scripture_connections": [
    { "reference": "Book ch:v", "text": "Full verse text" }
  ]
}
```
> **`verse_overlay`** and **`scripture_connections`** are optional on this card type.

#### `theological_depth`
Exegetical insight — Greek/Hebrew word studies, cultural context, cross-references.
```json
{
  "order": 5,
  "type": "theological_depth",
  "mood": "string",
  "image_url": "filename.png",
  "title": "string",
  "subtitle": "string",
  "content": "Prose with emoji markers for key insights. Greek/Hebrew in transliteration.",
  "revelation_key": "One sentence.",
  "verse_overlay": {
    "reference": "Book ch:v",
    "text": "Full verse text"
  },
  "scripture_connections": [
    { "reference": "Book ch:v", "text": "Full verse text" }
  ]
}
```
> **`verse_overlay`** is optional on this card type.

#### `discovery_activation`
Application card — 3 reflection questions + closing prayer. Always near the end.
```json
{
  "order": 14,
  "type": "discovery_activation",
  "image_url": "filename.png",
  "title": "Tu Encuentro",
  "subtitle": "One-line bridge from the story to the reader's life.",
  "discovery_questions": [
    { "category": "Honesty | Faith | Purpose | etc.", "question": "string" }
  ],
  "prayer": {
    "title": "Prayer title",
    "content": "Prayer text. First person. Pastoral. Honest."
  }
}
```

#### `completion`
Final card. Repeats the key verse + one reflection prompt.
```json
{
  "order": 15,
  "type": "completion",
  "mood": "string",
  "image_url": "filename.png",
  "completion_verse": {
    "reference": "Book ch:v",
    "text": "Full verse",
    "bible_version": "RVR1960"
  },
  "reflection_prompt": "One question.",
  "celebration_type": "gentle_light | burst | ripple | etc."
}
```

#### `interactive_moment` (optional)
Pause for personal naming/reflection. Used sparingly.
```json
{
  "order": 9,
  "type": "interactive_moment",
  "icon": "emoji",
  "image_url": "filename.png",
  "title": "string",
  "subtitle": "string",
  "reflection_prompt": "string"
}
```

---

## Mood Palette

Every card requires a `mood` field. Use only values from this palette — they map to background colors in the app via `EncounterMoodTheme.fromMood()`. Choosing the right mood creates a visual arc the reader feels without noticing.

| Mood | Color | Use for |
|------|-------|---------|
| `storm` | `#0d1a2e` | Danger, external conflict, journey into the unknown |
| `tense` | `#0f1828` | Inner conflict, anticipation, unresolved situation |
| `mysterious` | `#0a0e1a` | Hidden meaning, theological depth, what lies beneath |
| `awe` | `#0a1220` | Divine presence, revelation, overwhelming encounter |
| `falling` | `#040810` | Despair, isolation, darkness before transformation |
| `grace` | `#12100a` | Forgiveness, restoration, unmerited gift |
| `peace` | `#0a120e` | Resolution, acceptance, rest after the encounter |
| `intense` | `#1a0a0e` | Confrontation, urgency, burning conviction |

> **Rule:** Never invent new mood values. If a card needs a mood not in this list, propose it first so it can be added to both the skill and `EncounterMoodTheme`.

---

## Image Prompts

Image prompts are delivered as a **separate JSON file** alongside the encounter file:
`<character_slug>_image_prompts.json` (e.g. `mary_garden_image_prompts.json`).

Every card that shows the character requires:
- `image_url` — filename: `<character_slug>_<scene_slug>.png` (always in English)
- `prompt` — AI generation prompt (always in English), **character-first** (see below)

### Image Prompts JSON structure

```json
{
  "encounter_id": "<id>",
  "character": "English character name",
  "master_character_prompt": "Full character description (see below)",
  "intro_image": {
    "filename": "<character>_intro.png",
    "prompt": "Character description first, then scene..."
  },
  "card_prompts": [
    {
      "order": 1,
      "image_url": "filename.png",
      "mood": "matches card mood",
      "shot_type": "wide establishing | medium two-figure | close-up portrait | object/still life | action/movement | wide departure",
      "prompt": "Character description first, then scene..."
    }
  ]
}
```

### Master Character Prompt

Write this **once** per encounter before writing any card prompts.
It locks the character's visual identity across all cards.
Include: age range, build, skin tone, hair, clothing (fabric, color, condition), style anchor.

```
A [age, build, skin tone, hair, expression baseline],
[clothing: fabric, color, condition, details].
Painterly warm 2D illustration style, Mediterranean palette,
ochre and sandstone tones, cinematic lighting.
Character reference sheet, full body and face close-up.
```

Store this as the `master_character_prompt` field in the image prompts JSON.

### Using the master character in every prompt (non-negotiable)

**Every card prompt where the character appears MUST open with the master character description
as its first paragraph.** Then follow with the scene-specific content. This ensures visual
consistency across all AI-generated images — the character looks like the SAME person in every card.

For object/still-life shots (no people), skip the character paragraph.
For shots where the character is distant/tiny, use a shortened version but keep the key visual
anchors (skin tone, hair, clothing color).

**Pattern:**
```
"prompt": "<master character description, adapted to the shot>. <Scene description: shot type,
setting, time of day, emotion, composition>. <Style anchor>."
```

### Intro Image Prompt
One cover image per encounter for the index (`intro_image` field).
Wide or atmospheric — establishes the world before the story begins.
Character may appear small or from behind. Still opens with character description. No text.

### Card Image Prompts

**Style anchor (end every prompt with this):**
> Painterly warm 2D illustration, Mediterranean palette, ochre and sandstone tones, cinematic lighting, no text.

**Rules:**
- **Character-first**: open with the master character description (adapted to the shot), then describe the scene
- Describe scene, time of day, setting, emotion, what's physically visible
- Never say "see character prompt" or "same character as above" — each prompt must be fully self-contained
- Vary shot distance: wide establishing shots, medium interaction shots, intimate close-ups, pure metaphor/object shots (no people)
- Jesus appears in soft focus, partial silhouette, or from behind. Never the visual center
- No halos. No supernatural glow. No photorealism
- Mood in the prompt must match the card's `mood` field
- Length: 3-5 sentences per prompt

**Shot variety to aim for across 11-15 cards:**
| Shot type | Purpose |
|-----------|---------|
| Wide establishing | Opens world, sets scale |
| Medium two-figure | Interaction, tension |
| Close-up portrait | Emotional truth, inner state |
| Object/still life | Pure metaphor, no people |
| Action/movement | Transformation, decision moment |
| Wide departure | After the encounter — changed |

**When Jesus appears (Ben-Hur style — non-negotiable):**
- **His face is NEVER visible.** Always from behind, partial silhouette, over-the-shoulder, or obscured
- A **subtle warm glow of glory** emanates from his form — this is the only supernatural element allowed
- Never the visual center — the story belongs to the biblical character
- Describe him as "a man in a simple first-century tunic, seen from behind, face never visible, a subtle warm glow of glory around his form"
- No halos. No full-body supernatural glow. No face. No eyes. No frontal view. Ever.

**Example (from Woman at the Well, card 2):**
```
"image_prompt": "A Samaritan woman — dark olive skin, dark pulled-back hair with loose strands, worn dusty terracotta tunic, clay water jar on her shoulder — approaches in the far background, slowing her step. In the foreground a man in a simple first-century tunic sits on the stone well's edge, head slightly bowed, tired from travel, not looking up. The tension is in the space between them. Painterly warm 2D, Mediterranean palette, warm dust tones, deep shadow under the well's edge, cinematic."
```

**Example object shot (card 4):**
```
"image_prompt": "Extreme close-up looking down into a stone well. Dark water far below. A single drop has just fallen — one perfect ripple expanding outward from the center. Rough ancient stone surrounds the water. No people. Pure metaphor. Painterly warm 2D illustration, deep indigo water, silver ripple light, black stone, Mediterranean palette."
```

**Close-up face-to-face encounter shot (character + Jesus sharing depth of field):**

When the character is close enough to Jesus (or another key figure) that both share the frame in a
close-up portrait — not a wide/medium shot — use this three-part structure. It consistently
outperforms single-note emotional portraits:

1. **Anchored gaze** — the character's eyes are fixed on a specific point (Jesus, the stranger, the
   other figure), not "distant" or "downward" or "upward" in isolation. Give the eyes an external
   target within the scene.
2. **Second figure sharing depth of field** — Jesus (or the companion) appears soft-focus/out-of-focus
   in the same frame, not absent from close-ups entirely. This forces a two-plane composition (sharp
   subject + blurred figure behind/beside) that reads as cinematic rather than flat portraiture.
3. **Two-layer emotional instruction, not one** — describe a contradiction or tension in the
   expression (e.g. "eyes open and attentive but looking without truly seeing"), not a single
   emotional note (e.g. just "exhaustion" or just "recognition"). The ambiguity produces more
   nuanced expressions than a flat single-emotion prompt.

Reserve this structure for close-up portraits where Jesus or another key figure is physically near
the character in the scene — not for solitary emotional beats where the character is alone in frame.

**Example (Emmaus, card 4 — "eyes veiled"):**
```
"image_prompt": "Close-up portrait of a man in his mid-forties, square weathered face, deep-set brown
eyes fixed on a nearby stranger with a puzzled, searching expression, full graying beard, faded
olive-green tunic. His eyes are open and attentive but something in his gaze suggests he is looking
without truly seeing. Soft out-of-focus figure of a man in a simple tunic walking just beside him,
face never visible. Painterly warm 2D illustration, Mediterranean palette, dim dusty light,
cinematic, no text."
```

---

## Editorial Rules (non-negotiable)

| Rule | Detail |
|------|--------|
| Build on affirmation, not negation | See detailed rule below |
| No excess of em dashes | Use sparingly — one per paragraph at most |
| No inflated drama or marketing cliches | Avoid "unprecedented", "extraordinary", "awe-inspiring", "that changes everything", "like never before", "words cannot describe", "something shifted" as filler |
| No casual/colloquial register | Avoid phrases like "sin rodeos", "menciona también lo otro", or any filler that reads as spoken slang — it breaks the devotional/narrative tone even when the underlying claim is accurate |
| No theological jargon without explanation | If using a term, unpack it in plain language |
| Pastoral tone always | God loves, transforms, and uses people in their imperfection |
| Scripture: complete verses | Never truncate. Use exact RVR1960 text including correct capitalization in the verse formats |
| RVR1960 capitalization | Respect the original: "Dios", "Señor", pronoun case as in source |
| Theological insight | Include Greek/Hebrew word studies where they illuminate meaning |
| Card count | 11-15 cards per encounter. ~10 min read. |
| Arc | Always: setup → scripture → character psychology → theology → application → completion |

### Affirmation over negation (non-negotiable)

The encounter must be built on **what Scripture says, what God does, what the character lives** — not on what things are NOT. Avoid the pattern of defining through negation ("No era X. Era Y." / "No dijo X. Dijo Y."). State what it IS directly.

This is a biblical content principle: we proclaim what God has done, not a catalog of what He hasn't.

**Examples:**

| Negation pattern (avoid) | Affirmative rewrite (use) |
|--------------------------|---------------------------|
| "No era una objeción. Era la pregunta más honesta." | "Era la pregunta más honesta que alguien podía hacer." |
| "No dijo: confiemos en Dios. No dijo: todo saldrá bien. Dijo: Vamos también nosotros." | "Una sola frase: Vamos también nosotros, para que muramos con él." |
| "No fue una reprimenda. Fue una invitación." | "Fue una invitación." |
| "Las heridas no eran un defecto. Eran parte de ella." | "Las heridas eran parte de la resurrección." |
| "Jesús no esperó a que Tomás lo buscara. Vino a él." | "Jesús vino a él." |
| "No tocó la puerta. No pidió permiso. Entró..." | "Entró en el espacio donde el miedo los tenía cautivos..." |

**When negation is acceptable:**
- When quoting Scripture that uses negation (e.g. "no creeré" — Thomas's own words)
- When the biblical text itself describes an absence (e.g. "no estaba con ellos" — John 20:24)
- Once per card maximum for rhetorical contrast, never in chains of "No X. No Y. No Z."

---

## Typical card arc (11-card minimum)

| Position | Type |
|----------|------|
| 1 | `cinematic_scene` — world/context |
| 2 | `scripture_moment` — key passage |
| 3 | `character_moment` — who is this person |
| 4 | `cinematic_scene` — narrative turn |
| 5 | `theological_depth` — first insight |
| 6 | `scripture_moment` or `cinematic_scene` |
| 7 | `cinematic_scene` — climax |
| 8 | `character_moment` — inner transformation |
| 9 | `theological_depth` or `interactive_moment` |
| 10 | `discovery_activation` |
| 11+ | `completion` (always last) |

For 15-card encounters, add more `cinematic_scene` and `theological_depth` cards to deepen the arc.

---

## Language handling

- **Default language: Spanish (es), bible_version: RVR1960**
- All prose, titles, subtitles, prayers, and reflection questions in Spanish
- English translation only after Spanish version is reviewed and approved
- When translating to English: switch `language` to `en`, `bible_version` to `KJV`, translate all text fields
- `image_url` and `image_prompt` fields remain in English regardless of language

---

## Naming conventions

| Field | Convention |
|-------|-----------|
| `id` | `<character>_<lang>_<NNN>` e.g. `woman_well_es_001` ENGLISH name + language +001 always|
| `image_url` | `<character>_<scene>.png` e.g. `mujer_pozo_llegada.png` |
| `version` | Start at `"1.0"`, increment on approved revisions |
| Output filename | Same as `id` + `.json` |

