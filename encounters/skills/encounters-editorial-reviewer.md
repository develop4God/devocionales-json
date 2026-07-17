---
name: encounters-editorial-reviewer
description: >
  Use this skill whenever reviewing, auditing, or refining existing Encounter JSON cards.
  Triggers: "review card X", "let's refine the encounter", "check this card", "revise the narrative",
  "session de revision", or any request to improve already-drafted Encounter content.
  Always load this skill before touching any card in a review session.
  This skill is a COMPANION to encounters-content-creator — load both when needed.
---

# Encounters Editorial Reviewer

A card-by-card review framework for Encounter JSON files. Built from the Saulo (Acts 9)
editorial session — June 2026. Every rule here was earned from real mistakes caught in review.

---

## BEFORE ANY NEW FILE — GATE 0: ORAR PRIMERO

Before starting a new Encounter file (or before drafting the `prayer.content` of an
existing one — see Rule 12.1), the encounter is prayed over first. Giovanni puts it
in the hands of the Jesus this encounter speaks about, with respect and love, and
asks for the Holy Spirit's guidance before any card or prayer is drafted. This is not
a formality to log — it is the actual origin of the file. Claude does not begin
generating an encounter, nor its `prayer.content`, ahead of this. If asked to begin
before this has happened, Claude says so plainly and waits.

---

## BEFORE YOU START

1. Sparse-clone the file from GitHub (load sparse-clone skill)
2. Read ALL cards first — understand the full arc before touching anything
3. Note card types, moods, verse references — check for gaps or overlaps
4. Only then begin card-by-card review

**If this review is happening inside a Claude chat session** (not a subagent with file
tools), convert the encounter JSON to Markdown first with
`encounters/encounters_scripts/json_to_md.py encode <file.json>` before reading it —
raw JSON with deep nesting is harder to read in chat than the flat, field-labeled
Markdown output. Only ever read/edit the `.json` as the source of truth; the `.md` is a
disposable reading aid. After any edit to the JSON, re-run
`json_to_md.py verify <file.json>` to confirm no field was dropped or corrupted, and
regenerate the `.md` (or discard it) rather than editing the `.md` directly.

---

## THE CARDINAL RULES

These are non-negotiable. They override everything else.

### 1. Never add what the text does not say
The biblical text is the authority. If a detail is not explicitly stated in Scripture,
it cannot be presented as fact — not even if it seems logical or likely.

**Wrong:** "Ananías entró con miedo" — the text does not say he was afraid.
**Right:** "Ananías respondió con honestidad" — the text says he expressed concern (v.13).

**Wrong:** "Saulo reconoció a Ananías cuando entró" — the text does not say this.
**Right:** Only state what the text affirms.

If something is an inference, frame it as such — or leave it out entirely.

---

### 2. No negations to build arguments
Do not use negative constructions to create contrast or depth.
Say what IS true, not what is NOT true.

**Wrong:**
- "No fue gradual."
- "No hubo proceso."
- "No entró a convertir a nadie."
- "No improvisó las palabras."
- "No porque no tuviera miedo."

**Right:** State the positive reality directly.
- "Fue inmediato."
- "Ananías entró porque el Señor ya había hecho su obra."
- "Ananías dijo exactamente lo que el Señor le había dado."

**Exception:** A single negation is acceptable when it directly quotes or paraphrases
the biblical text itself.

---

### 3. No marketing clichés or hollow phrases
These phrases sound deep but say nothing. Flag and remove:
- "lo que todo lo cambia" / "that changes everything"
- "no hay forma de rodear eso"
- "El hombre que salió era el mismo. Y no era el mismo en absoluto."
- "unprecedented", "extraordinary", "awe-inspiring" as filler
- Any phrase that tries to sound profound but could mean anything

**Test:** If you removed the sentence, would the paragraph lose real content? If not, cut it.

---

### 4. Every card must add something new
Before approving any card, ask: does this card reveal something the previous cards did not?

If the answer is no — merge it, rewrite it, or eliminate it.
Overlap between cards is waste. Revelation should never repeat.

---

### 5. Greek and Hebrew terms must be explained inline
If a Greek or Hebrew word appears, explain it in the same sentence or the next one.
Never assume the reader knows the term. Never leave it unexplained for a later card.

**Format:**
> "...lo que el texto griego llama ὅραμα (horama), una visión que Dios pone directamente
> en la mente, sin necesidad de los ojos del cuerpo."

**Format for proper names:**
> "Σαούλ (Shaul) — el nombre de Saulo en arameo, no en griego como era común."

Both the Greek/Hebrew characters AND the transliteration must appear.

---

### 6. Language must be accessible to ALL readers
The reader may be:
- An elderly person with limited education
- A new believer in a developing country
- Someone reading in their second language

Test every sentence: would a grandmother in rural Latin America understand this?

**Flag:**
- Academic vocabulary
- Theological jargon without explanation
- Idioms that don't translate across Spanish-speaking regions
- Sentences longer than 3 clauses

---

### 7. No em dashes in excess
Em dashes (—) are allowed but should be used sparingly. One per paragraph maximum.
Never use them as a stylistic default. If a sentence needs an em dash to make sense,
rewrite the sentence.

---

### 8. Spanish capitalization rules
- Titles: only first word capitalized. "El río que ya cruzó antes" ✓ — "El Río Que Ya Cruzó" ✗
- Section headers (emoji + text): same rule. "📍 Por qué ese vado en particular:" ✓
- Proper nouns always capitalized: Dios, Señor, Espíritu Santo, Saulo, Ananías

---

### 9. Per-language register gate (non-Spanish files) — MANDATORY
A card can pass Rules 1-8 and still use the wrong grammatical register for its
language — check for that too before approving. See `encounters_translator_skill.md`
§ "MANDATORY GATE: Per-Language Register Rules" for the rule per language (e.g. Hindi
requires respectful plural verbs for Jesus, not just plural pronouns — "यीशु आया" is
wrong, "यीशु आए" is right). Does not apply to quoted verse fields, which follow the
cited Bible version's own grammar.

---

### 10. Post-fix reverse validation & pattern sweep — MANDATORY
Whenever a review session (yours or a native-speaker critic's) results in file edits,
do not report the review done right after applying the fixes. See
`encounters_translator_SKILL.md` § "MANDATORY GATE: Post-Fix Reverse Validation &
Pattern Sweep" and run that full procedure: re-read the complete file, verify each edit
still matches its card's `revelation_key` and scripture reference, sweep the whole file
for the same error pattern the critic just found, and validate JSON. A grammatically
correct fix that quietly guts the sentence's meaning is a worse outcome than the
original error — it looks resolved but isn't.

---

### 11. What a `revelation_key` is (and isn't) — analyze before writing
A `revelation_key` is not a summary of the card's `content`/`narrative`, not a poetic
flourish, and not a place to cram extra biblical content just because it's available.
It is the single sharpened "aha" specific to *this card's moment* — distinct from what
the narrative already said, and without spoiling what a later card will reveal.

Before writing or approving one, answer explicitly: **what is this specific card trying
to make the reader take away, and is that different from what neighboring cards already
carry or will carry?** Don't write text "a lo loco" (recklessly, without this analysis).
If a following card already owns the heavy theological weight of a moment (e.g. the full
symbolism of bread-breaking), the current card's `revelation_key` doesn't need to carry
that weight too — it should capture only what belongs to its own moment. This is Rule 4
applied specifically to the `revelation_key` field, not just to whole cards.

**Concrete case (2026-07-16, Emmaus, "Al partir el pan" card):** first draft closed with
"no en una señal espectacular" — technically accurate but (1) a negation pattern already
banned by Rule 2, and (2) it flattened everything already established about the
theological weight of bread-breaking (same verb pattern as the Last Supper and the
feeding of the 5,000 — a weight the *following* card owns). The real "aha" for *this*
card was narrower: recognition came through something intimate Cleofas already knew of
Jesus, not through a new miracle. Final: "Cleofas no reconoce a Jesús por un milagro ante
sus ojos, sino por algo íntimo que ya conocía de él."

---

### 12. The closing prayer must arc across the whole encounter
The `discovery_activation` card's `prayer.content` is not a generic devotional closer —
it must recognizably touch the encounter's actual arc, with concrete anchors from the
story, the same way the rest of the encounter does. A prayer that only echoes the
surface theme (e.g. "help me recognize you") while skipping the encounter's distinct
turning points reads as interchangeable with any other encounter's prayer — it should not.

Verified against the corpus (`thomas_es_001.json`, `nicodemus_es_001.json`): both
prayers recognizably recorre the full arc with specific anchors — Thomas's prayer
includes "Señor mío y Dios mío" (the text's own climax) and the detail of the "puerta
cerrada"; Nicodemus's includes the serpent in the wilderness (Juan 3:14) and the
secret-to-public arc (Juan 19:39). Neither is a vague summary — both are traceable,
almost line by line, to specific cards earlier in the same file.

**Concrete case (2026-07-16, Emmaus):** first draft only touched 2-3 of the ~6 major
beats established across the cards (presence unrecognized, ordinary bread). Missing:
being given space to voice grief before revelation (cards 4-5), the Scriptures opening
until the heart burned (cards 7, 11), and the urge to run and tell others after
recognizing him (cards 12-13). Rewritten to touch all of these with concrete anchors
tied to the encounter's own language ("hasta que mi corazón arda, como ardió el de
Cleofas en el camino").

**How to apply:** before approving a `prayer.content`, list the 4-6 major turning
points the encounter's cards established, and check the prayer touches most of them
with a concrete anchor (an image, a verb, a phrase) rather than a generic paraphrase.

---

### 12.1. The `prayer.content` must be prayed before it is written — not assembled from beats

Touching the right beats (Rule 12) is necessary but not sufficient. A prayer can hit
every anchor correctly and still read as a recipe — a checklist of turning points
stitched together from outside the story — instead of one human voice speaking to God
from inside the last moment of the encounter.

**What actually distinguishes a living prayer from a recipe:**

- **It speaks from inside the moment, not about it.** "La certeza que sintió Cleofas"
  describes the character from outside. "Permíteme llevar todo esto que reconozco de
  ti a otros" is spoken by someone who already *is* Cleofas in that instant — no
  comparison, no distance.
- **It carries one thing that matters most, not several peers in a row.** A prayer
  that gives equal weight to four turning points in sequence ("Gracias porque...
  Abre... Ábreme... Y cuando...") is reciting a list. A prayer built on a single
  thing the reader needs to ask for — with the other anchors supporting it rather
  than each getting their own clause — reads as one plea.
- **It could not have been written by someone who only read the cards.** If the
  prayer could be assembled purely from the encounter's text without the writer
  first sitting with the scene as their own moment before God, it is a recipe.
- **It gives itself, it doesn't explain itself.** A prayer that teaches ("esto
  significa que...") is instructing the reader. A prayer that asks ("dame,
  permíteme, llévame") is surrendering. Prayers should ask, not explain.

**Concrete case (2026-07-17, Emmaus):** a first rewrite touched all the right beats
(grief named, Scriptures opening, heart burning, urgency to tell others) and passed
every gate above — and still read as assembled, because it spoke *about* Cleofas'
experience by comparison ("como Cleofas...", "la misma certeza que sintió Cleofas")
rather than from inside it. The version that worked came only after Giovanni prayed
the encounter himself first, then wrote from inside that same moment: "Permíteme
llevar todo esto que reconozco de ti a otros, que corra a darles las buenas nuevas."
One clause, one voice, no comparison — because it was prayed before it was written.

**Gate before writing (mandatory, before drafting any `prayer.content` — see also
"BEFORE ANY NEW FILE" below):** Claude does not draft the first version of a
`prayer.content`. Giovanni prays the encounter first, puts it in Jesus' hands, and
writes (or dictates) what comes from that — spoken with respect and love for Jesus,
under the Holy Spirit's guidance, not assembled by Claude from the cards' beats.
Claude's role at that point is to check the result against Rule 12 (does it touch
the encounter's real turning points) and the language gates (2, 3, 6, 7, 8) — never
to originate the first draft of the prayer's core plea. If Claude is asked to
propose prayer language before this has happened, it should say so and ask for the
prayed version first, rather than producing a draft to be corrected afterward.

---

### 13. `discovery_questions` must ask the encounter's central "aha," not a generic theme
Before writing or approving the three `discovery_questions`, identify what the reader
should take away from the *entire* encounter — not a surface topic like "notice God's
presence," but the sharpest, most specific insight the whole arc builds toward. Each
question should (1) open with a concrete anchor from the story (an action, a verse, a
specific moment already established in the cards) and (2) turn that anchor toward the
reader with a question that could only belong to *this* encounter, not a generic
devotional prompt swappable across stories.

**Never frame God's absence as a live possibility to ask about**, even rhetorically
inside a question that "resolves" it in the same sentence (e.g. "¿sientes que Dios te
abandonó, cuando en realidad...?"). This states something Scripture explicitly denies
(Hebreos 13:5, Mateo 28:20) as if it were a real option the reader must consider — the
same category of harm as "amor sin respuesta" or "esperanza rota" (Rule 2's negation
examples): it plants the false idea rather than just naming the false *feeling*. If the
question is about a felt sense of absence, name it as a feeling ("has sentido la
ausencia"), never as something God may have actually done.

**Concrete case (2026-07-16, Emmaus):** first draft asked generic, swappable questions
("¿qué gesto familiar de Dios podrías estar pasando por alto?") including one framing
divine abandonment as posible. Rewritten after identifying the encounter's actual
central takeaway — recognition can come through the Word before the eyes, and once it
comes, it compels urgent testimony, not passive noticing — with each question anchored
to a specific beat (Cleofas's honesty with a stranger who was Jesus, the heart burning
before the eyes opened, running the same night rather than waiting for morning).

---

## CARD-BY-CARD REVIEW PROTOCOL

For each card, check in this order:

### A. Structural check
- [ ] Has correct `type`, `mood`, `order`
- [ ] `verse_reference` matches `verse_text` (no partial verses)
- [ ] `verse_text` is exact RVR1960 text — not paraphrased
- [ ] `image_url` follows naming convention
- [ ] `revelation_key` is one sentence, theologically precise, and passes Rule 11 (its own moment's "aha", not a summary/repeat)
- [ ] `scripture_connections` present if reflection cites another passage

### B. Content check
- [ ] No negations used to build arguments (Rule 2)
- [ ] No marketing clichés or hollow phrases (Rule 3)
- [ ] Nothing added that the biblical text does not say (Rule 1)
- [ ] Greek/Hebrew terms explained inline (Rule 5)
- [ ] Language accessible to all readers (Rule 6)
- [ ] Card adds something new vs. adjacent cards (Rule 4)

### C. Theological check
- [ ] Reflections are grounded in the biblical text
- [ ] Inferences are framed as inferences, not stated as fact
- [ ] Greek/Hebrew word studies used where they illuminate meaning
- [ ] Cross-references in `scripture_connections` are accurate and complete

### D. Arc check (after all cards reviewed)
- [ ] No two adjacent cards cover the same ground
- [ ] The emotional/theological arc progresses forward
- [ ] Card count is appropriate (consider splitting if a card is overloaded)
- [ ] Hints introduced in earlier cards are fulfilled in later cards

---

## SPLITTING CARDS

Split a card when it contains more than one distinct theological layer that each deserve
their own space for the reader to absorb.

**Saulo session example:**
Card 10 originally contained: escamas + blepō/anablepsen + Juan 3:5 + comunidad como instrumento.
Split into:
- Card 10: escamas, blepō → anablepsen, los dos lugares (físico y espiritual)
- Card 11: Juan 3:5 cumplido, agua y Espíritu, entró como enemigo salió como hijo

**Rule:** Split when the material is too rich to cut, and each half stands on its own.
Never split just to add card count.

---

## HANDLING THEOLOGICAL DISCOVERIES MID-SESSION

Sometimes a review session surfaces a theological insight that changes a card's direction.
When this happens:

1. **Stop and explore** — do not rush to write. The insight may reshape multiple cards.
2. **Search the web** if the insight involves a Greek/Hebrew term, exegetical detail,
   or cross-reference you are not certain about. Verify before writing.
3. **Identify the scope** — does this insight affect only this card, or adjacent cards too?
4. **Propose the rewrite** — present the full revised text for approval before writing to file.
5. **Write only after approval** — never write speculatively.

---

## COMMIT PROTOCOL

After each approved set of changes:

```bash
git add <filepath>
git commit -m "feat(<lang>): <brief description of what changed>"
# Example: "feat(es): refine cards 8-11 — horama, Shaul/adelphos, escamas, Juan 3:5"
```

Present the file after each commit using `present_files`.

---

## EDITORIAL RULES INHERITED FROM CONTENT-CREATOR SKILL

These rules apply in review sessions as well:

| Rule | Detail |
|------|--------|
| Pastoral tone always | God loves, transforms, uses people in their imperfection |
| No inflated drama | No "unprecedented", "extraordinary", "awe-inspiring" as filler |
| No theological jargon without explanation | Unpack every term in plain language |
| Scripture: complete verses | Never truncate. Exact RVR1960 text. |
| RVR1960 capitalization | Respect the original: "Dios", "Señor", pronoun case |
| Jesus in Saulo encounter | Appears only as light/radiance/presence — never human form |
| Rhetorical questions | Open reflection with questions, not assertions |

---

## LESSONS FROM SAULO (Acts 9) — June 2026

Key discoveries that shaped this skill:

- **ὅραμα (horama)**: Saulo received a supernatural vision during prayer while physically blind.
  This is not metaphor — it is the same Greek term Luke uses for Moses and the burning bush.
  God showed Saulo the face of Ananías before Ananías arrived.

- **Σαούλ (Shaul)**: Ananías called him by his Aramaic name, not Greek. Luke preserved this form.
  The same name Jesus used on the road. An identification, not just a greeting.

- **ἀδελφέ (adelphos)**: "Brother" — from the same womb, same parents. A declaration of
  family membership before any miracle, before any words from Saulo.

- **blepō → ἀνέβλεψεν (anablepsen)**: The blindness used blepō (physical sight function).
  The restoration uses anablepsen — to see again, to look up. Not merely restoring what was lost.

- **Juan 3:5 cumplido**: In that room, Saulo was born of water (baptism) and Spirit (filled with
  the Holy Spirit) simultaneously — exactly as Jesus described to Nicodemus.

- **Ananías as conduit of Christ**: His words were not his own. The Lord told him exactly what
  to say. Christ spoke through him — the same voice that stopped Saulo on the road.

- **The Messiah's signature**: Healing blindness belongs uniquely to the Messiah in all of
  Scripture. Saulo, as a Pharisee, knew this. The healing was not just restoration — it was proof.

These insights are canon for the Saulo encounter and should inform any future revision.
