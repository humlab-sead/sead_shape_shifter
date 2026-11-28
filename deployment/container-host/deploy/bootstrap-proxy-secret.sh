#!/usr/bin/env bash
# Creates one site's proxy secret. Running it again keeps the secret.
# Run as root on the container host. See ../README.md, "Create the proxy secret".
# To replace the secret: delete the app file, run this again, then right away
# reload NGINX and recreate the app container.
set -euo pipefail
umask 077

(( $# == 1 || $# == 2 )) || { echo "Usage: $0 DOMAIN [DEPLOY_USER]" >&2; exit 1; }
domain=$1
# The domain becomes part of file paths.
[[ $domain =~ ^[A-Za-z0-9][A-Za-z0-9.-]*$ ]] || { echo "Invalid domain: $domain" >&2; exit 1; }
# DEPLOY_USER defaults to DOMAIN. The app container reads its file through this user's group.
group=$(id -gn -- "${2:-$domain}")

app_dir=/etc/shape-shifter/$domain
app_file=$app_dir/proxy-secret
nginx_dir=/etc/nginx/shape-shifter-secrets
nginx_file=$nginx_dir/$domain.conf

mkdir -p "$app_dir" "$nginx_dir"
chmod 755 /etc/shape-shifter
chmod 700 "$nginx_dir"
chown "root:$group" "$app_dir"
chmod 750 "$app_dir"

[[ -s $app_file ]] || openssl rand -hex 32 >"$app_file"
chown "root:$group" "$app_file"
chmod 640 "$app_file"

printf 'proxy_set_header X-Proxy-Secret "%s";\n' "$(<"$app_file")" >"$nginx_file"
chmod 600 "$nginx_file"

echo "In the proxy location block, add if missing: include $nginx_file;"
echo "Then run 'nginx -t', reload NGINX, and recreate the app container if the secret is new."
