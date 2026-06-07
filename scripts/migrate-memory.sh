#!/usr/bin/env bash
# Migrate data hub from an old path to MEMORY_HOME (rsync --ignore-existing).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
# shellcheck source=lib/config.sh
source "$SCRIPT_DIR/lib/config.sh"

FROM=""
TO=""
INCLUDE_SKILLS=false
DRY_RUN=false

usage() {
  cat <<EOF
Usage: $0 --from OLD_HUB [--to NEW_HUB] [--include-skills] [--dry-run]

Copies missing files from OLD_HUB into NEW_HUB (default: resolved MEMORY_HOME).
Layers: context/, feedback/, chats/ — never overwrites existing files.

Default NEW_HUB: <clone>/memory/ — edit memory/config.json after migrate
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --from) FROM="$2"; shift 2 ;;
    --to) TO="$2"; shift 2 ;;
    --include-skills) INCLUDE_SKILLS=true; shift ;;
    --dry-run) DRY_RUN=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown: $1"; usage; exit 1 ;;
  esac
done

[[ -n "$FROM" ]] || { echo "Error: --from required"; usage; exit 1; }

FROM="$(cd "$(_expand_tilde "$FROM")" && pwd)"
if [[ -n "$TO" ]]; then
  TO="$(_expand_tilde "$TO")"
  mkdir -p "$TO"
  TO="$(cd "$TO" && pwd)"
else
  TO="$(resolve_memory_home "")"
  mkdir -p "$TO"
fi

if [[ ! -d "$FROM" ]]; then
  echo "Error: source not found: $FROM"
  exit 1
fi

if [[ "$FROM" == "$TO" ]]; then
  echo "Error: --from and --to are the same"
  exit 1
fi

RSYNC=(rsync -a --ignore-existing)
[[ "$DRY_RUN" == true ]] && RSYNC+=(--dry-run -v)

echo "Migrate memory hub"
echo "  From: $FROM"
echo "  To:   $TO"
echo

migrate_tree() {
  local sub="$1"
  if [[ ! -d "$FROM/$sub" ]]; then
    echo "  skip: $sub (not in source)"
    return
  fi
  mkdir -p "$TO/$sub"
  echo "  copy: $sub/"
  "${RSYNC[@]}" "$FROM/$sub/" "$TO/$sub/"
}

migrate_tree context
migrate_tree feedback
migrate_tree chats

if [[ "$INCLUDE_SKILLS" == true ]]; then
  migrate_tree skills
fi

# config.json — only if missing at destination
if [[ -f "$FROM/config.json" && ! -f "$TO/config.json" && "$DRY_RUN" != true ]]; then
  cp "$FROM/config.json" "$TO/config.json"
  echo "  created: config.json"
elif [[ -f "$REPO_ROOT/templates/config.json" && ! -f "$TO/config.json" && "$DRY_RUN" != true ]]; then
  cp "$REPO_ROOT/templates/config.json" "$TO/config.json"
  echo "  created: config.json (from template)"
fi

# utility scripts
if [[ "$DRY_RUN" != true ]]; then
  mkdir -p "$TO/scripts"
  for script in list-chats.py verify-memory.py memory-status.py; do
    if [[ -f "$REPO_ROOT/scripts/$script" ]]; then
      cp -f "$REPO_ROOT/scripts/$script" "$TO/scripts/$script"
      chmod +x "$TO/scripts/$script" 2>/dev/null || true
    fi
  done
  cp -rf "$REPO_ROOT/scripts/lib" "$TO/scripts/" 2>/dev/null || true
fi

echo
echo "Done."
if [[ "$DRY_RUN" != true ]]; then
  write_hub_config_paths "$REPO_ROOT" "$TO" 2>/dev/null || true
  echo "  Hub: $TO (memory/config.json updated)"
  echo "  Or: export MEMORY_HOME=$TO"
  echo "  Check: python3 $REPO_ROOT/scripts/memory-status.py --memory-home $TO"
  echo "  Verify: python3 $TO/scripts/verify-memory.py --memory-home $TO"
fi
