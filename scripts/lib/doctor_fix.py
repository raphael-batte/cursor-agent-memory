"""memory-doctor --fix: align anchor + hub config."""

from __future__ import annotations

from pathlib import Path

from lib.memory_config import persist_paths

SCRIPT_DIR = Path(__file__).resolve().parents[1]


def run_fix(
    *,
    memory_home: Path,
    framework_root: Path,
    dry_run: bool = False,
) -> dict:
    actions: list[str] = []
    errors: list[str] = []

    fw_str = str(framework_root.resolve())
    hub_str = str(memory_home.resolve())
    if not dry_run:
        persist_paths(framework_root.resolve(), memory_home.resolve())
        actions.append(
            f"set anchor + hub config → plugin_root={fw_str}, memory_home={hub_str}"
        )
    else:
        actions.append(f"would set anchor + hub → plugin_root={fw_str}")

    actions.append(
        "if using plugin: remove legacy ~/.cursor/hooks.json agent-memory entries "
        "and ~/.cursor/skills/agent-memory symlink to avoid double distill"
    )

    legacy_link = SCRIPT_DIR / "link-cursor-skills.sh"
    if legacy_link.is_file():
        actions.append(
            "legacy link-cursor-skills.sh not run — plugin provides skills via bundle"
        )

    return {
        "actions": actions,
        "errors": errors,
        "ok": not errors,
        "dry_run": dry_run,
    }
