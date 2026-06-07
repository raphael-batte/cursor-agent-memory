#!/usr/bin/env bash
# sessionStart — catch-up distill for open workspace (background).
set -euo pipefail

_HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$_HOOK_DIR/hook_env.sh"
FRAMEWORK="$(resolve_hook_framework)" || {
  echo "[agent-memory] framework root unknown — run install-memory-hooks.sh from your clone" >&2
  printf '%s\n' '{}'
  exit 0
}
LOG="${AGENT_MEMORY_SESSION_START_LOG:-$HOME/.cursor/hooks/agent-memory-session-start.log}"

INPUT="$(cat)"
RESULT="$(python3 "$FRAMEWORK/scripts/boundary-hooks.py" session-start <<<"$INPUT" 2>&1)" || RESULT='{}'

mkdir -p "$(dirname "$LOG")"
{
  echo "$(date '+%Y-%m-%d %H:%M:%S') session-start"
  echo "$RESULT"
} >>"$LOG"

if echo "$RESULT" | python3 -c "import json,sys; json.load(sys.stdin)" 2>/dev/null; then
  printf '%s\n' "$RESULT"
else
  printf '%s\n' '{}'
fi

exit 0
