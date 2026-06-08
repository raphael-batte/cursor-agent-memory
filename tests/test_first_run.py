"""Tests for scripts/lib/first_run.py"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from lib import first_run as fr  # noqa: E402
from lib import memory_config as mc  # noqa: E402


class TestFirstRun(unittest.TestCase):
    def test_recommend_scope_auto_small(self) -> None:
        scan = {"pending_90d": 12, "total_chats": 50}
        scope = fr.recommend_scope(scan)
        self.assertEqual(scope, {"days": 90, "limit": 40})

    def test_recommend_scope_ask_large(self) -> None:
        scan = {"pending_90d": 100, "total_chats": 200}
        self.assertIsNone(fr.recommend_scope(scan))

    def test_mark_and_check_initialized(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            hub = Path(tmp)
            self.assertFalse(fr.is_initialized(hub))
            fr.mark_initialized(hub, {"distilled": 0})
            self.assertTrue(fr.is_initialized(hub))
            state = json.loads((hub / ".state" / "first-run.json").read_text())
            self.assertEqual(state["distilled"], 0)

    def test_write_read_scope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            hub = Path(tmp)
            fr.write_scope(hub, {"days": 7, "limit": None})
            self.assertEqual(fr.read_scope(hub), {"days": 7, "limit": None})

    def test_handle_awaiting_scope_when_large(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            plugin = Path(tmp) / "plugin"
            hub = Path(tmp) / "hub"
            plugin.mkdir()
            hub.mkdir()
            (plugin / "INSTRUCTIONS.md").write_text("#", encoding="utf-8")
            (plugin / ".cursor-plugin").mkdir()
            (plugin / ".cursor-plugin" / "plugin.json").write_text("{}", encoding="utf-8")
            anchor = Path(tmp) / "anchor.json"
            with mock.patch.object(mc, "ANCHOR_FILE", anchor):
                with mock.patch.object(mc, "memory_home_from_anchor", return_value=hub):
                    with mock.patch.object(fr, "ensure_hub", return_value={"status": "ok"}):
                        with mock.patch.object(
                            fr,
                            "scan_chat_stats",
                            return_value={
                                "pending_90d": 80,
                                "total_chats": 120,
                                "pending_180d": 90,
                                "active_90d": 80,
                                "active_180d": 100,
                            },
                        ):
                            out = fr.handle_first_run(
                                memory_home=hub,
                                plugin_root=plugin,
                            )
            self.assertEqual(out["first_run"], "awaiting_scope")
            self.assertIn("first-run-scope.py", out["user_message"])
            self.assertFalse(fr.is_initialized(hub))

    def test_apply_mechanical_auto_decisions(self) -> None:
        from lib.project_merge import apply_mechanical_auto_decisions

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "proj.md"
            extract = {
                "workspace_slug": "demo",
                "user_messages": [
                    "We decided to deploy using docker compose for production "
                    "because it simplifies the rollout process significantly."
                ],
            }
            n = apply_mechanical_auto_decisions(path, extract)
            self.assertGreaterEqual(n, 1)
            text = path.read_text(encoding="utf-8")
            self.assertIn("[auto]", text)


if __name__ == "__main__":
    unittest.main()
