"""Apply distill extract into chats/projects/<slug>.md (preserve language)."""

from __future__ import annotations

import re
from pathlib import Path

from lib.defaults import DEFAULT_KEYWORDS, MAX_LAYER_FILE_LINES
from lib.distill_links import recent_bullet
from lib.secrets_guard import scan_file
from lib.timestamps import now_iso

LAST_UPDATED = re.compile(r"^_Last updated:\s*.+$", re.M | re.I)
DEFAULT_SECTIONS = ("Summary", "Decisions", "Preferences", "Open threads", "Recent")


def _today() -> str:
    return now_iso()


def _parse_sections(text: str) -> tuple[str, dict[str, str]]:
    preamble_lines: list[str] = []
    sections: dict[str, list[str]] = {}
    current: str | None = None

    for line in text.splitlines():
        m = re.match(r"^##\s+(.+?)\s*$", line)
        if m:
            current = m.group(1).strip()
            sections[current] = []
            continue
        if current is None:
            preamble_lines.append(line)
        else:
            sections[current].append(line)

    preamble = "\n".join(preamble_lines).strip()
    return preamble, {k: "\n".join(v).strip() for k, v in sections.items()}


def _join_sections(preamble: str, sections: dict[str, str]) -> str:
    lines: list[str] = []
    if preamble:
        lines.append(preamble)
        lines.append("")
    for name in DEFAULT_SECTIONS:
        if name not in sections:
            continue
        lines.append(f"## {name}")
        lines.append("")
        body = sections[name].strip()
        if body:
            lines.append(body)
        lines.append("")
    for name, body in sections.items():
        if name in DEFAULT_SECTIONS:
            continue
        lines.append(f"## {name}")
        lines.append("")
        if body.strip():
            lines.append(body.strip())
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _bullets(block: str) -> list[str]:
    out: list[str] = []
    for line in block.splitlines():
        m = re.match(r"^-\s+(.*)$", line.strip())
        if m:
            out.append(m.group(1).strip())
    return out


def _format_bullets(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items if item)


def recent_line(extract: dict, today: str | None = None) -> str:
    return recent_bullet(extract, today or _today())


def decision_candidates_from_extract(
    extract: dict,
    *,
    max_items: int = 3,
    max_len: int = 200,
    min_len: int = 24,
) -> list[str]:
    """
    Heuristic decision seeds from user messages (keyword signal).
    Used only when Decisions is empty — agent should refine later.
    """
    seen: set[str] = set()
    out: list[str] = []
    for msg in extract.get("user_messages") or []:
        text = re.sub(r"\s+", " ", msg.strip())
        if len(text) < min_len:
            continue
        lower = text.lower()
        if not any(kw in lower for kw in DEFAULT_KEYWORDS):
            continue
        if len(text) > max_len:
            text = text[: max_len - 3].rstrip() + "..."
        if text in seen:
            continue
        seen.add(text)
        out.append(f"[bootstrap] {text}")
        if len(out) >= max_items:
            break
    return out


def apply_extract_to_project(
    project_path: Path,
    extract: dict,
    *,
    max_recent: int = 3,
    today: str | None = None,
    bootstrap_decisions: bool = False,
) -> dict:
    """
    Bookkeeping merge: _Last updated_ + Recent≤3.
    Optional bootstrap_decisions when ## Decisions is empty (first sync).
    Does NOT write Summary — agent curates from staging.
    Raises ValueError if merged text fails secrets scan.
    """
    day = today or _today()
    project_path.parent.mkdir(parents=True, exist_ok=True)

    if project_path.is_file():
        text = project_path.read_text(encoding="utf-8", errors="replace")
    else:
        slug = extract.get("workspace_slug", "project")
        text = (
            f"# {slug}\n"
            f"_Last updated: {day}_\n\n"
            "## Summary\n\n\n"
            "## Decisions\n\n\n"
            "## Preferences\n\n\n"
            "## Open threads\n\n\n"
            "## Recent\n\n"
        )

    if LAST_UPDATED.search(text):
        text = LAST_UPDATED.sub(f"_Last updated: {day}_", text, count=1)
    else:
        lines = text.splitlines()
        if lines:
            lines.insert(1, f"_Last updated: {day}_")
            text = "\n".join(lines) + "\n"

    preamble, sections = _parse_sections(text)

    existing_recent = _bullets(sections.get("Recent", ""))
    new_recent_line = recent_line(extract, day)
    recent_items = [new_recent_line] + [r for r in existing_recent if r != new_recent_line]
    sections["Recent"] = _format_bullets(recent_items[:max_recent])

    decisions_added = 0
    if bootstrap_decisions and not _bullets(sections.get("Decisions", "")):
        seeds = decision_candidates_from_extract(extract)
        if seeds:
            sections["Decisions"] = _format_bullets(seeds)
            decisions_added = len(seeds)

    merged = _join_sections(preamble, sections)

    tmp = project_path.with_suffix(".md.tmpcheck")
    tmp.write_text(merged, encoding="utf-8")
    try:
        hits = scan_file(tmp)
        if hits:
            raise ValueError(
                f"refusing to write project file — secrets detected: {hits[0]}"
            )
    finally:
        tmp.unlink(missing_ok=True)

    project_path.write_text(merged, encoding="utf-8")

    return {
        "project_file": str(project_path),
        "decisions_added": decisions_added,
        "recent_lines": min(len(recent_items), max_recent),
        "lines": len(merged.splitlines()),
        "over_limit": len(merged.splitlines()) > MAX_LAYER_FILE_LINES,
    }
