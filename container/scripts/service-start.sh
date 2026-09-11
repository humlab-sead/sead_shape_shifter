#!/usr/bin/env bash
set -euo pipefail
systemctl --user start shape-shifter
echo "✓ Service started"
