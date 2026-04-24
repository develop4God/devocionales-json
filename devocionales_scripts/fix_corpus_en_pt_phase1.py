#!/usr/bin/env python3
"""
Corpus fix script — ARC (PT) + KJV (EN)
Applies P1 fixes, P2 hard typos, and one P3 batch-fixable pattern.
Produces patched files in-place with a dry-run report first.
"""
import json, re, sys
from pathlib import Path

ROOT = Path("/home/claude/devocionales-json")
FIELDS = ["reflexion", "para_meditar", "oracion"]

def load(fname, lang):
    with open(ROOT / fname) as f:
        data = json.load(f)
    return data, data["data"][lang]

def save(fname, data):
    with open(ROOT / fname, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def all_entries(lang_data):
    for date, arr in lang_data.items():
        for e in arr:
            yield e

# ─── ARC FIXES ─────────────────────────────────────────────────────────────

ARC_FILES = [
    ("Devocional_year_2025_pt_ARC.json", "pt"),
    ("Devocional_year_2026_pt_ARC.json", "pt"),
]

# P1-A: em o nome → em nome (oracion only)
def fix_em_o_nome(text):
    return text.replace("em o nome de Jesus", "em nome de Jesus")

# P1-B: dEle → d'Ele, dAquele → d'Aquele (all fields)
def fix_dele(text):
    text = text.replace("dEle", "d'Ele")
    text = text.replace("dAquele", "d'Aquele")
    return text

# P1-C: capitalize reverential pronouns in oracion
# te → Te, teu → Teu, tua → Tua, ti → Ti (word-boundary aware)
REV_PATTERN = re.compile(r'\b(te|teu|tua|ti)(?=[,. \n\r])')
def fix_reverential(text):
    return REV_PATTERN.sub(lambda m: m.group(0).capitalize(), text)

# P2: Hard typos in specific entries (id → list of (field, old, new))
P2_FIXES_ARC = {
    "hb612PTARC20251125":       [("oracion", "sabedidade", "sabedoria"), ("reflexion", "sabedidade", "sabedoria"), ("para_meditar", "sabedidade", "sabedoria")],
    "tito1v5-9ARC":             [("oracion", "sabedemia", "sabedoria"), ("reflexion", "sabedemia", "sabedoria"), ("para_meditar", "sabedemia", "sabedoria")],
    "2corintios517ARC":         [("oracion", "nossas vives", "nossas vidas"), ("reflexion", "nossas vives", "nossas vidas"), ("para_meditar", "nossas vives", "nossas vidas")],
    "1pedro315ARC20251215":     [("oracion", "nossas vives", "nossas vidas"), ("reflexion", "nossas vives", "nossas vidas"), ("para_meditar", "nossas vives", "nossas vidas")],
    "joao14_6ARC20260114":      [("oracion", "oferecend", "oferecendo"), ("reflexion", "oferecend", "oferecendo"), ("para_meditar", "oferecend", "oferecendo")],
    "lucas24_6-7ARC20260120":   [("oracion", "crucifixação", "crucificação"), ("reflexion", "crucifixação", "crucificação"), ("para_meditar", "crucifixação", "crucificação")],
    "lucas15_7ARC20260202":     [("oracion", "evangelio", "evangelho"), ("reflexion", "evangelio", "evangelho"), ("para_meditar", "evangelio", "evangelho")],
    "tiago2_8ARC20260118":      [("oracion", "atmos de bondade", "atos de bondade"), ("reflexion", "atmos de bondade", "atos de bondade"), ("para_meditar", "atmos de bondade", "atos de bondade")],
    "filemon116ARC20250827":    [("oracion", "Filemom 1:16", "Filemon 1:16"), ("reflexion", "Filemom 1:16", "Filemon 1:16"), ("versiculo", "Filemom 1:16", "Filemon 1:16")],
    "2Timoteo317ARC":           [("oracion", "me equips", "me equipa"), ("reflexion", "me equips", "me equipa"), ("para_meditar", "me equips", "me equipa")],
    "1Joao5v13ARC":             [("oracion", "assurance espiritual", "certeza espiritual"), ("reflexion", "assurance espiritual", "certeza espiritual"), ("para_meditar", "assurance espiritual", "certeza espiritual")],
}

# ─── KJV FIXES ─────────────────────────────────────────────────────────────

KJV_FILES = [
    ("Devocional_year_2025_en_KJV.json", "en"),
    ("Devocional_year_2026_en_KJV.json", "en"),
]

# P1: lowercase closing → capitalize "in" after period
# ". in the name of Jesus, amen." → ". In the name of Jesus, amen."
KJV_CLOSING = re.compile(r'\. in the name of Jesus, amen\.')
def fix_kjv_closing(text):
    return KJV_CLOSING.sub(". In the name of Jesus, amen.", text)

# ─── RUNNER ────────────────────────────────────────────────────────────────

def process_arc(dry_run=False):
    total_changes = {"em_o_nome": 0, "dele": 0, "reverential": 0, "p2": 0}
    for fname, lang in ARC_FILES:
        data, lang_data = load(fname, lang)
        year = "2025" if "2025" in fname else "2026"
        changed_entries = 0
        for e in all_entries(lang_data):
            entry_changed = False
            eid = e.get("id", "?")

            # P1-A: em o nome (oracion only)
            orig = e.get("oracion", "")
            fixed = fix_em_o_nome(orig)
            if fixed != orig:
                total_changes["em_o_nome"] += 1
                if not dry_run:
                    e["oracion"] = fixed
                else:
                    print(f"  [em_o_nome] {eid}")
                entry_changed = True

            # P1-B: dEle / dAquele (all fields)
            for field in FIELDS + ["versiculo"]:
                orig = e.get(field, "")
                if not isinstance(orig, str): continue
                fixed = fix_dele(orig)
                if fixed != orig:
                    total_changes["dele"] += 1
                    if not dry_run:
                        e[field] = fixed
                    else:
                        print(f"  [dEle] {eid} [{field}]")
                    entry_changed = True

            # P1-C: reverential pronouns (oracion only)
            orig = e.get("oracion", "")
            fixed = fix_reverential(orig)
            if fixed != orig:
                total_changes["reverential"] += 1
                if not dry_run:
                    e["oracion"] = fixed
                else:
                    print(f"  [reverential] {eid}")
                entry_changed = True

            # P2: hard typos
            if eid in P2_FIXES_ARC:
                for field, old, new in P2_FIXES_ARC[eid]:
                    orig = e.get(field, "")
                    if not isinstance(orig, str): continue
                    if old in orig:
                        total_changes["p2"] += 1
                        if not dry_run:
                            e[field] = orig.replace(old, new)
                        else:
                            print(f"  [P2] {eid} [{field}] '{old}' → '{new}'")
                        entry_changed = True

            if entry_changed:
                changed_entries += 1

        if not dry_run:
            save(fname, data)
            print(f"  ✅ Saved {fname} ({changed_entries} entries modified)")

    print(f"\nARC totals: {total_changes}")

def process_kjv(dry_run=False):
    total_changes = {"kjv_closing": 0}
    for fname, lang in KJV_FILES:
        data, lang_data = load(fname, lang)
        changed_entries = 0
        for e in all_entries(lang_data):
            eid = e.get("id", "?")
            orig = e.get("oracion", "")
            if not isinstance(orig, str): continue
            fixed = fix_kjv_closing(orig)
            if fixed != orig:
                total_changes["kjv_closing"] += 1
                changed_entries += 1
                if not dry_run:
                    e["oracion"] = fixed
                else:
                    print(f"  [kjv_closing] {eid}")

        if not dry_run:
            save(fname, data)
            print(f"  ✅ Saved {fname} ({changed_entries} entries modified)")

    print(f"\nKJV totals: {total_changes}")

if __name__ == "__main__":
    dry = "--apply" not in sys.argv
    if dry:
        print("=" * 60)
        print("DRY RUN — pass --apply to write changes")
        print("=" * 60)
    print("\n── ARC ──")
    process_arc(dry_run=dry)
    print("\n── KJV ──")
    process_kjv(dry_run=dry)
    if dry:
        print("\nRe-run with --apply to commit all changes.")
