#!/usr/bin/env bash
# Copy framework from dev clone to install clone (Cursor-connected).
# User data (memory/) stays on install only — never synced from dev.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEV_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
# shellcheck source=lib/config.sh
source "$SCRIPT_DIR/lib/config.sh"

DRY_RUN=false
INSTALL_OVERRIDE=""

usage() {
  cat <<EOF
Usage: $0 [options]

Sync framework code from dev clone → install clone.
Excludes: memory/, .git/, dev.config.json, user-local files.

Options:
  --install-root PATH   Override dev.config.json install_root
  --dry-run             Show rsync command without copying
  -h, --help            This help

Setup:
  cp dev.config.json.example dev.config.json
  git clone … <install-clone>   # set install_root in dev.config.json
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=true; shift ;;
    --install-root) INSTALL_OVERRIDE="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown: $1" >&2; usage; exit 1 ;;
  esac
done

if [[ ! -f "$DEV_ROOT/INSTRUCTIONS.md" ]]; then
  echo "Error: not a framework repo: $DEV_ROOT" >&2
  exit 1
fi

INSTALL_ROOT="$(resolve_install_root "$INSTALL_OVERRIDE" "$DEV_ROOT")"
if [[ -z "$INSTALL_ROOT" ]]; then
  echo "Error: install root unknown — copy dev.config.json.example → dev.config.json" >&2
  exit 1
fi

if [[ "$(cd "$DEV_ROOT" && pwd)" == "$(cd "$INSTALL_ROOT" && pwd)" ]]; then
  echo "Dev and install are the same path — nothing to sync." >&2
  exit 0
fi

RSYNC_EXCLUDES=(
  --exclude memory/
  --exclude .git/
  --exclude dev.config.json
  --exclude .DS_Store
  --exclude .idea/
  --exclude .vscode/
)

echo "Agent Memory — sync to install"
echo "  Dev:     $DEV_ROOT"
echo "  Install: $INSTALL_ROOT"
echo

if [[ "$DRY_RUN" == true ]]; then
  echo "would rsync -a ${RSYNC_EXCLUDES[*]} --delete $DEV_ROOT/ $INSTALL_ROOT/"
  exit 0
fi

if ! command -v rsync &>/dev/null; then
  echo "Error: rsync required" >&2
  exit 1
fi

mkdir -p "$INSTALL_ROOT"
rsync -a "${RSYNC_EXCLUDES[@]}" --delete "$DEV_ROOT/" "$INSTALL_ROOT/"

echo "Done. Next:"
echo "  bash $INSTALL_ROOT/scripts/link-cursor-skills.sh --force"
echo "  bash $INSTALL_ROOT/scripts/init-memory.sh   # hub at $INSTALL_ROOT/memory/"
