#!/usr/bin/env bash
# Start the Shape Shifter container with podman-compose.
set -euo pipefail

# Load CONFIG_DIR/deployment.env values that the environment has not already set.
# shellcheck source=load-env.sh
. "$(dirname -- "${BASH_SOURCE[0]}")/load-env.sh"

SCRIPT_DIR="$(
  CDPATH=''
  cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd
)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

export CONTAINER_DATA_DIR="${CONTAINER_DATA_DIR:-$DATA_DIR}"
export HOST_PORT="${HOST_PORT:-8012}"
export IMAGE_NAME="${IMAGE_NAME:-shape-shifter:latest}"
COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-shapeshifter}"

if [ ! -f "$CONFIG_DIR/backend.env" ]; then
  echo "error: $CONFIG_DIR/backend.env is missing. Run 'make setup' first." >&2
  exit 1
fi

# The compose mounts resolve from these values, and podman reports only
# "statfs <path>: no such file or directory" when one is wrong. Name the
# setting instead, because a relative path override that was carried over from
# the retired container/.env resolves one level too high.
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

cd "$ROOT_DIR"

echo "Starting container..."
podman-compose \
  -f podman-compose.yml \
  -p "${COMPOSE_PROJECT_NAME}" \
  up -d

echo "Container started"
echo ""
echo "Access your application at:"
echo "  http://localhost:${HOST_PORT}"
echo ""
echo "View logs:    make logs"
echo "Check health: make healthcheck"
