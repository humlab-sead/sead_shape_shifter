#!/usr/bin/env bash
set -euo pipefail

CONTAINER_NAME="${CONTAINER_NAME:-shape-shifter}"

echo "Container Status:"
podman ps --filter=name="${CONTAINER_NAME}" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""
echo "Container Details:"
podman inspect "${CONTAINER_NAME}" 2>/dev/null | grep -E '"Status"|"Running"' || echo "Container not running"
