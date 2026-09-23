#!/usr/bin/env bash
# Check the container health endpoint.
set -euo pipefail

# Load CONFIG_DIR/deployment.env values that the environment has not already
# set, so the container name and host port match the deployed environment.
# shellcheck source=load-env.sh
. "$(dirname -- "${BASH_SOURCE[0]}")/load-env.sh"

CONTAINER_NAME="${CONTAINER_NAME:-shape-shifter}"
HOST_PORT="${HOST_PORT:-8012}"
HEALTHCHECK_TIMEOUT="${HEALTHCHECK_TIMEOUT:-60}"

echo "Running health check (up to ${HEALTHCHECK_TIMEOUT}s)..."

# The application needs time to answer after `make up` returns, so retry until
# the timeout instead of reporting a failure for a container that is still
# starting. Set HEALTHCHECK_TIMEOUT=0 for a single attempt.
health_deadline=$((SECONDS + HEALTHCHECK_TIMEOUT))
while :; do
  # Prefer Podman's own healthcheck, which uses the image's Python interpreter.
  if podman healthcheck run "${CONTAINER_NAME}" >/dev/null 2>&1; then
    echo "+ Health check passed (podman healthcheck)"
    exit 0
  fi

  # Fall back to an in-container request.
  if podman exec "${CONTAINER_NAME}" \
    python -c "import urllib.request; urllib.request.urlopen('http://localhost:8012/api/v1/health').read()" >/dev/null 2>&1; then
    echo "+ Health check passed (in-container request)"
    exit 0
  fi

  # Last resort: query the published port from the host.
  if command -v curl >/dev/null 2>&1 && curl -sf "http://localhost:${HOST_PORT}/api/v1/health" >/dev/null 2>&1; then
    echo "+ Health check passed (host request)"
    exit 0
  fi

  if [ "$SECONDS" -ge "$health_deadline" ]; then
    break
  fi
  sleep 2
done

echo "x Health check failed after ${HEALTHCHECK_TIMEOUT}s" >&2
echo "  The application did not answer on port ${HOST_PORT}. Check its state and logs:" >&2
echo "    make status" >&2
echo "    make logs" >&2
exit 1
