#!/usr/bin/env python3
"""Distill / boundary health from agent-memory-metrics.jsonl."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from lib.defaults import POINTER_LOW_CONFIDENCE  # noqa: E402
from lib.distill_metrics import read_metrics  # noqa: E402
from lib.memory_config import resolve_memory_home  # noqa: E402


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value[:19])
    except ValueError:
        return None


def analyze_metrics(
    rows: list[dict],
    *,
    days: int = 7,
) -> dict:
    cutoff = datetime.now() - timedelta(days=days)
    recent = []
    for row in rows:
        ts = _parse_ts(row.get("ts"))
        if ts is None or ts >= cutoff:
            recent.append(row)

    status_counts = Counter(r.get("status") for r in recent)
    reason_counts = Counter(
        r.get("reason") for r in recent if r.get("status") == "skipped"
    )
    distilled = [r for r in recent if r.get("status") == "distilled"]
    errors = [r for r in recent if r.get("status") == "error"]

    pointer_extracted = sum(
        1 for r in distilled if r.get("pointer_kind") == "extracted"
    )
    pointer_total = sum(1 for r in distilled if r.get("pointer_kind"))
    pointer_rate = (
        pointer_extracted / pointer_total if pointer_total else None
    )

    durations = [int(r["duration_ms"]) for r in distilled if r.get("duration_ms")]
    avg_ms = int(sum(durations) / len(durations)) if durations else None

    low_conf = sum(
        1
        for r in distilled
        if r.get("pointer_confidence") is not None
        and float(r["pointer_confidence"]) < POINTER_LOW_CONFIDENCE
    )

    incremental = sum(1 for r in distilled if r.get("incremental"))
    map_reduce = sum(1 for r in distilled if (r.get("window_count") or 0) > 0)

    return {
        "window_days": days,
        "events_total": len(recent),
        "distilled": status_counts.get("distilled", 0),
        "skipped": status_counts.get("skipped", 0),
        "errors": len(errors),
        "debounced": reason_counts.get("debounced", 0),
        "already_distilled": reason_counts.get("already_distilled", 0),
        "pointer_extracted_rate": pointer_rate,
        "pointer_low_confidence": low_conf,
        "avg_distill_ms": avg_ms,
        "incremental_distills": incremental,
        "map_reduce_distills": map_reduce,
        "healthy": len(errors) == 0 and (pointer_rate is None or pointer_rate >= 0.4),
    }


def print_report(data: dict) -> None:
    print("Agent Memory Health (metrics)")
    print(f"  Window:         {data['window_days']}d")
    print(f"  Events:         {data['events_total']}")
    print(f"  Distilled:      {data['distilled']}")
    print(f"  Skipped:        {data['skipped']} (debounced {data['debounced']}, up-to-date {data['already_distilled']})")
    print(f"  Errors:         {data['errors']}")
    rate = data.get("pointer_extracted_rate")
    if rate is not None:
        print(f"  Pointer hit:    {rate * 100:.0f}% extracted")
    print(f"  Low-confidence: {data['pointer_low_confidence']}")
    if data.get("avg_distill_ms") is not None:
        print(f"  Avg distill:    {data['avg_distill_ms']} ms")
    print(f"  Incremental:    {data['incremental_distills']}")
    print(f"  Map-reduce:     {data['map_reduce_distills']}")
    mark = "✓" if data.get("healthy") else "⚠"
    print(f"  {mark} baseline OK" if data.get("healthy") else f"  {mark} review metrics")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--memory-home", help="Hub path override")
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    memory_home = resolve_memory_home(args.memory_home, script_file=__file__)
    rows = read_metrics(memory_home)
    data = analyze_metrics(rows, days=args.days)
    data["memory_home"] = str(memory_home)

    if args.json:
        print(json.dumps(data, indent=2))
    else:
        print_report(data)
    return 0


if __name__ == "__main__":
    sys.exit(main())
