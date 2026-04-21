#!/usr/bin/env python3
"""
export_gold.py — Export "gold" (OK) entries from a critic audit JSONL.

Reads archive/critic_audit_tl_ASND_2026.jsonl (or a file passed via --audit)
and cross-references against the corresponding devotional JSON to produce a
subset JSON file containing only the entries that passed review (action=reviewed,
verdict=OK).

Usage:
    python3 devocionales_scripts/export_gold.py
    python3 devocionales_scripts/export_gold.py \
        --audit  archive/critic_audit_tl_ASND_2026.jsonl \
        --source Devocional_year_2026_tl_ASND.json \
        --out    /tmp/gold_tl_ASND_2026.json
"""

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_AUDIT = REPO_ROOT / "archive" / "critic_audit_tl_ASND_2026.jsonl"
DEFAULT_SOURCE = REPO_ROOT / "Devocional_year_2026_tl_ASND.json"
DEFAULT_OUT = REPO_ROOT / "archive" / "gold_tl_ASND_2026.json"


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
    parser = argparse.ArgumentParser(description="Export gold (OK) devotional entries.")
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT,
                        help="Path to critic audit JSONL")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE,
                        help="Path to source devotional JSON")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT,
                        help="Output path for gold JSON")
    args = parser.parse_args()

    if not args.audit.exists():
        sys.exit(f"ERROR: audit file not found: {args.audit}")
    if not args.source.exists():
        sys.exit(f"ERROR: source file not found: {args.source}")

    audit = load_audit(args.audit)
    gold_ids = {id_ for id_, rec in audit.items()
                if rec.get("action") == "reviewed" and rec.get("verdict") == "OK"}

    with open(args.source, encoding="utf-8") as fh:
        source = json.load(fh)

    lang_key = next(iter(source["data"]))
    out_data: dict = {}
    kept = 0
    for date_key, entries in source["data"][lang_key].items():
        gold_entries = [e for e in entries if e["id"] in gold_ids]
        if gold_entries:
            out_data[date_key] = gold_entries
            kept += len(gold_entries)

    result = {"data": {lang_key: out_data}}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=2)

    total = sum(len(v) for v in source["data"][lang_key].values())
    print(f"Gold entries exported : {kept} / {total}")
    print(f"Output                : {args.out}")


if __name__ == "__main__":
    main()
