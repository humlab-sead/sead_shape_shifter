#!/usr/bin/env bash
# Control the Shape Shifter systemd user service.
#
# Usage: service.sh <action>
#
# One entry point for every systemd action, so the unit name and the command
# behind each action are defined in one place. The Makefile service-* targets
# call this script. The unit itself starts the container through up.sh and
# stops it through down.sh.
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

SERVICE_NAME="${SERVICE_NAME:-shape-shifter}"
SERVICE_UNIT_FILE="${SERVICE_UNIT_FILE:-$ROOT_DIR/service/$SERVICE_NAME.service}"
USER_UNIT_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"

usage() {
  cat <<EOF
Usage: $(basename -- "${BASH_SOURCE[0]}") <action>

Actions:
  install   Copy the unit file into the systemd user unit directory and
            reload systemd
  enable    Start the service on login
  disable   Stop starting the service on login
  start     Start the service
  stop      Stop the service
  restart   Restart the service
  status    Show the service status
  logs      Follow the service log
  help      Show this help

Environment:
  SERVICE_NAME       systemd unit name (default: shape-shifter)
  SERVICE_UNIT_FILE  unit file to install
                     (default: service/<SERVICE_NAME>.service)

Examples:
  scripts/service.sh install
  make service-status
  SERVICE_NAME=shape-shifter-dev scripts/service.sh restart
EOF
}

# Copy the unit file into the user unit directory and make systemd read it.
install_unit() {
  if [ ! -f "$SERVICE_UNIT_FILE" ]; then
    echo "error: $SERVICE_UNIT_FILE not found" >&2
    exit 1
  fi
  mkdir -p "$USER_UNIT_DIR"
  cp "$SERVICE_UNIT_FILE" "$USER_UNIT_DIR/"
  systemctl --user daemon-reload
  echo "✓ Systemd user service installed"
  echo "Run: make service-enable"
}

action="${1:-}"
case "$action" in
install)
  install_unit
  ;;
enable)
  systemctl --user enable "$SERVICE_NAME"
  echo "✓ Service enabled for auto-start"
  ;;
disable)
  systemctl --user disable "$SERVICE_NAME"
  echo "✓ Service disabled"
  ;;
start)
  systemctl --user start "$SERVICE_NAME"
  echo "✓ Service started"
  ;;
stop)
  systemctl --user stop "$SERVICE_NAME"
  echo "✓ Service stopped"
  ;;
restart)
  systemctl --user restart "$SERVICE_NAME"
  echo "✓ Service restarted"
  ;;
status)
  systemctl --user status "$SERVICE_NAME"
  ;;
logs)
  # exec so Ctrl-C reaches journalctl instead of the dispatcher.
  exec journalctl --user -u "$SERVICE_NAME" -f
  ;;
help | -h | --help)
  usage
  ;;
'')
  usage >&2
  exit 64
  ;;
*)
  echo "error: unknown action '$action'" >&2
  usage >&2
  exit 64
  ;;
esac
