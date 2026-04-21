#!/usr/bin/env python3
"""
export_flagged.py — Export flagged (PAUSE) entries from a critic audit JSONL.

Reads archive/critic_audit_tl_ASND_2026.jsonl (or a file passed via --audit)
and cross-references against the corresponding devotional JSON to produce a
subset JSON file containing only the entries that were flagged for manual
review (action=flagged, verdict=PAUSE).

Categories present in the 2026 tl/ASND audit:
  register_drift      — pronoun inconsistency (Mo/mo vs Inyong/Iyong) or
                        academic/Greek language breaking devotional tone
  generic_reflection  — reflection drifts into universal statements not
                        anchored to the specific verse
  prayer_drift        — prayer pivots to a theme not in the verse or reflection
  other               — miscellaneous quality issues

Usage:
    python3 devocionales_scripts/export_flagged.py
    python3 devocionales_scripts/export_flagged.py \
        --audit    archive/critic_audit_tl_ASND_2026.jsonl \
        --source   Devocional_year_2026_tl_ASND.json \
        --out      /tmp/flagged_tl_ASND_2026.json \
        --category register_drift
"""

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_AUDIT = REPO_ROOT / "archive" / "critic_audit_tl_ASND_2026.jsonl"
DEFAULT_SOURCE = REPO_ROOT / "Devocional_year_2026_tl_ASND.json"
DEFAULT_OUT = REPO_ROOT / "archive" / "flagged_tl_ASND_2026.json"

VALID_CATEGORIES = {"register_drift", "generic_reflection", "prayer_drift", "other"}


def load_audit(path: Path) -> dict[str, dict]:
    """Return latest record per id from a critic audit JSONL."""
    by_id: dict[str, dict] = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            id_ = rec["id"]
            if id_ not in by_id or rec["reviewed_at"] > by_id[id_]["reviewed_at"]:
                by_id[id_] = rec
    return by_id


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export flagged (PAUSE) devotional entries for manual review."
    )
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT,
                        help="Path to critic audit JSONL")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE,
                        help="Path to source devotional JSON")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT,
                        help="Output path for flagged JSON")
    parser.add_argument("--category", choices=sorted(VALID_CATEGORIES),
                        default=None,
                        help="Filter by category (default: all flagged entries)")
    args = parser.parse_args()

    if not args.audit.exists():
        sys.exit(f"ERROR: audit file not found: {args.audit}")
    if not args.source.exists():
        sys.exit(f"ERROR: source file not found: {args.source}")

    audit = load_audit(args.audit)
    flagged_ids: dict[str, dict] = {
        id_: rec for id_, rec in audit.items()
        if rec.get("action") == "flagged" and rec.get("verdict") == "PAUSE"
        and (args.category is None or rec.get("category") == args.category)
    }

    with open(args.source, encoding="utf-8") as fh:
        source = json.load(fh)

    lang_key = next(iter(source["data"]))
    out_data: dict = {}
    kept = 0
    for date_key, entries in source["data"][lang_key].items():
        flag_entries = []
        for e in entries:
            if e["id"] in flagged_ids:
                audit_rec = flagged_ids[e["id"]]
                # Annotate entry with audit metadata for easy review
                annotated = dict(e)
                annotated["_audit_category"] = audit_rec.get("category")
                annotated["_audit_confidence"] = audit_rec.get("confidence")
                annotated["_audit_quoted_pause"] = audit_rec.get("quoted_pause")
                annotated["_audit_reaction"] = audit_rec.get("reaction")
                annotated["_audit_genome_fragment_id"] = audit_rec.get("genome_fragment_id")
                flag_entries.append(annotated)
        if flag_entries:
            out_data[date_key] = flag_entries
            kept += len(flag_entries)

    from collections import Counter
    cat_counts = Counter(
        rec.get("category") for rec in flagged_ids.values()
    )

    result = {"data": {lang_key: out_data}}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=2)

    total = sum(len(v) for v in source["data"][lang_key].values())
    print(f"Flagged entries exported : {kept} / {total}")
    if args.category:
        print(f"Category filter          : {args.category}")
    else:
        print(f"Category breakdown       : {dict(sorted(cat_counts.items(), key=lambda x: -x[1]))}")
    print(f"Output                   : {args.out}")


if __name__ == "__main__":
    main()
