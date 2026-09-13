#!/usr/bin/env bash
# Deploy one Shape Shifter environment for a dedicated system user.
#
# Run as root (or a sudo-capable admin) on the deployment host. The script
# fetches the container/ deployment files into the user's home directory
# (~/container), keeps ~/container-data intact, and runs the initial setup.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/deploy_single_environment.sh <USER> [--repo URL] [--branch BRANCH] [--host-port PORT]

Deploy a single Shape Shifter environment for a dedicated system user.

Options:
  --repo, --repository  Git repository URL. Default: https://github.com/humlab-sead/sead_shape_shifter.git
  --branch              Git branch to fetch. Default: main
  --host-port           Host port for the container. Default: 8012
  --no-build            Prepare files only; do not build or start
  -h, --help            Show this help message

Examples:
  scripts/deploy_single_environment.sh test-shape-shifter.sead.se
  scripts/deploy_single_environment.sh shapeshifter-prod --host-port 8013
EOF
}

USER=""
REPO_URL="${REPO_URL:-https://github.com/humlab-sead/sead_shape_shifter.git}"
BRANCH="${BRANCH:-main}"
HOST_PORT="${HOST_PORT:-8012}"
DO_BUILD=true

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --repo|--repository) REPO_URL="$2"; shift 2 ;;
    --branch) BRANCH="$2"; shift 2 ;;
    --host-port) HOST_PORT="$2"; shift 2 ;;
    --no-build) DO_BUILD=false; shift ;;
    -*) echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    *)
      if [[ -z "$USER" ]]; then USER="$1"; else echo "Unexpected argument: $1" >&2; exit 1; fi
      shift
      ;;
  esac
done

if [[ -z "$USER" ]]; then
  echo "A system user name is required." >&2
  usage >&2
  exit 1
fi

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run this script as root so it can act as the deployment user." >&2
  exit 1
fi

ARCHIVE_URL="${REPO_URL%.git}/archive/refs/heads/${BRANCH}.tar.gz"
ARCHIVE_PREFIX="sead_shape_shifter-${BRANCH}/container/*"

echo "Fetching deployment files for $USER (branch $BRANCH)..."
sudo -u "$USER" env ARCHIVE_URL="$ARCHIVE_URL" ARCHIVE_PREFIX="$ARCHIVE_PREFIX" bash -lc '
set -euo pipefail
cd ~
if [ -d container ]; then
  tmp_dir="$(mktemp -d)"
  curl -fsSL "$ARCHIVE_URL" | tar -xz -C "$tmp_dir" --wildcards --strip-components=1 "$ARCHIVE_PREFIX"
  cp -a "$tmp_dir/container/." "$HOME/container/"
  rm -rf "$tmp_dir"
else
  curl -fsSL "$ARCHIVE_URL" | tar -xz --wildcards --strip-components=1 "$ARCHIVE_PREFIX"
fi
cd ~/container
bash scripts/setup.sh
'

if [[ "$DO_BUILD" = true ]]; then
  echo "Building and starting the container..."
  sudo -u "$USER" env HOST_PORT="$HOST_PORT" bash -lc '
set -euo pipefail
cd ~/container
make build
make up
'
fi

echo
echo "Deployment for $USER is configured."
echo "Edit the environment file before first use:"
echo "  sudo -u $USER nano ~/container-data/backend.env"
echo "Then verify the service with:"
echo "  curl http://localhost:$HOST_PORT/api/v1/health"
