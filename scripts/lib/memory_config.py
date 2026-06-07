"""Shared path resolution for agent-memory scripts."""

from __future__ import annotations

import json
import os
import warnings
from pathlib import Path

HUB_DIRNAME = "memory"
DEV_CONFIG_NAME = "dev.config.json"
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


def is_dev_project(dev_root: Path | None) -> bool:
    """Dev clone has gitignored dev.config.json pointing at install — no local memory/."""
    if dev_root is None:
        return False
    return (dev_root / DEV_CONFIG_NAME).is_file()


def dev_config_install_root(dev_root: Path | None) -> Path | None:
    if dev_root is None:
        return None
    cfg = _read_json(dev_root / DEV_CONFIG_NAME)
    raw = str(cfg.get("install_root", "")).strip()
    return _valid_framework_dir(raw)


def resolve_install_root(
    override: str | None = None,
    *,
    dev_root: Path | None = None,
) -> Path | None:
    """
    Cursor-connected install clone (install_root in dev.config.json or env).
    Dev project is separate — see dev.config.json.
    """
    found = _valid_framework_dir(override or "")
    if found:
        return found
    for key in ("AGENT_MEMORY_INSTALL", "AGENT_MEMORY_FRAMEWORK", "FRAMEWORK_ROOT"):
        found = _valid_framework_dir(os.environ.get(key, "").strip())
        if found:
            return found
    hook = _load_cursor_hook_env()
    found = _valid_framework_dir(hook.get("AGENT_MEMORY_FRAMEWORK", ""))
    if found:
        return found
    if dev_root is None:
        return None
    from_dev = dev_config_install_root(dev_root)
    if from_dev is not None:
        return from_dev
    return None


def default_memory_home(
    script_file: str | Path | None = None,
    *,
    install_root: Path | None = None,
) -> Path | None:
    """
    Hub at <install>/memory/.
    Dev clone (dev.config.json) never uses <dev>/memory/.
    Single-clone install may use <clone>/memory/ when no separate install exists.
    """
    if install_root is not None:
        return (install_root / HUB_DIRNAME).resolve()
    if script_file is None:
        return None
    dev = detect_framework_root_from_script(script_file)
    install = resolve_install_root(dev_root=dev)
    if install is not None:
        return (install / HUB_DIRNAME).resolve()
    if dev is not None and is_dev_project(dev):
        return None
    if dev is not None:
        return (dev / HUB_DIRNAME).resolve()
    return None


def resolve_memory_home(
    override: str | None = None,
    script_file: str | Path | None = None,
) -> Path:
    """
    CLI > MEMORY_HOME env > <install>/memory > dev clone memory/ > legacy read.
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
    dev = detect_framework_root_from_script(script_file) if script_file else None
    install = resolve_install_root(dev_root=dev)
    hub = default_memory_home(script_file, install_root=install)
    if hub is not None:
        return hub
    legacy = _read_json(LEGACY_GLOBAL_CONFIG)
    legacy_hub = legacy.get("memory_home", "").strip()
    if legacy_hub:
        warnings.warn(
            "Reading memory_home from legacy XDG cursor-agent-memory config is "
            "deprecated; use Cursor hook env or <install>/memory/config.json instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return Path(legacy_hub).expanduser().resolve()
    if dev is not None and is_dev_project(dev):
        raise RuntimeError(
            "dev clone must not use <dev>/memory/ — set install_root in dev.config.json "
            "and run scripts/sync-to-install.sh"
        )
    raise RuntimeError(
        "memory_home unknown — pass --memory-home or set install_root in dev.config.json "
        f"(expected <install>/{HUB_DIRNAME}/)"
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


def resolve_framework_root(
    memory_home: Path,
    override: str | None = None,
    script_file: str | None = None,
) -> Path | None:
    """Prefer Cursor install root over dev clone script location."""
    found = _valid_framework_dir(override or "")
    if found:
        return found
    dev = detect_framework_root_from_script(script_file) if script_file else None
    install = resolve_install_root(dev_root=dev)
    if install is not None:
        return install
    from_parent = framework_root_from_memory_home(memory_home)
    if from_parent is not None:
        return from_parent
    agent_env = os.environ.get("AGENT_MEMORY_FRAMEWORK", "").strip()
    found = _valid_framework_dir(agent_env)
    if found:
        return found
    hub_cfg = load_hub_config(memory_home)
    found = _valid_framework_dir(str(hub_cfg.get("framework_root", "")).strip())
    if found:
        return found
    if script_file:
        return detect_framework_root_from_script(script_file)
    return None


def persist_hub_config(
    framework_root: Path,
    memory_home: Path,
    *,
    dev_root: Path | None = None,
) -> None:
    """Write memory/config.json at install hub."""
    fw_str = str(framework_root.resolve())
    hub_cfg_path = memory_home / "config.json"
    hub_cfg = load_hub_config(memory_home)
    if not isinstance(hub_cfg, dict):
        hub_cfg = {}
    changed = False
    for key, val in (
        ("framework_root", fw_str),
        ("memory_home", str(memory_home.resolve())),
        ("install_root", fw_str),
    ):
        if hub_cfg.get(key) != val:
            hub_cfg[key] = val
            changed = True
    if dev_root is not None and str(dev_root.resolve()) != fw_str:
        dev_str = str(dev_root.resolve())
        if hub_cfg.get("dev_root") != dev_str:
            hub_cfg["dev_root"] = dev_str
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
    dev_root: Path | None = None,
    update_global: bool = False,
    update_hub: bool = True,
) -> None:
    if update_global:
        raise ValueError("update_global is disabled — use memory/config.json only")
    if update_hub and memory_home is not None:
        persist_hub_config(
            framework_root.resolve(),
            memory_home.resolve(),
            dev_root=dev_root,
        )


def framework_version(framework_root: Path | None) -> str | None:
    if not framework_root:
        return None
    version_file = framework_root / "VERSION"
    if version_file.is_file():
        return version_file.read_text(encoding="utf-8").strip()
    return None
