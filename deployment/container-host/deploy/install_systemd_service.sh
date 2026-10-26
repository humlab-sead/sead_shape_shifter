#!/usr/bin/env bash
# Install and enable the Shape Shifter user systemd service for an environment user.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: deployment/container-host/deploy/install_systemd_service.sh [USER]

Install and enable the Shape Shifter user systemd service for a configured
environment user (run as root).

The user must already have deployment files in ~/container, placed there by
whatever flow the environment uses. Until container images are published to
GHCR (see docs/proposals/GHCR_IMAGE_RELEASE.md), that is a manual copy or
sync of the deployment/container/ tree; the retired
shape-shifter-container-release manager is no longer required.

The unit runs the lifecycle scripts in ~/container, which read configuration from
the sibling ~/config directory, so no deployment value is stored in the unit
itself.

Examples:
  deployment/container-host/deploy/install_systemd_service.sh test-shape-shifter.sead.se
  USER=test-shape-shifter.sead.se deployment/container-host/deploy/install_systemd_service.sh
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
if [[ -z "$USER_HOME" || ! -d "$USER_HOME" ]]; then
  echo "error: cannot resolve a home directory for $USER" >&2
  exit 1
fi

# Require deployment files in ~/container. A real directory (the manual layout)
# or a symlink both pass, as long as the directory holds a Makefile and VERSION.
CONTAINER_DIR="$USER_HOME/container"
if [[ ! -d "$CONTAINER_DIR" ]]; then
  echo "error: $CONTAINER_DIR does not exist. Place the deployment/container/ tree there first." >&2
  exit 1
fi
if [[ ! -f "$CONTAINER_DIR/Makefile" || ! -f "$CONTAINER_DIR/VERSION" ]]; then
  echo "error: $CONTAINER_DIR does not look like a container deployment (no Makefile or VERSION)." >&2
  exit 1
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
