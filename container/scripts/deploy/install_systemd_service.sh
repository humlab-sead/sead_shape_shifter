#!/usr/bin/env bash
# Install and enable the Shape Shifter user systemd service for an environment user.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/deploy/install_systemd_service.sh [USER]

Install and enable the Shape Shifter user systemd service for a configured
environment user (run as root).

Examples:
  scripts/deploy/install_systemd_service.sh test-shape-shifter.sead.se
  USER=test-shape-shifter.sead.se scripts/deploy/install_systemd_service.sh
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

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run this script as root so it can install the user service." >&2
  exit 1
fi

USER_HOME="$(getent passwd "$USER" | cut -d: -f6)"
if [[ -z "$USER_HOME" || ! -d "$USER_HOME/container" ]]; then
  echo "Warning: no container/ directory found for $USER; run the deploy helper first." >&2
fi

sudo -u "$USER" bash -lc '
set -euo pipefail
cd ~/container
make service-install
systemctl --user enable shape-shifter
'

echo "Installed and enabled the systemd service for $USER"
printf 'Commands:\n'
printf '  systemctl --user -M %s@ status shape-shifter\n' "$USER"
printf '  systemctl --user -M %s@ restart shape-shifter\n' "$USER"
printf '  journalctl --user -M %s@ -u shape-shifter -f\n' "$USER"
