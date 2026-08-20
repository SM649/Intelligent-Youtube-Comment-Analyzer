#!/usr/bin/env bash
set -euo pipefail

CLI_VERSION="v3.4.17"
CLI_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/.tailwindcss-cli"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ ! -x "$CLI_PATH" ]; then
  OS="$(uname -s)"
  ARCH="$(uname -m)"
  case "$OS-$ARCH" in
    Linux-x86_64) ASSET="tailwindcss-linux-x64" ;;
    Linux-aarch64) ASSET="tailwindcss-linux-arm64" ;;
    Darwin-x86_64) ASSET="tailwindcss-macos-x64" ;;
    Darwin-arm64) ASSET="tailwindcss-macos-arm64" ;;
    *)
      echo "Unsupported platform: $OS-$ARCH. Download the CLI manually from" >&2
      echo "https://github.com/tailwindlabs/tailwindcss/releases/tag/$CLI_VERSION" >&2
      echo "and save it as $CLI_PATH" >&2
      exit 1
      ;;
  esac
  echo "Downloading Tailwind CLI $CLI_VERSION ($ASSET)..."
  curl -sSL -o "$CLI_PATH" \
    "https://github.com/tailwindlabs/tailwindcss/releases/download/$CLI_VERSION/$ASSET"
  chmod +x "$CLI_PATH"
fi

"$CLI_PATH" \
  -i "$REPO_ROOT/static/tailwind-input.css" \
  -o "$REPO_ROOT/static/tailwind.css" \
  --config "$REPO_ROOT/tailwind.config.js" \
  --watch
