"""Tests for scripts/lib/forward_pointer.py"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from lib import forward_pointer as fp  # noqa: E402


class TestForwardPointer(unittest.TestCase):
    def test_pattern_next_step_en(self) -> None:
        extract = {
            "user_messages": [],
            "source_path": "",
        }
        with tempfile.TemporaryDirectory() as tmp:
            jsonl = Path(tmp) / "chat.jsonl"
            jsonl.write_text(
                json.dumps(
                    {
                        "role": "assistant",
                        "message": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": "Summary.\n\nNext step: run flutter test on device",
                                }
                            ]
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            extract["source_path"] = str(jsonl)
            hit = fp.extract_forward_pointer(extract)
            self.assertIsNotNone(hit)
            self.assertIn("flutter test", hit.lower())

    def test_user_fallback_with_action_hint(self) -> None:
        extract = {
            "user_messages": [
                "please run ./scripts/run-device.sh and record a 3 minute session"
            ],
            "source_path": "/nonexistent/chat.jsonl",
        }
        hit = fp.extract_forward_pointer(extract)
        self.assertIsNotNone(hit)
        self.assertIn("run-device", hit)


if __name__ == "__main__":
    unittest.main()
