#!/usr/bin/env bash
# Install and enable the Shape Shifter user systemd service for an environment user.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/deploy/install_systemd_service.sh [USER]

Install and enable the Shape Shifter user systemd service for a configured
environment user (run as root).

The user must already have a selected container release: ~/container is the
symlink the host release manager creates. Install and select a release first:

  sudo shape-shifter-container-release install  USER container-vX.Y.Z
  sudo shape-shifter-container-release activate USER container-vX.Y.Z

The unit runs the lifecycle scripts in ~/container, which read configuration from
the sibling ~/config directory, so no deployment value is stored in the unit
itself.

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
if [[ -z "$USER_HOME" || ! -d "$USER_HOME" ]]; then
  echo "error: cannot resolve a home directory for $USER" >&2
  exit 1
fi

# Require a selected release, the same way the single-environment helper does.
# A real directory or an unrelated symlink is refused: an administrator must
# review and move it before the release manager can select a version.
CONTAINER_LINK="$USER_HOME/container"
if [[ ! -L "$CONTAINER_LINK" ]]; then
  echo "error: $CONTAINER_LINK is not a selected container release." >&2
  if [[ -d "$CONTAINER_LINK" ]]; then
    echo "       It is a real directory. An administrator must review and move it, then install" >&2
    echo "       and activate a release:" >&2
  else
    echo "       Nothing is selected. As root, run:" >&2
  fi
  echo "         shape-shifter-container-release install  $USER container-vX.Y.Z" >&2
  echo "         shape-shifter-container-release activate $USER container-vX.Y.Z" >&2
  exit 1
fi
SELECTED_DIR="$(readlink -f -- "$CONTAINER_LINK")"
if [[ ! -d "$SELECTED_DIR" || ! -f "$SELECTED_DIR/Makefile" || ! -f "$SELECTED_DIR/VERSION" ]]; then
  echo "error: $CONTAINER_LINK does not resolve to a complete container release ($SELECTED_DIR)" >&2
  echo "       Reinstall and activate the release with shape-shifter-container-release." >&2
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
