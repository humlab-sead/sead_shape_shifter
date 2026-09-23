#!/usr/bin/env bash
# Deploy the project to multiple dedicated environment users.
set -euo pipefail

SCRIPT_DIR="$(CDPATH='' cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

# Take DEPLOY_ENVIRONMENTS from the environment, or from CONFIG_DIR/deployment.env.
# shellcheck source=../load-env.sh
. "$SCRIPT_DIR/../load-env.sh"

usage() {
  cat <<'EOF'
Usage: scripts/deploy_all_environments.sh [USER:PORT ...]

Deploy the project to several dedicated environment users.

Environments come from the arguments first, then from DEPLOY_ENVIRONMENTS, which
can be exported or set in CONFIG_DIR/deployment.env. There is no built-in
environment list, so an unconfigured run stops instead of deploying somewhere
unrequested.

Examples:
  scripts/deploy_all_environments.sh test-shape-shifter.sead.se:8012
  scripts/deploy_all_environments.sh shapeshifter-test:8012 shapeshifter-prod:8013
  DEPLOY_ENVIRONMENTS='shapeshifter-test:8012 shapeshifter-prod:8013' scripts/deploy_all_environments.sh
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ $# -gt 0 ]]; then
  ENVIRONMENTS=("$@")
elif [[ -n "${DEPLOY_ENVIRONMENTS:-}" ]]; then
  read -r -a ENVIRONMENTS <<< "$DEPLOY_ENVIRONMENTS"
else
  echo "No environments given." >&2
  usage >&2
  exit 1
fi

for env_pair in "${ENVIRONMENTS[@]}"; do
  IFS=':' read -r USER PORT <<< "$env_pair"
  if [[ -z "$USER" || -z "$PORT" ]]; then
    echo "Invalid environment entry: $env_pair" >&2
    exit 1
  fi

  echo "Deploying to: $USER (port $PORT)"
  HOST_PORT="$PORT" bash "$SCRIPT_DIR/deploy_single_environment.sh" "$USER"
  echo "Configured and started for $USER"
  echo "  Settings: sudo -u $USER nano ~/config/deployment.env"
  echo "  Runtime:  sudo -u $USER nano ~/config/backend.env"
  echo "  Status:   sudo -u $USER systemctl --user status shape-shifter"
  echo
done
