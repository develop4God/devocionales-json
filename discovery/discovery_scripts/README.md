
# 🚦 Discovery Studies Validation Workflow

## 🏁 Overview
This folder contains all scripts needed to validate the structure, translation, and consistency of the Discovery Studies JSON files across all languages and studies.

---

## 🧑‍💻 Main Scripts

- **🚀 discovery_master_validator.py**: The all-in-one orchestrator. Runs all validations for the entire codebase automatically.
- **🌐 validate_discovery.py**: Global validator. Checks all translation files for JSON validity, structure, language codes, and completeness using index.json as the source of truth.

---

## 🔄 Typical Validation Flows

### 1️⃣ Full Codebase Validation (Recommended)
Run this to check everything in one go:

```bash
python3 discovery_master_validator.py
```
- ✅ Runs global translation/JSON/structure/index validation for all files
- 🟢 If all pass, your codebase is fully validated!
- Whether you're translating one file or a whole batch, this is the standard workflow — always run the master validator (or `validate_discovery.py` directly) after any translation work.

### 2️⃣ Validate All Translations Only

```bash
python3 validate_discovery.py
```
- 🌐 Checks all translation files for JSON, structure, and language issues
- Uses index.json as the source of truth

---

## 🤖 How It Works

- **discovery_master_validator.py** runs validate_discovery.py's full translation/JSON/structure/index validation, including recursive EN-vs-translation key and shape diffing per study.
- All scripts print clear error messages and stop on failure, so you always know what to fix.

---

## 📝 Quick Reference

- ▶️ Run `discovery_master_validator.py` for full validation (global + per-study structure checks)
- ▶️ Run `validate_discovery.py` directly for the same checks

---

## 📋 Validation Details & Rules

### 🌐 validate_discovery.py — Two-Phase Validation

**PHASE A: Index Validation**
- 🗂️ Validates index.json format, structure, and data integrity
- 🕵️ Checks for missing translations and marks them as PENDING
- 🛑 If Phase A fails, validation stops and errors are reported
- 📖 index.json becomes the single source of truth for Phase B

**PHASE B: Translation Files Validation**
- ▶️ Only runs if Phase A passes
- 📚 Uses index.json as the authoritative source of studies
- 📝 Validates all translation files referenced in index.json
- 🏷️ Verifies file existence, structure, and content quality

#### Key Checks
- ✅ JSON format and syntax
- ✅ Required fields: id, version, emoji, files, titles, subtitles, estimated_reading_minutes
- ✅ Data structure integrity
- ✅ No duplicate study IDs
- ✅ Correct language codes (en, es, pt, fr, ja, zh)
- ✅ Proper Bible version for each language
- ✅ No mixed languages in content
- ✅ All required fields present in each file
- ✅ Array structures (cards, tags, themes)
- ✅ Metadata completeness
- ✅ Card, tag, and theme counts match across translations
- ✅ No English content in non-English files (for ja/zh)
- ✅ All files listed in index.json exist and follow naming convention

#### 📦 Expected Languages
- 🇬🇧 English (en) - KJV, NIV
- 🇪🇸 Spanish (es) - RVR1960, NVI
- 🇵🇹 Portuguese (pt) - ARC, NVI
- 🇫🇷 French (fr) - LSG1910, TOB
- 🇯🇵 Japanese (ja) - 新改訳2003, リビングバイブル
- 🇨🇳 Chinese (zh) - 和合本1919, 新译本

#### 📁 File Naming Convention
- Format: `{study_name}_{language}_001.json`
- Example: `born_again_en_001.json`

#### 🖥️ Usage

```bash
# From the discovery folder
python3 scripts/validate_discovery.py
# Make it executable (optional)
chmod +x scripts/validate_discovery.py
./scripts/validate_discovery.py
```

#### 🟢 Expected Output
- **Phase A Report**: Index validation results
- **Phase B Report**: Translation files validation (only if Phase A passes)
- Statistics (total files, languages, studies, pending translations)
- Information messages, warnings, and errors
- Exit code: `0` = All validations passed, `1` = Errors found

#### ⚙️ Requirements
- Python 3.6 or higher
- Standard library only (no external dependencies)

---

## ➕ Adding New Translations

1. 📝 Update index.json with the new study entry
2. ✅ Ensure all required fields are present
3. 📂 Add translation files to appropriate language folders
4. 🔄 Run validation — it will automatically use index.json as source of truth
5. 🟡 Fix any PENDING translations as needed

### 🟡 Understanding PENDING Status
- Studies with incomplete translations are reported as PENDING in Phase A
- Shows which languages are missing for each study
- Helps track translation progress
- Does not cause validation failure (only a warning)
