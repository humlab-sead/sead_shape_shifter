#!/usr/bin/env bash
# Control the Shape Shifter container with podman-compose.
#
# Usage: container.sh <action>
#
# One entry point for every container lifecycle action, so the deployment
# configuration and the command behind each action are defined in one place.
# The Makefile up/down/restart/logs/status targets call this script, and the
# systemd unit starts the container through its up action and stops it through
# its down action.
set -euo pipefail

# Load CONFIG_DIR/deployment.env values that the environment has not already
# set, and resolve the paths podman-compose mounts.
# shellcheck source=load-env.sh
. "$(dirname -- "${BASH_SOURCE[0]}")/load-env.sh"

SCRIPT_DIR="$(
  CDPATH=''
  cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd
)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# The compose file mounts CONTAINER_DATA_DIR and reads the image, container and
# port names from the environment. Resolve each value the same way for every
# action, so up, down, logs and status agree on the running container.
export CONTAINER_DATA_DIR="${CONTAINER_DATA_DIR:-$DATA_DIR}"
export HOST_PORT="${HOST_PORT:-8012}"
export IMAGE_NAME="${IMAGE_NAME:-shape-shifter:latest}"
CONTAINER_NAME="${CONTAINER_NAME:-shape-shifter}"
COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-shapeshifter}"

# Run every compose action from the container directory, because the compose
# path is relative and the build context resolves from there.
cd "$ROOT_DIR"
compose=(podman-compose -f podman-compose.yml -p "$COMPOSE_PROJECT_NAME")

usage() {
  cat <<EOF
Usage: $(basename -- "${BASH_SOURCE[0]}") <action>

Actions:
  up        Start the container (reuses the image built by make build)
  down      Stop and remove the container
  restart   Stop the container, then start it again
  logs      Follow the container log
  status    Show container status and health
  help      Show this help

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
    echo "       A relative DATA_DIR names a path beside the checkout. Run 'make setup', or correct" >&2
    echo "       DATA_DIR in $CONFIG_DIR/deployment.env." >&2
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
