#!/usr/bin/env bash
# Configure one Shape Shifter environment for a dedicated system user.
#
# Run as root (or a sudo-capable admin) on the deployment host. This script does
# not fetch or replace container files. The deployment user must already have a
# selected container release, created with the host release manager
# (/usr/local/sbin/shape-shifter-container-release): ~/container is a symlink to
# that selection. The script runs the release's setup and records the application
# image settings (repository, image ref, image name, port) in
# ~/config/deployment.env. The container release tag is never written there.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/deploy_single_environment.sh <USER> [--repo URL] [--ref REF] [--host-port PORT]

Configure one Shape Shifter environment for a dedicated system user.

The user must already have a selected container release: ~/container must be the
symlink the host release manager creates. Install and select a release first:

  sudo shape-shifter-container-release install  USER container-vX.Y.Z
  sudo shape-shifter-container-release activate USER container-vX.Y.Z

Options:
  --repo, --repository  Application repository URL for `make build`. Default: https://github.com/humlab-sead/sead_shape_shifter.git
  --ref                 Application image git ref for `make build`. Default: main
  --branch              Alias for --ref, kept so existing calls keep working
  --host-port           Host port for the container. Default: 8012
  --no-build            Configure only; do not build or start
  -h, --help            Show this help message

The repository, image ref, matching image name, and host port are written to
~/config/deployment.env, so later `make build` and `make up` runs keep using
them. These are application image settings: they are independent of the selected
container release and do not name it. The ~/config and ~/container-data
directories are never removed, and nothing is written into the selected release.

Examples:
  scripts/deploy_single_environment.sh test-shape-shifter.sead.se
  scripts/deploy_single_environment.sh shapeshifter-prod --host-port 8013 --ref v2.3.0
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

# Rootless Podman needs the user's systemd user manager when it creates
# containers. Without an interactive login that manager only starts when
# lingering is enabled; otherwise `make build` and `make up` fail with a polkit
# "Access denied" error from crun. Enable lingering here (root can do this) and
# expose the user's runtime directory to the `sudo -u` commands below.
user_record="$(getent passwd "$USER" || true)"
if [[ -z "$user_record" ]]; then
  echo "No such system user: $USER" >&2
  exit 1
fi
user_home="$(printf '%s\n' "$user_record" | cut -d: -f6)"
if [[ -z "$user_home" || ! -d "$user_home" ]]; then
  echo "Cannot resolve the home directory for $USER" >&2
  exit 1
fi

# Require a selected release. A real directory is refused: an administrator must
# review and move it before the release manager can select a version.
container_link="$user_home/container"
if [[ ! -L "$container_link" ]]; then
  echo "error: $container_link is not a selected container release." >&2
  if [[ -d "$container_link" ]]; then
    echo "       It is a real directory. An administrator must review and move it, then install" >&2
    echo "       and activate a release with shape-shifter-container-release." >&2
  else
    echo "       Nothing is selected. As root, run:" >&2
    echo "         shape-shifter-container-release install  $USER container-vX.Y.Z" >&2
    echo "         shape-shifter-container-release activate $USER container-vX.Y.Z" >&2
  fi
  exit 1
fi
selected_dir="$(readlink -f -- "$container_link")"
if [[ ! -d "$selected_dir" || ! -f "$selected_dir/Makefile" || ! -f "$selected_dir/VERSION" ]]; then
  echo "error: $container_link does not resolve to a complete container release ($selected_dir)" >&2
  echo "       Reinstall the release with shape-shifter-container-release and try again." >&2
  exit 1
fi

loginctl enable-linger "$USER"
USER_UID="$(id -u "$USER")"

echo "Using the selected container release at $selected_dir"
echo "Configuring application image settings for $USER..."
sudo -u "$USER" \
  env DEPLOY_REPO="$REPO_URL" DEPLOY_REF="$REF" DEPLOY_PORT="$HOST_PORT" \
      XDG_RUNTIME_DIR="/run/user/$USER_UID" \
  bash -lc '
set -euo pipefail
cd ~/container
bash scripts/setup.sh

# Record the application image source and port in CONFIG_DIR/deployment.env.
# These are image settings and are separate from the selected release tag, so
# later `make build` and `make up` runs use the source this deploy configured.
. scripts/env-config.sh
. scripts/load-env.sh
deployment_env="$CONFIG_DIR/deployment.env"
env_image="${IMAGE_NAME:-shape-shifter:latest}"
shapeshifter_env_file_set "$deployment_env" GIT_REPO "$DEPLOY_REPO"
shapeshifter_env_file_set "$deployment_env" GIT_REF "$DEPLOY_REF"
shapeshifter_env_file_set "$deployment_env" IMAGE_NAME "$(shapeshifter_image_for_ref "$DEPLOY_REF" "${env_image%%:*}")"
shapeshifter_env_file_set "$deployment_env" HOST_PORT "$DEPLOY_PORT"
'
echo "Recorded GIT_REPO, GIT_REF, IMAGE_NAME and HOST_PORT in ~/config/deployment.env"

if [[ "$DO_BUILD" = true ]]; then
  echo "Building and starting the container..."
  sudo -u "$USER" \
    env "XDG_RUNTIME_DIR=/run/user/$USER_UID" \
    bash -lc '
set -euo pipefail
cd ~/container
make build
make up
'
fi

echo
echo "Deployment for $USER is configured."
echo "Container release: $selected_dir"
echo "Application image ref: $REF"
echo "Review the deployment settings and runtime environment before first use:"
echo "  sudo -u $USER nano ~/config/deployment.env"
echo "  sudo -u $USER nano ~/config/backend.env"
echo "Provision the authorization inputs described in container/DEPLOYMENT.md, then verify with:"
echo "  curl http://localhost:$HOST_PORT/api/v1/health"
