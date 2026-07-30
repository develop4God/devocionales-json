"""run_strong_search.py — CLI entry point to search Strong's codes in corpus files.

Shows detailed context for each match: field path, matched text, position,
lexicon entry, text before/after, and nearby Greek/Hebrew words.

Usage:
    # Search a single file
    python3 shared_validation/run_strong_search.py discovery/es/passed_from_death_es_001.json

    # Search one family (all language versions of a study)
    python3 shared_validation/run_strong_search.py --family passed_from_death_001

    # Search all discovery + encounters files
    python3 shared_validation/run_strong_search.py --all

    # Run tests
    python3 -m unittest tests.test_strong_search -v
"""

import argparse
import glob
import json
import os
import re
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared_validation.strong_search import (
    find_strong_codes_phase1,
    find_strong_codes_phase2,
    find_strong_codes_phase3,
    summarize_results,
)
from shared_validation.lexicon_source import StrongsLexiconSource
from shared_validation.family_resolver import (
    _resolve_discovery_family,
    _resolve_encounters_family,
)


def _find_nearby_script(text: str, pos: int, window: int = 80) -> dict:
    """Find Greek and Hebrew characters near a position in text."""
    start = max(0, pos - window)
    end = min(len(text), pos + window)
    snippet = text[start:end]
    greek = re.findall(r'[\u0370-\u03FF\u1F00-\u1FFF]+', snippet)
    hebrew = re.findall(r'[\u0590-\u05FF]+', snippet)
    result = {}
    if greek:
        result["greek"] = list(dict.fromkeys(greek))  # unique, preserve order
    if hebrew:
        result["hebrew"] = list(dict.fromkeys(hebrew))
    return result


def analyze_file(filepath: str, lex: StrongsLexiconSource = None):
    """Analyze a single file and return structured match data."""
    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)

    if lex is None:
        lex = StrongsLexiconSource()

    matches = []

    for i, card in enumerate(data.get("cards", [])):
        for key in ["content", "reflection", "narrative", "title", "question", "answer", "note"]:
            text = card.get(key, "")
            if not text:
                continue

            p1 = find_strong_codes_phase1(text)
            p2 = find_strong_codes_phase2(text)
            p3 = find_strong_codes_phase3(text)

            for r in p3:
                entry = lex.lookup_by_number(r.code)
                before = text[:r.start]
                after = text[r.end:]
                match = text[r.start:r.end]

                # Determine if Phase 1 or Phase 2
                in_p1 = any(r.start == p.start and r.end == p.end for p in p1)

                # Find nearby script
                nearby = _find_nearby_script(text, r.start)

                matches.append({
                    "field_path": f"cards[{i}].{key}",
                    "card_index": i,
                    "field_type": key,
                    "code": r.code,
                    "prefix": r.prefix,
                    "number": r.number,
                    "matched_text": match,
                    "start": r.start,
                    "end": r.end,
                    "match_length": len(match),
                    "phase": "Phase 1 (Strong prefix)" if in_p1 else "Phase 2 (bare code)",
                    "text_before": before,
                    "text_after": after,
                    "nearby_script": nearby,
                    "lexicon_lemma": entry.lemma if entry else None,
                    "lexicon_translit": entry.translit if entry else None,
                    "lexicon_gloss": entry.gloss if entry else None,
                    "lexicon_found": entry is not None,
                })

    return matches


def print_matches(matches: list, show_full_context: bool = False):
    """Print match data in a readable format."""
    if not matches:
        print("  (no Strong codes found)")
        return

    for m in matches:
        print(f'\n{"─"*70}')
        print(f'  Field: {m["field_path"]}')
        print(f'  Code:  {m["code"]}  ({m["phase"]})')
        print(f'  Match: "{m["matched_text"]}"  (pos={m["start"]}-{m["end"]}, len={m["match_length"]})')

        if m["lexicon_found"]:
            print(f'  Lexicon:  lemma="{m["lexicon_lemma"]}"  translit="{m["lexicon_translit"]}"')
            print(f'  Gloss:    {m["lexicon_gloss"]}')
        else:
            print(f'  Lexicon:  NOT FOUND')

        if m["nearby_script"]:
            for script, words in m["nearby_script"].items():
                print(f'  Nearby {script}: {", ".join(words)}')

        # Show context before/after
        ctx_before = m["text_before"][-80:] if len(m["text_before"]) > 80 else m["text_before"]
        ctx_after = m["text_after"][:80] if len(m["text_after"]) > 80 else m["text_after"]
        print(f'  Before ({len(m["text_before"])} chars): ...{ctx_before}')
        print(f'  After  ({len(m["text_after"])} chars):  {ctx_after}...')

        if show_full_context:
            print(f'\n  --- Full text before ---')
            print(f'  {m["text_before"]}')
            print(f'  --- Full text after ---')
            print(f'  {m["text_after"]}')

    print(f'\n{"─"*70}')
    print(f'  Total: {len(matches)} match(es)')


def print_summary(matches: list):
    """Print a summary table of all matches."""
    codes = {}
    for m in matches:
        codes.setdefault(m["code"], []).append(m["field_path"])

    print(f'\n{"─"*70}')
    print(f'  SUMMARY: {len(matches)} match(es), {len(codes)} unique code(s)')
    for code, fields in sorted(codes.items()):
        print(f'    {code}: {len(fields)} occurrence(s) in {", ".join(fields)}')


def _run():
    parser = argparse.ArgumentParser(description="Search Strong's codes in corpus files")
    parser.add_argument("filepath", nargs="?", help="Path to a single JSON file")
    parser.add_argument("--family", help="Search one family (all language versions of a study)")
    parser.add_argument("--type", default="discovery", choices=["discovery", "encounters"], help="Content type for --family (default: discovery)")
    parser.add_argument("--dir", help="Search all JSON files in a directory")
    parser.add_argument("--all", action="store_true", help="Search all discovery + encounters files")
    parser.add_argument("--full", action="store_true", help="Show full context (not just 80 chars)")
    parser.add_argument("--summary", action="store_true", help="Show only summary, no details")

    args = parser.parse_args()
    lex = StrongsLexiconSource()
    all_matches = []

    if args.filepath:
        all_matches = analyze_file(args.filepath, lex)

    elif args.family:
        resolver = {
            "discovery": _resolve_discovery_family,
            "encounters": _resolve_encounters_family,
        }.get(args.type)
        if not resolver:
            print(f"Unknown content type: {args.type}")
            return
        family = resolver(args.family)
        if not family:
            print(f"Study '{args.family}' not found in {args.type} index")
            return
        print(f"\nFamily: {args.family} ({args.type})")
        print(f"Languages: {', '.join(sorted(family.keys()))}")
        for lang in sorted(family.keys()):
            fp = str(family[lang])
            matches = analyze_file(fp, lex)
            if matches:
                print(f"\n  {lang}: {os.path.basename(fp)} — {len(matches)} match(es)")
                for m in matches:
                    ctx_before = m["text_before"][-60:] if len(m["text_before"]) > 60 else m["text_before"]
                    ctx_after = m["text_after"][:60] if len(m["text_after"]) > 60 else m["text_after"]
                    print(f'    {m["code"]:8s}  "{m["matched_text"]:25s}"  before: ...{ctx_before}')
                    print(f'    {"":8s}  {"":25s}  after:  {ctx_after}...')
                    if m["nearby_script"]:
                        for script, words in m["nearby_script"].items():
                            print(f'    {"":8s}  {"":25s}  {script}: {", ".join(words)}')
                all_matches.extend(matches)
        print_summary(all_matches)

    elif args.dir:
        for fp in sorted(glob.glob(os.path.join(args.dir, "**/*.json"), recursive=True)):
            matches = analyze_file(fp, lex)
            if matches:
                print(f"\n{os.path.basename(fp):50s} {len(matches):2d} match(es)")
                for m in matches:
                    print(f'  {m["code"]:8s}  "{m["matched_text"]:25s}"  {m["field_path"]}')
                all_matches.extend(matches)
        print_summary(all_matches)

    elif args.all:
        for dirpath in ["discovery", "encounters"]:
            for fp in sorted(glob.glob(os.path.join(dirpath, "**/*.json"), recursive=True)):
                matches = analyze_file(fp, lex)
                if matches:
                    print(f"\n{os.path.basename(fp):50s} {len(matches):2d} match(es)")
                    for m in matches:
                        print(f'  {m["code"]:8s}  "{m["matched_text"]:25s}"  {m["field_path"]}')
                    all_matches.extend(matches)
        print_summary(all_matches)

    else:
        parser.print_help()
        return

    if all_matches and not args.summary and not args.family:
        print_matches(all_matches, show_full_context=args.full)


if __name__ == "__main__":
    _run()