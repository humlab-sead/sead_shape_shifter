#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SERVICE_DIR="${ROOT_DIR}/service"

if [[ ! -d ~/.config/systemd/user ]]; then
  mkdir -p ~/.config/systemd/user
fi

if [[ -f "$SERVICE_DIR/shape-shifter.service" ]]; then
  cp "$SERVICE_DIR/shape-shifter.service" ~/.config/systemd/user/
  systemctl --user daemon-reload
  echo "✓ Systemd user service installed"
  echo "Run: systemctl --user enable shape-shifter"
else
  echo "✗ service/shape-shifter.service not found" >&2
  exit 1
fi
