#!/bin/bash
# Install nginx authentication, group membership, per-principal deployment
# roles, and the reviewed authorization manifest for one target environment.
#
# Everything is read from the target configuration directory, never from this
# checkout or the repository secrets folder:
#   CONFIG_DIR/authorization.env            credentials, rosters, actor, manifest
#   CONFIG_DIR/authorization-manifest.yaml  reviewed policy manifest
#   CONFIG_DIR/groups.d/shape-shifter.conf  nginx group membership
#
# CONFIG_DIR defaults to the sibling of the checkout this script belongs to,
# which is ~/config when the checkout is ~/container; set CONFIG_DIR to use
# another layout. AUTHORIZATION_MANIFEST names a file below CONFIG_DIR, and an
# absolute path is accepted only when an operator configures one deliberately.
#
# Run as root, because the script writes the htpasswd file and the nginx group
# file. Every input is validated before any account, role, or file is changed.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
CHECKOUT_DIR="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
CONFIG_DIR="${CONFIG_DIR:-$(cd -- "$CHECKOUT_DIR/.." && pwd)/config}"

ENV_FILE="$CONFIG_DIR/authorization.env"
GROUPS_FILE="$CONFIG_DIR/groups.d/shape-shifter.conf"
HTPASSWD_FILE="/etc/nginx/htpasswd/shape-shifter"

fail() {
    printf '%s\n' "$@" >&2
    exit 1
}

if [[ ! -r "$ENV_FILE" ]]; then
    fail "Missing authorization configuration: $ENV_FILE"
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
    fail "AUTHORIZATION_MANIFEST is required in $ENV_FILE"
fi
if [[ "$AUTHORIZATION_MANIFEST" != /* ]]; then
    AUTHORIZATION_MANIFEST="$CONFIG_DIR/$AUTHORIZATION_MANIFEST"
fi

if [[ ! -r "$AUTHORIZATION_MANIFEST" ]]; then
    fail "Authorization manifest is not readable: $AUTHORIZATION_MANIFEST"
fi

if [[ ! -r "$GROUPS_FILE" ]]; then
    fail "Group membership file is not readable: $GROUPS_FILE"
fi

DEPLOY_DIR="/data/$DEPLOY_USER/container"
if [[ ! -d "$DEPLOY_DIR" ]]; then
    fail "Deployment directory does not exist: $DEPLOY_DIR"
fi

# sudo switches user but keeps the caller's working directory. The deployment
# user cannot always read the directory this script was started from, which
# makes sudo -u fail with "cannot chdir". Move somewhere that user can read
# before switching; every remaining path in this script is absolute.
cd -- "$DEPLOY_DIR" || fail "Cannot enter deployment directory: $DEPLOY_DIR"

DEPLOY_UID="$(id -u "$DEPLOY_USER")"
CONTAINER_NAME="${CONTAINER_NAME:-shape-shifter}"
# The deployment user's Podman lives under their own user manifest, so run the
# wrapper with the target user's home and runtime directory. Without them podman
# looks in the wrong storage and reports the running container as absent.
TARGET_PATH="/home/linuxbrew/.linuxbrew/bin:/usr/local/bin:/usr/bin:/bin"

target_run() {
    # The -- marker must precede the assignments: some env implementations
    # (uutils coreutils) reject -- after variable assignments.
    sudo -u "$DEPLOY_USER" -H env -- \
        "PATH=$TARGET_PATH" \
        "XDG_RUNTIME_DIR=/run/user/$DEPLOY_UID" \
        "CONFIG_DIR=$CONFIG_DIR" \
        "$@"
}

# The role assignments and the manifest import act on the running container, so
# confirm it is reachable before any account, group, or role changes.
if [[ $EUID -ne 0 ]]; then
    fail "This script must be run as root (i.e. use sudo)"
fi

container_status="$(target_run podman container inspect --format '{{.State.Status}}' "$CONTAINER_NAME" 2>&1 || true)"
if [[ "$container_status" != running ]]; then
    fail "Container '$CONTAINER_NAME' is not running for $DEPLOY_USER. podman reported:" \
        "  $container_status" \
        "Start it as that user, then rerun this script:" \
        "  sudo -u $DEPLOY_USER -H bash -lc 'cd ~/container && make up'"
fi

# -i reads the password from stdin. Without it htpasswd prompts on the terminal
# and ignores the here-string, so the script would wait for input instead of
# setting the configured passwords.
HTPASSWD_OPTIONS=(-i -c)

htpasswd "${HTPASSWD_OPTIONS[@]}" "$HTPASSWD_FILE" "$ADMIN_AUTH_USER" <<< "$ADMIN_AUTH_PASSWORD"
HTPASSWD_OPTIONS=(-i)

for user in $AUTH_USERS; do
    htpasswd "${HTPASSWD_OPTIONS[@]}" "$HTPASSWD_FILE" "$user" <<< "$AUTH_PASSWORD"
done

chown root:www-data "$HTPASSWD_FILE"
chmod 640 "$HTPASSWD_FILE"

# Keep the trusted administrator group available for future resource grants.
install -D -m 640 -o root -g www-data \
    "$GROUPS_FILE" \
    /etc/nginx/authz/groups.d/shape-shifter.conf

# The wrapper resolves its configuration from CONFIG_DIR, so pass the directory
# this script validated instead of letting the deploy user's home decide.
run_authorization() {
    target_run "$DEPLOY_DIR/scripts/authorization.sh" "$@"
}

grant_application_role() {
    local principal_id="$1"
    local role="$2"

    run_authorization grant-application-role \
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

sudo -u "$DEPLOY_USER" -H env -- \
    "PATH=$TARGET_PATH" \
    "XDG_RUNTIME_DIR=/run/user/$DEPLOY_UID" \
    "CONFIG_DIR=$CONFIG_DIR" \
    "$DEPLOY_DIR/scripts/authorization.sh" import-manifest "$AUTHORIZATION_MANIFEST"