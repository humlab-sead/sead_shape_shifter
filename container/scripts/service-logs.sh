#!/usr/bin/env bash
set -euo pipefail
journalctl --user -u shape-shifter -f
