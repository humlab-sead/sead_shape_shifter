#!/usr/bin/env bash
set -euo pipefail

CONTAINER_NAME="${CONTAINER_NAME:-shape-shifter}"

echo "Running health check..."
if podman exec "${CONTAINER_NAME}" curl -f http://localhost:8012/api/v1/health >/dev/null 2>&1; then
  echo "✓ Health check passed"
else
  echo "✗ Health check failed"
  exit 1
fi
