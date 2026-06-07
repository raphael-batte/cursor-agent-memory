#!/usr/bin/env bash
# Dev clone (cursor-agent-memory) vs install clone (agent-memory) for Cursor.
# Hub: <install>/memory/ only. See dev.config.json.example

HUB_DIRNAME="memory"
DEV_CONFIG_NAME="dev.config.json"

# Safe leading-tilde expansion. Replaces `eval echo "$p"`, which would execute
# command substitutions / backticks embedded in a path value.
_expand_tilde() {
  local p="$1"
  case "$p" in
    "~") printf '%s\n' "$HOME" ;;
    "~/"*) printf '%s\n' "$HOME/${p#"~/"}" ;;
    *) printf '%s\n' "$p" ;;
  esac
}

_read_install_from_dev_config() {
  local dev_root="$1"
  local cfg="$dev_root/$DEV_CONFIG_NAME"
  [[ -f "$cfg" ]] || return 1
  python3 - "$cfg" <<'PY'
import json, sys
from pathlib import Path
data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(data.get("install_root", "") or "")
PY
}

_valid_framework_dir() {
  local path
  path="$(_expand_tilde "$1")"
  [[ -n "$path" && -f "$path/INSTRUCTIONS.md" ]] || return 1
  echo "$(cd "$path" && pwd)"
}

_valid_install_dir() {
  local path
  path="$(_expand_tilde "$1")"
  [[ -n "$path" && -d "$path" ]] || return 1
  echo "$(cd "$path" && pwd)"
}

resolve_install_root() {
  local override="${1:-}"
  local dev_root="${2:-${REPO_ROOT:-}}"
  local root=""
  if [[ -n "$override" ]]; then
    root="$(_valid_framework_dir "$override")" || root="$(_valid_install_dir "$override")"
    [[ -n "$root" ]] && echo "$root" && return
  fi
  if [[ -f "${dev_root}/${DEV_CONFIG_NAME}" ]]; then
    local from_cfg
    from_cfg="$(_read_install_from_dev_config "$dev_root" 2>/dev/null || true)"
    if [[ -n "$from_cfg" ]]; then
      root="$(_valid_install_dir "$from_cfg")" && echo "$root" && return
    fi
  fi
  for var in AGENT_MEMORY_INSTALL AGENT_MEMORY_FRAMEWORK FRAMEWORK_ROOT; do
    if [[ -n "${!var:-}" ]]; then
      root="$(_valid_framework_dir "${!var}")" && echo "$root" && return
    fi
  done
  local env_file="$HOME/.cursor/hooks/agent-memory.env"
  if [[ -f "$env_file" ]]; then
    # shellcheck disable=SC1090
    source "$env_file"
    root="$(_valid_framework_dir "${AGENT_MEMORY_FRAMEWORK:-}")" && echo "$root" && return
  fi
  echo ""
}

resolve_memory_home() {
  local override="${1:-}"
  local install_root="${2:-}"
  if [[ -n "$override" ]]; then
    echo "$(cd "$(_expand_tilde "$override")" && pwd)"
    return
  fi
  if [[ -n "${MEMORY_HOME:-}" ]]; then
    echo "$(cd "$(_expand_tilde "$MEMORY_HOME")" && pwd)"
    return
  fi
  if [[ -z "$install_root" ]]; then
    install_root="$(resolve_install_root "" "${REPO_ROOT:-}")"
  fi
  if [[ -n "$install_root" ]]; then
    echo "$install_root/$HUB_DIRNAME"
    return
  fi
  if [[ -f "${REPO_ROOT:-}/$DEV_CONFIG_NAME" ]]; then
    echo "Error: dev clone must not use <dev>/memory/ — set install_root in dev.config.json" >&2
    return 1
  fi
  if [[ -f "${REPO_ROOT:-}/INSTRUCTIONS.md" ]]; then
    echo "$REPO_ROOT/$HUB_DIRNAME"
    return
  fi
  echo "Error: memory_home unknown — set install_root in dev.config.json" >&2
  return 1
}

resolve_framework_root() {
  local memory_home="$1"
  local override="${2:-}"
  local install_root="${3:-}"
  if [[ -n "$override" ]]; then
    echo "$(cd "$(_expand_tilde "$override")" && pwd)"
    return
  fi
  if [[ -z "$install_root" ]]; then
    install_root="$(resolve_install_root "" "${REPO_ROOT:-}")"
  fi
  if [[ -n "$install_root" ]]; then
    echo "$install_root"
    return
  fi
  if [[ -n "${FRAMEWORK_ROOT:-}" ]]; then
    echo "$(cd "$(_expand_tilde "$FRAMEWORK_ROOT")" && pwd)"
    return
  fi
  if [[ -f "${REPO_ROOT:-}/INSTRUCTIONS.md" ]]; then
    echo "${REPO_ROOT}"
    return
  fi
  echo ""
}

write_cursor_hook_env() {
  local framework_root="$1"
  local memory_home="${2:-$framework_root/$HUB_DIRNAME}"
  local hooks_dir="${CURSOR_DIR:-$HOME/.cursor}/hooks"
  mkdir -p "$hooks_dir"
  {
    printf 'AGENT_MEMORY_FRAMEWORK=%s\n' "$framework_root"
    printf 'MEMORY_HOME=%s\n' "$memory_home"
  } > "$hooks_dir/agent-memory.env"
  local hook_src="$framework_root/scripts/lib/hook_env.sh"
  if [[ -f "$hook_src" ]]; then
    cp -f "$hook_src" "$hooks_dir/hook_env.sh"
  fi
}

write_hub_config_paths() {
  local framework_root="$1"
  local memory_home="${2:-$framework_root/$HUB_DIRNAME}"
  local dev_root="${3:-}"
  if ! command -v python3 &>/dev/null; then
    return
  fi
  python3 - "$memory_home/config.json" "$framework_root" "$memory_home" "$dev_root" <<'PY'
import json, sys
from pathlib import Path
cfg_path = Path(sys.argv[1])
fw, hub, dev = sys.argv[2], sys.argv[3], sys.argv[4]
data = {}
if cfg_path.is_file():
    data = json.loads(cfg_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        data = {}
data["framework_root"] = fw
data["install_root"] = fw
data["memory_home"] = hub
if dev and Path(dev).resolve() != Path(fw).resolve():
    data["dev_root"] = dev
cfg_path.parent.mkdir(parents=True, exist_ok=True)
cfg_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
PY
}
