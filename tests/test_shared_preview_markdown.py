"""test_shared_preview_markdown.py — unit tests for shared_preview/markdown.py,
the escape()/render_emphasis_markdown() helpers shared by
discovery/discovery_scripts/app_preview.py and
encounters/encounters_scripts/app_preview.py.

Mirrors buildEmphasisMarkdownText in devocional_nuevo's
lib/widgets/markdown_emphasis_text.dart: **bold** and *italic*, with bold
matched first so **x** is never split into two italic markers. These tests
pin that contract so a future edit to either app_preview.py (or a drift back
into per-script duplicates) gets caught here rather than only visually in a
generated preview HTML file.

Imports the module directly (not via subprocess), matching the pattern in
test_business_rules_shared_validation.py.

Does not modify any production logic — test-only.
"""

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from shared_preview.markdown import escape, render_emphasis_markdown  # noqa: E402


class TestEscape(unittest.TestCase):
    def test_escapes_html_special_characters(self):
        self.assertEqual(
            escape('<b>a & "b"</b>'),
            "&lt;b&gt;a &amp; &quot;b&quot;&lt;/b&gt;",
        )

    def test_none_returns_empty_string(self):
        self.assertEqual(escape(None), "")

    def test_plain_text_unchanged(self):
        self.assertEqual(escape("plain text"), "plain text")


class TestRenderEmphasisMarkdown(unittest.TestCase):
    def test_bold_renders_as_b_tag(self):
        self.assertEqual(
            render_emphasis_markdown("a **bold** word"),
            "a <b>bold</b> word",
        )

    def test_italic_renders_as_i_tag(self):
        self.assertEqual(
            render_emphasis_markdown("a *italic* word"),
            "a <i>italic</i> word",
        )

    def test_bold_and_italic_together(self):
        self.assertEqual(
            render_emphasis_markdown("a **bold** and *italic* word"),
            "a <b>bold</b> and <i>italic</i> word",
        )

    def test_bold_is_not_split_into_two_italic_markers(self):
        self.assertEqual(render_emphasis_markdown("**bold**"), "<b>bold</b>")

    def test_multiple_bold_segments(self):
        self.assertEqual(
            render_emphasis_markdown("**one** and **two**"),
            "<b>one</b> and <b>two</b>",
        )

    def test_multiple_italic_segments(self):
        self.assertEqual(
            render_emphasis_markdown("*one* and *two*"),
            "<i>one</i> and <i>two</i>",
        )

    def test_plain_text_unchanged(self):
        self.assertEqual(render_emphasis_markdown("plain text"), "plain text")

    def test_none_returns_empty_string(self):
        self.assertEqual(render_emphasis_markdown(None), "")

    def test_newlines_become_br_tags(self):
        self.assertEqual(
            render_emphasis_markdown("line one\nline two"),
            "line one<br>line two",
        )

    def test_html_special_characters_are_escaped_before_emphasis(self):
        self.assertEqual(
            render_emphasis_markdown("a **<script>** tag"),
            "a <b>&lt;script&gt;</b> tag",
        )

    def test_unmatched_single_asterisk_left_as_literal_text(self):
        self.assertEqual(render_emphasis_markdown("5 * 3 = 15"), "5 * 3 = 15")

    def test_two_unpaired_asterisks_are_greedily_treated_as_italic(self):
        # Inherited from the Dart regex this mirrors (buildEmphasisMarkdownText):
        # a lone `*` isn't distinguishable from an open italic marker, so two
        # of them in the same string get paired even when neither was meant
        # as emphasis. Not something this script can fix independently of
        # the Dart source it mirrors -- documented here as known behavior.
        self.assertEqual(
            render_emphasis_markdown("5 * 3 = 15 and 2 * 4 = 8"),
            "5 <i> 3 = 15 and 2 </i> 4 = 8",
        )


if __name__ == "__main__":
    unittest.main()
