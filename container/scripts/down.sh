#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-shapeshifter}"

cd "$ROOT_DIR"

echo "Stopping container..."
podman-compose \
  -f podman-compose.yml \
  -p "${COMPOSE_PROJECT_NAME}" \
  down

echo "✓ Container stopped"
