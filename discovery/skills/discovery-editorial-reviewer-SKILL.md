---
name: discovery-studies-editorial-reviewer
description: "Use this skill whenever reviewing, auditing, or refining existing Discovery Bible study JSON cards. Triggers: \"review card X\", \"let's refine this discovery study\", \"check this card\", \"revise the content\", \"session de revisión\", \"veo un error en el card X\", or any request to improve already-drafted Discovery study content. Always load this skill before touching any card in a review session. This skill is a COMPANION to discovery-study-generator — load both when needed."
---

---
name: discovery-studies-editorial-reviewer
description: >
  Use this skill whenever reviewing, auditing, or refining existing Discovery
  Bible study JSON cards. Triggers: "review card X", "let's refine this
  discovery study", "check this card", "revise the content", "session de
  revisión", "veo un error en el card X", or any request to improve
  already-drafted Discovery study content. Always load this skill before
  touching any card in a review session. This skill is a COMPANION to
  discovery-study-generator — load both when needed.
---

# Discovery Studies Editorial Reviewer

A card-by-card review framework for Discovery Bible study JSON files. Built
from the "Morir al yo" (Mateo 19, dying_to_self_001) editorial session —
July 2026. Every rule here was earned from a real mistake caught in review,
not written speculatively.

---

## BEFORE YOU START

1. Load `discovery-study-generator` alongside this skill — it defines the
   JSON schema, card types, and top-level structure this review operates on.
2. If the file lives in the repo, sparse-clone it first (load sparse-clone +
   sparse-clone-devocionales-json if applicable).
3. Read ALL cards first — understand the full arc before touching anything.
4. Note card types, verse references, Greek/Hebrew terms — check for gaps,
   overlaps, or missing `scripture_references`.
5. Only then begin card-by-card review.

---

## THE CARDINAL RULES

These are non-negotiable. They override everything else, including a
request to move faster or a prior card that already shipped this way.

### 1. Never state what the biblical text does not say
The biblical text is the authority. No emotional, physical, or narrative
detail may be added beyond what the text states or the original language
directly supports — even when the addition feels natural, evocative, or
"safe."

**Wrong:** "...y se fue con el corazón roto." (Mateo 19:22 says only that he
went away λυπούμενος — grieved/sad. "Corazón roto" is an invented
escalation, not a translation or a reasonable inference.)
**Right:** "...y se fue triste." — matches what the text and the Greek word
actually say.

**Wrong:** Inventing that a character trembled, wept, or felt a specific
named emotion the text never mentions.
**Right:** Name only the emotion or reaction the text states. Let the Greek
word study card carry the theological weight instead of dramatizing prose
elsewhere.

**Test:** For every descriptive or emotional claim, ask — does the text say
this, or does the original language support this specific word? If the
honest answer is "this was added for effect," rewrite using only what the
text states. When in doubt, use the plainer, less dramatic word.

---

### 2. No negation-built arguments
Do not construct a sentence, or a run of sentences, whose meaning depends on
negation. This is broader than "no X sino Y" — **stacked negations without
"sino" are the same violation** and are easy to miss if you only pattern-match
for "sino."

**Wrong (no...sino):**
- "No es solo cumplir mandamientos, es..."
- "No se trata de perder, sino de invertir en la eternidad."

**Wrong (stacked negation, no "sino" present — the harder one to catch):**
- "No discutió con Jesús. No lo acusó de exagerar. No se defendió con
  excusas." — three negations in a row defining the person by what he did
  NOT do, instead of stating what he did.
- "La decisión de soltar el control no duele porque uno no entienda lo que
  Dios pide." — double negation, confusing and passive.

**Right:** State the positive reality directly.
- "Escuchó a Jesús en silencio. Aceptó cada palabra como cierta."
- "La decisión de soltar el control duele precisamente porque se entiende
  con claridad lo que está en juego."

**Exception:** A single negation is acceptable when it directly quotes or
paraphrases the biblical text itself, or when removing it would distort the
meaning more than keeping it (rare — default to rewriting).

**Check method:** Re-read every sentence individually, not just scan for the
word "sino." Count occurrences of "no" per sentence — two or more is a flag
requiring a rewrite, regardless of whether "sino" appears.

---

### 3. Verse text lives only in `scripture_references`
A passage's full text may be mentioned by reference in prose inside
`content` (e.g. "Jesús responde en Mateo 19:14..."), but the **complete quoted
verse text must never also appear inline in `content`.** It belongs only in
that card's `scripture_references[]` array as `{reference, text}`.

**Wrong:** `content` contains: "Jesús responde con firmeza: **\"Dejad a los
niños venir a mí...\"** (Mateo 19:14)."
**Right:** `content` contains: "Jesús responde con firmeza en Mateo 19:14,
ordenando que los dejen venir a Él." Full text lives in
`scripture_references: [{"reference": "Mateo 19:14", "text": "..."}]`.

**Why:** the app renders `scripture_references[]` as a distinct verse
block. Quoting the same verse inline in `content` duplicates it for the
reader — once as plain paragraph text, once as the rendered verse
component — and breaks reading flow.

**Check both directions:**
- No verse quoted with quotation marks inside `content` (look for `**"`
  patterns or bolded phrases followed by a parenthetical reference like
  `(Mateo 19:14)` or `(v. 20)`).
- No card that discusses a passage in `content` while missing the matching
  `scripture_references[]` entry for it (an orphaned reference is just as
  wrong as a duplicated quote).

---

### 4. No marketing clichés or hollow phrases
Forbidden everywhere — titles, subtitles, content, revelation_key, prayers:

❌ "que lo cambia todo" / "that changes everything"
❌ "que transforma tu vida"
❌ "revolucionario" / "revolutionary"
❌ "poderoso" used as empty filler
❌ "increíble" / "amazing" / "impactante"
❌ "descubre el secreto de..."
❌ "la clave que nunca te enseñaron"
❌ Anything that reads like a YouTube thumbnail or book cover blurb

**Test:** If you removed the sentence, would the paragraph lose real
content? If not, cut it.

---

### 5. Be alert for unverifiable claims and unreal hyperbole
Beyond the cliché list above, watch for claims that sound authoritative but
are not actually grounded — historical superlatives, popular-preaching
trivia, or exaggerated framing not attested in the text.

**Examples to flag:**
- "La oración más corta de la Biblia" (a popular-preaching claim, not an
  exegetical fact — usually attributed loosely and inconsistently)
- Hyperbolic claims presented as literal historical fact without support
- Superlatives ("el más grande", "el único caso en toda la Biblia") stated
  without being able to actually verify them

**Test:** Could this claim be fact-checked against the text or against
reliable sources? If it's a popular saying repeated without a verifiable
anchor, cut it or reframe it as what it is (illustration, not fact).

---

### 6. Every card must add something new
Before approving any card, ask: does this card reveal something the
previous cards did not? If the answer is no — merge it, rewrite it, or
eliminate it. Overlap between cards is waste. Revelation should never repeat.

**What a `revelation_key` is (and isn't) — analyze before writing.** This
is Rule 6 applied specifically to the `revelation_key` field, not just to
whole cards. A `revelation_key` is not a summary of the card's `content`,
not a poetic flourish, and not a place to cram extra biblical content just
because it's available. It is the single sharpened "aha" specific to
*this card's moment* — distinct from what the content already said,
distinct from neighboring cards, and without spoiling what a later card
will reveal (see also Rule 15).

Before writing or approving one, answer explicitly: **what is this
specific card trying to make the reader take away, and is that different
from what neighboring cards already carry or will carry?** Don't write it
"a lo loco" (recklessly, without this analysis). If a following card
already owns the heavy theological weight of a moment, the current card's
`revelation_key` doesn't need to carry that weight too — it should
capture only what belongs to its own moment.

**Concrete case (2026-08-18, "El pan y la noche," Card 4 — "Una expresión
con historia"):** first draft of the `revelation_key` restated the card's
own content almost verbatim ("El lenguaje que Jesús usa para describir la
traición de Judas es el de un golpe violento...") — technically accurate,
but it added nothing beyond what the card's body had just said. Caught in
review, not by an automated scan, because it read as reasonable rather
than obviously redundant.

---

### 7. Greek and Hebrew terms must be explained inline
If a Greek or Hebrew word appears, explain it in the same sentence or the
next one. Never assume the reader knows the term.

**Format:** word in original characters + transliteration + plain-language
meaning, together, every time. The transliteration must sit in its own
parentheses immediately after the word, separate from the Strong's code —
`word, (transliteration) (GXXX)` — this is a HARD GATE the validator
enforces (`check_greek_hebrew_transliteration` in
`shared_validation/checks/greek_hebrew_gloss.py`); `word, transliteration
(GXXX)` (transliteration outside its own parens) fails it.

> "κτῆμα, (ktēma) (G2933) — bienes inmuebles, propiedades que dan
> estatus y seguridad social."

**Maximum one `greek_exegesis`/`hebrew_exegesis` card per study** (per
discovery-study-generator's architecture rules) — additional terms can
still be explained inline in other card types without needing their own card.

---

### 8. Language must be accessible to ALL readers
The reader may be an elderly person with limited education, a new believer,
or someone reading in their second language.

**Test every sentence:** would a grandmother in rural Latin America
understand this?

**Flag:**
- Academic vocabulary or theological jargon without inline explanation
- Idioms that don't translate across Spanish-speaking regions
- Sentences longer than 3 clauses

---

### 9. No em dashes in excess
Em dashes (—) are allowed but sparingly — one per paragraph maximum. Never
as a stylistic default. If a sentence needs an em dash to make sense,
rewrite the sentence.

---

### 10. Spanish capitalization rules
- Titles: only first word capitalized. "Morir al yo" ✓ — "Morir Al Yo" ✗
- Section headers (emoji + text): same rule. "🔍 Lo que hace único a este
  momento:" — capitalize only the first word after the emoji.
- Proper nouns always capitalized: Dios, Señor, Espíritu Santo, Jesús.

---

### 11. Per-language register gate (non-Spanish files) — MANDATORY
A card can pass Rules 1-10 and still use the wrong grammatical register for its
language — check for that too before approving. See `discovery-translator-SKILL.md`
§ "MANDATORY GATE: Per-Language Register Rules" for the rule per language (e.g. Hindi
requires respectful plural verbs for Jesus, not just plural pronouns — "यीशु आया" is
wrong, "यीशु आए" is right). Does not apply to quoted verse fields, which follow the
cited Bible version's own grammar.

---

### 12. Post-fix reverse validation & pattern sweep — MANDATORY
Whenever a review session (yours or a native-speaker critic's) results in file edits,
do not report the review done right after applying the fixes. See
`discovery-translator-SKILL.md` § "MANDATORY GATE: Post-Fix Reverse Validation &
Pattern Sweep" and run that full procedure: re-read the complete file, verify each edit
still matches its card's `revelation_key` and scripture reference, sweep the whole file
for the same error pattern the critic just found, and validate JSON. A grammatically
correct fix that quietly guts the sentence's meaning is a worse outcome than the
original error — it looks resolved but isn't.

---

### 13. Verse citations always carry the book name — MANDATORY
Every in-text citation of a verse, anywhere in `content`, must use the full
reference — `(Juan 13:9)` — never a bare `v. 9` or `versículo 9`. A citation
without the book name breaks once the study is translated into other
languages, since "versículo 9" doesn't travel with the file.

**Wrong:** "...como se ve en el versículo 9." / "(v. 8)"
**Right:** "...como se ve en Juan 13:9." / "(Juan 13:8)"

This applies even when the whole card only discusses one book — never rely
on context to imply which book "v. 9" refers to.

**Also check (restates Rule 3's orphan-reference check for citations
specifically):** every verse cited this way — even briefly, even unquoted —
must have a matching entry in that card's `scripture_references[]`. A verse
mentioned only by number in prose, with no `scripture_references` entry, is
still an orphaned reference.

---

### 14. Multi-word Greek/Hebrew phrases — cite each word separately
When a term under discussion is made of two (or more) original-language
words — e.g. ἐντολή καινή (a "new commandment") — cite each word on its own,
each with its own Strong's number, rather than combining both words under
one transliteration with both numbers stacked at the end.

**Wrong:** "ἐντολή καινή, entolē kainē (G1785, G2537)"
**Right:** "ἐντολή, (entolē) (G1785)... καινή, (kainē) (G2537)..." — each
word introduced and glossed on its own.

**Why:** Giovanni cross-checks every Greek/Hebrew citation against a
dictionary after review. A combined citation can't be looked up directly;
separated citations can be verified word by word.

**Format for a single word (all cards, not just `greek_exegesis`):**
`word, (transliteration) (GXXX)` — the transliteration sits in its own
parentheses immediately after the word, separate from the Strong's code —
e.g. `μέρος, (méros) (G3313)`. This is a HARD GATE
(`check_greek_hebrew_transliteration` in
`shared_validation/checks/greek_hebrew_gloss.py`): `word, translit (GXXX)`
— transliteration outside its own parens — fails validation even though it
reads naturally in prose.

**`greek_words[]`/`hebrew_words[].transliteration` never carries the
Strong's code inline.** That field is bare transliteration only (e.g.
`méros`, not `méros (G3313)`) — confirmed against every clean file in the
corpus (gethsemane_agony, good_shepherd, damascus_road, etc.). Putting the
code inline there triggers a separate HARD GATE
(`check_strong_code_bare_transliteration`): each string field is checked
in isolation, and `transliteration` alone has no native Greek/Hebrew
character nearby to anchor the code to, so the validator reports it as a
dangling citation.

**The Strong's code goes in its own sibling field, `"strong"`** (e.g.
`born_again_es_001.json`'s `{"word": "γεννάω", "transliteration":
"gennáō", "strong": "G1080", ...}`) — not inside `transliteration`, and
not omitted. Use this field on every `greek_words[]`/`hebrew_words[]`
entry. The Strong's code also belongs inline in `content` prose, attached
to the real word in its own well-formed gloss, wherever the term is
discussed there.

**Every transliteration must match the SOT exactly, diacritics
included** — pull it from `shared_validation/checks/lexicon_data/
strongs_greek.json` (or `strongs_hebrew.json`) by Strong's code rather
than typing from memory; a missing macron/acute (`tarassō` vs. the SOT's
`tarássō`) is a HARD GATE failure (`check_greek_hebrew_transliteration`),
not a stylistic nicety.

**A transliteration introduced once by a well-formed gloss must never
reappear bare later in the same field.** HARD GATE
(`check_bare_transliteration_reuse`): every occurrence needs its own
`word, (translit)` — reusing just the bare Latin transliteration for
flow ("el **psōmion** era gracia...") fails, even mid-paragraph, even
in the same card that already introduced it correctly. If re-glossing
every occurrence reads clunky, fall back to the Spanish gloss word
("el bocado...") instead of repeating the transliteration.

---

### 15. Titles, subtitles, and key_verse must not spoil the discovery
The series is called "Discovery" because the reader is meant to arrive at
the insight themselves, through the content — not have it handed to them
in the title before they've read a word. This applies at three levels:

**Card titles/subtitles** must not name the connection, term, or conclusion
the card exists to reveal. They can name the *scene*, the *question*, or
the *tension* — never the *answer*.

**Wrong:** "El mismo verbo de la cruz" (names the connection up front)
**Wrong:** "Dos palabras para lavar" (states the card's own discovery)
**Right:** "Una palabra que ya había usado antes" (invites, doesn't resolve)
**Right:** "¿Por qué Jesús responde así a Pedro?" (opens the question)

**A card must never spoil a *later* card.** If Card 1 ends on an open
question, Card 3's title must not hand over the answer before the reader
reaches Card 3's content — even though the study is sequential, the title
appears in navigation/preview contexts before the reader has necessarily
read the intervening cards.

**Wrong:** Card 1 asks "how does this happen?"; Card 3 is titled "El bocado
y la entrada" — this answers Card 1's question in Card 3's title alone.
**Right:** Card 3 titled "Lo que dice el texto griego" — signals depth
without pre-answering.

**The study's top-level `key_verse`** appears on the study's cover, before
Card 1. It must not be the narrative's climax verse — that spoils the
entire study before it opens. Choose a verse that opens the tension or
sets the scene instead.

**Wrong:** `key_verse` = Juan 13:27 ("Satanás entró en él") for a study
about Judas's betrayal — this is the story's climax, shown on the cover.
**Right:** `key_verse` = Juan 13:21 ("uno de vosotros me va a entregar") —
opens the mystery without resolving it.

**Not in scope of this rule:** a card's own `revelation_key` (the closing
insight *within* that same card, read only after its content) and a
card's own content resolving its own question by the end. The rule is
about what appears *before* the reader has engaged with the relevant
content — title, subtitle, and the study-level key_verse — not about
content properly building to its own conclusion.

**Small-card exception:** for a compact card with only one clear beat
(most `discovery_activation` or very short `cultural_context` cards), a
plain descriptive title that doesn't reveal a specific connection or
term is fine even if it's not phrased as a question — the anti-spoiler
concern is about naming the discovery, not about every title needing to
be a cliffhanger.

---



### A. Structural check
- [ ] Has correct `type`, `order`, `icon`, `title`, `subtitle`
- [ ] `scripture_references[]` uses exact RVR1960 text — not paraphrased,
      not truncated
- [ ] Every passage discussed in `content` has a matching
      `scripture_references[]` entry (Rule 3)
- [ ] `revelation_key` present, one sentence, theologically precise, and
      its own moment's "aha" — not a summary/repeat of the card's own
      content (Rule 6)
- [ ] `greek_words[]` entries have word, transliteration, strong, meaning,
      AND revelation — all five fields (if the card type is
      `greek_exegesis`)
- [ ] `greek_words[]`/`hebrew_words[].transliteration` is bare
      transliteration only, never `translit (GXXX)`; the code lives in its
      own `strong` field instead (Rule 14)
- [ ] Every transliteration matches strongs_greek/hebrew.json exactly,
      diacritics included — pulled from the file, not typed from memory
      (Rule 14)

### B. Content check
- [ ] Nothing added that the biblical text does not say (Rule 1)
- [ ] No negation-built arguments — checked sentence-by-sentence, not just
      pattern-matched for "sino" (Rule 2)
- [ ] No verse text duplicated inline in `content` (Rule 3)
- [ ] No marketing clichés or hollow phrases (Rule 4)
- [ ] No unverifiable claims or unreal hyperbole (Rule 5)
- [ ] Greek/Hebrew terms explained inline where they appear (Rule 7)
- [ ] Language accessible to all readers (Rule 8)
- [ ] Card adds something new vs. adjacent cards (Rule 6)
- [ ] Per-language register correct, for non-Spanish files (Rule 11)
- [ ] Every verse citation uses full book:chapter:verse, never bare "v. N"
      (Rule 13)
- [ ] Multi-word Greek/Hebrew terms cited word by word, each with its own
      Strong's number, in gate format `word, (translit) (GXXX)` (Rule 14)
- [ ] Title/subtitle don't name the card's own discovery or spoil a later
      card's answer; study-level `key_verse` isn't the narrative's climax
      (Rule 15)

### C. Theological check
- [ ] Reflections are grounded directly in the biblical text
- [ ] Inferences are framed as inferences, never stated as fact
- [ ] Greek/Hebrew word studies illuminate meaning, not decoration
- [ ] `scripture_references` are accurate and theologically load-bearing,
      not decorative citations

### D. Arc check (after all cards reviewed)
- [ ] `discovery_activation` is the last card, with prayer + 3 questions
- [ ] No two adjacent cards cover the same ground
- [ ] The emotional/theological arc progresses forward
- [ ] Card count is appropriate (5–7 sweet spot; consider splitting if a
      card is overloaded)
- [ ] Ideas introduced in earlier cards (e.g. "dependencia total") are
      picked up, not dropped, in later cards

---

## HANDLING THEOLOGICAL DISCOVERIES MID-SESSION

Sometimes a review session surfaces an insight that deepens or reframes a
card — as happened when Giovanni noted the inverted logic of grace in the
niños card (card 2 of "Morir al yo"): the Reino is given to those who have
least to negotiate with, which is grace rather than a transaction.

When this happens:

1. **Stop and explore** — do not rush to write. The insight may reshape
   multiple cards, not just the one being discussed.
2. **Search the web** if the insight involves a Greek/Hebrew term,
   exegetical detail, or cross-reference you are not certain about. Verify
   before writing.
3. **Identify the scope** — does this insight affect only this card, or
   adjacent cards too?
4. **Propose the addition or rewrite** — present the full revised text for
   explicit approval before writing to file. Never write speculatively.
5. **Run all three mandatory gates on the new text** before presenting it —
   a fresh insight is exactly where a new negation or an unbiblical
   flourish tends to slip back in.
6. **Write only after approval.**

---

## COMMIT PROTOCOL

After each approved set of changes:

```bash
git add <filepath>
git commit -m "feat(<lang>): <brief description of what changed>"
# Example: "feat(es): refine card 2 — gracia invertida, corrige card 1 dramatización"
```

Present the file after each commit using `present_files`. Regenerate the
companion `.md` reading copy (if one exists for this session) after any
content change, so Giovanni is always reviewing the current version.

---

## LESSONS FROM "MORIR AL YO" (Mateo 19) — July 2026

Real mistakes caught in this review session, which shaped this skill:

- **Triple stacked negation, undetected by a "no...sino" scan**: Card 1
  originally read "No discutió con Jesús. No lo acusó de exagerar. No se
  defendió con excusas." — three negations in a row, none using "sino," so
  an automated scan for that pattern alone missed it entirely. Caught only
  on a full manual re-read. Lesson: negation checks must go sentence-by-
  sentence counting "no" occurrences, never rely on a single phrase pattern.

- **Verse text duplicated in `content`**: Multiple cards quoted the full
  verse text inline with quotation marks AND repeated it in
  `scripture_references[]`. The app only needs the reference mentioned in
  prose — the complete text belongs solely in the structured field.

- **Unbiblical emotional escalation**: Card 1 described the rich young
  ruler as leaving "con el corazón roto." The text (Mateo 19:22) and the
  Greek (λυπούμενος) say only "triste" / grieved. "Corazón roto" was an
  invented dramatization that overstated what Scripture actually says —
  caught by Giovanni, not by any automated scan, because it read as
  plausible rather than obviously wrong.

- **A theological insight surfacing mid-review**: Giovanni's observation
  that God's logic inverts human logic — giving the Kingdom to those with
  nothing to negotiate, rather than to the powerful — was not yet in the
  card. It was added as a new block within the existing niños card (card 2)
  rather than creating a new card, because it deepened an existing card's
  point rather than introducing a separate one.

These lessons are canon for future Discovery study reviews and should
inform review sessions on any study, not only "Morir al yo."

---

## LESSONS FROM "El amor que se arrodilla" (Juan 13) — first session
using the gate-per-card generation workflow

- **Gates applied during generation, not after, cut review time
  drastically**: running each card through all 12 (now 14) gates
  immediately after drafting it — before moving to the next card — caught
  every issue in minutes instead of requiring a full back-and-forth pass
  over a finished file. This is now the default generation workflow, not
  just a review-session practice.
- **Bare verse citations ("v. 9") slip in constantly during drafting**,
  especially in the second half of a card once the book has already been
  named once. This is what Rule 13 exists to catch — check every single
  parenthetical and inline verse mention, not just the first one in a card.
- **Combined Greek/Hebrew citations for multi-word phrases** (e.g.
  "entolē kainē (G1785, G2537)") look tidy but can't be cross-checked
  word by word against a dictionary. Rule 14 exists because Giovanni
  verifies every citation afterward — combined citations block that.