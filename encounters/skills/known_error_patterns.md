# Known Error Patterns — Final Gate Reference

This file accumulates recurring translation-quality issues discovered across encounters
and languages. It exists **only for the Final Gate stage** — after the open-ended
native-speaker critic review (see `encounters_translator_SKILL.md` § "MANDATORY:
Native-Speaker Critic Review") has already run and its fixes are applied.

**Do not inject this file's contents into the first-pass critic subagent's prompt.**
That prompt must stay simple and open-ended ("read line by line, report typos / grammar
errors / awkward phrasing") with no named categories. Priming the critic with a fixed
list of things to check causes it to anchor on those and under-report everything else —
this is exactly how the richest findings this session (tautologies, calques, term drift)
were caught: by a critic with no prior hint of what to look for.

This file is consumed in two different ways depending on entry type:

- **Mechanical** entries are checked directly (grep/read), no subagent needed.
- **Judgment** entries are handed to a *second*, fresh subagent — separate context from
  the first critic, framed as "check specifically for these categories" — because at
  this stage the goal is targeted confirmation of known failure modes, not open
  discovery. Priming is appropriate here; it is not appropriate at the first-pass stage.

---

## Register Consistency — Mechanical

**Pattern:** A language with a formal/informal second-person distinction drifts between
the two registers across the file, usually settling into the formal one in the
reader-facing cards (discovery_activation, prayer, completion) while narrative cards use
neither.

**Languages affected:** ZH (你/您), DE (du/Sie), FR (tu/vous), PT (você/tu), HI (आप/तू).

**Example found:** ZH `bleeding_woman_zh_001.json` used 您 exclusively in Card 10
(discovery_activation) and Card 11 (reflection_prompt) — 17 instances — while the project
rule requires 你 always, for both God/Jesus and reader address.

**Check:** grep every second-person pronoun for the language across the whole file.
Confirm a single register is used throughout — not just within one card.

**Fix pattern:** pick the informal/intimate register (你, du, tu) for devotional address
to God and reader in this project's house style; replace all formal-register instances.

---

## Theological/Legal Term Drift — Mechanical

**Pattern:** A precise theological or legal term (e.g. "impurity/uncleanness" in
Levitical-purity narratives) gets correctly used in most of the file but drifts to a
generic synonym ("condition," "state," "situation") in one or two isolated sentences,
usually in the opening narrative card.

**Languages affected:** PT (condição → impureza needed), HI (चिन्हित used instead of
अशुद्ध), FIL (kalagayan → karumihan needed), DE (Zustand → Unreinheit needed in the
specific impurity-transmission sentence — note "Zustand" is fine elsewhere when it
generically means "her circumstances," only wrong when it stands in for the specific
legal concept of ritual impurity).

**Check:** identify the 1-2 terms central to the encounter's theological point. Grep
every occurrence in the file. Confirm the same term is used every time the concept is
meant, even if a generic synonym would be grammatically valid in that sentence.

**Caution:** not every instance of the generic word is wrong — some legitimately refer to
a different, broader idea (her life circumstances vs. her ritual-impurity status). Read
the surrounding sentence before "fixing" — see DE example above.

---

## Calque / Literal-Translation Phrasing — Judgment

**Pattern:** A phrase is grammatically valid in the target language but reads as a direct
structural translation from the Spanish/English source — a native speaker would express
the same idea with different imagery or word order entirely.

**Examples found across this session:**
- HI: "बारह वर्ष अलग रहने के भी..." — dangling calque fragment, no natural connector.
- HI/FR/AR: "asking for/hoping for only a little space" (उतनी ही सावधानी से...पिचोटा स्थान
  माँगते समय / n'espérant qu'un tout petit espace / راجية مساحة صغيرة) — the "small space"
  spatial metaphor for humility reads awkward or opaque in all three, translated nearly
  word-for-word from the same source image.
- FIL: "putol mula sa" (cut off from) — literal calque of English idiom; natural Filipino
  is "hiwalay sa."
- HI: "लैव्यव्यवस्था की व्यवस्था" — tautology ("the law of the law"), an artifact of
  translating "the law of Leviticus" where the book name itself already contains "law."
- DE: "ohne ihren Zustand zu übertragen" — see Term Drift above; also a mistranslation,
  since you transmit impurity/disease, not a "condition."

**Check:** cannot be grepped. Requires a native-speaker judgment pass specifically
scoped to this category — hand a fresh subagent the file with the instruction: "flag
only sentences that read as literal translation from Spanish/English rather than
natural {language} prose — tautologies, unnatural spatial/idiomatic calques, dangling
fragments that don't connect naturally." Keep this subagent separate from the first
open-ended critic so its narrower framing doesn't contaminate the broader pass.

---

## Inclusive Dual-Address in Prayer — Not an Error, Just Confirm Intentional

**Pattern:** The prayer card addresses the reader with both genders explicitly (e.g.
"you call me son, you call me daughter" / "me chamas filho, me chamas filha" / 私を息子と
呼び、娘と呼び / 谢谢你称我为儿子，称我为女儿).

**Languages affected:** PT, FR, HI, JA, ZH, DE — present in every language reviewed this
session, always in the same prayer card.

**Verdict:** this is a deliberate cross-language design choice for gender-inclusive
prayer language, not a translation error. Every native-speaker critic this session
flagged it as "slightly unusual phrasing" — correctly noted, but **do not fix it**. It's
consistent project style. Only flag it if a *new* language renders it in a way that's
outright ungrammatical (not just stylistically unusual), which has not happened so far.

---

## Post-Fix Drift Check — Mandatory Regardless of Entry Type

After applying any fix from this file (mechanical or judgment-based), re-read the full
paragraph the fix sits in — not just the diffed line — and re-validate JSON. A
grammatically-corrected sentence can silently lose the theological point the card's
`revelation_key` depends on. This mirrors the existing "MANDATORY GATE: Post-Fix Reverse
Validation & Pattern Sweep" in `encounters_translator_SKILL.md` and is not optional just
because the fix came from this reference file instead of a live critic finding.
