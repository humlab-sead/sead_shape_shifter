#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# The upstream port is the backend's HOST_PORT, which lives in
# CONFIG_DIR/deployment.env.
# shellcheck source=../load-env.sh
. "$SCRIPT_DIR/../load-env.sh"

usage() {
  cat <<'EOF'
Usage: scripts/install_nginx_reverse_proxy.sh <DOMAIN> [UPSTREAM_PORT]

Create an NGINX vhost that proxies HTTPS traffic to the Podman service.

UPSTREAM_PORT defaults to HOST_PORT from CONFIG_DIR/deployment.env, then to 8012.
CONFIG_DIR defaults to the invoking user's ~/config, so either run this as the
deployment user or name that user's config directory:
  sudo CONFIG_DIR=/data/<user>/config scripts/deploy/install_nginx_reverse_proxy.sh ...

The site file is rendered from nginx-shape-shifter.conf.template in this
directory, and the application itself keeps running from ~/container.

Examples:
  sudo -u test-shape-shifter.sead.se scripts/deploy/install_nginx_reverse_proxy.sh shapeshifter.example.com 8012
  DOMAIN=shapeshifter.example.com PORT=8012 scripts/deploy/install_nginx_reverse_proxy.sh
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

DOMAIN="${1:-${DOMAIN:-}}"
UPSTREAM_PORT="${2:-${PORT:-${HOST_PORT:-8012}}}"

if [[ -z "$DOMAIN" ]]; then
  echo "A domain name is required." >&2
  usage >&2
  exit 1
fi

if [[ "$(id -u)" -ne 0 ]]; then
  echo "This script must run as root so it can install the NGINX site." >&2
  exit 1
fi

TEMPLATE_PATH="$SCRIPT_DIR/nginx-shape-shifter.conf.template"
OUTPUT_PATH="/etc/nginx/sites-available/$DOMAIN"

if [[ ! -f "$TEMPLATE_PATH" ]]; then
  echo "Missing template: $TEMPLATE_PATH" >&2
  exit 1
fi

python3 - "$TEMPLATE_PATH" "$OUTPUT_PATH" "$DOMAIN" "$UPSTREAM_PORT" <<'PY'
from pathlib import Path
import sys

template_path = Path(sys.argv[1])
out_path = Path(sys.argv[2])
domain = sys.argv[3]
port = sys.argv[4]

text = template_path.read_text()
rendered = text.replace('__DOMAIN__', domain).replace('__UPSTREAM_PORT__', port)
out_path.write_text(rendered)
PY

ln -sf "$OUTPUT_PATH" "/etc/nginx/sites-enabled/$DOMAIN"
nginx -t
systemctl reload nginx

echo "NGINX config installed for $DOMAIN on port $UPSTREAM_PORT"
