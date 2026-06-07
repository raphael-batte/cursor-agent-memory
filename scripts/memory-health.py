#!/usr/bin/env python3
"""Distill / boundary health from agent-memory-metrics.jsonl."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from lib.defaults import POINTER_LOW_CONFIDENCE  # noqa: E402
from lib.distill_metrics import read_metrics  # noqa: E402
from lib.health_baseline import (  # noqa: E402
    check_degradation,
    load_baseline,
    record_snapshot,
)
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
    durations.sort()
    avg_ms = int(sum(durations) / len(durations)) if durations else None
    p95_ms = durations[int(len(durations) * 0.95)] if len(durations) >= 2 else avg_ms

    truncated = sum(1 for r in distilled if r.get("truncated"))
    secrets = sum(int(r.get("secrets_redacted") or 0) for r in distilled)

    low_conf = sum(
        1
        for r in distilled
        if r.get("pointer_confidence") is not None
        and float(r["pointer_confidence"]) < POINTER_LOW_CONFIDENCE
    )

    incremental = sum(1 for r in distilled if r.get("incremental"))
    map_reduce = sum(1 for r in distilled if (r.get("window_count") or 0) > 0)

    truncation_rate = truncated / len(distilled) if distilled else None
    error_rate = len(errors) / len(recent) if recent else None

    return {
        "window_days": days,
        "events_total": len(recent),
        "distilled": status_counts.get("distilled", 0),
        "skipped": status_counts.get("skipped", 0),
        "errors": len(errors),
        "error_rate": error_rate,
        "debounced": reason_counts.get("debounced", 0),
        "no_transcript": reason_counts.get("no_transcript", 0),
        "already_distilled": reason_counts.get("already_distilled", 0),
        "pointer_extracted_rate": pointer_rate,
        "pointer_low_confidence": low_conf,
        "truncation_rate": truncation_rate,
        "secrets_redacted_total": secrets,
        "avg_distill_ms": avg_ms,
        "p95_distill_ms": p95_ms,
        "incremental_distills": incremental,
        "map_reduce_distills": map_reduce,
        "healthy": len(errors) == 0 and (pointer_rate is None or pointer_rate >= 0.4),
    }


def enrich_with_baseline(
    memory_home: Path,
    data: dict[str, Any],
    *,
    update_baseline: bool = False,
) -> dict:
    baseline = load_baseline(memory_home)
    if update_baseline:
        baseline = record_snapshot(
            memory_home,
            pointer_hit_rate=data.get("pointer_extracted_rate"),
            distilled_count=int(data.get("distilled") or 0),
            error_count=int(data.get("errors") or 0),
        )
    degradation = check_degradation(data, baseline)
    data["baseline"] = {
        "median_hit_rate": baseline.get("pointer_hit_median"),
        "samples": len(baseline.get("pointer_hit_rates") or []),
    }
    data["degradation"] = degradation
    if degradation.get("degraded"):
        data["healthy"] = False
    return data


def notify_macos(title: str, message: str) -> None:
    safe_title = title.replace('"', "'")
    safe_msg = message.replace('"', "'")[:200]
    script = f'display notification "{safe_msg}" with title "{safe_title}"'
    try:
        subprocess.run(["osascript", "-e", script], check=False, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        pass


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
    bl = data.get("baseline") or {}
    if bl.get("median_hit_rate") is not None:
        print(
            f"  Baseline:       median {float(bl['median_hit_rate']) * 100:.0f}% "
            f"({bl.get('samples', 0)} samples)"
        )
    deg = data.get("degradation") or {}
    if deg.get("degraded"):
        print(f"  Degradation:    {deg.get('degradation_reason')}")
    print(f"  Low-confidence: {data['pointer_low_confidence']}")
    tr = data.get("truncation_rate")
    if tr is not None:
        print(f"  Truncation:     {tr * 100:.0f}%")
    if data.get("avg_distill_ms") is not None:
        print(f"  Avg / p95 ms:   {data['avg_distill_ms']} / {data.get('p95_distill_ms') or '—'}")
    print(f"  Incremental:    {data['incremental_distills']}")
    print(f"  Map-reduce:     {data['map_reduce_distills']}")
    mark = "✓" if data.get("healthy") else "⚠"
    print(f"  {mark} {'healthy' if data.get('healthy') else 'review metrics'}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--memory-home", help="Hub path override")
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--update-baseline", action="store_true")
    parser.add_argument("--strict", action="store_true", help="Exit 1 when unhealthy")
    parser.add_argument("--notify", action="store_true", help="macOS notification on degradation")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    memory_home = resolve_memory_home(args.memory_home, script_file=__file__)
    rows = read_metrics(memory_home)
    data = analyze_metrics(rows, days=args.days)
    data = enrich_with_baseline(memory_home, data, update_baseline=args.update_baseline)
    data["memory_home"] = str(memory_home)

    if args.json:
        print(json.dumps(data, indent=2))
    else:
        print_report(data)

    if args.notify and (data.get("degradation") or {}).get("degraded"):
        notify_macos(
            "Agent Memory",
            (data.get("degradation") or {}).get("degradation_reason") or "metrics degraded",
        )

    if args.strict and not data.get("healthy"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
