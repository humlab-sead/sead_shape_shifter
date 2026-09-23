#!/bin/bash 
set -euo pipefail

set -euo pipefail

g_script_dir="$(CDPATH='' cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
g_deploy_user="${DEPLOY_USER:-}"
g_dry_run=false

usage() {
  cat <<EOF
Usage: container/scripts/deploy/rebuild-image.sh --deploy-user USER [--dry-run]

Rebuild the container image for a deployment user, then restart the container.
The deployment user owns ~/container, ~/config and ~/container-data, and the
build reads its settings from ~/config/deployment.env.

Options:
  --deploy-user USER       Target deployment user (required)
  --dry-run                Show the commands without running them
  -h, --help               Show this help message

EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --deploy-user)
      [[ $# -ge 2 ]] || { echo "--deploy-user requires a value." >&2; exit 1; }
      g_deploy_user="$2"
      shift 2
      ;;
    --dry-run) g_dry_run=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
  esac
done

if [[ -z "$g_deploy_user" ]]; then
  echo "A deployment user is required." >&2
  usage >&2
  exit 1
fi

if [[ "$g_dry_run" = true ]]; then
  echo "Would rebuild and restart for $g_deploy_user:"
  echo "  cd ~/container"
  echo "  make build"
  echo "  make restart"
  exit 0
fi

sudo su -l "$g_deploy_user" << EOF
cd container || exit
echo "info: rebuilding image for $g_deploy_user"
make build
make restart
EOF
