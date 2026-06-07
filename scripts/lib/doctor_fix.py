"""memory-doctor --fix: align in-repo hub config and skill symlinks."""

from __future__ import annotations

import subprocess
from pathlib import Path

from lib.memory_config import persist_hub_config

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
        persist_hub_config(framework_root.resolve(), memory_home.resolve())
        actions.append(f"set memory/config.json → framework_root={fw_str}, memory_home={hub_str}")
    else:
        actions.append(f"would set memory/config.json → framework_root={fw_str}")

    link_script = SCRIPT_DIR / "link-cursor-skills.sh"
    if link_script.is_file():
        cmd = [
            "bash",
            str(link_script),
            "--force",
            "--memory-home",
            str(memory_home),
            "--framework-root",
            str(framework_root),
        ]
        if dry_run:
            actions.append(f"would run: {' '.join(cmd)}")
        else:
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
                if proc.returncode == 0:
                    actions.append("relinked Cursor skills (--force)")
                else:
                    errors.append(proc.stderr.strip() or "link-cursor-skills failed")
            except OSError as exc:
                errors.append(str(exc))
    else:
        errors.append(f"missing {link_script}")

    hooks_install = SCRIPT_DIR / "install-memory-hooks.sh"
    if hooks_install.is_file():
        actions.append("run install-memory-hooks.sh if sessionEnd/afterFileEdit hooks missing")

    return {
        "actions": actions,
        "errors": errors,
        "ok": not errors,
        "dry_run": dry_run,
    }
