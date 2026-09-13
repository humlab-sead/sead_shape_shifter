#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/install_nginx_reverse_proxy.sh <DOMAIN> [UPSTREAM_PORT]

Create an NGINX vhost that proxies HTTPS traffic to the Podman service.

Examples:
  scripts/install_nginx_reverse_proxy.sh shapeshifter.example.com 8012
  DOMAIN=shapeshifter.example.com PORT=8012 scripts/install_nginx_reverse_proxy.sh
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

DOMAIN="${1:-${DOMAIN:-}}"
UPSTREAM_PORT="${2:-${PORT:-8012}}"

if [[ -z "$DOMAIN" ]]; then
  echo "A domain name is required." >&2
  usage >&2
  exit 1
fi

if [[ "$(id -u)" -ne 0 ]]; then
  echo "This script must run as root so it can install the NGINX site." >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
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
