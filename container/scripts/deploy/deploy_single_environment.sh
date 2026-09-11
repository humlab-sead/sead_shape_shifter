#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/deploy_single_environment.sh <USER> [--repo URL] [--branch BRANCH] [--host-port PORT]

Deploy a single Shape Shifter environment for a dedicated system user.

Options:
  --repo, --repository     Git repository URL to clone. Default: https://github.com/humlab-sead/sead_shape_shifter.git
  --branch                 Git branch to checkout. Default: main
  --host-port              Host port for the container service. Default: 8012
  -h, --help               Show this help message

Examples:
  scripts/deploy_single_environment.sh shapeshifter-test
  scripts/deploy_single_environment.sh shapeshifter-prod --host-port 8013
EOF
}

USER=""
REPO_URL="${REPO_URL:-https://github.com/humlab-sead/sead_shape_shifter.git}"
BRANCH="${BRANCH:-main}"
HOST_PORT="${HOST_PORT:-8012}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --repo|--repository)
      [[ $# -ge 2 ]] || { echo "Missing value for $1" >&2; exit 1; }
      REPO_URL="$2"
      shift 2
      ;;
    --branch)
      [[ $# -ge 2 ]] || { echo "Missing value for $1" >&2; exit 1; }
      BRANCH="$2"
      shift 2
      ;;
    --host-port)
      [[ $# -ge 2 ]] || { echo "Missing value for $1" >&2; exit 1; }
      HOST_PORT="$2"
      shift 2
      ;;
    -*)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
    *)
      if [[ -z "$USER" ]]; then
        USER="$1"
      else
        echo "Unexpected extra argument: $1" >&2
        usage >&2
        exit 1
      fi
      shift
      ;;
  esac
done

if [[ -z "$USER" ]]; then
  echo "A system user name is required." >&2
  usage >&2
  exit 1
fi

sudo -u "$USER" env REPO_URL="$REPO_URL" BRANCH="$BRANCH" bash -lc '
set -euo pipefail
cd ~
if [ -d sead_shape_shifter ]; then
  cd sead_shape_shifter
  git pull --ff-only || git fetch --all --prune && git reset --hard "origin/${BRANCH:-main}"
else
  git clone -b "${BRANCH:-main}" "${REPO_URL:-https://github.com/humlab-sead/sead_shape_shifter.git}" ~/sead_shape_shifter
fi
cd ~/sead_shape_shifter/container
bash setup.sh
# Configure application manually before starting the container.
# Example: nano ~/container-data/backend.env
'

HOST_PORT="$HOST_PORT" sudo -u "$USER" bash -lc '
set -euo pipefail
cd ~/sead_shape_shifter/container
make build
make up
'

echo
printf 'Deployment for %s is configured.\n' "$USER"
printf 'Edit the environment file before first use: nano ~/container-data/backend.env\n'
printf 'Then verify the service with: curl http://localhost:%s/api/v1/health\n' "$HOST_PORT"
