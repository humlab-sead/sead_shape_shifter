#!/usr/bin/env bash
# Bootstrap the Podman deployment on a fresh host.
#
# Checks prerequisites, downloads the container/ deployment files for a branch,
# then leaves the host ready to run: make setup && make build && make up
#
# Usage:
#   bash get-install.sh [--ref REF] [--repo URL]
#
# REF is a branch or a release tag. --branch is accepted as an alias.
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/humlab-sead/sead_shape_shifter.git}"
REF="${REF:-${BRANCH:-main}}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --ref | --branch)
      REF="$2"
      shift 2
      ;;
    --repo)
      REPO_URL="$2"
      shift 2
      ;;
    -h | --help)
      echo "Usage: bash get-install.sh [--ref REF] [--repo URL]"
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

# The archive URL accepts a branch or a tag. The wildcard matches the top-level
# directory, whose name differs between the two: GitHub strips the leading 'v'
# from a tag, so v2.1.0 extracts to sead_shape_shifter-2.1.0/.
ARCHIVE_URL="${REPO_URL%.git}/archive/${REF}.tar.gz"

echo ""
echo "Downloading container deployment files for ref '$REF'..."
if ! curl -fsSL "$ARCHIVE_URL" | tar -xz --wildcards --strip-components=1 '*/container/*'; then
  echo "error: could not download $ARCHIVE_URL" >&2
  echo "info: check that '$REF' is an existing branch or tag in $REPO_URL" >&2
  exit 1
fi

echo "Deployment files extracted."

# Record the repository and ref in container/.env, so `make build` builds the
# ref that was just downloaded instead of the default in .env.example.
if [ -d container ]; then
  if [ ! -f container/.env ] && [ -f container/.env.example ]; then
    cp container/.env.example container/.env
  fi
  # shellcheck source=env-config.sh
  . container/scripts/env-config.sh
  # shellcheck source=load-env.sh
  ENV_FILE="$PWD/container/.env" . container/scripts/load-env.sh
  env_image="${IMAGE_NAME:-shape-shifter:latest}"
  shapeshifter_env_file_set container/.env GIT_REPO "$REPO_URL"
  shapeshifter_env_file_set container/.env GIT_REF "$REF"
  shapeshifter_env_file_set container/.env IMAGE_NAME "$(shapeshifter_image_for_ref "$REF" "${env_image%%:*}")"
  echo "Recorded GIT_REPO, GIT_REF and IMAGE_NAME in container/.env"
fi

echo ""
echo "Next steps:"
echo "  cd container"
echo "  review .env               # repository, ref, image, port"
echo "  make install-ucanaccess   # required only for MS Access data sources"
echo "  make setup"
echo "  nano ../container-data/backend.env"
echo "  make build"
echo "  make up"
