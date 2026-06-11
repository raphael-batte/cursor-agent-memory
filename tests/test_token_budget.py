"""Tests for scripts/lib/token_budget.py and hub threshold overrides."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from lib import token_budget as tb  # noqa: E402
from lib.defaults import load_thresholds  # noqa: E402


class TestTokenBudget(unittest.TestCase):
    def test_select_by_importance_respects_budget(self) -> None:
        messages = [f"message number {i} with deploy keyword" for i in range(40)]
        picked = tb.select_by_importance(
            messages, max_messages=20, token_budget=200, always_include_first=True
        )
        tokens = sum(tb.estimate_tokens(m) for m in picked)
        self.assertLessEqual(tokens, 200)
        self.assertEqual(picked[0], messages[0])

    def test_hub_threshold_override(self) -> None:
        thresholds = load_thresholds({"thresholds": {"distill_token_budget": 8000}})
        self.assertEqual(thresholds["distill_token_budget"], 8000)


if __name__ == "__main__":
    unittest.main()
