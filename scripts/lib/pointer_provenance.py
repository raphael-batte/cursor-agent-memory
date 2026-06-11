"""Pointer provenance classes and curated Next step markers."""

from __future__ import annotations

import re
from typing import Any

CURATED_POINTER_PREFIX = "[curated]"
LIVE_POINTER_SOURCES = frozenset({"user_commitment", "todo_state"})
PROVENANCE_CURATED = "curated"
PROVENANCE_LIVE = "live"
PROVENANCE_AUTO = "auto"

_CURATED_RE = re.compile(r"^\[curated\]\s*", re.I)


def pointer_provenance_class(source: str) -> str:
    if source in LIVE_POINTER_SOURCES:
        return PROVENANCE_LIVE
    return PROVENANCE_AUTO


def strip_curated_marker(bullet: str) -> str:
    return _CURATED_RE.sub("", bullet.strip()).strip()


def is_curated_next_step(bullet: str) -> bool:
    return bool(_CURATED_RE.match(bullet.strip()))


def find_curated_next_step(bullets: list[str]) -> str | None:
    for bullet in bullets:
        if is_curated_next_step(bullet):
            text = strip_curated_marker(bullet)
            if text:
                return text
    return None


def format_curated_next_step(text: str) -> str:
    body = text.strip()
    if is_curated_next_step(body):
        return f"- {body}"
    return f"- {CURATED_POINTER_PREFIX} {body}"


def watermark_changed(extract: dict, manifest_entry: dict[str, Any] | None) -> bool:
    from lib.distill_watermark import watermark_needs_redistill

    if manifest_entry is None:
        return True
    wm = {
        "user_message_count": int(
            extract.get("watermark_user_count") or extract.get("user_message_count") or 0
        ),
        "tail_hash": str(extract.get("watermark_tail_hash") or ""),
    }
    return watermark_needs_redistill(manifest_entry, wm)
