#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd -- "$SCRIPT_DIR/../../.." && pwd)"
ENV_FILE="$REPO_DIR/secrets/.env"

if [[ ! -r "$ENV_FILE" ]]; then
    echo "Missing secret configuration: $ENV_FILE" >&2
    exit 1
fi

# shellcheck disable=SC1090
source "$ENV_FILE"
: "${AUTH_PASSWORD:?AUTH_PASSWORD is required in $ENV_FILE}"
: "${AUTH_USERS:?AUTH_USERS is required in $ENV_FILE}"
: "${ADMIN_AUTH_USER:?ADMIN_AUTH_USER is required in $ENV_FILE}"
: "${ADMIN_AUTH_PASSWORD:?ADMIN_AUTH_PASSWORD is required in $ENV_FILE}"
: "${PROJECT_MAINTAINERS:?PROJECT_MAINTAINERS is required in $ENV_FILE}"
: "${PROJECT_CREATOR_AND_OPERATOR:?PROJECT_CREATOR_AND_OPERATOR is required in $ENV_FILE}"
: "${DEPLOY_USER:?DEPLOY_USER is required in $ENV_FILE}"
: "${AUTHORIZATION_ACTOR:?AUTHORIZATION_ACTOR is required in $ENV_FILE}"
if [[ -z "${AUTHORIZATION_MANIFEST:-}" ]]; then
    echo "AUTHORIZATION_MANIFEST is required in $ENV_FILE" >&2
    exit 1
fi
if [[ "$AUTHORIZATION_MANIFEST" != /* ]]; then
    AUTHORIZATION_MANIFEST="$REPO_DIR/$AUTHORIZATION_MANIFEST"
fi

if [[ ! -r "$AUTHORIZATION_MANIFEST" ]]; then
    echo "Authorization manifest is not readable: $AUTHORIZATION_MANIFEST" >&2
    exit 1
fi

HTPASSWD_FILE="/etc/nginx/htpasswd/shape-shifter"
HTPASSWD_OPTIONS=(-c)

if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root (i.e. use sudo)" >&2
    exit 1
fi

htpasswd "${HTPASSWD_OPTIONS[@]}" "$HTPASSWD_FILE" "$ADMIN_AUTH_USER" <<< "$ADMIN_AUTH_PASSWORD"
HTPASSWD_OPTIONS=()

for user in $AUTH_USERS; do
    htpasswd "${HTPASSWD_OPTIONS[@]}" "$HTPASSWD_FILE" "$user" <<< "$AUTH_PASSWORD"
done

chown root:www-data "$HTPASSWD_FILE"
chmod 640 "$HTPASSWD_FILE"

# Keep the trusted administrator group available for future resource grants.
install -D -m 640 -o root -g www-data \
    "$REPO_DIR/secrets/groups.d/shape-shifter.conf" \
    /etc/nginx/authz/groups.d/shape-shifter.conf

DEPLOY_DIR="/data/$DEPLOY_USER/container"
if [[ ! -d "$DEPLOY_DIR" ]]; then
    echo "Deployment directory does not exist: $DEPLOY_DIR" >&2
    exit 1
fi

grant_application_role() {
    local principal_id="$1"
    local role="$2"

    sudo -u "$DEPLOY_USER" -- "$DEPLOY_DIR/scripts/authorization.sh" grant-application-role \
        --principal-id "$principal_id" \
        --role "$role" \
        --actor "$AUTHORIZATION_ACTOR"
}

for principal_id in $PROJECT_MAINTAINERS; do
    grant_application_role "$principal_id" project_maintainer
done

for principal_id in $PROJECT_CREATOR_AND_OPERATOR; do
    grant_application_role "$principal_id" project_creator
    grant_application_role "$principal_id" operator
done

grant_application_role "$ADMIN_AUTH_USER" admin

sudo -u "$DEPLOY_USER" -- "$DEPLOY_DIR/scripts/authorization.sh" import-manifest "$AUTHORIZATION_MANIFEST"