"""Tests for scripts/lib/chats_manifest.py"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from lib import chats_manifest as cm  # noqa: E402


class TestChatsManifest(unittest.TestCase):
    def test_upsert_insert_and_update(self) -> None:
        manifest: dict = {"processed": [], "pending": []}
        e1 = cm.make_processed_entry(
            chat_id="aaa",
            workspace="Users-x-Work-Foo",
            transcript_date="2026-01-01",
            summary="hello",
            distilled_to=["projects/Foo.md"],
        )
        self.assertTrue(cm.upsert_processed(manifest, e1))
        self.assertFalse(cm.upsert_processed(manifest, {**e1, "summary": "updated"}))
        self.assertEqual(manifest["processed"][0]["summary"], "updated")

    def test_primary_project_rel_prefers_manifest(self) -> None:
        manifest = {
            "processed": [
                {"id": "x", "distilled_to": ["projects/other-app.md", "handoff/x.md"]}
            ]
        }
        rel = cm.primary_project_rel(manifest, "x", workspace_slug="example-app")
        self.assertEqual(rel, "projects/other-app.md")

    def test_primary_project_rel_override(self) -> None:
        rel = cm.primary_project_rel({}, "new", workspace_slug="example-app", override="custom-site")
        self.assertEqual(rel, "projects/custom-site.md")

    def test_count_chats(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "manifest.json"
            path.write_text(
                '{"processed":[{"id":"a"},{"id":"b"}],"pending":[]}',
                encoding="utf-8",
            )
            p, pend, total = cm.count_chats(path, total_transcripts=5)
            self.assertEqual((p, pend, total), (2, 3, 5))


if __name__ == "__main__":
    unittest.main()
