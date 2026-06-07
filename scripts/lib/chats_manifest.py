"""manifest.json helpers — shared by list-chats, distill-merge, memory-status."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from lib.timestamps import now_iso
from lib.transcript_cursor import (  # noqa: I001
    decode_workspace_folder_to_path,
    safe_path_component,
    workspace_slug,
)

_PROJECT_REL_RE = re.compile(r"projects/[A-Za-z0-9._-]+\.md")


def load_manifest(path: Path) -> dict[str, Any]:
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"processed": [], "pending": []}


def save_manifest(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def primary_project_rel(
    manifest: dict[str, Any],
    chat_id: str,
    *,
    workspace_slug: str,
    override: str | None = None,
) -> str:
    """
    Relative path under chats/ for the project markdown file.
    Prefers manifest distilled_to, then --project override, else workspace slug.
    """
    if override:
        raw = override.strip().lstrip("/")
        if raw.startswith("projects/"):
            raw = raw[len("projects/") :]
        if raw.endswith(".md"):
            raw = raw[: -len(".md")]
        return f"projects/{safe_path_component(raw, fallback='project')}.md"

    entry = processed_by_id(manifest).get(chat_id)
    if entry:
        for rel in entry.get("distilled_to") or []:
            # Only trust entries that are exactly projects/<safe-name>.md — a
            # crafted manifest must not redirect writes outside the hub.
            if isinstance(rel, str) and _PROJECT_REL_RE.fullmatch(rel):
                return rel

    return f"projects/{safe_path_component(workspace_slug, fallback='unknown')}.md"


def processed_by_id(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for entry in manifest.get("processed", []):
        if isinstance(entry, dict) and entry.get("id"):
            out[str(entry["id"])] = entry
    return out


def upsert_processed(
    manifest: dict[str, Any],
    entry: dict[str, Any],
) -> bool:
    """Insert or update processed[] entry. Returns True if newly inserted."""
    uid = entry.get("id")
    if not uid:
        raise ValueError("manifest entry requires id")

    processed = manifest.setdefault("processed", [])
    if not isinstance(processed, list):
        raise ValueError("manifest processed must be a list")

    for i, existing in enumerate(processed):
        if isinstance(existing, dict) and existing.get("id") == uid:
            merged = {**existing, **entry}
            processed[i] = merged
            return False

    processed.append(entry)
    return True


def make_processed_entry(
    *,
    chat_id: str,
    workspace: str,
    transcript_date: str,
    summary: str,
    distilled_to: list[str],
    distilled_at: str | None = None,
    transcript_available: bool | None = None,
    workspace_path: str | None = None,
) -> dict[str, Any]:
    today = distilled_at or now_iso()
    slug = workspace_slug(workspace)
    target = f"projects/{slug}.md"
    if target not in distilled_to:
        distilled_to = [target, *distilled_to]
    resolved_path = workspace_path or decode_workspace_folder_to_path(workspace)
    entry: dict[str, Any] = {
        "id": chat_id,
        "workspace": workspace,
        "date": transcript_date,
        "distilled_at": today,
        "distilled_to": distilled_to,
        "summary": summary[:140],
    }
    if resolved_path:
        entry["workspace_path"] = resolved_path
    if transcript_available is not None:
        entry["transcript_available"] = transcript_available
    return entry


def count_chats(
    manifest_path: Path,
    *,
    total_transcripts: int | None = None,
) -> tuple[int, int, int]:
    """
    Return (processed_count, pending_count, total).
    pending = total - processed_ids if total_transcripts given, else len(pending list).
    """
    if not manifest_path.is_file():
        return 0, 0, total_transcripts or 0

    manifest = load_manifest(manifest_path)
    processed_ids = {p.get("id") for p in manifest.get("processed", []) if isinstance(p, dict)}
    processed_ids.discard(None)
    n_processed = len(processed_ids)

    if total_transcripts is not None:
        return n_processed, max(0, total_transcripts - n_processed), total_transcripts

    pending_list = manifest.get("pending", [])
    n_pending = len(pending_list) if isinstance(pending_list, list) else 0
    return n_processed, n_pending, n_processed + n_pending
