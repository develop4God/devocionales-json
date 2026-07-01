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

## BEFORE YOU START

1. Sparse-clone the file from GitHub (load sparse-clone skill)
2. Read ALL cards first — understand the full arc before touching anything
3. Note card types, moods, verse references — check for gaps or overlaps
4. Only then begin card-by-card review

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

## CARD-BY-CARD REVIEW PROTOCOL

For each card, check in this order:

### A. Structural check
- [ ] Has correct `type`, `mood`, `order`
- [ ] `verse_reference` matches `verse_text` (no partial verses)
- [ ] `verse_text` is exact RVR1960 text — not paraphrased
- [ ] `image_url` follows naming convention
- [ ] `revelation_key` is one sentence, theologically precise
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
