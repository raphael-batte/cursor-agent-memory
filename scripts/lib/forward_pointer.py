"""Extract forward pointer (next step) from transcript tail — replaces repo handoff."""

from __future__ import annotations

import json
import re
from pathlib import Path

from lib.secrets_guard import is_terminal_noise, sanitize_message
from lib.transcript_cursor import is_redacted_or_noise, normalize_user_text

MAX_POINTER_LEN = 240
MIN_POINTER_LEN = 12

NO_POINTER_MARKER = "_No forward pointer._"
STALE_POINTER_PREFIX = "[?]"

# Ordered — first match wins within _match_patterns.
# Non-ASCII cue words use \\u escapes (framework source stays English-only).
_LINE_PATTERNS = [
    re.compile(
        r"(?:next\s+step[s]?|"
        r"\u0441\u043b\u0435\u0434\u0443\u044e\u0449(?:\u0438\u0439|\u0438\u043c)\s+"
        r"\u0448\u0430\u0433(?:\u043e\u043c)?)\s*[:—\-]\s*(.+)",
        re.I | re.S,
    ),
    re.compile(
        r"(?:^|\n)\s*(?:\d+\.|[-*•])\s*"
        r"(?:next|\u0434\u0430\u043b\u0435\u0435|\u0437\u0430\u0442\u0435\u043c|"
        r"\u0441\u043b\u0435\u0434\u0443\u0449(?:\u0438\u0439|\u0438\u043c)?)\s*[:—\-]?\s*(.+)",
        re.I | re.S,
    ),
    re.compile(
        r"(?:\u0440\u0435\u043a\u043e\u043c\u0435\u043d\u0434\u0443\u044e|\u043b\u043e\u0433\u0438\u0447\u043d\u043e|"
        r"\u0441\u0442\u043e\u0438\u0442|\u043c\u043e\u0436\u043d\u043e)\s+"
        r"(?:\u0441\u043b\u0435\u0434\u0443\u044e\u0449(?:\u0438\u043c|\u0438\u0439)?|"
        r"\u043d\u0430\u0447\u0430\u0442\u044c|\u043f\u0440\u043e\u0434\u043e\u043b\u0436\u0438\u0442\u044c|"
        r"\u0438\u0434\u0442\u0438)\s*[:\-]?\s*(.+)",
        re.I | re.S,
    ),
    re.compile(
        r"(?:if you want to continue|to continue|start with)\s*[:—\-]?\s*(.+)",
        re.I | re.S,
    ),
]

_COMMITMENT_PATTERN = re.compile(
    r"(?:^|\b)(?:"
    r"ok(?:ay)?\s*,?\s*(?:then\s+)?|"
    r"(?:let's|lets)\s+(?:do|start)\s+|"
    r"go\s+with\s+|"
    r"\u043e\u043a(?:\u0435\u0439)?\s*,?\s*(?:\u0442\u043e\u0433\u0434\u0430\s+)?|"
    r"(?:\u0441\u0434\u0435\u043b\u0430\u0435\u043c|\u0434\u0435\u043b\u0430\u0435\u043c|"
    r"\u0431\u0435\u0440\u0451\u043c|\u0431\u0435\u0440\u0435\u043c|"
    r"\u0438\u0434\u0451\u043c\s+\u0441|\u0438\u0434\u0435\u043c\s+\u0441)"
    r")\s*(.+)",
    re.I | re.S,
)

_ACTION_HINT = re.compile(
    r"(?:\bcd\s+|\bflutter\s+|\bnpm\s+|\bpython3?\s+|\bbash\s+|\brun\s+|\./scripts/|"
    r"device\s+QA|\bdeploy\b|\bcommit\b)",
    re.I,
)


def _clean_candidate(text: str) -> str | None:
    line = re.sub(r"\s+", " ", text.strip())
    line = re.sub(r"^[-*•]\s+", "", line)
    if len(line) < MIN_POINTER_LEN:
        return None
    if len(line) > MAX_POINTER_LEN:
        line = line[: MAX_POINTER_LEN - 3].rstrip() + "..."
    clean, _n = sanitize_message(line)
    if not clean:
        return None
    return clean


def _match_patterns(blob: str) -> str | None:
    for pat in _LINE_PATTERNS:
        m = pat.search(blob)
        if m:
            cand = _clean_candidate(m.group(1).split("\n")[0])
            if cand:
                return cand
    return None


def _match_commitment(blob: str) -> str | None:
    m = _COMMITMENT_PATTERN.search(blob)
    if not m:
        return None
    return _clean_candidate(m.group(1).split("\n")[0])


def _try_user_text(blob: str) -> str | None:
    norm = normalize_user_text(blob).strip()
    if not norm or is_terminal_noise(norm):
        return None
    hit = _match_commitment(norm)
    if hit:
        return hit
    hit = _match_patterns(norm)
    if hit:
        return hit
    if "?" not in norm and _ACTION_HINT.search(norm):
        return _clean_candidate(norm)
    return None


def _assistant_text_blocks(jsonl: Path, *, tail_rows: int = 12) -> list[str]:
    """Last N assistant text messages from Cursor jsonl."""
    if not jsonl.is_file():
        return []
    rows: list[str] = []
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
        if parts:
            rows.append("\n".join(parts))
    return rows[-tail_rows:]


def _last_raw_user_text(jsonl: Path) -> str | None:
    """Last user message from raw jsonl (not distill extract sampling)."""
    if not jsonl.is_file():
        return None
    last: str | None = None
    for line in jsonl.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if obj.get("role") != "user":
            continue
        for block in obj.get("message", {}).get("content", []):
            if block.get("type") != "text":
                continue
            text = normalize_user_text(block.get("text", ""))
            if text and not is_redacted_or_noise(text):
                last = text
    if not last:
        return None
    clean, _n = sanitize_message(last)
    return clean


def _user_tail_from_extract(extract: dict, *, n: int = 3) -> list[str]:
    msgs = extract.get("user_messages") or []
    return [m for m in msgs[-n:] if isinstance(m, str) and m.strip()]


def extract_forward_pointer(extract: dict) -> str | None:
    """
    Heuristic next-step from transcript tail.
    Priority: last raw user (commitment) → user patterns → assistant patterns
    → extract user fallback → assistant action-hint (lowest).
    """
    source = extract.get("source_path")
    jsonl = Path(str(source)).expanduser() if source else None

    if jsonl and jsonl.is_file():
        last_user = _last_raw_user_text(jsonl)
        if last_user:
            hit = _try_user_text(last_user)
            if hit:
                return hit

        for blob in reversed(_assistant_text_blocks(jsonl)):
            hit = _match_patterns(blob)
            if hit:
                return hit

        for blob in reversed(_assistant_text_blocks(jsonl)):
            paras = [p.strip() for p in blob.split("\n\n") if p.strip()]
            if not paras:
                continue
            last = paras[-1]
            if _ACTION_HINT.search(last):
                cand = _clean_candidate(last.split("\n")[0])
                if cand:
                    return cand

    for msg in reversed(_user_tail_from_extract(extract)):
        hit = _try_user_text(msg)
        if hit:
            return hit

    return None
