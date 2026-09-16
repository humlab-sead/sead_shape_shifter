#!/usr/bin/env bash
# Deploy one Shape Shifter environment for a dedicated system user.
#
# Run as root (or a sudo-capable admin) on the deployment host. The script
# fetches the container/ deployment files into the user's home directory
# (~/container), keeps ~/container-data intact, and runs the initial setup.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/deploy_single_environment.sh <USER> [--repo URL] [--ref REF] [--host-port PORT]

Deploy a single Shape Shifter environment for a dedicated system user.

Options:
  --repo, --repository  Git repository URL. Default: https://github.com/humlab-sead/sead_shape_shifter.git
  --ref                 Git branch or release tag to fetch. Default: main
  --branch              Alias for --ref, kept so existing calls keep working
  --host-port           Host port for the container. Default: 8012
  --no-build            Prepare files only; do not build or start
  -h, --help            Show this help message

The repository, ref, host port, and the matching image name are written to
~/container/.env, so later `make build` and `make up` runs keep using them.

Examples:
  scripts/deploy_single_environment.sh test-shape-shifter.sead.se
  scripts/deploy_single_environment.sh shapeshifter-prod --host-port 8013
EOF
}

USER=""
REPO_URL="${REPO_URL:-https://github.com/humlab-sead/sead_shape_shifter.git}"
REF="${REF:-${BRANCH:-main}}"
HOST_PORT="${HOST_PORT:-8012}"
DO_BUILD=true

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    --repo|--repository) REPO_URL="$2"; shift 2 ;;
    --ref | --branch) REF="$2"; shift 2 ;;
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

# The archive URL accepts a branch or a tag, so no branch or tag detection is
# needed. The wildcard matches the top-level directory, whose name differs
# between the two: GitHub strips the leading 'v' from a tag, so v2.1.0 extracts
# to sead_shape_shifter-2.1.0/.
ARCHIVE_URL="${REPO_URL%.git}/archive/${REF}.tar.gz"

echo "Fetching deployment files for $USER (ref $REF)..."
sudo -u "$USER" \
  env ARCHIVE_URL="$ARCHIVE_URL" \
      DEPLOY_REPO="$REPO_URL" DEPLOY_REF="$REF" DEPLOY_PORT="$HOST_PORT" \
  bash -lc '
set -euo pipefail
cd ~
if [ -d container ]; then
  tmp_dir="$(mktemp -d)"
  curl -fsSL "$ARCHIVE_URL" | tar -xz -C "$tmp_dir" --wildcards --strip-components=1 "*/container/*"
  cp -a "$tmp_dir/container/." "$HOME/container/"
  rm -rf "$tmp_dir"
else
  curl -fsSL "$ARCHIVE_URL" | tar -xz --wildcards --strip-components=1 "*/container/*"
fi
cd ~/container
bash scripts/setup.sh

# Record the repository, branch, image and port in container/.env, so later
# `make build` and `make up` runs use the source this deploy fetched instead of
# the defaults in .env.example.
. scripts/env-config.sh
. scripts/load-env.sh
env_image="${IMAGE_NAME:-shape-shifter:latest}"
shapeshifter_env_file_set .env GIT_REPO "$DEPLOY_REPO"
shapeshifter_env_file_set .env GIT_REF "$DEPLOY_REF"
shapeshifter_env_file_set .env IMAGE_NAME "$(shapeshifter_image_for_ref "$DEPLOY_REF" "${env_image%%:*}")"
shapeshifter_env_file_set .env HOST_PORT "$DEPLOY_PORT"
'
echo "Recorded GIT_REPO, GIT_REF, IMAGE_NAME and HOST_PORT in ~/container/.env"

if [[ "$DO_BUILD" = true ]]; then
  echo "Building and starting the container..."
  sudo -u "$USER" bash -lc '
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
