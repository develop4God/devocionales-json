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

If the user provides all of this upfront, skip to step 2.

---

### 2. Draft the encounter IN-CHAT (no file yet)

Generate the full JSON structure directly in the chat as a code block.
Do NOT save a file until the user approves. This is the token-efficient path.

Use the envelope + card schema below.

---

### 3. User reviews → iterate in-chat

Make all edits to the in-chat JSON until the user approves. Only then proceed to step 4.

---

### 4. Save the approved JSON file

Once the user says it's approved, save to `/mnt/user-data/outputs/<id>.json`
and use `present_files` to deliver it.

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
- `image_prompt` (string — AI generation prompt, see Image Prompt section)
- `revelation_key` (string — the one-sentence theological insight, optional on some types)

---

#### `cinematic_scene`
Opens or transitions a narrative beat. Immersive, present-tense prose.
```json
{
  "order": 1,
  "type": "cinematic_scene",
  "mood": "string",
  "image_url": "filename.png",
  "image_prompt": "...",
  "title": "Short evocative title.",
  "narrative": "Prose paragraph(s). No em dashes. Pastoral tone.",
  "ambient_sound": "crowd_distant | wind | water | silence | fire | etc.",
  "haptic": null,
  "verse_overlay": "Optional short verse quote (if the scene has a verse anchor)",
  "revelation_key": "One sentence."
}
```

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
  "image_prompt": "...",
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
  "image_prompt": "...",
  "title": "string",
  "subtitle": "string",
  "content": "Prose. May include emphasis markers like 🔑 or ⚠️ for key phrases.",
  "revelation_key": "One sentence."
}
```

#### `theological_depth`
Exegetical insight — Greek/Hebrew word studies, cultural context, cross-references.
```json
{
  "order": 5,
  "type": "theological_depth",
  "mood": "string",
  "image_url": "filename.png",
  "image_prompt": "...",
  "title": "string",
  "subtitle": "string",
  "content": "Prose with emoji markers for key insights. Greek/Hebrew in transliteration.",
  "revelation_key": "One sentence.",
  "scripture_connections": [
    { "reference": "Book ch:v", "text": "Full verse text" }
  ]
}
```

#### `discovery_activation`
Application card — 3 reflection questions + closing prayer. Always near the end.
```json
{
  "order": 14,
  "type": "discovery_activation",
  "image_url": "filename.png",
  "image_prompt": "...",
  "icon": "🙏",
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
  "image_prompt": "...",
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
  "image_prompt": "...",
  "title": "string",
  "subtitle": "string",
  "reflection_prompt": "string"
}
```

---

## Image Prompts

Every card requires both:
- `image_url` — filename: `<character_slug>_<scene_slug>.png` (always in English)
- `image_prompt` — AI generation prompt (always in English)

Plus, every new encounter requires two additional image assets:

### Master Character Prompt
Write this once per encounter before writing any card prompts.
It locks the character's visual identity across all cards.
Include: age range, skin tone, hair, clothing, style anchor.
Store it as a comment block at the top of the image prompts document.

```
// MASTER CHARACTER PROMPT — <Character Name>
// Use this first to lock the character before generating any card image.
A [character description: age, build, skin tone, hair, expression baseline],
[clothing: fabric, color, condition, details].
Painterly warm 2D illustration style, Mediterranean palette,
ochre and sandstone tones, cinematic lighting.
Character reference sheet, full body and face close-up.
```

### Intro Image Prompt
One cover image per encounter for the index (`intro_image` field).
Wide or atmospheric — establishes the world before the story begins.
Character may appear small or from behind. No text.

### Card Image Prompts

**Style anchor (use in every prompt):**
> Painterly warm 2D illustration, Mediterranean palette, ochre and sandstone tones, cinematic lighting, no text.

**Rules:**
- Describe scene, time of day, setting, emotion, what's physically visible
- Include character description inline in every card prompt — do not rely on "see character prompt." Each prompt must be self-contained for generation
- Vary shot distance: wide establishing shots, medium interaction shots, intimate close-ups, pure metaphor/object shots (no people)
- Jesus appears in soft focus, partial silhouette, or from behind. Never the visual center
- No halos. No supernatural glow. No photorealism
- The character must feel like the SAME person across all cards — repeat key visual anchors (skin tone, hair, clothing color) in every prompt where they appear
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

**When Jesus appears:**
- Soft focus or partial silhouette
- Never the visual center — the story belongs to the biblical character
- Describe him as "a man in a simple first-century tunic" — no supernatural markers

**Example (from Woman at the Well, card 2):**
```
"image_prompt": "A Samaritan woman — dark olive skin, dark pulled-back hair with loose strands, worn dusty terracotta tunic, clay water jar on her shoulder — approaches in the far background, slowing her step. In the foreground a man in a simple first-century tunic sits on the stone well's edge, head slightly bowed, tired from travel, not looking up. The tension is in the space between them. Painterly warm 2D, Mediterranean palette, warm dust tones, deep shadow under the well's edge, cinematic."
```

**Example object shot (card 4):**
```
"image_prompt": "Extreme close-up looking down into a stone well. Dark water far below. A single drop has just fallen — one perfect ripple expanding outward from the center. Rough ancient stone surrounds the water. No people. Pure metaphor. Painterly warm 2D illustration, deep indigo water, silver ripple light, black stone, Mediterranean palette."
```

---

## Editorial Rules (non-negotiable)

| Rule | Detail |
|------|--------|
| No excess of em dashes |
| No inflated drama or marketing cliches| Avoid "unprecedented", "extraordinary", "awe-inspiring, that changes everthing, etc as filler |
| No theological jargon without explanation | If using a term, unpack it in plain language |
| Pastoral tone always | God loves, transforms, and uses people in their imperfection |
| Scripture: complete verses | Never truncate. Use exact RVR1960 text including correct capitalization in the verse formats|
| RVR1960 capitalization | Respect the original: "Dios", "Señor", pronoun case as in source |
| Theological insight | Include Greek/Hebrew word studies where they illuminate meaning |
| Card count | 11-15 cards per encounter. ~10 min read. |
| Arc | Always: setup → scripture → character psychology → theology → application → completion |

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

