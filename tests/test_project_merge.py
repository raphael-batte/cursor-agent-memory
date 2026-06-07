"""Tests for scripts/lib/project_merge.py"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from lib import project_merge as pm  # noqa: E402


class TestProjectMerge(unittest.TestCase):
    def test_apply_updates_recent_not_decisions(self) -> None:
        extract = {
            "uuid": "abcd-1234",
            "workspace_slug": "app",
            "first_query": "First query text",
            "user_messages": ["Raw user message not a decision"],
            "user_message_count": 2,
            "strategy": "tail",
            "keywords_hit": ["deploy"],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "app.md"
            path.write_text(
                "# app\n_Last updated: 2020-01-01_\n\n"
                "## Decisions\n\n- Curated only\n\n"
                "## Recent\n\n- old1\n- old2\n- old3\n- old4\n",
                encoding="utf-8",
            )
            result = pm.apply_extract_to_project(path, extract, today="2026-06-06")
            text = path.read_text(encoding="utf-8")
            self.assertEqual(result["decisions_added"], 0)
            self.assertNotIn("Raw user message", text)
            self.assertNotIn("First query text", text)
            self.assertIn("Curated only", text)
            self.assertIn("2026-06-06", text)
            recent = pm._bullets(pm._parse_sections(text)[1].get("Recent", ""))
            self.assertLessEqual(len(recent), 3)

    def test_apply_leaves_summary_empty(self) -> None:
        extract = {
            "uuid": "x",
            "workspace_slug": "newapp",
            "first_query": "What is the deploy process for production?",
            "user_messages": [],
            "user_message_count": 1,
            "strategy": "all",
            "keywords_hit": [],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "newapp.md"
            pm.apply_extract_to_project(path, extract, today="2026-06-06")
            text = path.read_text(encoding="utf-8")
            sections = pm._parse_sections(text)[1]
            self.assertEqual(sections.get("Summary", "").strip(), "")
            self.assertNotIn("deploy process", text)


if __name__ == "__main__":
    unittest.main()
