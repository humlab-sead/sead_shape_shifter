#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# The upstream port is the backend's HOST_PORT, which lives in
# CONFIG_DIR/deployment.env. The runtime helper is the one in the sibling
# deployment/container/ bundle, because this script lives in the source-only
# deployment/container-host/ tree.
# shellcheck source=../../container/scripts/_load-env.sh
. "$SCRIPT_DIR/../../container/scripts/_load-env.sh"

usage() {
  cat <<'EOF'
Usage: deployment/container-host/deploy/install_nginx_reverse_proxy.sh [--bootstrap] <DOMAIN> [UPSTREAM_PORT]

Create an NGINX vhost that proxies HTTPS traffic to the Podman service.

UPSTREAM_PORT defaults to HOST_PORT from CONFIG_DIR/deployment.env, then to 8012.
CONFIG_DIR defaults to the invoking user's ~/config, so either run this as the
deployment user or name that user's config directory:
  sudo CONFIG_DIR=/data/<user>/config deployment/container-host/deploy/install_nginx_reverse_proxy.sh ...

The site file is rendered from nginx-shape-shifter.conf.template in this
directory, and the application itself keeps running from ~/container. The
shared maps file nginx-shape-shifter-maps.conf is installed to
/etc/nginx/conf.d/ so a second Shape Shifter site does not redefine them.

A TLS certificate must exist before the HTTPS vhost is enabled. Until it does,
install the HTTP-only bootstrap vhost, obtain the certificate, then re-run
without --bootstrap:
  sudo install_nginx_reverse_proxy.sh --bootstrap <DOMAIN>
  sudo certbot certonly --webroot -w /var/www/html -d <DOMAIN>
  sudo install_nginx_reverse_proxy.sh <DOMAIN> <port>

Examples:
  sudo CONFIG_DIR=/data/test-shape-shifter.sead.se/config \
    deployment/container-host/deploy/install_nginx_reverse_proxy.sh test-shape-shifter.sead.se 8012
EOF
}

BOOTSTRAP=0
ARGS=()
for arg in "$@"; do
  case "$arg" in
    -h|--help) usage; exit 0 ;;
    --bootstrap) BOOTSTRAP=1 ;;
    *) ARGS+=("$arg") ;;
  esac
done
set -- "${ARGS[@]:-}"

DOMAIN="${1:-${DOMAIN:-}}"
UPSTREAM_PORT="${2:-${PORT:-${HOST_PORT:-8012}}}"

if [[ -z "$DOMAIN" ]]; then
  echo "A domain name is required." >&2
  usage >&2
  exit 1
fi

# DOMAIN and UPSTREAM_PORT are written into root-owned NGINX files. Reject
# anything that is not a plain hostname or port so they cannot inject a path
# or an NGINX directive.
if [[ ! "$DOMAIN" =~ ^[A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?(\.[A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?)*$ ]]; then
  echo "Invalid DOMAIN: $DOMAIN" >&2
  exit 1
fi
if [[ ! "$UPSTREAM_PORT" =~ ^[0-9]{1,5}$ ]]; then
  echo "Invalid UPSTREAM_PORT: $UPSTREAM_PORT" >&2
  exit 1
fi

if [[ "$(id -u)" -ne 0 ]]; then
  echo "This script must run as root so it can install the NGINX site." >&2
  exit 1
fi

MAPS_PATH="/etc/nginx/conf.d/shape-shifter-maps.conf"
OUTPUT_PATH="/etc/nginx/sites-available/$DOMAIN"
ENABLED_PATH="/etc/nginx/sites-enabled/$DOMAIN"
CERT_PATH="/etc/letsencrypt/live/$DOMAIN/fullchain.pem"

install_maps() {
  local src="$SCRIPT_DIR/nginx-shape-shifter-maps.conf"
  if [[ ! -f "$src" ]]; then
    echo "Missing maps file: $src" >&2
    exit 1
  fi
  install -m 0644 "$src" "$MAPS_PATH"
}

# Render a template to the site file. Replaces __DOMAIN__, __UPSTREAM_PORT__,
# and __UPSTREAM_NAME__ (a host-unique upstream derived from the domain, so a
# second Shape Shifter site does not redefine the upstream block).
render() {
  local template_path="$1"
  if [[ ! -f "$template_path" ]]; then
    echo "Missing template: $template_path" >&2
    exit 1
  fi
  local upstream_name
  upstream_name="up_$(printf '%s' "$DOMAIN" | tr -c 'A-Za-z0-9' '_')"
  python3 - "$template_path" "$OUTPUT_PATH" "$DOMAIN" "$UPSTREAM_PORT" "$upstream_name" <<'PY'
from pathlib import Path
import sys

template_path, out_path, domain, port, upstream_name = sys.argv[1:6]
text = Path(template_path).read_text()
rendered = (
    text.replace("__DOMAIN__", domain)
    .replace("__UPSTREAM_PORT__", port)
    .replace("__UPSTREAM_NAME__", upstream_name)
)
Path(out_path).write_text(rendered)
PY
}

# Enable the site only if the rendered config is valid. On failure, remove the
# symlink this script created so a broken vhost cannot break the next reload.
enable_site() {
  ln -sf "$OUTPUT_PATH" "$ENABLED_PATH"
  if ! nginx -t; then
    rm -f "$ENABLED_PATH"
    echo "NGINX config test failed; $ENABLED_PATH was not left enabled." >&2
    exit 1
  fi
  systemctl reload nginx
}

if [[ "$BOOTSTRAP" -eq 1 ]]; then
  install_maps
  render "$SCRIPT_DIR/nginx-shape-shifter.bootstrap.conf.template"
  enable_site
  echo "Bootstrap (HTTP-only) NGINX config installed for $DOMAIN."
  echo "Next: sudo certbot certonly --webroot -w /var/www/html -d $DOMAIN"
  echo "Then re-run this script without --bootstrap to enable HTTPS."
  exit 0
fi

if [[ ! -f "$CERT_PATH" ]]; then
  echo "No certificate at $CERT_PATH." >&2
  echo "Install the bootstrap vhost and obtain the certificate first:" >&2
  echo "  sudo $0 --bootstrap $DOMAIN" >&2
  echo "  sudo certbot certonly --webroot -w /var/www/html -d $DOMAIN" >&2
  exit 1
fi

install_maps
render "$SCRIPT_DIR/nginx-shape-shifter.conf.template"
enable_site

echo "NGINX config installed for $DOMAIN on port $UPSTREAM_PORT"
