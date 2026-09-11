#!/usr/bin/env bash
set -euo pipefail
systemctl --user disable shape-shifter
echo "✓ Service disabled"
