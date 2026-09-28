#!/usr/bin/env bash
# Runs a frontend quality tool for pre-commit.
#
# pre-commit invokes hooks with a minimal PATH, and on Windows `npm run` routes
# scripts through cmd.exe (which may not have node on PATH). So we ensure node is
# reachable and call the tool's JS entrypoint directly via node.
set -euo pipefail

if ! command -v node >/dev/null 2>&1; then
  # Standard Windows install location; adjust if node lives elsewhere.
  export PATH="/c/Program Files/nodejs:$PATH"
fi

cd "$(dirname "$0")/../frontend"

case "${1:-}" in
  lint) exec node node_modules/eslint/bin/eslint.js . ;;
  format) exec node node_modules/prettier/bin/prettier.cjs --check . ;;
  *)
    echo "usage: frontend-check.sh {lint|format}" >&2
    exit 2
    ;;
esac
