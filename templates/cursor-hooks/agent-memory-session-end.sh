#!/usr/bin/env bash
# Cursor sessionEnd hook — checklist (handoff step only when handoff_mode != off).
# Install: bash scripts/install-memory-hooks.sh from your framework clone
# Log: ~/.cursor/hooks/agent-memory-session.log (and stderr for Cursor UI)

set -euo pipefail

_HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$_HOOK_DIR/hook_env.sh"
FRAMEWORK="$(resolve_hook_framework)" || {
  echo "[agent-memory] framework root unknown — run install-memory-hooks.sh from your clone" >&2
  exit 0
}
MEMORY_HOME="$(resolve_hook_memory_home 2>/dev/null || true)"
LOG="${AGENT_MEMORY_SESSION_LOG:-$HOME/.cursor/hooks/agent-memory-session.log}"

if [[ -z "$MEMORY_HOME" ]]; then
  echo "[agent-memory] memory hub unknown — run init-memory.sh from your clone" >&2
  exit 0
fi

emit() {
  echo "$1"
  echo "$1" >&2
  echo "$(date '+%Y-%m-%d %H:%M:%S') $1" >> "$LOG"
}

HANDOFF_MODE="$(python3 -c "
import json, pathlib
hub = pathlib.Path('${MEMORY_HOME}').expanduser()
cfg = hub / 'config.json'
mode = 'optional'
if cfg.is_file():
    try:
        mode = json.loads(cfg.read_text()).get('handoff_mode', 'optional') or 'optional'
    except json.JSONDecodeError:
        pass
print(str(mode).strip().lower())
" 2>/dev/null || echo "optional")"

mkdir -p "$(dirname "$LOG")"
emit "[agent-memory] Session end checklist (handoff_mode=$HANDOFF_MODE):"
step=1
if [[ "$HANDOFF_MODE" != "off" ]]; then
  emit "  $step. Update AGENT_HANDOFF.md if phase/next step changed"
  step=$((step + 1))
fi
emit "  $step. Boundary distill runs via hooks; review merge-staging if needed"
step=$((step + 1))
emit "  $step. verify-memory.py --memory-home $MEMORY_HOME"

if [[ -f "$FRAMEWORK/scripts/list-chats.py" ]]; then
  pending="$(python3 "$FRAMEWORK/scripts/list-chats.py" --memory-home "$MEMORY_HOME" 2>/dev/null | head -1 || true)"
  if [[ -n "$pending" ]]; then
    emit "  Chats: $pending"
  fi
fi

exit 0
