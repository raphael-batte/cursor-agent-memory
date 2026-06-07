"""Tests for scripts/lib/memory_routing.py"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from lib import memory_routing as mr  # noqa: E402


class TestMemoryRouting(unittest.TestCase):
    def test_off_mode_skips_handoff(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AGENT_HANDOFF.md").write_text(
                "## Next Step\n\nDo thing\n", encoding="utf-8"
            )
            layers = mr.session_read_layers(
                handoff_mode="off",
                workspace_roots=[str(root)],
                workspace_slug="app",
            )
            self.assertEqual(layers, ["distill"])

    def test_optional_with_next_step(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AGENT_HANDOFF.md").write_text(
                "## Next Step\n\nShip v2\n", encoding="utf-8"
            )
            layers = mr.session_read_layers(
                handoff_mode="optional",
                workspace_roots=[str(root)],
                workspace_slug="app",
            )
            self.assertEqual(layers[0], "handoff")

    def test_normalize_handoff_mode(self) -> None:
        self.assertEqual(mr.normalize_handoff_mode("OFF"), "off")
        self.assertEqual(mr.normalize_handoff_mode(None), "optional")


if __name__ == "__main__":
    unittest.main()
