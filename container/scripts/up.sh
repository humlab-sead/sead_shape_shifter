#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-shapeshifter}"
HOST_PORT="${HOST_PORT:-8012}"

cd "$ROOT_DIR"

echo "Starting container..."
podman-compose \
  -f podman-compose.yml \
  -p "${COMPOSE_PROJECT_NAME}" \
  up -d

echo "✓ Container started"
echo ""
echo "Access your application at:"
echo "  http://localhost:${HOST_PORT}"
echo ""
echo "View logs: make logs"
echo "Check health: make healthcheck"
