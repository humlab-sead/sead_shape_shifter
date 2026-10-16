#!/usr/bin/env bash
# Configure one Shape Shifter environment for a dedicated system user.
#
# Run as root (or a sudo-capable admin) on the deployment host. This script does
# not fetch or replace container files. The deployment user must already have
# deployment files in ~/container, placed there by whatever flow the environment
# uses (until images are published to GHCR, a manual copy or sync of the
# deployment/container/ tree). The script runs the setup there and records the
# application image settings (repository, image ref, image name, port) in
# ~/config/deployment.env.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: deployment/container-host/deploy/deploy_environment.sh <USER> [--repo URL] [--ref REF] [--host-port PORT]

Configure one Shape Shifter environment for a dedicated system user.

The user must already have deployment files in ~/container: a directory (or
symlink) holding the deployment/container/ tree, including a Makefile and
VERSION. Place the tree there first, by copying it or with
deployment/container-host/deploy/sync-to-deploy.

Options:
  --repo, --repository  Application repository URL for `make build`. Default: https://github.com/humlab-sead/sead_shape_shifter.git
  --ref                 Application image git ref for `make build`. Default: main
  --branch              Alias for --ref, kept so existing calls keep working
  --host-port           Host port for the container. Default: 8012
  --no-build            Configure only; do not build or start
  -h, --help            Show this help message

The repository, image ref, matching image name, and host port are written to
~/config/deployment.env, so later `make build` and `make up` runs keep using
them. The ~/config and ~/container-data directories are never removed, and
nothing is written into ~/container.

Examples:
  deployment/container-host/deploy/deploy_environment.sh test-shape-shifter.sead.se
  deployment/container-host/deploy/deploy_environment.sh shapeshifter-prod --host-port 8013 --ref v2.3.0
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

# Require deployment files in ~/container. A real directory (the manual layout)
# or a symlink both pass, as long as the directory holds a Makefile and VERSION.
container_dir="$user_home/container"
if [[ ! -d "$container_dir" ]]; then
  echo "error: $container_dir does not exist. Place the deployment/container/ tree there first." >&2
  exit 1
fi
if [[ ! -f "$container_dir/Makefile" || ! -f "$container_dir/VERSION" ]]; then
  echo "error: $container_dir does not look like a container deployment (no Makefile or VERSION)." >&2
  exit 1
fi

loginctl enable-linger "$USER"
USER_UID="$(id -u "$USER")"

echo "Using the deployment files at $container_dir"
echo "Configuring application image settings for $USER..."
sudo -u "$USER" \
  env DEPLOY_REPO="$REPO_URL" DEPLOY_REF="$REF" DEPLOY_PORT="$HOST_PORT" \
      XDG_RUNTIME_DIR="/run/user/$USER_UID" \
  bash -lc '
set -euo pipefail
cd ~/container
bash scripts/setup.sh

# Record the application image source and port in CONFIG_DIR/deployment.env,
# so later `make build` and `make up` runs use the source this deploy configured.
. scripts/_env-config.sh
. scripts/_load-env.sh
deployment_env="$CONFIG_DIR/deployment.env"
# _load-env.sh supplies IMAGE_NAME from deployment.env or the bundled
# .env.example template, so only the image name without its tag is derived here.
env_image="$IMAGE_NAME"
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
echo "Deployment files: $container_dir"
echo "Application image ref: $REF"
echo "Review the deployment settings and runtime environment before first use:"
echo "  sudo -u $USER nano ~/config/deployment.env"
echo "  sudo -u $USER nano ~/config/backend.env"
echo "Provision the authorization inputs described in deployment/container/DEPLOYMENT.md, then verify with:"
echo "  curl http://localhost:$HOST_PORT/api/v1/health"
