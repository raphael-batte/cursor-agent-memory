"""Tests for scripts/lib/pointer_feedback.py"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from helpers import minimal_hub

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from lib.distill_metrics import read_metrics  # noqa: E402
from lib.pointer_feedback import log_session_start_pointer_feedback  # noqa: E402


class TestPointerFeedback(unittest.TestCase):
    def test_logs_hit_for_real_pointer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            hub = Path(tmp)
            minimal_hub(hub, projects=0)
            project = hub / "chats" / "projects" / "app.md"
            project.parent.mkdir(parents=True, exist_ok=True)
            project.write_text(
                "## Next step\n\n- Run smoke tests on staging\n\n## Recent\n\n",
                encoding="utf-8",
            )
            rows = log_session_start_pointer_feedback(hub, {"app"})
            self.assertEqual(rows[0]["outcome"], "hit")
            metrics = read_metrics(hub)
            self.assertTrue(any(r.get("event") == "pointer_feedback" for r in metrics))

    def test_logs_miss_for_placeholder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            hub = Path(tmp)
            project = hub / "chats" / "projects" / "app.md"
            project.parent.mkdir(parents=True, exist_ok=True)
            project.write_text(
                "## Next step\n\n- _No forward pointer._\n\n",
                encoding="utf-8",
            )
            rows = log_session_start_pointer_feedback(hub, {"app"})
            self.assertEqual(rows[0]["outcome"], "miss")


if __name__ == "__main__":
    unittest.main()
