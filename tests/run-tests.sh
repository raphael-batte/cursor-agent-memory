#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/tests"

echo "== Python tests =="
python3 -m unittest discover -v

echo
echo "== Shell tests =="
bash test_shell_scripts.sh

echo
echo "All tests passed."
