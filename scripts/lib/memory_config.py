"""Shared path resolution for agent-memory scripts."""

from __future__ import annotations

import json
import os
import warnings
from pathlib import Path

HUB_DIRNAME = "memory"
# Legacy read-only fallback (never created by framework scripts)
LEGACY_GLOBAL_CONFIG = Path.home() / ".config" / "cursor-agent-memory" / "config.json"
CURSOR_HOOK_ENV = Path.home() / ".cursor" / "hooks" / "agent-memory.env"


def _read_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _load_cursor_hook_env() -> dict[str, str]:
    """Parse AGENT_MEMORY_FRAMEWORK / MEMORY_HOME from ~/.cursor/hooks/agent-memory.env."""
    out: dict[str, str] = {}
    if not CURSOR_HOOK_ENV.is_file():
        return out
    for line in CURSOR_HOOK_ENV.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        out[key.strip()] = val.strip().strip("'\"")
    return out


def detect_framework_root_from_script(script_file: str | Path) -> Path | None:
    """Infer framework clone from any script path inside scripts/."""
    scripts = Path(script_file).resolve().parent
    if scripts.name == "scripts":
        candidate = scripts.parent
        if (candidate / "INSTRUCTIONS.md").is_file():
            return candidate
    if (scripts / "INSTRUCTIONS.md").is_file():
        return scripts
    return None


def resolve_framework_root(
    override: str | None = None,
    *,
    script_file: str | Path | None = None,
    memory_home: Path | None = None,
) -> Path | None:
    """
    Framework clone — directory containing INSTRUCTIONS.md.
    CLI/env/hook override > hub config > script location.
    """
    found = _valid_framework_dir(override or "")
    if found:
        return found
    for key in ("AGENT_MEMORY_FRAMEWORK", "FRAMEWORK_ROOT", "AGENT_MEMORY_INSTALL"):
        found = _valid_framework_dir(os.environ.get(key, "").strip())
        if found:
            return found
    hook = _load_cursor_hook_env()
    found = _valid_framework_dir(hook.get("AGENT_MEMORY_FRAMEWORK", ""))
    if found:
        return found
    if memory_home is not None:
        from_parent = framework_root_from_memory_home(memory_home)
        if from_parent is not None:
            return from_parent
        hub_cfg = load_hub_config(memory_home)
        found = _valid_framework_dir(str(hub_cfg.get("framework_root", "")).strip())
        if found:
            return found
    if script_file is not None:
        detected = detect_framework_root_from_script(script_file)
        if detected is not None:
            return detected
    return None


def default_memory_home(
    script_file: str | Path | None = None,
    *,
    framework_root: Path | None = None,
) -> Path | None:
    """Hub at <framework>/memory/."""
    if framework_root is not None:
        return (framework_root / HUB_DIRNAME).resolve()
    if script_file is None:
        return None
    fw = detect_framework_root_from_script(script_file)
    if fw is not None:
        return (fw / HUB_DIRNAME).resolve()
    return None


def resolve_memory_home(
    override: str | None = None,
    script_file: str | Path | None = None,
) -> Path:
    """
    CLI > MEMORY_HOME env > hook env > <framework>/memory > legacy read.
    """
    if override:
        return Path(override).expanduser().resolve()
    env = os.environ.get("MEMORY_HOME", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    hook = _load_cursor_hook_env()
    hook_hub = hook.get("MEMORY_HOME", "").strip()
    if hook_hub:
        p = Path(hook_hub).expanduser()
        if p.is_dir():
            return p.resolve()
    fw = resolve_framework_root(script_file=script_file) if script_file else None
    hub = default_memory_home(script_file, framework_root=fw)
    if hub is not None:
        return hub
    legacy = _read_json(LEGACY_GLOBAL_CONFIG)
    legacy_hub = legacy.get("memory_home", "").strip()
    if legacy_hub:
        warnings.warn(
            "Reading memory_home from legacy XDG cursor-agent-memory config is "
            "deprecated; use Cursor hook env or <clone>/memory/config.json instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return Path(legacy_hub).expanduser().resolve()
    raise RuntimeError(
        "memory_home unknown — pass --memory-home, set MEMORY_HOME env, "
        f"or run init-memory.sh (expected <clone>/{HUB_DIRNAME}/)"
    )


def load_global_config() -> dict:
    """Legacy global pointer — read only."""
    return _read_json(LEGACY_GLOBAL_CONFIG)


def load_hub_config(memory_home: Path) -> dict:
    return _read_json(memory_home / "config.json")


def _valid_framework_dir(path: str) -> Path | None:
    if not path or not isinstance(path, str):
        return None
    p = Path(path).expanduser()
    if p.is_dir() and (p / "INSTRUCTIONS.md").is_file():
        return p.resolve()
    return None


def framework_root_from_memory_home(memory_home: Path) -> Path | None:
    if memory_home.name == HUB_DIRNAME:
        parent = memory_home.parent
        if (parent / "INSTRUCTIONS.md").is_file():
            return parent.resolve()
    return None


def persist_hub_config(
    framework_root: Path,
    memory_home: Path,
) -> None:
    """Write memory/config.json at hub."""
    fw_str = str(framework_root.resolve())
    hub_cfg_path = memory_home / "config.json"
    hub_cfg = load_hub_config(memory_home)
    if not isinstance(hub_cfg, dict):
        hub_cfg = {}
    changed = False
    for key, val in (
        ("framework_root", fw_str),
        ("memory_home", str(memory_home.resolve())),
    ):
        if hub_cfg.get(key) != val:
            hub_cfg[key] = val
            changed = True
    for legacy_key in ("install_root", "dev_root"):
        if legacy_key in hub_cfg:
            del hub_cfg[legacy_key]
            changed = True
    if changed:
        memory_home.mkdir(parents=True, exist_ok=True)
        hub_cfg_path.write_text(
            json.dumps(hub_cfg, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )


def persist_framework_root(
    framework_root: Path,
    *,
    memory_home: Path | None = None,
    update_global: bool = False,
    update_hub: bool = True,
) -> None:
    if update_global:
        raise ValueError("update_global is disabled — use memory/config.json only")
    if update_hub and memory_home is not None:
        persist_hub_config(framework_root.resolve(), memory_home.resolve())


def framework_version(framework_root: Path | None) -> str | None:
    if not framework_root:
        return None
    version_file = framework_root / "VERSION"
    if version_file.is_file():
        return version_file.read_text(encoding="utf-8").strip()
    return None
