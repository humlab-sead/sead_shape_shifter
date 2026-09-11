#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/install_systemd_service.sh [USER]

Install and enable the Shape Shifter user systemd service for a configured environment user.

Examples:
  scripts/install_systemd_service.sh shapeshifter-test
  USER=shapeshifter-test scripts/install_systemd_service.sh
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

USER="${1:-${USER:-}}"
if [[ -z "$USER" ]]; then
  echo "A system user is required." >&2
  usage >&2
  exit 1
fi

sudo -u "$USER" bash -lc '
set -euo pipefail
cd ~/sead_shape_shifter/container
make service-install
systemctl --user enable shape-shifter
'

echo "Installed and enabled the systemd service for $USER"
printf 'Use these commands as needed:\n'
printf '  systemctl --user -M %s@ start shape-shifter\n' "$USER"
printf '  systemctl --user -M %s@ status shape-shifter\n' "$USER"
printf '  systemctl --user -M %s@ stop shape-shifter\n' "$USER"
