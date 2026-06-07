"""Central thresholds for agent-memory scripts."""

from __future__ import annotations

from typing import Any

# Distill
MAX_DISTILL_MESSAGES = 30
AUTO_SPREAD_THRESHOLD = 50

# Layer rotation / verify
MAX_HANDOFF_LINES = 80
MAX_LAYER_FILE_LINES = 100
ROTATION_WARN_LINES = 80

# Secrets (strict / entropy mode)
ENTROPY_MIN_LENGTH = 24
ENTROPY_MIN_BITS = 4.5

DEFAULT_KEYWORDS = (
    "deploy",
    "decision",
    "prod",
    "migration",
    "docker",
    "ssl",
    "canonical",
    "architecture",
)

# Cross-layer overlap: domain tokens too common to signal duplication
DOMAIN_STOPWORDS = frozenset(
    {
        "deploy",
        "deployment",
        "docker",
        "branch",
        "merge",
        "test",
        "tests",
        "ci",
        "fix",
        "prod",
        "production",
        "staging",
        "commit",
        "push",
        "pull",
        "repo",
        "github",
        "workflow",
        "build",
        "run",
        "file",
        "files",
        "code",
        "project",
        "memory",
        "agent",
        "cursor",
        "script",
        "scripts",
    }
)

CROSS_LAYER_MAX_DF = 2
CROSS_LAYER_MIN_SHARED_BIGRAMS = 2


def load_thresholds(hub_config: dict[str, Any] | None = None) -> dict[str, int]:
    """Merge hub config.json thresholds over framework defaults."""
    out = {
        "max_distill_messages": MAX_DISTILL_MESSAGES,
        "auto_spread_threshold": AUTO_SPREAD_THRESHOLD,
        "max_handoff_lines": MAX_HANDOFF_LINES,
        "max_layer_file_lines": MAX_LAYER_FILE_LINES,
        "rotation_warn_lines": ROTATION_WARN_LINES,
    }
    if not hub_config:
        return out
    custom = hub_config.get("thresholds") or {}
    if isinstance(custom, dict):
        for key in out:
            if key in custom and isinstance(custom[key], int):
                out[key] = custom[key]
    return out
