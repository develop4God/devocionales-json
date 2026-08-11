"""test_shared_preview_unrendered.py — unit tests for
shared_preview/unrendered.py, the TrackedDict/find_unrendered_keys gate
shared by discovery/discovery_scripts/app_preview.py and
encounters/encounters_scripts/app_preview.py.

The gate replaces hand-maintained "which fields does this script render"
allowlists: TrackedDict records every key actually read during rendering,
and find_unrendered_keys() diffs that against populated keys, so a new
JSON field can never go silently undisplayed -- it either gets read by the
renderer, is explicitly listed in ignored_keys as deliberately non-visual,
or shows up as a warning.

Imports the module directly (not via subprocess), matching the pattern in
test_shared_preview_markdown.py.

Does not modify any production logic -- test-only.
"""

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from shared_preview.unrendered import TrackedDict, find_unrendered_keys  # noqa: E402


class TestTrackedDict(unittest.TestCase):
    def test_getitem_marks_key_accessed(self):
        d = TrackedDict({"a": 1, "b": 2})
        _ = d["a"]
        self.assertEqual(d.accessed_keys, {"a"})

    def test_get_marks_key_accessed(self):
        d = TrackedDict({"a": 1, "b": 2})
        d.get("a")
        self.assertEqual(d.accessed_keys, {"a"})

    def test_get_with_missing_key_still_marks_accessed(self):
        d = TrackedDict({"a": 1})
        d.get("missing")
        self.assertIn("missing", d.accessed_keys)

    def test_contains_marks_key_accessed(self):
        d = TrackedDict({"a": 1})
        self.assertTrue("a" in d)
        self.assertIn("a", d.accessed_keys)

    def test_unaccessed_keys_not_recorded(self):
        d = TrackedDict({"a": 1, "b": 2})
        d.get("a")
        self.assertNotIn("b", d.accessed_keys)

    def test_nested_dict_is_wrapped_and_tracked_independently(self):
        d = TrackedDict({"outer": {"inner": 1, "other": 2}})
        nested = d.get("outer")
        self.assertIsInstance(nested, TrackedDict)
        nested.get("inner")
        self.assertEqual(nested.accessed_keys, {"inner"})
        # accessing "outer" on the parent does not mark its children accessed
        self.assertEqual(find_unrendered_keys(nested), ["other"])

    def test_list_of_dicts_is_wrapped_elementwise(self):
        d = TrackedDict({"items": [{"a": 1, "b": 2}]})
        items = d.get("items")
        self.assertIsInstance(items[0], TrackedDict)
        items[0].get("a")
        self.assertEqual(find_unrendered_keys(items[0]), ["b"])

    def test_repeated_get_returns_same_wrapped_object_with_access_history(self):
        # Regression: a report script that scans `data` again AFTER a
        # render pass already read from it must see that render pass's
        # accessed_keys, not a fresh, empty-history wrapper.
        d = TrackedDict({"cards": [{"title": "x", "dropped": "y"}]})
        first_cards = d.get("cards")
        first_cards[0].get("title")  # simulates render_card() reading title
        second_cards = d.get("cards")  # simulates a report re-scanning later
        self.assertIs(first_cards[0], second_cards[0])
        self.assertEqual(find_unrendered_keys(second_cards[0]), ["dropped"])


class TestFindUnrenderedKeys(unittest.TestCase):
    def test_flags_populated_key_never_read(self):
        d = TrackedDict({"title": "x", "made_up_future_field": "y"})
        d.get("title")
        self.assertEqual(find_unrendered_keys(d), ["made_up_future_field"])

    def test_no_flags_when_all_populated_keys_read(self):
        d = TrackedDict({"title": "x", "content": "y"})
        d.get("title")
        d.get("content")
        self.assertEqual(find_unrendered_keys(d), [])

    def test_empty_and_none_values_are_not_flagged(self):
        d = TrackedDict({"title": "x", "empty_str": "", "empty_list": [], "empty_dict": {}, "none_val": None})
        d.get("title")
        self.assertEqual(find_unrendered_keys(d), [])

    def test_ignored_keys_are_excluded_even_if_unread(self):
        d = TrackedDict({"title": "x", "order": 3, "type": "insight"})
        d.get("title")
        self.assertEqual(
            find_unrendered_keys(d, ignored_keys=("order", "type")), []
        )

    def test_raises_on_plain_dict_not_trackeddict(self):
        with self.assertRaises(TypeError):
            find_unrendered_keys({"title": "x"})

    def test_multiple_unrendered_keys_returned_sorted(self):
        d = TrackedDict({"title": "x", "zeta_field": "z", "alpha_field": "a"})
        d.get("title")
        self.assertEqual(
            find_unrendered_keys(d), ["alpha_field", "zeta_field"]
        )


if __name__ == "__main__":
    unittest.main()
