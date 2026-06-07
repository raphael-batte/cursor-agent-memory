"""Cursor boundary hooks — sessionStart catch-up distill, preCompact/sessionEnd distill."""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from lib.chats_manifest import load_manifest, processed_by_id  # noqa: E402
from lib.memory_config import resolve_memory_home  # noqa: E402
from lib.pending_chats import (  # noqa: E402
    list_chats_needing_distill,
    needs_distill,
    slugs_from_workspace_roots,
)
from lib.transcript import TranscriptSchemaError, find_transcript  # noqa: E402

DEFAULT_PROJECTS_ROOT = Path.home() / ".cursor/projects"
BOUNDARY_EVENTS = frozenset({"preCompact", "sessionEnd"})
SESSION_START_CATCHUP_LIMIT = 5
SESSION_START_DAYS = 180


def chat_id_from_payload(payload: dict[str, Any]) -> str | None:
    transcript = payload.get("transcript_path")
    if isinstance(transcript, str) and transcript.strip():
        stem = Path(transcript).stem
        if stem:
            return stem
    conversation_id = payload.get("conversation_id")
    if isinstance(conversation_id, str) and conversation_id.strip():
        return conversation_id.strip()
    session_id = payload.get("session_id")
    if isinstance(session_id, str) and session_id.strip():
        return session_id.strip()
    return None


def resolve_transcript_jsonl(
    payload: dict[str, Any],
    *,
    memory_home: Path,
    projects_root: Path,
) -> Path | None:
    transcript = payload.get("transcript_path")
    if isinstance(transcript, str) and transcript.strip():
        path = Path(transcript).expanduser()
        if path.is_file():
            return path.resolve()

    chat_id = chat_id_from_payload(payload)
    if not chat_id:
        return None
    return find_transcript(chat_id, projects_root, memory_home=memory_home)


def should_skip_boundary_distill(
    *,
    memory_home: Path,
    chat_id: str,
    jsonl: Path,
) -> str | None:
    """Return skip reason if distill not needed."""
    manifest = load_manifest(memory_home / "chats" / "manifest.json")
    if needs_distill(chat_id, jsonl, manifest):
        return None
    return "already_distilled"


_DISTILL_MODULES_CACHE: tuple[Any, Any] | None = None


def _load_distill_modules() -> tuple[Any, Any]:
    global _DISTILL_MODULES_CACHE
    if _DISTILL_MODULES_CACHE is not None:
        return _DISTILL_MODULES_CACHE
    extract_spec = importlib.util.spec_from_file_location(
        "distill_extract_mod", SCRIPT_DIR / "distill-extract.py"
    )
    merge_spec = importlib.util.spec_from_file_location(
        "distill_merge_mod", SCRIPT_DIR / "distill-merge.py"
    )
    if (
        extract_spec is None
        or extract_spec.loader is None
        or merge_spec is None
        or merge_spec.loader is None
    ):
        raise RuntimeError("distill modules unavailable")
    extract_mod = importlib.util.module_from_spec(extract_spec)
    merge_mod = importlib.util.module_from_spec(merge_spec)
    extract_spec.loader.exec_module(extract_mod)
    merge_spec.loader.exec_module(merge_mod)
    _DISTILL_MODULES_CACHE = (extract_mod, merge_mod)
    return _DISTILL_MODULES_CACHE


def distill_jsonl(
    jsonl: Path,
    *,
    memory_home: Path,
    projects_root: Path,
    strategy: str = "auto",
) -> dict[str, Any]:
    chat_id = jsonl.stem
    extract_mod, merge_mod = _load_distill_modules()
    try:
        extract = extract_mod.build_extract(
            jsonl, projects_root=projects_root, strategy=strategy
        )
    except TranscriptSchemaError as exc:
        return {
            "status": "error",
            "reason": "transcript_schema",
            "detail": str(exc),
            "chat_id": chat_id,
        }
    merge_result = merge_mod.run_merge(
        memory_home=memory_home,
        chat_id=chat_id,
        extract=extract,
        dry_run=False,
        apply=False,
    )
    return {
        "status": "distilled",
        "chat_id": chat_id,
        "transcript": str(jsonl),
        **merge_result,
    }


def run_boundary_distill(
    payload: dict[str, Any],
    *,
    memory_home: Path,
    projects_root: Path = DEFAULT_PROJECTS_ROOT,
    strategy: str = "auto",
) -> dict[str, Any]:
    jsonl = resolve_transcript_jsonl(
        payload, memory_home=memory_home, projects_root=projects_root
    )
    if jsonl is None:
        return {"status": "skipped", "reason": "no_transcript"}

    chat_id = jsonl.stem
    skip = should_skip_boundary_distill(
        memory_home=memory_home, chat_id=chat_id, jsonl=jsonl
    )
    if skip:
        return {
            "status": "skipped",
            "reason": skip,
            "chat_id": chat_id,
            "transcript": str(jsonl),
        }

    result = distill_jsonl(
        jsonl,
        memory_home=memory_home,
        projects_root=projects_root,
        strategy=strategy,
    )
    result["event"] = payload.get("hook_event_name")
    return result


def run_session_start_catchup(
    payload: dict[str, Any],
    *,
    memory_home: Path,
    projects_root: Path = DEFAULT_PROJECTS_ROOT,
    days: int = SESSION_START_DAYS,
    limit: int = SESSION_START_CATCHUP_LIMIT,
    strategy: str = "auto",
) -> dict[str, Any]:
    """Background distill for pending chats in open workspace(s)."""
    slugs = slugs_from_workspace_roots(payload.get("workspace_roots") or [])
    if not slugs:
        return {
            "status": "catchup",
            "distilled": 0,
            "skipped": 0,
            "errors": 0,
            "candidates": 0,
            "workspace_slugs": [],
            "results": [],
            "reason": "no_workspace_roots",
        }
    pending = list_chats_needing_distill(
        memory_home,
        projects_root=projects_root,
        days=days,
        workspace_slugs=slugs,
        limit=limit,
    )
    results: list[dict[str, Any]] = []
    distilled = 0
    skipped = 0
    errors = 0

    for row in pending:
        jsonl = row["jsonl"]
        chat_id = row["id"]
        out = distill_jsonl(
            jsonl,
            memory_home=memory_home,
            projects_root=projects_root,
            strategy=strategy,
        )
        results.append(out)
        if out.get("status") == "distilled":
            distilled += 1
        elif out.get("status") == "error":
            errors += 1

    return {
        "status": "catchup",
        "distilled": distilled,
        "skipped": skipped,
        "errors": errors,
        "candidates": len(pending),
        "workspace_slugs": sorted(slugs),
        "results": results,
    }


def handle_session_start(
    payload: dict[str, Any],
    *,
    memory_home: Path,
    projects_root: Path = DEFAULT_PROJECTS_ROOT,
) -> dict[str, Any]:
    """sessionStart — catch-up distill only (no handoff inject)."""
    catchup = run_session_start_catchup(
        payload, memory_home=memory_home, projects_root=projects_root
    )
    return {"catchup": catchup}


def handle_boundary(
    payload: dict[str, Any],
    *,
    memory_home: Path,
    projects_root: Path = DEFAULT_PROJECTS_ROOT,
) -> dict[str, Any]:
    event = payload.get("hook_event_name", "")
    result: dict[str, Any] = {
        "event": event,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }

    if event not in BOUNDARY_EVENTS:
        result["status"] = "ignored"
        return result

    distill = run_boundary_distill(
        payload, memory_home=memory_home, projects_root=projects_root
    )
    result["distill"] = distill

    if event == "preCompact":
        msg = "[agent-memory] Context compacting — review merge-staging and latest distills."
        if distill.get("status") == "distilled":
            staging = distill.get("staging_path", "")
            msg += f" Staging: {staging}"
        result["user_message"] = msg

    return result


def dispatch(
    mode: str,
    payload: dict[str, Any],
    *,
    memory_home: Path | None = None,
    projects_root: Path | None = None,
) -> dict[str, Any]:
    hub = resolve_memory_home(
        str(memory_home) if memory_home else None,
        script_file=str(SCRIPT_DIR / "boundary-hooks.py"),
    )
    proot = (
        projects_root.expanduser().resolve()
        if projects_root
        else DEFAULT_PROJECTS_ROOT
    )
    if mode == "session-start":
        return handle_session_start(payload, memory_home=hub, projects_root=proot)
    if mode == "boundary":
        return handle_boundary(payload, memory_home=hub, projects_root=proot)
    raise ValueError(f"unknown mode: {mode}")


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "mode",
        choices=("session-start", "boundary"),
        help="Hook handler mode",
    )
    parser.add_argument("--memory-home", help="MEMORY_HOME override")
    parser.add_argument("--projects-root", help="Cursor projects root")
    parser.add_argument(
        "--input",
        help="JSON file (default: stdin)",
    )
    parser.add_argument("-o", "--output", help="Write JSON result to file")
    args = parser.parse_args(argv)

    if args.input:
        raw = Path(args.input).expanduser().read_text(encoding="utf-8")
    else:
        raw = sys.stdin.read()
    if not raw.strip():
        print("Error: empty hook input", file=sys.stderr)
        return 1

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"Error: invalid JSON: {exc}", file=sys.stderr)
        return 1

    if not isinstance(payload, dict):
        print("Error: hook input must be a JSON object", file=sys.stderr)
        return 1

    proot = (
        Path(args.projects_root).expanduser().resolve()
        if args.projects_root
        else None
    )
    hub = Path(args.memory_home).expanduser() if args.memory_home else None
    result = dispatch(args.mode, payload, memory_home=hub, projects_root=proot)
    out = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        Path(args.output).expanduser().write_text(out, encoding="utf-8")
    else:
        sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
