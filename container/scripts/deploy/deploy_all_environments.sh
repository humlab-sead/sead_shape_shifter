#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/deploy_all_environments.sh [USER:PORT ...]

Deploy the project to multiple dedicated environment users.

If no arguments are supplied, the script uses these defaults:
  shapeshifter-test:8012
  shapeshifter-prod:8013

Examples:
  scripts/deploy_all_environments.sh
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
  ENVIRONMENTS=(
    "shapeshifter-test:8012"
    "shapeshifter-prod:8013"
  )
fi

for env_pair in "${ENVIRONMENTS[@]}"; do
  IFS=':' read -r USER PORT <<< "$env_pair"
  if [[ -z "$USER" || -z "$PORT" ]]; then
    echo "Invalid environment entry: $env_pair" >&2
    exit 1
  fi

  echo "Deploying to: $USER (port $PORT)"
  HOST_PORT="$PORT" bash scripts/deploy_single_environment.sh "$USER"
  echo "✓ Configured and ready to start for $USER"
  echo "  Config: nano ~/container-data/backend.env"
  echo "  Start:  systemctl --user start shape-shifter"
  echo

done
