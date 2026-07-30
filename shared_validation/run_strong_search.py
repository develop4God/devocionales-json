"""run_strong_search.py — CLI for Strong code search, preview, and fix.

Usage:
    # Search a single file
    python3 shared_validation/run_strong_search.py discovery/es/passed_from_death_es_001.json

    # Preview fixes for a file
    python3 shared_validation/run_strong_search.py discovery/es/passed_from_death_es_001.json --preview

    # Preview fixes for a family (all languages)
    python3 shared_validation/run_strong_search.py --family passed_from_death_001 --preview

    # Apply fixes to a file
    python3 shared_validation/run_strong_search.py discovery/es/passed_from_death_es_001.json --fix

    # Apply fixes to a family
    python3 shared_validation/run_strong_search.py --family passed_from_death_001 --fix

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

sys.path.insert(0, str(Path(__file__).parent.parent))

from shared_validation.strong_search import (
    find_strong_codes_phase1,
    find_strong_codes_phase2,
    find_strong_codes_phase3,
    summarize_results,
)
from shared_validation.strong_fixer import (
    preview_file,
    preview_family,
    apply_fixes,
    FixAction,
)
from shared_validation.strong_balance_fixer import (
    preview_balance_fixes,
    apply_balance_fixes,
    validate_after_fix,
)
from shared_validation.lexicon_source import StrongsLexiconSource
from shared_validation.family_resolver import (
    _resolve_discovery_family,
    _resolve_encounters_family,
)


def _find_nearby_script(text: str, pos: int, window: int = 80) -> dict:
    start = max(0, pos - window)
    end = min(len(text), pos + window)
    snippet = text[start:end]
    greek = re.findall(r'[\u0370-\u03FF\u1F00-\u1FFF]+', snippet)
    hebrew = re.findall(r'[\u0590-\u05FF]+', snippet)
    result = {}
    if greek:
        result["greek"] = list(dict.fromkeys(greek))
    if hebrew:
        result["hebrew"] = list(dict.fromkeys(hebrew))
    return result


def analyze_file(filepath: str, lex: StrongsLexiconSource = None):
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
                in_p1 = any(r.start == p.start and r.end == p.end for p in p1)
                nearby = _find_nearby_script(text, r.start)
                matches.append({
                    "field_path": f"cards[{i}].{key}",
                    "code": r.code,
                    "matched_text": match,
                    "start": r.start,
                    "end": r.end,
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


def print_matches(matches: list):
    if not matches:
        print("  (no Strong codes found)")
        return
    for m in matches:
        print(f'\n{"─"*70}')
        print(f'  Field: {m["field_path"]}')
        print(f'  Code:  {m["code"]}  ({m["phase"]})')
        print(f'  Match: "{m["matched_text"]}"  (pos={m["start"]}-{m["end"]})')
        if m["lexicon_found"]:
            print(f'  Lexicon:  lemma="{m["lexicon_lemma"]}"  translit="{m["lexicon_translit"]}"')
        if m["nearby_script"]:
            for script, words in m["nearby_script"].items():
                print(f'  Nearby {script}: {", ".join(words)}')
        ctx_before = m["text_before"][-80:] if len(m["text_before"]) > 80 else m["text_before"]
        ctx_after = m["text_after"][:80] if len(m["text_after"]) > 80 else m["text_after"]
        print(f'  Before ({len(m["text_before"])} chars): ...{ctx_before}')
        print(f'  After  ({len(m["text_after"])} chars):  {ctx_after}...')
    print(f'\n{"─"*70}')
    print(f'  Total: {len(matches)} match(es)')


def print_preview(actions: list, filepath: str = ""):
    """Print a clean preview of what will change."""
    fixes = [a for a in actions if a.status == "fix"]
    skips = [a for a in actions if a.status == "skip"]

    if filepath:
        print(f'\n{"─"*70}')
        print(f'  File: {filepath}')

    if fixes:
        print(f'  Fixes ({len(fixes)}):')
        for a in fixes:
            with open(a.filepath, encoding="utf-8") as f:
                data = json.load(f)
            from shared_validation.strong_fixer import _get_field
            text = _get_field(data, a.field_path)
            before = text[:a.start]
            after = text[a.end:]
            ctx_before = before[-60:] if len(before) > 60 else before
            ctx_after = after[:60] if len(after) > 60 else after
            print(f'    {a.code:8s}  "{a.old:25s}" → "{a.new}"')
            print(f'    {"":8s}  {"":25s}  ...{ctx_before}{a.old}{ctx_after}...')
            print(f'    {"":8s}  {"":25s}  ...{ctx_before}{a.new}{ctx_after}...')
    else:
        print(f'  No fixes needed.')

    if skips:
        print(f'  Already correct: {len(skips)}')

    if filepath:
        print(f'{"─"*70}')


def print_family_preview(family_preview: dict, study_id: str):
    """Print preview across all languages in a family."""
    total_fixes = sum(len(v) for v in family_preview.values())
    total_langs = len(family_preview)

    print(f'\n{"="*70}')
    print(f'  Family: {study_id}')
    print(f'  Languages with fixes: {total_langs}/{total_langs}')
    print(f'  Total fixes: {total_fixes}')
    print(f'{"="*70}')

    for lang, actions in sorted(family_preview.items()):
        print(f'\n  {lang}:')
        for a in actions:
            print(f'    {a.code:8s}  "{a.old:25s}" → "{a.new}"  ({a.field_path})')


def _run():
    parser = argparse.ArgumentParser(description="Search, preview, and fix Strong codes")
    parser.add_argument("filepath", nargs="?", help="Path to a single JSON file")
    parser.add_argument("--family", help="Search/fix one family (all language versions)")
    parser.add_argument("--type", default="discovery", choices=["discovery", "encounters"])
    parser.add_argument("--dir", help="Search all JSON files in a directory")
    parser.add_argument("--all", action="store_true", help="Search all discovery + encounters")
    parser.add_argument("--preview", action="store_true", help="Preview fixes without applying")
    parser.add_argument("--fix", action="store_true", help="Apply fixes")
    parser.add_argument("--preview-balance", action="store_true", help="Preview balance fixes")
    parser.add_argument("--fix-balance", action="store_true", help="Apply balance fixes")
    parser.add_argument("--summary", action="store_true", help="Show only summary")

    args = parser.parse_args()
    lex = StrongsLexiconSource()

    # --preview or --fix mode (Strong codes)
    if args.preview or args.fix:
        if args.filepath:
            actions = preview_file(args.filepath)
            if args.preview:
                print_preview(actions, args.filepath)
            if args.fix:
                result = apply_fixes(args.filepath, actions)
                print(f"  Applied {result.applied} fix(es) to {args.filepath}")
                if result.failed:
                    print(f"  ⚠ {result.failed} fix(es) FAILED to apply (old text no longer matched)")

        elif args.family:
            family_preview = preview_family(args.family, args.type)
            if args.preview:
                print_family_preview(family_preview, args.family)
            if args.fix:
                total = 0
                total_failed = 0
                for lang, actions in family_preview.items():
                    fp = actions[0].filepath
                    result = apply_fixes(fp, actions)
                    total += result.applied
                    total_failed += result.failed
                    msg = f"  Applied {result.applied} fix(es) to {lang}"
                    if result.failed:
                        msg += f" (⚠ {result.failed} FAILED)"
                    print(msg)
                print(f"  Total: {total} fix(es) across {len(family_preview)} languages")
                if total_failed:
                    print(f"  ⚠ {total_failed} fix(es) FAILED to apply across the run")

        elif args.dir:
            for fp in sorted(glob.glob(os.path.join(args.dir, "**/*.json"), recursive=True)):
                actions = preview_file(fp)
                fixes = [a for a in actions if a.status == "fix"]
                if fixes:
                    if args.preview:
                        print_preview(actions, fp)
                    if args.fix:
                        result = apply_fixes(fp, actions)
                        print(f"  Applied {result.applied} fix(es) to {fp}")
                        if result.failed:
                            print(f"  ⚠ {result.failed} fix(es) FAILED to apply")

        elif args.all:
            for dirpath in ["discovery", "encounters"]:
                for fp in sorted(glob.glob(os.path.join(dirpath, "**/*.json"), recursive=True)):
                    actions = preview_file(fp)
                    fixes = [a for a in actions if a.status == "fix"]
                    if fixes:
                        if args.preview:
                            print_preview(actions, fp)
                        if args.fix:
                            result = apply_fixes(fp, actions)
                            print(f"  Applied {result.applied} fix(es) to {fp}")
                            if result.failed:
                                print(f"  ⚠ {result.failed} fix(es) FAILED to apply")
        else:
            parser.print_help()
        return

    # Search mode (no preview/fix)
    if args.preview_balance or args.fix_balance:
        if not args.filepath:
            parser.error("--preview-balance and --fix-balance require a JSON filepath")
        actions = preview_balance_fixes(args.filepath)
        if args.preview_balance:
            print(f"Balance fixes ({len(actions)}) for {args.filepath}:")
            for action in actions:
                print(f"  {action.issue_type}: {action.old!r} → {action.new!r} ({action.field_path})")
        if args.fix_balance:
            result = apply_balance_fixes(args.filepath, actions)
            is_clean, remaining = validate_after_fix(args.filepath)
            print(f"Applied {result.applied} balance fix(es) to {args.filepath}")
            if result.failed:
                print(f"WARNING: {result.failed} balance fix(es) failed to apply")
            print(f"Validation: {'clean' if is_clean else f'{remaining} issue(s) remain'}")
        return

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
            print(f"Study '{args.family}' not found")
            return
        for lang in sorted(family.keys()):
            fp = str(family[lang])
            matches = analyze_file(fp, lex)
            if matches:
                print(f"\n  {lang}: {os.path.basename(fp)} — {len(matches)} match(es)")
                for m in matches:
                    print(f'    {m["code"]:8s}  "{m["matched_text"]:25s}"  {m["field_path"]}')
                all_matches.extend(matches)
        print(f'\n  Total: {len(all_matches)} match(es) across {len(family)} languages')

    elif args.dir:
        for fp in sorted(glob.glob(os.path.join(args.dir, "**/*.json"), recursive=True)):
            matches = analyze_file(fp, lex)
            if matches:
                print(f"\n{os.path.basename(fp):50s} {len(matches):2d} match(es)")
                for m in matches:
                    print(f'  {m["code"]:8s}  "{m["matched_text"]:25s}"  {m["field_path"]}')
                all_matches.extend(matches)
        print(f'\n  Total: {len(all_matches)} match(es)')

    elif args.all:
        for dirpath in ["discovery", "encounters"]:
            for fp in sorted(glob.glob(os.path.join(dirpath, "**/*.json"), recursive=True)):
                matches = analyze_file(fp, lex)
                if matches:
                    print(f"\n{os.path.basename(fp):50s} {len(matches):2d} match(es)")
                    for m in matches:
                        print(f'  {m["code"]:8s}  "{m["matched_text"]:25s}"  {m["field_path"]}')
                    all_matches.extend(matches)
        print(f'\n  Total: {len(all_matches)} match(es)')

    else:
        parser.print_help()


if __name__ == "__main__":
    _run()
