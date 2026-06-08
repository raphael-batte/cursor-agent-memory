#!/usr/bin/env bash
# Create public GitHub repo and push. Requires: gh auth login -h github.com -p ssh -s repo
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO="raphael-batte/cursor-agent-memory"
GITHUB_DESCRIPTION='Persistent working memory for Cursor. Routed layers, private hub, one @agent-memory skill, auto-distill + ## Next step pointer. Secrets redaction on distill; verify-memory + gitleaks guard the hub. MIT.'
VERSION="$(tr -d '[:space:]' < "$REPO_ROOT/VERSION")"

cd "$REPO_ROOT"

if ! command -v gh &>/dev/null; then
  echo "Install: brew install gh"
  exit 1
fi

if ! gh auth status &>/dev/null; then
  echo "Not logged in. Run:"
  echo "  gh auth login -h github.com -p ssh -s repo"
  exit 1
fi

if git ls-remote "git@github-personal:${REPO}.git" HEAD &>/dev/null; then
  echo "Repo exists — pushing only"
  git push -u origin main
else
  gh repo create "$REPO" \
    --public \
    --source=. \
    --remote=origin \
    --description "$GITHUB_DESCRIPTION" \
    --push
fi

gh repo edit "$REPO" --description "$GITHUB_DESCRIPTION"

if git rev-parse "v${VERSION}" &>/dev/null; then
  git push origin "v${VERSION}" || git push origin "v${VERSION}" --force
fi

echo "Done: https://github.com/${REPO}"
