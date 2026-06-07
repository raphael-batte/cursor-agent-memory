"""Session read order from handoff_mode hub setting."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from lib.memory_config import load_hub_config

HANDOFF_MODES = frozenset({"off", "optional", "required"})
DEFAULT_HANDOFF_MODE = "optional"
HANDOFF_NAME = "AGENT_HANDOFF.md"
NEXT_STEP_RE = re.compile(
    r"##\s*Next Step\s*\n\s*\S",
    re.IGNORECASE | re.MULTILINE,
)


def normalize_handoff_mode(value: str | None) -> str:
    if isinstance(value, str) and value.strip().lower() in HANDOFF_MODES:
        return value.strip().lower()
    return DEFAULT_HANDOFF_MODE


def load_handoff_mode(memory_home: Path) -> str:
    cfg = load_hub_config(memory_home)
    return normalize_handoff_mode(cfg.get("handoff_mode"))


def handoff_has_next_step(path: Path) -> bool:
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8", errors="replace")
    return bool(NEXT_STEP_RE.search(text))


def find_handoff_in_roots(workspace_roots: list[str] | None) -> Path | None:
    if not workspace_roots:
        return None
    for root in workspace_roots:
        if not isinstance(root, str) or not root.strip():
            continue
        candidate = Path(root).expanduser() / HANDOFF_NAME
        if candidate.is_file():
            return candidate.resolve()
    return None


def session_read_layers(
    *,
    handoff_mode: str,
    workspace_roots: list[str] | None,
    workspace_slug: str | None = None,
) -> list[str]:
    """
    Ordered layer names for session start.
    Values: handoff, distill, global-context, feedback.
    """
    mode = normalize_handoff_mode(handoff_mode)
    handoff = find_handoff_in_roots(workspace_roots)
    use_handoff = False
    if mode == "required":
        use_handoff = handoff is not None
    elif mode == "optional":
        use_handoff = handoff is not None and handoff_has_next_step(handoff)
    # mode "off" -> never handoff

    layers: list[str] = []
    if use_handoff:
        layers.append("handoff")
    layers.append("distill")
    if not workspace_slug:
        layers.append("global-context")
    return layers


def routing_summary(memory_home: Path) -> dict[str, Any]:
    return {
        "handoff_mode": load_handoff_mode(memory_home),
        "memory_home": str(memory_home),
    }
