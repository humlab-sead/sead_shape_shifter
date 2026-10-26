#!/usr/bin/env bash
# Control the Shape Shifter container and its systemd user service.
#
# Usage: container.sh <action> [service-action]
#
# One entry point for every container lifecycle action and systemd service
# action, so the deployment configuration and the command behind each action are
# defined in one place. The Makefile up/down/restart/logs/status targets and the
# service-* targets call this script, and the systemd unit starts the container
# through its up action and stops it through its down action.
set -euo pipefail

# Load CONFIG_DIR/deployment.env values that the environment has not already
# set, resolve the paths podman-compose mounts, and export the shared deployment
# settings (image, container, port, compose project) the compose file reads.
# shellcheck source=_load-env.sh
. "$(dirname -- "${BASH_SOURCE[0]}")/_load-env.sh"

SCRIPT_DIR="$(
  CDPATH=''
  cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd
)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# The compose file mounts CONTAINER_DATA_DIR and reads the image, container and
# port names from the environment. _load-env.sh resolves CONTAINER_DATA_DIR and
# exports the shared deployment settings from deployment.env or the bundled
# .env.example template, so every action agrees on the running container without
# another set of defaults here.
export CONTAINER_DATA_DIR HOST_PORT IMAGE_NAME CONTAINER_NAME COMPOSE_PROJECT_NAME

# Run every compose action from the container directory, because the compose
# path is relative and the build context resolves from there.
cd "$ROOT_DIR"
compose=(podman-compose -f podman-compose.yml -p "$COMPOSE_PROJECT_NAME")

usage() {
  cat <<EOF
Usage: $(basename -- "${BASH_SOURCE[0]}") <action> [service-action]

Actions:
  up               Start the container (reuses the image built by make build)
  down             Stop and remove the container
  restart          Stop the container, then start it again
  logs             Follow the container log
  status           Show container status and health
  service ACTION   Control the systemd user service (see 'service help')
  help             Show this help

Environment:
  CONFIG_DIR            deployment configuration directory (default: ~/config)
  DATA_DIR              mutable data directory (default: ~/container-data)
  CONTAINER_DATA_DIR    directory podman-compose mounts (defaults to DATA_DIR)
  IMAGE_NAME            image to run (default: shape-shifter:latest)
  HOST_PORT             published host port (default: 8012)
  COMPOSE_PROJECT_NAME  compose project name (default: shapeshifter)
  CONTAINER_NAME        container name for status (default: shape-shifter)

Examples:
  scripts/container.sh up
  make logs
  IMAGE_NAME=shape-shifter:dev scripts/container.sh restart
EOF
}

# Confirm the inputs the compose file mounts and the image up reuses. Naming the
# setting in the error, rather than letting podman report a missing path, keeps a
# stale relative override diagnosable.
check_deployment() {
  if [ ! -f "$CONFIG_DIR/backend.env" ]; then
    echo "error: $CONFIG_DIR/backend.env is missing. Run 'make setup' first." >&2
    exit 1
  fi

  if [ ! -d "$CONTAINER_DATA_DIR" ]; then
    echo "error: data directory does not exist: $CONTAINER_DATA_DIR" >&2
    echo "       CONFIG_DIR=$CONFIG_DIR" >&2
    echo "       A relative DATA_DIR names a path under your home directory. Run 'make setup', or" >&2
    echo "       correct DATA_DIR in $CONFIG_DIR/deployment.env." >&2
    exit 1
  fi

  for data_subdir in projects shared logs output backups tmp state; do
    if [ ! -d "$CONTAINER_DATA_DIR/$data_subdir" ]; then
      echo "error: data directory is incomplete: $CONTAINER_DATA_DIR/$data_subdir is missing" >&2
      echo "       Run 'make setup' to create the data directories." >&2
      exit 1
    fi
  done

  if ! podman image exists "$IMAGE_NAME"; then
    echo "error: image $IMAGE_NAME not found. Run 'make build' first." >&2
    exit 1
  fi
}

up() {
  check_deployment
  echo "Starting container..."
  "${compose[@]}" up -d --no-build
  echo "Container started"
  echo ""
  echo "Access your application at:"
  echo "  http://localhost:${HOST_PORT}"
  echo ""
  echo "View logs:    make logs"
  echo "Check health: make healthcheck"
}

down() {
  echo "Stopping container..."
  "${compose[@]}" down
  echo "Container stopped"
}

restart() {
  down
  up
}

logs() {
  # exec so Ctrl-C reaches podman-compose instead of the dispatcher.
  exec "${compose[@]}" logs -f
}

status() {
  echo "Container status:"
  podman ps -a --filter=name="${CONTAINER_NAME}" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
  echo ""
  echo "Health:"
  podman inspect "${CONTAINER_NAME}" \
    --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}no healthcheck{{end}}' 2>/dev/null \
    || echo "Container not present"
}

# ---------------------------------------------------------------------------
# systemd user service
# ---------------------------------------------------------------------------
# One entry point for every systemd action, so the unit name and the command
# behind each action live with the container actions. The unit itself starts the
# container through container.sh up and stops it through container.sh down.
# Service actions never invoke Podman or podman-compose.

SERVICE_NAME="${SERVICE_NAME:-shape-shifter}"
SERVICE_UNIT_FILE="${SERVICE_UNIT_FILE:-$ROOT_DIR/service/$SERVICE_NAME.service}"
USER_UNIT_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"

service_usage() {
  cat <<EOF
Usage: $(basename -- "${BASH_SOURCE[0]}") service <action>

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
  scripts/container.sh service install
  make service-status
  SERVICE_NAME=shape-shifter-dev scripts/container.sh service restart
EOF
}

# Copy the unit file into the user unit directory and make systemd read it.
service_install_unit() {
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

# Dispatch one service action. Called as 'container.sh service <action>'.
service() {
  case "${1:-}" in
  install)
    service_install_unit
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
    service_usage
    ;;
  '')
    service_usage >&2
    exit 64
    ;;
  *)
    echo "error: unknown service action '$1'" >&2
    service_usage >&2
    exit 64
    ;;
  esac
}

action="${1:-}"
case "$action" in
up)
  up
  ;;
down)
  down
  ;;
restart)
  restart
  ;;
logs)
  logs
  ;;
status)
  status
  ;;
service)
  service "${2:-}"
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
