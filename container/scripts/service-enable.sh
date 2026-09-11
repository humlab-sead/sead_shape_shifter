#!/usr/bin/env bash
set -euo pipefail
systemctl --user enable shape-shifter
echo "✓ Service enabled for auto-start"
