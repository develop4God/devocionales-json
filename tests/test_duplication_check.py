"""test_duplication_check.py — unit tests for
shared_validation/duplication_check.py (issue #89).

Mirrors tests/test_business_rules_encounters.py's conventions: imports the
module directly (no subprocess), asserts on the returned Finding list.

Two synthetic cases per function, matching the issue's stated test plan:
  - an obviously copy-pasted sentence/paragraph across different entries
    (should flag)
  - text that only shares common vocabulary, no copy-pasted phrase (should
    NOT flag) — regression-guards the measured noise floor from the issue
    (whole-field char-ratio ~2%, longest contiguous match <=9 chars,
    Jaccard 0.14-0.18 on unrelated real encounters).

Also covers the same-entry exclusion rule for find_prose_duplicates (never
flag two cards within the same top-level entry — that's intentional reuse).
"""

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from shared_validation.duplication_check import (
    find_prose_duplicates, find_character_prompt_duplicates,
)


class TestFindProseDuplicates(unittest.TestCase):
    def test_flags_copy_pasted_sentence_across_different_entries(self):
        text_by_location = {
            'encounter_a::cards[0].narrative': (
                "The morning light fell across the empty courtyard. "
                "He knelt in the dust and said nothing at all, waiting for grace to arrive unannounced."
            ),
            'encounter_b::cards[2].content': (
                "A crowd gathered at the well before noon. "
                "He knelt in the dust and said nothing at all, waiting for grace to arrive unannounced."
            ),
        }
        findings = find_prose_duplicates(text_by_location)
        self.assertTrue(
            findings,
            "Expected a duplicate finding for the verbatim shared sentence across two different entries",
        )
        pair = {f.location_a for f in findings} | {f.location_b for f in findings}
        self.assertIn('encounter_a::cards[0].narrative', pair)
        self.assertIn('encounter_b::cards[2].content', pair)

    def test_does_not_flag_shared_vocabulary_only(self):
        # Distinct sentences that merely share common theological words
        # ("grace", "mercy", "Lord") — this is the corpus's actual measured
        # noise floor per issue #89 (whole-field ratio ~2%, longest
        # contiguous match <=9 chars on real unrelated encounters).
        text_by_location = {
            'encounter_a::cards[0].narrative': (
                "By the grace of the Lord, the fishermen returned to shore before the storm broke."
            ),
            'encounter_b::cards[1].content': (
                "Her mercy toward the beggar surprised the crowd gathered near the temple gate."
            ),
        }
        findings = find_prose_duplicates(text_by_location)
        self.assertEqual(
            findings, [],
            f"Expected no findings for merely-shared-vocabulary text, got: {findings}",
        )

    def test_does_not_flag_two_cards_within_the_same_entry(self):
        """Never flag two chunks from the same top-level entry — that's
        intentional reuse (e.g. a revelation_key echoed in its own
        completion card), per issue #89's design."""
        text_by_location = {
            'encounter_a::cards[0].narrative': (
                "He knelt in the dust and said nothing at all, waiting for grace to arrive unannounced."
            ),
            'encounter_a::cards[5].content': (
                "He knelt in the dust and said nothing at all, waiting for grace to arrive unannounced."
            ),
        }
        findings = find_prose_duplicates(text_by_location)
        self.assertEqual(
            findings, [],
            "Two chunks from the same entry must never be compared/flagged",
        )

    def test_short_chunks_below_min_length_are_not_compared(self):
        text_by_location = {
            'encounter_a::cards[0].title': "Grace.",
            'encounter_b::cards[0].title': "Grace.",
        }
        findings = find_prose_duplicates(text_by_location)
        self.assertEqual(findings, [])


class TestFindCharacterPromptDuplicates(unittest.TestCase):
    def test_flags_near_identical_character_prompts(self):
        prompts_by_character = {
            'The Woman at the Well': (
                "A woman in her mid-thirties, clearly a grown adult woman, fuller matronly build "
                "and average height, a round asymmetric face with visible fine lines at the eyes "
                "and mouth, a small nose, downturned hooded eyes with heavy lids, olive-tan "
                "sun-touched skin, dark wavy hair loose and uncovered, wearing a simple faded "
                "rust-brown wool tunic, plain and modest, no jewelry, bare feet dusty from the walk."
            ),
            'The Woman Caught in Adultery': (
                "A woman in her mid-thirties, clearly a grown adult woman, fuller matronly build "
                "and average height, a round asymmetric face with visible fine lines at the eyes "
                "and mouth, a small nose, downturned hooded eyes with heavy lids, olive-tan "
                "sun-touched skin, dark wavy hair loose and uncovered, wearing a simple faded "
                "rust-brown wool tunic, plain and modest, no jewelry, bare feet dusty from a walk."
            ),
        }
        findings = find_character_prompt_duplicates(prompts_by_character)
        self.assertTrue(findings, "Expected near-identical character prompts to be flagged")

    def test_does_not_flag_distinct_character_prompts(self):
        # Two genuinely different characters, sharing only the format/
        # boilerplate structure and common vocabulary, not physical detail.
        prompts_by_character = {
            'Bartimaeus': (
                "An older man in his sixties, thin and weathered, sunken clouded eyes, "
                "a short grey beard, wrapped in a dark patched cloak, sitting cross-legged "
                "beside a dusty roadside, a wooden staff resting across his lap."
            ),
            'Nicodemus': (
                "A distinguished man in his fifties, upright bearing, a neatly trimmed dark "
                "beard streaked with silver, wearing fine indigo-dyed robes with an embroidered "
                "hem, a phylactery visible at his brow, standing in a torch-lit courtyard at night."
            ),
        }
        findings = find_character_prompt_duplicates(prompts_by_character)
        self.assertEqual(
            findings, [],
            f"Expected no findings for genuinely distinct character prompts, got: {findings}",
        )


if __name__ == '__main__':
    unittest.main()
