#!/usr/bin/env bash
# Path resolution — single framework clone + gitignored memory/ hub.

HUB_DIRNAME="memory"

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

_valid_framework_dir() {
  local path
  path="$(_expand_tilde "$1")"
  [[ -n "$path" && -f "$path/INSTRUCTIONS.md" ]] || return 1
  echo "$(cd "$path" && pwd)"
}

resolve_framework_root() {
  local override="${1:-}"
  local repo_root="${2:-${REPO_ROOT:-}}"
  local root=""
  if [[ -n "$override" ]]; then
    root="$(_valid_framework_dir "$override")"
    [[ -n "$root" ]] && echo "$root" && return
  fi
  for var in AGENT_MEMORY_FRAMEWORK FRAMEWORK_ROOT AGENT_MEMORY_INSTALL; do
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
  if [[ -f "${repo_root}/INSTRUCTIONS.md" ]]; then
    echo "$(cd "$repo_root" && pwd)"
    return
  fi
  echo ""
}

resolve_memory_home() {
  local override="${1:-}"
  local framework_root="${2:-}"
  if [[ -n "$override" ]]; then
    echo "$(cd "$(_expand_tilde "$override")" && pwd)"
    return
  fi
  if [[ -n "${MEMORY_HOME:-}" ]]; then
    echo "$(cd "$(_expand_tilde "$MEMORY_HOME")" && pwd)"
    return
  fi
  if [[ -z "$framework_root" ]]; then
    framework_root="$(resolve_framework_root "" "${REPO_ROOT:-}")"
  fi
  if [[ -n "$framework_root" ]]; then
    echo "$framework_root/$HUB_DIRNAME"
    return
  fi
  echo "Error: memory_home unknown — run init-memory.sh or pass --memory-home" >&2
  return 1
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
  if ! command -v python3 &>/dev/null; then
    return
  fi
  python3 - "$memory_home/config.json" "$framework_root" "$memory_home" <<'PY'
import json, sys
from pathlib import Path
cfg_path = Path(sys.argv[1])
fw, hub = sys.argv[2], sys.argv[3]
data = {}
if cfg_path.is_file():
    data = json.loads(cfg_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        data = {}
data["framework_root"] = fw
data["memory_home"] = hub
for legacy in ("install_root", "dev_root"):
    data.pop(legacy, None)
cfg_path.parent.mkdir(parents=True, exist_ok=True)
cfg_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
PY
}
