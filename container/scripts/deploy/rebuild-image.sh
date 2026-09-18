#!/bin/bash 
set -euo pipefail

set -euo pipefail

g_script_dir="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
g_deploy_user="${DEPLOY_USER:-test-shape-shifter.sead.se}"
g_dry_run=false

usage() {
  cat <<'EOF'
Usage: container/scripts/deploy/rebuild-image.sh [--deploy-user USER] [--dry-run]

Rebuild the container image for the deployment user's container directory.

Options:
  --deploy-user USER       Target owner. Default: $g_deploy_user
  --dry-run                Show changes without modifying the target
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

sudo su -l $g_deploy_user << EOF
cd container || exit
echo "info: rebuilding image for $g_deploy_user"
make build
make restart
EOF
