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
test -x "$ROOT/scripts/weekly-verify.sh"

# sync-to-install dry-run (dev + install layout)
DEV_CLONE="$TMP/dev-clone"
INSTALL_CLONE="$TMP/install-clone"
mkdir -p "$DEV_CLONE/scripts" "$INSTALL_CLONE"
cp "$ROOT/INSTRUCTIONS.md" "$DEV_CLONE/"
cp "$ROOT/VERSION" "$DEV_CLONE/"
cp -r "$ROOT/scripts" "$DEV_CLONE/"
echo '{"install_root":"'"$INSTALL_CLONE"'"}' > "$DEV_CLONE/dev.config.json"
sync_out="$(bash "$DEV_CLONE/scripts/sync-to-install.sh" --dry-run 2>&1)"
echo "$sync_out" | grep -q "would rsync"
echo "$sync_out" | grep -q "$INSTALL_CLONE"

echo "shell tests: OK"
