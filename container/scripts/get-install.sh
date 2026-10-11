#!/usr/bin/env bash
# Check the host prerequisites for the Podman deployment.
#
# This script only inspects the host: Podman, podman-compose, lingering, and the
# rootless user namespace. It downloads nothing and writes nothing into
# ~/container. Container deployment files are installed as a versioned release
# with the host release manager (shape-shifter-container-release); see
# container/DEPLOYMENT.md. Application image settings are configured by
# scripts/deploy/deploy_single_environment.sh.
#
# Usage:
#   bash get-install.sh
set -euo pipefail

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h | --help)
      echo "Usage: bash get-install.sh"
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
echo "Host prerequisites are satisfied for $CURRENT_USER."
echo ""
echo "Next steps:"
echo "  # Install and select a container release (as root):"
echo "  sudo shape-shifter-container-release install  $CURRENT_USER container-vX.Y.Z"
echo "  sudo shape-shifter-container-release activate $CURRENT_USER container-vX.Y.Z"
echo ""
echo "  # Then configure and start the environment as $CURRENT_USER:"
echo "  cd ~/container"
echo "  make setup"
echo "  nano ~/config/backend.env"
echo "  make build"
echo "  make up"
