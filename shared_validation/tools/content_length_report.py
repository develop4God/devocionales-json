"""content_length_report.py — STANDALONE, opt-in diagnostic. Reports per-card prose
length ratios across every language file of one content id, against one baseline
language. Not wired into any validator entrypoint, not imported by family_check.py or
any validate_*.py script, not part of any CI gate — run it manually, read its output,
decide for yourself whether a flagged card is a real translation gap or legitimate
script-density brevity.

Why this exists, and why it's a report and not a check: no validator in this corpus
compares prose *length/substance* across sibling language files, only structural key
parity (family_check.py's check_key_parity/check_drift) — a card can be a fraction of
its siblings' length and still pass every existing check (confirmed 2026-08-03 on
zechariah_14_return_001: ar/fil cards were as thin as 21-38% of en's length with zero
findings anywhere).

An automated pass/fail threshold was tried and rejected for this: raw character-ratio
overlaps between a language's legitimate script-density brevity (zh dips to 22% of en
on a dense numbered-list card) and an actual incomplete-translation bug (ar's 31-38%,
fil's 21%) — the same number means different things in different files depending on
how that specific card's content happens to be structured. No single threshold (fixed,
or relative to a language's own median) can cleanly separate the two without either
missing real gaps or flagging legitimate dense-script content. This script reports the
ratios and lets a human read the flagged card before deciding.

Usage:
    python3 shared_validation/content_length_report.py <content_type> <content_id> [--baseline en] [--threshold 0.5]
    python3 shared_validation/content_length_report.py discovery zechariah_14_return_001
    python3 shared_validation/content_length_report.py encounters peters_restoration_001 --baseline es
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from shared_validation.checks.family_resolver import RESOLVERS
from shared_validation.checks.text_checks import iter_strings

YLW, CYN, RST = "\033[93m", "\033[96m", "\033[0m"


def _card_prose_length(card: dict) -> int:
    """Length of the single longest string leaf in one card — a schema-agnostic
    proxy for 'how much prose was actually written here' (discovery cards use
    `content`, encounters cards use `narrative`/`reflection`/`content` depending
    on card type; the main prose field is always by far the longest string on
    any card of either content type). Deliberately max(), not sum(), of every
    string leaf: summing pulls in title/subtitle/revelation_key, which are
    short and roughly constant length regardless of how much the main prose
    field was cut, diluting the exact ratio drop this report needs to show.
    """
    return max((len(value) for _, value in iter_strings(card)), default=0)


def report(
    content_type: str, content_id: str, baseline_lang: str, threshold: float
) -> None:
    resolver = RESOLVERS.get(content_type)
    if resolver is None:
        print(
            f"Unknown content type '{content_type}' — expected one of {list(RESOLVERS)}"
        )
        sys.exit(2)
    family = resolver(content_id)
    if not family:
        print(f"No '{content_id}' found for content type '{content_type}'")
        sys.exit(2)

    loaded = {}
    for lang, path in family.items():
        if not path.exists():
            continue
        loaded[lang] = json.loads(path.read_text(encoding="utf-8"))

    if baseline_lang not in loaded:
        print(f"Baseline language '{baseline_lang}' not found among: {sorted(loaded)}")
        sys.exit(2)

    baseline_cards = loaded[baseline_lang].get("cards", [])
    baseline_lengths = [_card_prose_length(c) for c in baseline_cards]

    print(f"\n{'=' * 70}")
    print(f"  CONTENT LENGTH REPORT — {content_id} (baseline: {baseline_lang})")
    print(f"{'=' * 70}")

    any_flag = False
    for lang in sorted(loaded):
        if lang == baseline_lang:
            continue
        cards = loaded[lang].get("cards", [])
        indexed_ratios = []
        for i, base_len in enumerate(baseline_lengths):
            if i >= len(cards) or base_len == 0:
                continue
            length = _card_prose_length(cards[i])
            if length == 0:
                continue
            indexed_ratios.append((i, length, base_len))
        if len(indexed_ratios) < 3:
            print(f"\n{CYN}{lang}{RST}: too few comparable cards, skipped")
            continue
        sorted_ratios = sorted(length / base for _, length, base in indexed_ratios)
        lang_median = sorted_ratios[len(sorted_ratios) // 2]
        print(
            f"\n{CYN}{lang}{RST} (own median ratio to {baseline_lang}: {lang_median:.0%})"
        )
        for i, length, base_len in indexed_ratios:
            ratio = length / base_len
            flag = ratio < lang_median * threshold
            marker = f"  {YLW}<< possible gap{RST}" if flag else ""
            any_flag = any_flag or flag
            print(f"  card[{i + 1}]: {length} / {base_len} chars ({ratio:.0%}){marker}")

    print(f"\n{'=' * 70}")
    if any_flag:
        print(
            f"{YLW}Flagged cards are relative outliers within their own file only — "
            f"read each one against {baseline_lang} before concluding it's a real "
            f"gap. A language-wide decline (every card thin, none an outlier "
            f"relative to the others) will NOT be flagged here — read the raw "
            f"ratios above, not just the markers.{RST}"
        )
    else:
        print(
            "No relative outliers found. This is not proof of completeness — see this script's docstring."
        )
    print(f"{'=' * 70}\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("content_type", choices=sorted(RESOLVERS))
    parser.add_argument("content_id")
    parser.add_argument("--baseline", default="en")
    parser.add_argument("--threshold", type=float, default=0.5)
    args = parser.parse_args()
    report(args.content_type, args.content_id, args.baseline, args.threshold)


if __name__ == "__main__":
    main()
