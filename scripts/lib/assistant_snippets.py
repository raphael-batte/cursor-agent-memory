"""Selective assistant snippets for distill extract."""

from __future__ import annotations

import json
import re
from pathlib import Path

from lib.defaults import ASSISTANT_SNIPPET_MAX, DEFAULT_KEYWORDS
from lib.secrets_guard import sanitize_message
from lib.transcript_cursor import is_redacted_or_noise

_DECISION_LINE = re.compile(
    r"(?:decided|decision|recommend|summary|next step|deploy|architecture|"
    r"\u0440\u0435\u0448\u0435\u043d\u0438\u0435|\u0441\u043b\u0435\u0434\u0443\u044e\u0449)",
    re.I,
)


def _score_assistant(text: str) -> float:
    lower = text.lower()
    score = 0.0
    if _DECISION_LINE.search(text):
        score += 2.0
    if any(kw in lower for kw in DEFAULT_KEYWORDS):
        score += 1.5
    if len(text) >= 80:
        score += 0.5
    if "```" in text:
        score += 0.5
    return score


def extract_assistant_snippets(
    jsonl: Path,
    *,
    max_snippets: int = ASSISTANT_SNIPPET_MAX,
    tail_rows: int = 30,
) -> list[str]:
    if not jsonl.is_file():
        return []
    rows: list[tuple[float, str]] = []
    for line in jsonl.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if obj.get("role") != "assistant":
            continue
        parts: list[str] = []
        for block in obj.get("message", {}).get("content", []):
            if block.get("type") != "text":
                continue
            text = block.get("text", "").strip()
            if text and not is_redacted_or_noise(text):
                parts.append(text)
        if not parts:
            continue
        blob = "\n".join(parts)
        clean, _n = sanitize_message(blob)
        if not clean:
            continue
        score = _score_assistant(clean)
        if score <= 0:
            continue
        snippet = re.sub(r"\s+", " ", clean)
        if len(snippet) > 320:
            snippet = snippet[:317].rstrip() + "..."
        rows.append((score, snippet))

    rows = rows[-tail_rows:]
    rows.sort(key=lambda r: -r[0])
    out: list[str] = []
    seen: set[str] = set()
    for _score, snippet in rows:
        key = snippet[:100].lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(snippet)
        if len(out) >= max_snippets:
            break
    return out
