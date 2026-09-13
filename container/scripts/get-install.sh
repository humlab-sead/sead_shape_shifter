#!/usr/bin/env bash
# Bootstrap the Podman deployment on a fresh host.
#
# Checks prerequisites, downloads the container/ deployment files for a branch,
# then leaves the host ready to run: make setup && make build && make up
#
# Usage:
#   bash get-install.sh [--branch BRANCH] [--repo URL]
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/humlab-sead/sead_shape_shifter.git}"
BRANCH="${BRANCH:-main}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --branch)
      BRANCH="$2"
      shift 2
      ;;
    --repo)
      REPO_URL="$2"
      shift 2
      ;;
    -h|--help)
      echo "Usage: bash get-install.sh [--branch BRANCH] [--repo URL]"
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 1
      ;;
  esac
done

CURRENT_USER="$(whoami)"
failed=0

echo "Checking Podman setup for $CURRENT_USER..."

if command -v podman >/dev/null 2>&1; then
  echo "OK: podman installed ($(podman --version))"
else
  echo "FAIL: podman is not installed"
  failed=1
fi

if command -v podman-compose >/dev/null 2>&1; then
  echo "OK: podman-compose installed ($(podman-compose --version 2>/dev/null | head -n1))"
else
  echo "FAIL: podman-compose is not installed"
  failed=1
fi

if [[ "$(loginctl show-user "$CURRENT_USER" -p Linger --value 2>/dev/null)" == "yes" ]]; then
  echo "OK: lingering enabled for $CURRENT_USER"
else
  echo "FAIL: lingering not enabled for $CURRENT_USER"
  echo "info: run: sudo loginctl enable-linger $CURRENT_USER"
  failed=1
fi

if podman unshare id >/dev/null 2>&1; then
  echo "OK: rootless Podman user namespace works"
else
  echo "FAIL: 'podman unshare id' failed"
  failed=1
fi

if (( failed )); then
  echo "Podman setup is incomplete."
  exit 1
fi

echo ""
echo "Downloading container deployment files for branch '$BRANCH'..."
curl -L "${REPO_URL%.git}/archive/refs/heads/${BRANCH}.tar.gz" |
  tar -xz \
    --wildcards \
    --strip-components=1 \
    "sead_shape_shifter-${BRANCH}/container/*"

echo "Deployment files extracted."
echo ""
echo "Next steps:"
echo "  cd container"
echo "  make install-ucanaccess   # required only for MS Access data sources"
echo "  make setup"
echo "  nano ../container-data/backend.env"
echo "  make build"
echo "  make up"
