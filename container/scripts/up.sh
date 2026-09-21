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
