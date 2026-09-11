# Handoff — Youth Bible Study Material Generator

## Context / Motivation

Giovanni (sole developer/content creator behind the "Devocionales Cristianos" Flutter app, active in 90+ countries, 10 languages) needs Bible study material for **youth groups (ages 13-16)**, for internal teaching/discipleship use — not for sale. Buying commercial curricula is expensive and hard to source consistently across all the countries the ministry operates in, so the goal is to generate original material with AI, following the same orchestrator-architect workflow he already uses for the app's **Encounters** and **Discovery Studies** series (he directs AI agents under his own editorial/architectural authority).

## Copyright groundwork (important — do not skip if resuming)

We researched an existing commercial curriculum, **"El Explorador"** (Editorial Nueva Vida / My Healthy Church), only via public marketing snippets and cross-comparison with other similar publishers (TeachKids, Adventist resources, LifeWay). We explicitly avoided ingesting the actual PDFs (which circulate on Scribd, likely without authorization).

Key conclusions reached in this session:
- **Structure/format is not protected** (idea-expression dichotomy) — the generic pattern (hook → Bible reading → key verse → teaching → comprehension questions → application → personal outline → family discussion → evangelism prompt), and the **student guide / teacher guide split**, is a shared industry convention across many publishers, not proprietary to one editorial.
- **Specific expression IS protected** — exact wording, specific stories, exact question phrasing, and the specific unit-title curation of a given publisher's quarter should NOT be copied or closely paraphrased.
- Loading full copyrighted PDFs into a RAG and generating "similar" output is legally risky even with a text-similarity threshold check — legal risk (substantial similarity / structure-sequence-organization doctrine) isn't captured by n-gram overlap, and ingesting pirated PDFs is itself a problem independent of output.
- "Non-commercial / not for sale" does **not** exempt from copyright — it's one factor among several (purpose, amount used, market effect), and using the *entire* structure/curriculum at scale, replacing the need to buy the original, weighs against any fair-use-style defense. This is especially true across the 90+ countries involved, most of which have narrower "fair dealing" exceptions than US fair use.
- **Agreed path forward:** build content 100% from scratch using a schema inspired only by the generic genre pattern, never by ingesting or closely following any specific publisher's actual text.

## Deliverables produced this session

Located in `/youth_material/`:

1. **`schema/lesson.schema.json`** — JSON Schema (draft-07) validating a master lesson document. Top-level: `unit` + `lesson`. Lesson contains:
   - `shared` (bible_reading, key_verse, hook)
   - `student_content` (audience-facing teaching, comprehension questions, fill-in-blanks, personal outline, family discussion, evangelism prompt)
   - `teacher_content` (deeper exposition, facilitation notes, group dynamics, **leader_training** — content the student never sees, e.g. how to guide a teen to Christ, how to handle emotional disclosures — and materials needed)
   - `metadata` (language, editorial_status: draft/reviewed/published, created_by: ai_generated/human_edited)

2. **`validate_lesson.py`** — CLI script (uses `jsonschema`) that:
   - Validates a master lesson JSON against the schema
   - With `--split`, generates two separate deliverable files: `<id>_alumno.json` (student-only) and `<id>_maestro.json` (teacher content + a read-only reference copy of the student content)
   - Tested both positive (valid doc passes) and negative (missing required field is correctly rejected)

3. **`lessons/lesson_social_media_01.json`** — Pilot master lesson: **"Redes sociales: el espejo que nunca deja de hablar"** (topic: social media and Christian discernment for teens), fully original content, Phil 4:4-9 / key verse Phil 4:8, includes both student and teacher tracks including a leader-training block on supporting anxious teens.

4. **`exports/lesson_social_media_01_alumno.json`** and **`exports/lesson_social_media_01_maestro.json`** — generated split outputs from the pilot, validated successfully.

## Two-audience model (student vs. teacher)

Confirmed via public product descriptions that commercial curricula in this genre commonly differ meaningfully between guides, not just in labeling:
- **Student guide**: shorter, self-contained, interactive (fill-in-blanks), personal application focus.
- **Teacher guide**: deeper exegetical/pastoral exposition, facilitation notes, group dynamics/activities, and **standalone leader-training content the student never sees** (e.g., how to guide a teen to Christ, how to handle sensitive disclosures — with guidance to involve parents/pastoral counselors when appropriate).

The schema's `teacher_content.leader_training` block captures this asymmetry.

## Open items / suggested next steps

- Decide field naming convention (snake_case vs. camelCase) to align with the actual `devocionales-json` repo conventions — not yet cross-checked against a real file from that repo.
- Decide on Bible version(s) to standardize on (used RVA1909 — public domain — in the pilot; confirm this fits app needs across languages/regions).
- Define the real unit/topic roadmap (this session only produced one pilot topic: social media). Needs Giovanni's own topic selection — do NOT reuse "El Explorador"'s specific unit titles.
- Decide whether to formalize a `unit.schema.json` as a separate file (currently unit is nested inside the same schema as an embedded definition).
- Decide how this new series integrates with the existing GEP pipeline (batch generation across languages) — not yet discussed.
- Consider whether `leader_training` needs its own sensitivity/review gate before publishing, given it may touch pastoral care topics.
