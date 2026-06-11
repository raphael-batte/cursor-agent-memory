"""Session-start pointer feedback — did ## Next step look usable?"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from lib.chats_manifest import load_manifest, processed_by_id
from lib.forward_pointer import NO_POINTER_MARKER, STALE_POINTER_PREFIX
from lib.pointer_metrics import log_pointer_feedback
from lib.pointer_provenance import is_curated_next_step, strip_curated_marker
from lib.project_merge import _bullets, _parse_sections
from lib.transcript_cursor import safe_path_component

_PLACEHOLDER_RE = re.compile(r"^\[\?\]")


def _project_path(memory_home: Path, slug: str) -> Path:
    safe = safe_path_component(slug, fallback="project")
    return memory_home / "chats" / "projects" / f"{safe}.md"


def _pointer_from_project(project_path: Path) -> tuple[str | None, bool]:
    if not project_path.is_file():
        return None, False
    _preamble, sections = _parse_sections(
        project_path.read_text(encoding="utf-8", errors="replace")
    )
    for bullet in _bullets(sections.get("Next step", "")):
        curated = is_curated_next_step(bullet)
        text = strip_curated_marker(bullet)
        if NO_POINTER_MARKER in bullet or _PLACEHOLDER_RE.match(bullet.strip()):
            return None, curated
        if text and not bullet.strip().startswith(STALE_POINTER_PREFIX):
            return text, curated
    return None, False


def _latest_pointer_source(memory_home: Path, slug: str) -> str | None:
    manifest = load_manifest(memory_home / "chats" / "manifest.json")
    rel = f"projects/{safe_path_component(slug, fallback='project')}.md"
    best: dict[str, Any] | None = None
    for entry in processed_by_id(manifest).values():
        targets = entry.get("distilled_to") or []
        if rel not in targets:
            continue
        if best is None or str(entry.get("distilled_at") or "") >= str(
            best.get("distilled_at") or ""
        ):
            best = entry
    if best:
        src = best.get("pointer_source")
        return str(src) if src else None
    return None


def classify_pointer_outcome(
    pointer: str | None,
    *,
    curated: bool,
) -> str:
    if pointer:
        return "hit"
    if curated:
        return "miss"
    return "miss"


def log_session_start_pointer_feedback(
    memory_home: Path,
    workspace_slugs: set[str] | list[str],
) -> list[dict[str, Any]]:
    """Log pointer_feedback per open workspace slug."""
    logged: list[dict[str, Any]] = []
    for raw_slug in sorted(set(workspace_slugs)):
        slug = str(raw_slug).strip()
        if not slug:
            continue
        project_path = _project_path(memory_home, slug)
        pointer, curated = _pointer_from_project(project_path)
        if not project_path.is_file():
            outcome = "skip"
        else:
            outcome = classify_pointer_outcome(pointer, curated=curated)
        row = {
            "outcome": outcome,
            "workspace_slug": slug,
            "curated": curated,
            "pointer_source": _latest_pointer_source(memory_home, slug),
            "pointer_preview": (pointer or "")[:120] or None,
        }
        log_pointer_feedback(memory_home, row)
        logged.append(row)
    return logged
