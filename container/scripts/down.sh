#!/usr/bin/env bash
# Stop the Shape Shifter container with podman-compose.
set -euo pipefail

# Load CONFIG_DIR/deployment.env values that the environment has not already
# set, and resolve CONFIG_DIR and CONTAINER_DATA_DIR for podman-compose.
# shellcheck source=load-env.sh
. "$(dirname -- "${BASH_SOURCE[0]}")/load-env.sh"

SCRIPT_DIR="$(CDPATH='' cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

export HOST_PORT="${HOST_PORT:-8012}"
export IMAGE_NAME="${IMAGE_NAME:-shape-shifter:latest}"
COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-shapeshifter}"

cd "$ROOT_DIR"

echo "Stopping container..."
podman-compose \
  -f podman-compose.yml \
  -p "${COMPOSE_PROJECT_NAME}" \
  down

echo "Container stopped"
