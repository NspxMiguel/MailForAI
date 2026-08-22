#!/usr/bin/env bash
# Puts `mailforai` on the PATH by symlinking it into ~/.local/bin.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="${MAILFORAI_BIN:-$HOME/.local/bin}"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required and was not found on PATH." >&2
  exit 1
fi

mkdir -p "$TARGET_DIR"
ln -sf "$REPO_DIR/bin/mailforai" "$TARGET_DIR/mailforai"
echo "linked $TARGET_DIR/mailforai -> $REPO_DIR/bin/mailforai"

case ":$PATH:" in
  *":$TARGET_DIR:"*) ;;
  *) echo "note: $TARGET_DIR is not on your PATH — add it to your shell profile." ;;
esac

echo
echo "next: mailforai setup"
