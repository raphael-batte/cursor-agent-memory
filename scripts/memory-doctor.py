#!/usr/bin/env python3
"""One-shot health check: paths, skills, pending chats, verify summary."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from lib.doctor_fix import run_fix  # noqa: E402
from lib.memory_config import (  # noqa: E402
    framework_version,
    load_global_config,
    load_hub_config,
    resolve_framework_root,
    resolve_memory_home,
)
from lib.memory_routing import load_handoff_mode  # noqa: E402


def load_script(name: str, filename: str):
    import importlib.util

    path = SCRIPT_DIR / filename
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_doctor(
    *,
    memory_home: Path,
    framework_root: Path | None,
    handoff: Path | None,
    strict_secrets: bool,
    gitleaks: bool = False,
) -> dict:
    lc = load_script("list_chats", "list-chats.py")
    vm = load_script("verify_memory", "verify-memory.py")
    ms = load_script("memory_status", "memory-status.py")

    global_cfg = load_global_config()
    hub_cfg = load_hub_config(memory_home)
    processed, pending, total = lc.chat_counts(memory_home)
    results, warnings = vm.run_checks_for_hub(
        memory_home,
        handoff=handoff,
        strict_secrets=strict_secrets,
        gitleaks=gitleaks,
    )
    passed, failed = vm.summarize_results(results)
    skills = ms.skills_stats(memory_home, framework_root)

    return {
        "memory_home": str(memory_home),
        "memory_home_exists": memory_home.is_dir(),
        "global_config": global_cfg,
        "hub_config": hub_cfg,
        "framework_root": str(framework_root) if framework_root else None,
        "framework_version": framework_version(framework_root),
        "chats": {"processed": processed, "pending": pending, "total": total},
        "verify": {"passed": passed, "failed": failed, "ok": failed == 0},
        "verify_details": [
            {"name": r.name, "ok": r.ok, "detail": r.detail} for r in results
        ],
        "warnings": warnings,
        "skills": {
            "framework_linked": skills["framework_linked"],
            "personal_linked": skills["personal_linked"],
            "unlinked": skills["unlinked"],
        },
        "handoff_mode": load_handoff_mode(memory_home),
        "path_resolution": (
            "CLI --memory-home > $MEMORY_HOME env > <clone>/memory; "
            "framework_root from hub parent or memory/config.json"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--memory-home")
    parser.add_argument("--framework-root")
    parser.add_argument("--handoff")
    parser.add_argument("--strict-secrets", action="store_true")
    parser.add_argument("--gitleaks", action="store_true")
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Align memory/config.json and relink Cursor skills",
    )
    parser.add_argument("--fix-dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    memory_home = resolve_memory_home(args.memory_home, script_file=__file__)
    framework_root = resolve_framework_root(
        memory_home, args.framework_root, script_file=__file__
    )
    handoff = Path(args.handoff).expanduser() if args.handoff else None

    if args.fix or args.fix_dry_run:
        if framework_root is None:
            print("Error: --fix requires resolvable framework_root", file=sys.stderr)
            return 1
        fix_report = run_fix(
            memory_home=memory_home,
            framework_root=framework_root,
            dry_run=args.fix_dry_run,
        )
        if args.json:
            print(json.dumps(fix_report, indent=2))
        else:
            print("Memory Doctor — fix")
            for action in fix_report["actions"]:
                print(f"  ✓ {action}")
            for err in fix_report["errors"]:
                print(f"  ✗ {err}")
        return 0 if fix_report["ok"] else 1

    report = run_doctor(
        memory_home=memory_home,
        framework_root=framework_root,
        handoff=handoff,
        strict_secrets=args.strict_secrets,
        gitleaks=args.gitleaks,
    )

    if args.json:
        print(json.dumps(report, indent=2))
        return 0 if report["verify"]["ok"] else 1

    print("Memory Doctor")
    print(f"  Hub:       {report['memory_home']}")
    if framework_root:
        print(f"  Framework: {framework_root} v{report['framework_version'] or '?'}")
    print(f"  Chats:     {report['chats']['processed']} processed · "
          f"{report['chats']['pending']} pending · {report['chats']['total']} total")
    print(f"  Verify:    {report['verify']['passed']} passed · "
          f"{report['verify']['failed']} failed")
    if report["skills"]["unlinked"]:
        print(f"  Skills:    unlinked in hub: {', '.join(report['skills']['unlinked'])}")
    for w in report["warnings"]:
        print(f"  ⚠ {w}")
    print()
    print(report["path_resolution"])
    print("  Tip: memory-doctor.py --fix  align configs + relink skills")
    return 0 if report["verify"]["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
