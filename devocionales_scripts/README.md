# devocionales_scripts

Validation and maintenance tools for the `devocionales-json` repository.

**Last full validation run:** 2026-03-30 · 32 files · 11 680 entries · all checks passed.

---

## Scripts

### `validate_devocional_gui.py` — primary validator (v5)

Validates a single devotional JSON file.  Run in **GUI mode** (no args) or **CLI mode** (`--file`).

```bash
# CLI
python3 validate_devocional_gui.py --file ../Devocional_year_2026_de_LU17.json

# GUI
python3 validate_devocional_gui.py
```

**All checks performed:**

| Category | Detail |
|---|---|
| Required fields present | All 9 fields must exist and be non-empty |
| Empty string | `versiculo`, `reflexion`, `oracion`, `language`, `version`, `date`, `id` must not be `""` |
| Empty list | `tags` and `para_meditar` must not be `[]` |
| Empty list items | Every `tags[n]` must be non-empty; every `para_meditar[n].cita` and `.texto` must be non-empty |
| Metadata match | `language` and `version` fields must match what is encoded in the filename |
| Date key match | Entry `date` value must match its parent date key |
| Per-file duplicate dates | Same date cannot appear twice within one file |
| **Per-file duplicate IDs** | Same `id` cannot appear twice within one file |
| Date continuity | No missing days between first and last entry |
| Entry count | Warns if < 365 entries |
| Reflexion min length | ≥ 800 chars (Latin scripts); ≥ 200 chars (CJK/Indic — `zh`, `ja`, `hi`) |
| Oracion min length | ≥ 150 chars (Latin); ≥ 60 chars (CJK/Indic) |
| Reflexion truncation | Must end with `.`, `!`, `?`, `»`, `"`, `'`, `।`, `。`, `！`, or `？` |
| Prayer Amen ending | `oracion` must end with a recognised Amen variant |
| Double Amen | Flags duplicate Amen in closing 120 chars |
| Consecutive duplicate words | Flags AI-generated word repetition (liturgical anaphora whitelisted) |
| Seasonal content | Flags holiday framing injected by AI (Christmas, New Year, etc.) in 8 languages |
| Non-Latin charset | `hi`, `ja`, `zh`: unexpected Latin words are flagged |
| Spanish vocabulary leak | `fr`, `pt`, `en`: Spanish-only words are flagged |

**CLI output example:**
```
  Entries   : 365
  Version ❌ : ✅
  Lang ❌    : ✅
  Dup IDs ❌ : ✅
  Gaps ⚠️   : ✅
  Char Issues: ✅
  Content ❌ : ✅
  Status     : ✅ PASSED
```

---

### `validate_duplicates.py` — cross-file duplicate ID checker

Checks that every `id` is globally unique across **all 32 production files** (11 680 entries).

```bash
python3 validate_duplicates.py
# Run from the repo root:
python3 devocionales_scripts/validate_duplicates.py
```

Scans all files listed inside the script. Reports duplicate IDs with their file and date location.

**Expected result after any valid release:**
```
✅ NO DUPLICATE IDs FOUND!
All devotional files have unique IDs. ✨
```

---

### `verse_resolver.py` — verse lookup utility

Resolves an English Bible reference to target-language citation and verse text, using the gzip-compressed SQLite3 databases in `../bible_database/`.

```python
from verse_resolver import VerseResolver

with VerseResolver("../bible_database/LU17_de.SQLite3.gz", "book_map.json", "de") as r:
    cita, texto, error = r.resolve("Luke 19:10")
    # ("Lukas 19:10", "Denn der Menschensohn ist gekommen...", None)
```

**Used by:** maintenance scripts that need to fill missing `para_meditar.texto` fields when a verse is absent or empty in the target Bible database.

**Note on absent verses:** Some translations omit textually disputed verses (e.g., Matthew 18:11 in LU17; Ephesians 1:4–5 in HERV). When `texto` returns `""`, use a canonical equivalent from the same translation (e.g., Luke 19:10 for LU17; Galatians 4:5 for HERV).

---

### `fix_devotional_ids.py` — one-time ID repair utility

**Status:** completed historical fix — do not re-run on production files.

Fixed 4 205 entries across 22 files where IDs were missing the book/chapter/verse component or the date component, causing cross-year duplicates.

| Phase | Files | Entries fixed |
|---|---|---|
| JA + ZH (missing book/ch/vs) | 8 files | 2 565 |
| EN + ES + PT + FR (missing date) | 14 files | 1 640 |

---

### `extract_unique_tags.py`

Scans all production files and prints a sorted, deduplicated list of all tag values used across every entry.  Useful for auditing tag vocabulary consistency.

```bash
python3 extract_unique_tags.py
```

---

### `book_map.json`

Maps English canonical book names to their counterparts in each supported language.  Used by `verse_resolver.py` and `fix_devotional_ids.py`.

Structure:
```json
{
  "OT": { "Genesis": { "book_number": 1, "de_name": "1. Mose", "hi_name": "उत्पत्ति", ... } },
  "NT": { "Matthew": { "book_number": 40, "de_name": "Matthäus", ... } }
}
```

---

## Running all 32 files in one pass

```bash
cd /path/to/devocionales-json

for f in Devocional_year_2025.json Devocional_year_2026.json \
  Devocional_year_{2025,2026}_{de_LU17,de_SCH2000,en_KJV,en_NIV,es_NVI,\
fr_LSG1910,fr_TOB,hi_HERV,hi_HIOV,pt_ARC,pt_NVI}.json \
  "Devocional_year_2025_ja_リビングバイブル.json" "Devocional_year_2025_ja_新改訳2003.json" \
  "Devocional_year_2026_ja_リビングバイブル.json" "Devocional_year_2026_ja_新改訳2003.json" \
  "Devocional_year_2025_zh_和合本1919.json" "Devocional_year_2025_zh_新译本.json" \
  "Devocional_year_2026_zh_和合本1919.json" "Devocional_year_2026_zh_新译本.json"; do
    result=$(python3 devocionales_scripts/validate_devocional_gui.py --file "$f" 2>&1)
    status=$(echo "$result" | grep "Status" | tail -1)
    echo "$f | $status"
done

python3 devocionales_scripts/validate_duplicates.py
```

---

## Known translation quirks

| Version | Quirk | Handling |
|---|---|---|
| HIOV (Hindi OV) | Labels itself `(ओ.वी.)` in `versiculo`, not `HIOV` | Expected — validator accepts this alias |
| LU17 (Luther 2017) | Matthew 18:11 is absent (disputed verse omitted) | Use Luke 19:10 as canonical equivalent |
| HERV (Hindi ERV) | Ephesians 1:4–5 empty in DB (restructured into vv.3 and 6) | Use Galatians 4:5 as canonical equivalent |
| LU17 / HERV | Some book numbers differ from standard (Matthew=470, not 40) | `verse_resolver.py` handles this via `book_map.json` |

**Summary**:
- **Total files fixed**: 22 files (6 languages × ~4 files each)
- **Total entries fixed**: 4,205 entries
- **Duplicate IDs after fix**: 0 ✅
- **Errors encountered**: 0 ✅

**Breakdown by language**:
- Japanese: 1,460 entries (34.7%)
- Chinese: 1,105 entries (26.3%)
- French: 795 entries (18.9%)
- Portuguese: 603 entries (14.3%)
- Spanish: 135 entries (3.2%)
- English: 107 entries (2.5%)

---

## Verification

All fixes have been verified:
- ✅ All IDs follow consistent format
- ✅ All IDs are unique across the dataset
- ✅ No data loss or corruption
- ✅ All files validated successfully
- ✅ Zero duplicate IDs remaining
