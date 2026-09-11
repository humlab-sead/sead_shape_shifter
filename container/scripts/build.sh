#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
USER_UID="${USER_UID:-$(id -u)}"
USER_GID="${USER_GID:-$(id -g)}"

cd "$ROOT_DIR"

echo "Building container image..."
podman-compose \
  -f podman-compose.yml \
  --profile default \
  build \
  --build-arg USER_UID="${USER_UID}" \
  --build-arg USER_GID="${USER_GID}"

echo "✓ Build complete"
