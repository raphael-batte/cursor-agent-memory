"""Cursor agent-transcripts jsonl adapter — isolated from distill CLI."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

USER_QUERY_RE = re.compile(r"<user_query>\s*(.*?)\s*</user_query>", re.S)
REDACTED_MARKERS = ("[REDACTED]", "<image_files>", "<open_and_recently_viewed_files>")


class TranscriptSchemaError(Exception):
    """Raised when jsonl has no parseable Cursor user messages."""


@dataclass
class ParseStats:
    lines_read: int = 0
    json_lines: int = 0
    user_rows: int = 0
    text_blocks: int = 0


_UNSAFE_COMPONENT = re.compile(r"[^A-Za-z0-9._-]")


def safe_path_component(name: str, *, fallback: str = "unknown") -> str:
    """Reduce a value to one filesystem-safe path component.

    Drops directory separators and neutralizes traversal (``..``) so slugs,
    uuids, or overrides derived from transcripts / CLI input cannot escape the
    hub when interpolated into a file path.
    """
    base = str(name).replace("\\", "/").split("/")[-1].strip()
    cleaned = _UNSAFE_COMPONENT.sub("-", base).strip(".-")
    return cleaned or fallback


def workspace_slug(workspace: str) -> str:
    if "-Work-" in workspace:
        raw = workspace.split("-Work-", 1)[-1]
    else:
        parts = workspace.split("-")
        raw = parts[-1] if parts else workspace
    return safe_path_component(raw, fallback="unknown")


def decode_workspace_folder_to_path(folder: str) -> str | None:
    """
    Decode Cursor ~/.cursor/projects/<folder>/ name to filesystem path.
    Cursor encodes /path/to/dir as path-to-dir (leading / dropped, / → -).
    """
    if not folder or folder == "unknown":
        return None
    if folder.startswith("/"):
        p = Path(folder).expanduser()
        try:
            return str(p.resolve()) if p.is_dir() else None
        except OSError:
            return None
    candidate = Path("/" + folder.replace("-", "/"))
    try:
        if candidate.is_dir():
            return str(candidate.resolve())
    except OSError:
        return None
    return None


def normalize_user_text(text: str) -> str:
    m = USER_QUERY_RE.search(text)
    body = (m.group(1) if m else text).strip()
    body = re.sub(r"</?user_query>", "", body, flags=re.I).strip()
    body = re.sub(r"\s+", " ", body)
    return body


def is_redacted_or_noise(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return True
    if stripped.startswith("["):
        return True
    return any(marker in stripped for marker in REDACTED_MARKERS)


def extract_raw_user_texts(jsonl: Path) -> tuple[list[str], ParseStats]:
    """Parse Cursor jsonl — raw user text before secret sanitization."""
    if not jsonl.is_file():
        raise TranscriptSchemaError(f"transcript not found: {jsonl}")

    texts: list[str] = []
    stats = ParseStats()

    for line in jsonl.read_text(encoding="utf-8", errors="replace").splitlines():
        stats.lines_read += 1
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        stats.json_lines += 1
        if obj.get("role") != "user":
            continue
        stats.user_rows += 1
        for block in obj.get("message", {}).get("content", []):
            if block.get("type") != "text":
                continue
            stats.text_blocks += 1
            text = normalize_user_text(block.get("text", ""))
            if is_redacted_or_noise(text):
                continue
            texts.append(text)

    if stats.lines_read == 0:
        raise TranscriptSchemaError(f"empty transcript: {jsonl}")
    if stats.json_lines == 0:
        raise TranscriptSchemaError(
            f"no JSON lines in transcript (unknown format?): {jsonl}"
        )
    if stats.user_rows == 0:
        raise TranscriptSchemaError(
            f"no user role rows (schema changed?): {jsonl}"
        )
    if stats.text_blocks == 0:
        raise TranscriptSchemaError(
            f"no text content blocks in user messages: {jsonl}"
        )
    if not texts:
        raise TranscriptSchemaError(
            f"only redacted/noise user messages in transcript: {jsonl}"
        )
    return texts, stats


def workspace_from_path(jsonl: Path, projects_root: Path) -> str:
    try:
        rel = jsonl.relative_to(projects_root)
        if len(rel.parts) >= 4:
            return rel.parts[0]
    except ValueError:
        pass
    return "unknown"


# uuid -> Path index cache per projects_root
_INDEX_CACHE: dict[str, tuple[float, dict[str, Path]]] = {}


def _index_mtime(projects_root: Path) -> float:
    if not projects_root.is_dir():
        return 0.0
    try:
        return projects_root.stat().st_mtime
    except OSError:
        return 0.0


def build_transcript_index(projects_root: Path) -> dict[str, Path]:
    """Map chat uuid -> newest jsonl path."""
    index: dict[str, Path] = {}
    if not projects_root.is_dir():
        return index
    for jsonl in projects_root.glob("**/agent-transcripts/**/*.jsonl"):
        if "/subagents/" in str(jsonl):
            continue
        uid = jsonl.stem
        prev = index.get(uid)
        if prev is None or jsonl.stat().st_mtime >= prev.stat().st_mtime:
            index[uid] = jsonl
    return index


def find_transcript(
    uuid: str,
    projects_root: Path,
    *,
    use_cache: bool = True,
) -> Path | None:
    needle = uuid.strip()
    if not needle:
        return None

    root_key = str(projects_root.resolve())
    mtime = _index_mtime(projects_root)

    if use_cache and root_key in _INDEX_CACHE:
        cached_mtime, cached_index = _INDEX_CACHE[root_key]
        if cached_mtime == mtime:
            return cached_index.get(needle)

    index = build_transcript_index(projects_root)
    _INDEX_CACHE[root_key] = (mtime, index)
    return index.get(needle)


def clear_transcript_cache() -> None:
    _INDEX_CACHE.clear()
