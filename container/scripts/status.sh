#!/usr/bin/env bash
# Show container status.
set -euo pipefail

CONTAINER_NAME="${CONTAINER_NAME:-shape-shifter}"

echo "Container status:"
podman ps -a --filter=name="${CONTAINER_NAME}" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""
echo "Health:"
podman inspect "${CONTAINER_NAME}" \
  --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}no healthcheck{{end}}' 2>/dev/null \
  || echo "Container not present"
