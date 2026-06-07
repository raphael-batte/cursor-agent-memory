#!/usr/bin/env bash
# Bootstrap user memory data directory from templates.
# Framework repo: agent-memory · Does not overwrite existing files.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
# shellcheck source=lib/config.sh
source "$SCRIPT_DIR/lib/config.sh"
INSTALL_ROOT="$(resolve_install_root "" "$REPO_ROOT")"
if [[ -z "$INSTALL_ROOT" ]]; then
  echo "Error: install root unknown — copy dev.config.json.example → dev.config.json" >&2
  exit 1
fi
MEMORY_HOME="$(resolve_memory_home "${MEMORY_HOME:-}" "$INSTALL_ROOT")"
DEV_ROOT=""
if [[ "$(cd "$REPO_ROOT" && pwd)" != "$(cd "$INSTALL_ROOT" && pwd)" ]]; then
  DEV_ROOT="$REPO_ROOT"
fi
TEMPLATES="$INSTALL_ROOT/templates"
if [[ ! -d "$TEMPLATES" && -d "$REPO_ROOT/templates" ]]; then
  TEMPLATES="$REPO_ROOT/templates"
fi
MANIFEST="$MEMORY_HOME/chats/manifest.json"

echo "Agent Memory — init"
echo "  Install:   $INSTALL_ROOT"
[[ -n "$DEV_ROOT" ]] && echo "  Dev:       $DEV_ROOT"
echo "  Data home: $MEMORY_HOME"
echo

copy_tree() {
  local src="$1" dst="$2"
  mkdir -p "$dst"
  if command -v rsync &>/dev/null; then
    rsync -a --ignore-existing "$src/" "$dst/"
  else
    cp -Rn "$src/." "$dst/" 2>/dev/null || true
  fi
}

mkdir -p "$MEMORY_HOME"
copy_tree "$TEMPLATES/context" "$MEMORY_HOME/context"
copy_tree "$TEMPLATES/chats" "$MEMORY_HOME/chats"
copy_tree "$TEMPLATES/feedback" "$MEMORY_HOME/feedback"

if [[ ! -f "$MEMORY_HOME/config.json" ]]; then
  cp "$TEMPLATES/config.json" "$MEMORY_HOME/config.json"
  echo "  created: config.json"
else
  echo "  kept:    config.json"
fi
write_hub_config_paths "$INSTALL_ROOT" "$MEMORY_HOME" "$DEV_ROOT"
write_cursor_hook_env "$INSTALL_ROOT" "$MEMORY_HOME"

mkdir -p "$MEMORY_HOME/chats/projects" "$MEMORY_HOME/chats/archive"
mkdir -p "$MEMORY_HOME/feedback/archive"
mkdir -p "$MEMORY_HOME/scripts" "$MEMORY_HOME/skills" "$MEMORY_HOME/sources"

# manifest.json — always ensure exists with distilled_at schema (do not wipe user data)
if [[ ! -f "$MANIFEST" ]]; then
  cp "$TEMPLATES/chats/manifest.json" "$MANIFEST"
  echo "  created: chats/manifest.json (with distilled_at schema)"
else
  echo "  kept:    chats/manifest.json (existing — run list-chats.py to check pending)"
fi

for script in list-chats.py verify-memory.py memory-status.py; do
  cp -f "$INSTALL_ROOT/scripts/$script" "$MEMORY_HOME/scripts/$script"
  chmod +x "$MEMORY_HOME/scripts/$script"
done
cp -rf "$INSTALL_ROOT/scripts/lib" "$MEMORY_HOME/scripts/"

touch "$MEMORY_HOME/sources/.gitkeep" 2>/dev/null || true

if [[ ! -f "$MEMORY_HOME/README.md" ]]; then
  cat > "$MEMORY_HOME/README.md" <<EOF
# Personal Memory Hub

User data for [agent-memory]($INSTALL_ROOT). **Do not commit to public git.**

- \`context/\` — identity, rules, preferences
- \`feedback/\` — wins (+) and fails (−), use \`_superseded_\` when codified in conventions
- \`chats/\` — distilled history + \`manifest.json\`
- \`skills/\` — your optional domain skills
- \`sources/\` — reference material

Framework: \`$INSTALL_ROOT/INSTRUCTIONS.md\` (Session start / Session end)
EOF
fi

echo
echo "Done."
echo "  1. Edit: $MEMORY_HOME/context/GLOBAL_CONTEXT.md"
echo "  2. Skill: bash $INSTALL_ROOT/scripts/link-cursor-skills.sh --force"
echo "  3. Sync: say 'sync with agent memory' in Cursor, or:"
echo "     python3 $INSTALL_ROOT/scripts/sync-memory.py --memory-home $MEMORY_HOME"
echo "  4. Optional handoff: cp templates/repo-handoff/AGENT_HANDOFF.md your-project/"
echo "  5. Status: python3 $INSTALL_ROOT/scripts/memory-status.py --memory-home $MEMORY_HOME"
echo "  6. Verify: python3 $INSTALL_ROOT/scripts/verify-memory.py --memory-home $MEMORY_HOME"
echo
echo "  Hub (gitignored): $MEMORY_HOME/"
echo "  Config: $MEMORY_HOME/config.json"
