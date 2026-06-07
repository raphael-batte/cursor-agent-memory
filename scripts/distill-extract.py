#!/usr/bin/env python3
"""Extract structured chat summary from Cursor jsonl — for agent distill (not raw jsonl)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from lib.defaults import (  # noqa: E402
    AUTO_SPREAD_THRESHOLD,
    DEFAULT_KEYWORDS,
    MAX_DISTILL_MESSAGES,
)
from lib.secrets_guard import is_terminal_noise, sanitize_message  # noqa: E402
from lib.transcript import (  # noqa: E402
    TranscriptSchemaError,
    extract_raw_user_texts,
    find_transcript,
    workspace_from_path,
    workspace_slug,
)
from lib.transcript_cursor import is_redacted_or_noise, normalize_user_text  # noqa: E402

DEFAULT_PROJECTS_ROOT = Path.home() / ".cursor/projects"

KEYWORDS = DEFAULT_KEYWORDS
STRATEGIES = ("tail", "spread", "all", "auto")


def resolve_strategy(strategy: str, total: int) -> str:
    if strategy == "auto":
        return "spread" if total > AUTO_SPREAD_THRESHOLD else "tail"
    return strategy


def select_tail(messages: list[str], max_messages: int) -> list[str]:
    if len(messages) <= max_messages:
        return messages
    head = messages[:1]
    tail_n = max_messages - len(head)
    return head + messages[-tail_n:]


def select_spread(messages: list[str], max_messages: int) -> list[str]:
    total = len(messages)
    if total <= max_messages:
        return messages
    third = max_messages // 3
    head_n = third
    mid_n = third
    tail_n = max_messages - head_n - mid_n
    head = messages[:head_n]
    tail = messages[-tail_n:] if tail_n else []
    middle_pool = messages[head_n : total - tail_n] if tail_n else messages[head_n:]
    if not middle_pool:
        return head + tail
    if len(middle_pool) <= mid_n:
        mid = middle_pool
    else:
        step = len(middle_pool) / mid_n
        mid = [middle_pool[int(i * step)] for i in range(mid_n)]
    return head + mid + tail


def select_messages(messages: list[str], max_messages: int, strategy: str) -> list[str]:
    if strategy == "spread":
        return select_spread(messages, max_messages)
    return select_tail(messages, max_messages)


def parse_user_messages(jsonl: Path) -> tuple[list[str], int, str]:
    raw_texts, _stats, adapter = extract_raw_user_texts(jsonl)
    all_msgs: list[str] = []
    secrets_redacted = 0
    for text in raw_texts:
        clean, n = sanitize_message(text)
        secrets_redacted += n
        if clean is None:
            continue
        if is_terminal_noise(clean):
            continue
        all_msgs.append(clean)
    if not all_msgs:
        raise TranscriptSchemaError(
            f"no usable user messages after sanitization: {jsonl}"
        )
    return all_msgs, secrets_redacted, adapter


def extract_user_messages(
    jsonl: Path,
    *,
    max_messages: int | None = MAX_DISTILL_MESSAGES,
    strategy: str = "tail",
) -> tuple[list[str], int, str, int, str]:
    all_msgs, secrets_redacted, adapter = parse_user_messages(jsonl)
    total = len(all_msgs)
    effective = resolve_strategy(strategy, total)

    if effective == "all" or max_messages is None:
        return all_msgs, total, "all", secrets_redacted, adapter
    if max_messages <= 0:
        return [], total, effective, secrets_redacted, adapter
    if total <= max_messages:
        return all_msgs, total, effective, secrets_redacted, adapter
    return (
        select_messages(all_msgs, max_messages, effective),
        total,
        effective,
        secrets_redacted,
        adapter,
    )


def keywords_hit(messages: list[str]) -> list[str]:
    blob = " ".join(messages).lower()
    return [kw for kw in KEYWORDS if kw in blob]


def build_extract(
    jsonl: Path,
    *,
    projects_root: Path = DEFAULT_PROJECTS_ROOT,
    max_messages: int | None = MAX_DISTILL_MESSAGES,
    strategy: str = "tail",
) -> dict:
    messages, total, effective, secrets_redacted, adapter = extract_user_messages(
        jsonl, max_messages=max_messages, strategy=strategy
    )
    workspace = workspace_from_path(jsonl, projects_root)
    st = jsonl.stat()
    truncated = effective != "all" and total > len(messages)
    first_query = messages[0][:140] if messages else "(no user text)"

    return {
        "uuid": jsonl.stem,
        "date": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d"),
        "workspace": workspace,
        "workspace_slug": workspace_slug(workspace),
        "first_query": first_query,
        "user_messages": messages,
        "user_message_count": total,
        "strategy": effective,
        "truncated": truncated,
        "keywords_hit": keywords_hit(messages),
        "secrets_redacted": secrets_redacted,
        "source_path": str(jsonl.resolve()),
        "size_bytes": st.st_size,
        "transcript_adapter": adapter,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("uuid", nargs="?", help="Chat transcript uuid")
    parser.add_argument("--path", metavar="JSONL", help="Direct path to .jsonl")
    parser.add_argument(
        "--max-messages",
        type=int,
        default=MAX_DISTILL_MESSAGES,
        metavar="N",
    )
    parser.add_argument(
        "--strategy",
        choices=STRATEGIES,
        default="tail",
    )
    parser.add_argument("--all", action="store_true", help="Alias for --strategy all")
    parser.add_argument("--projects-root", metavar="DIR")
    parser.add_argument("--memory-home", help="Hub path (for transcripts/ fallback)")
    parser.add_argument("-o", "--output", metavar="FILE")
    args = parser.parse_args()

    projects_root = (
        Path(args.projects_root).expanduser().resolve()
        if args.projects_root
        else DEFAULT_PROJECTS_ROOT
    )
    memory_home = None
    if args.memory_home:
        from lib.memory_config import resolve_memory_home  # noqa: E402

        memory_home = resolve_memory_home(args.memory_home, script_file=__file__)

    try:
        if args.path:
            jsonl = Path(args.path).expanduser().resolve()
            if not jsonl.is_file():
                print(f"Error: not a file: {jsonl}", file=sys.stderr)
                return 1
        elif args.uuid:
            jsonl = find_transcript(
                args.uuid, projects_root, memory_home=memory_home
            )
            if jsonl is None:
                print(f"Error: transcript not found for uuid: {args.uuid}", file=sys.stderr)
                return 1
        else:
            parser.print_help()
            return 1

        strategy = "all" if args.all else args.strategy
        data = build_extract(
            jsonl,
            projects_root=projects_root,
            max_messages=args.max_messages,
            strategy=strategy,
        )
    except TranscriptSchemaError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    out = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        Path(args.output).expanduser().write_text(out, encoding="utf-8")
    else:
        sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
