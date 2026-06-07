"""Importance scoring for distill message selection."""

from __future__ import annotations

import re

from lib.defaults import DEFAULT_KEYWORDS

_CORRECTION = re.compile(
    r"(?:don't|do not|instead|wrong|fix|broken|regression|revert|not working|"
    r"\u043d\u0435\s+\u043d\u0430\u0434\u043e|\u0432\u043c\u0435\u0441\u0442\u043e|\u043e\u0448\u0438\u0431\u043a)",
    re.I,
)
_ACTION = re.compile(
    r"(?:\bcd\s+|\bnpm\s+|\bpython3?\s+|\bbash\s+|\./scripts/|\bdeploy\b|\bcommit\b|"
    r"\bflutter\s+|\brun\s+)",
    re.I,
)
_CODE = re.compile(r"```|`[^`]+`")


def score_message(text: str, *, index: int, total: int) -> float:
    """Higher = more important for distill sampling."""
    t = text.strip()
    if not t:
        return 0.0
    score = 0.0
    lower = t.lower()
    if len(t) >= 40:
        score += 1.0
    if len(t) >= 120:
        score += 0.5
    if any(kw in lower for kw in DEFAULT_KEYWORDS):
        score += 2.0
    if _CORRECTION.search(t):
        score += 2.5
    if _ACTION.search(t):
        score += 1.5
    if _CODE.search(t):
        score += 1.0
    if "?" in t and len(t) < 80:
        score -= 0.3
    # Recency bias — last 20% of chat gets a bump
    if total > 0 and index >= int(total * 0.8):
        score += 1.5
    elif total > 0 and index >= int(total * 0.5):
        score += 0.5
    return score


def rank_messages(messages: list[str]) -> list[tuple[int, float, str]]:
    total = len(messages)
    ranked: list[tuple[int, float, str]] = []
    for i, msg in enumerate(messages):
        ranked.append((i, score_message(msg, index=i, total=total), msg))
    ranked.sort(key=lambda r: (-r[1], -r[0]))
    return ranked


def mechanical_bullets(messages: list[str], *, max_items: int = 4) -> list[str]:
    """Short bullets from high-importance messages (map-reduce / rolling)."""
    ranked = rank_messages(messages)
    out: list[str] = []
    seen: set[str] = set()
    for _idx, _score, msg in ranked:
        snippet = re.sub(r"\s+", " ", msg.strip())
        if len(snippet) < 20:
            continue
        if len(snippet) > 160:
            snippet = snippet[:157].rstrip() + "..."
        key = snippet[:80].lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(snippet)
        if len(out) >= max_items:
            break
    return out
