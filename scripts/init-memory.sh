#!/usr/bin/env bash
# Bootstrap user memory data directory from templates.
# Framework repo: agent-memory · Does not overwrite existing files.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
# shellcheck source=lib/config.sh
source "$SCRIPT_DIR/lib/config.sh"

if [[ ! -f "$REPO_ROOT/INSTRUCTIONS.md" ]]; then
  echo "Error: not a framework repo: $REPO_ROOT" >&2
  exit 1
fi

FRAMEWORK_ROOT="$(resolve_framework_root "" "$REPO_ROOT")"
MEMORY_HOME="$(resolve_memory_home "${MEMORY_HOME:-}" "$FRAMEWORK_ROOT")"
TEMPLATES="$FRAMEWORK_ROOT/templates"
MANIFEST="$MEMORY_HOME/chats/manifest.json"

echo "Agent Memory — init"
echo "  Framework: $FRAMEWORK_ROOT"
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
write_hub_config_paths "$FRAMEWORK_ROOT" "$MEMORY_HOME"
write_cursor_hook_env "$FRAMEWORK_ROOT" "$MEMORY_HOME"

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
  cp -f "$FRAMEWORK_ROOT/scripts/$script" "$MEMORY_HOME/scripts/$script"
  chmod +x "$MEMORY_HOME/scripts/$script"
done
cp -rf "$FRAMEWORK_ROOT/scripts/lib" "$MEMORY_HOME/scripts/"

touch "$MEMORY_HOME/sources/.gitkeep" 2>/dev/null || true

if [[ ! -f "$MEMORY_HOME/README.md" ]]; then
  cat > "$MEMORY_HOME/README.md" <<EOF
# Personal Memory Hub

User data for [agent-memory]($FRAMEWORK_ROOT). **Do not commit to public git.**

- \`context/\` — identity, rules, preferences
- \`feedback/\` — wins (+) and fails (−), use \`_superseded_\` when codified in conventions
- \`chats/\` — distilled history + \`manifest.json\`
- \`skills/\` — your optional domain skills
- \`sources/\` — reference material

Framework: \`$FRAMEWORK_ROOT/INSTRUCTIONS.md\` (Session start / Session end)
EOF
fi

echo
echo "Done."
echo "  1. Edit: $MEMORY_HOME/context/GLOBAL_CONTEXT.md"
echo "  2. Skill: bash $FRAMEWORK_ROOT/scripts/link-cursor-skills.sh --force"
echo "  3. Sync: say 'sync with agent memory' in Cursor, or:"
echo "     python3 $FRAMEWORK_ROOT/scripts/sync-memory.py --memory-home $MEMORY_HOME"
echo "  4. Status: python3 $FRAMEWORK_ROOT/scripts/memory-status.py --memory-home $MEMORY_HOME"
echo "  5. Verify: python3 $FRAMEWORK_ROOT/scripts/verify-memory.py --memory-home $MEMORY_HOME"
echo
echo "  Hub (gitignored): $MEMORY_HOME/"
echo "  Config: $MEMORY_HOME/config.json"
