#!/usr/bin/env bash
# Integration tests for bash scripts. Run via tests/run-tests.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

OLD_HUB="$TMP/old"
NEW_HUB="$TMP/new"
mkdir -p "$OLD_HUB/context" "$OLD_HUB/feedback" "$OLD_HUB/chats/projects"
echo "# Old conventions" > "$OLD_HUB/context/conventions.md"
echo '{"processed":[],"pending":[]}' > "$OLD_HUB/chats/manifest.json"
mkdir -p "$OLD_HUB/feedback"
echo -e "## T\n\n+ win" > "$OLD_HUB/feedback/wins.md"

# migrate
bash "$ROOT/scripts/migrate-memory.sh" --from "$OLD_HUB" --to "$NEW_HUB"
test -f "$NEW_HUB/context/conventions.md"
test -f "$NEW_HUB/feedback/wins.md"
test -f "$NEW_HUB/config.json"

# migrate does not overwrite
echo "KEEP" > "$NEW_HUB/context/conventions.md"
bash "$ROOT/scripts/migrate-memory.sh" --from "$OLD_HUB" --to "$NEW_HUB"
grep -q "KEEP" "$NEW_HUB/context/conventions.md"

# link dry-run (capture output — pipefail + grep -q closes pipe → SIGPIPE)
bash "$ROOT/scripts/link-cursor-skills.sh" --list --framework-root "$ROOT" >/dev/null
link_out="$(bash "$ROOT/scripts/link-cursor-skills.sh" --only agent-memory --dry-run \
  --framework-root "$ROOT" 2>&1)"
echo "$link_out" | grep -qE 'would link|exists:'

# skills-status
bash "$ROOT/scripts/skills-status.sh" \
  --memory-home "$NEW_HUB" --framework-root "$ROOT" >/dev/null

# config.sh resolve
# shellcheck source=../scripts/lib/config.sh
source "$ROOT/scripts/lib/config.sh"
resolved="$(resolve_memory_home "$NEW_HUB")"
test "$resolved" = "$(cd "$NEW_HUB" && pwd)"

# memory hooks install dry-run (capture — grep -q closes pipe → SIGPIPE on python tail)
hooks_out="$(bash "$ROOT/scripts/install-memory-hooks.sh" --dry-run 2>&1)"
echo "$hooks_out" | grep -q "agent-memory-session-start"
echo "$hooks_out" | grep -q "agent-memory-boundary"
echo "$hooks_out" | grep -q "agent-memory-session-end"

# boundary-hooks CLI (session-start catchup JSON)
HANDOFF_WS="$TMP/workspace"
mkdir -p "$HANDOFF_WS"
boundary_out="$(printf '%s' '{"workspace_roots":["'"$HANDOFF_WS"'"]}' \
  | python3 "$ROOT/scripts/boundary-hooks.py" session-start)"
echo "$boundary_out" | python3 -c "import json,sys; d=json.load(sys.stdin); assert 'catchup' in d"

# sync-memory scan-only
scan_out="$(python3 "$ROOT/scripts/sync-memory.py" --memory-home "$NEW_HUB" --scan-only 2>/dev/null)"
echo "$scan_out" | python3 -c "import json,sys; d=json.load(sys.stdin); assert 'pending_90d' in d"

# sync-memory dry-run
sync_out="$(python3 "$ROOT/scripts/sync-memory.py" --memory-home "$NEW_HUB" --dry-run --no-hooks 2>/dev/null)"
echo "$sync_out" | python3 -c "import json,sys; d=json.load(sys.stdin); assert d.get('dry_run') is True; assert d.get('distills')==0"
chmod +x "$ROOT/scripts/weekly-verify.sh"
weekly_out="$(bash "$ROOT/scripts/weekly-verify.sh" --dry-run 2>&1)"
echo "$weekly_out" | grep -q "would run memory-doctor"
echo "$weekly_out" | grep -q "memory-health"
echo "$weekly_out" | grep -q "update-baseline"
test -x "$ROOT/scripts/weekly-verify.sh"

# init-memory on empty hub
INIT_HUB="$TMP/init-hub"
mkdir -p "$INIT_HUB"
MEMORY_HOME="$INIT_HUB" bash "$ROOT/scripts/init-memory.sh" >/dev/null
test -f "$INIT_HUB/config.json"
test -f "$INIT_HUB/chats/manifest.json"

echo "shell tests: OK"
