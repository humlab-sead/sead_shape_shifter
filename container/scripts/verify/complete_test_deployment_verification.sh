#!/usr/bin/env bash
# Run the remaining test-environment deployment checks.
set -Eeuo pipefail

SCRIPT_DIR="$(CDPATH='' cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
CONTAINER_DIR="$(CDPATH='' cd -- "$SCRIPT_DIR/../.." && pwd)"
# shellcheck source=../load-env.sh
# shellcheck disable=SC1091
. "$CONTAINER_DIR/scripts/load-env.sh"

BASE_URL="${BASE_URL:-https://test-shape-shifter.sead.se}"
CONTAINER_NAME="${CONTAINER_NAME:-shape-shifter}"
MANIFEST="${MANIFEST:-$CONFIG_DIR/authorization-manifest.yaml}"
HOST_PORT="${HOST_PORT:-8012}"
SERVICE_NAME="${SERVICE_NAME:-shape-shifter}"
PROJECT_A="${PROJECT_A:-}"
PROJECT_B="${PROJECT_B:-}"
PRINCIPAL_A="${PRINCIPAL_A:-}"
PRINCIPAL_B="${PRINCIPAL_B:-}"
CLEANUP_PREFIX=""
declare -a KEEP_PROJECTS=()
ADMIN_USER="admin"
RUN_AUTHENTICATED=false
RUN_GRANT_ACCESS=false
RUN_CLEANUP=false
RUN_ROLLBACK=false
ROLLBACK_IMAGE=""
AUTHORIZATION_BACKUP=""
ASSUME_YES=false

usage() {
    cat <<EOF
Usage: $(basename -- "$0") [OPTIONS]

Run the remaining target deployment checks. Safe checks and manifest
reconciliation run by default. Cleanup, authenticated access, and rollback
require explicit options.

Options:
  --manifest FILE             Host-side authorization manifest
  --base-url URL              Proxy URL (default: $BASE_URL)
    --service-name NAME         User service (default: $SERVICE_NAME)
  --project-a NAME            Project for principal A
  --project-b NAME            Project for principal B
  --principal-a USER          Principal A
  --principal-b USER          Principal B
  --authenticated             Run the principal isolation check
    --grant-access              Grant viewer access to project-a/project-b first
  --cleanup-prefix PREFIX     Delete active project resources with this prefix
    --keep-project NAME         Exclude a project from prefix cleanup (repeatable)
  --admin-user USER           Admin proxy user for cleanup (default: $ADMIN_USER)
  --rollback                  Run the state-changing rollback exercise
  --rollback-image IMAGE      Recorded image for rollback
  --authorization-backup FILE Backup filename or path for rollback
  --yes                       Skip cleanup and rollback confirmations
  -h, --help                  Show this help

Passwords are prompted without echoing them. Do not put credentials in this
script's arguments or in its options files.
EOF
}

fail() {
    printf 'FAIL: %s\n' "$*" >&2
    exit 1
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --manifest)              [[ $# -ge 2 ]] || fail "--manifest requires a value"; MANIFEST="$2"; shift 2 ;;
        --base-url)              [[ $# -ge 2 ]] || fail "--base-url requires a value"; BASE_URL="$2"; shift 2 ;;
        --service-name)          [[ $# -ge 2 ]] || fail "--service-name requires a value"; SERVICE_NAME="$2"; shift 2 ;;
        --project-a)             [[ $# -ge 2 ]] || fail "--project-a requires a value"; PROJECT_A="$2"; shift 2 ;;
        --project-b)             [[ $# -ge 2 ]] || fail "--project-b requires a value"; PROJECT_B="$2"; shift 2 ;;
        --principal-a)           [[ $# -ge 2 ]] || fail "--principal-a requires a value"; PRINCIPAL_A="$2"; shift 2 ;;
        --principal-b)           [[ $# -ge 2 ]] || fail "--principal-b requires a value"; PRINCIPAL_B="$2"; shift 2 ;;
        --authenticated)         RUN_AUTHENTICATED=true; shift ;;
        --grant-access)          RUN_GRANT_ACCESS=true; shift ;;
        --cleanup-prefix)        [[ $# -ge 2 ]] || fail "--cleanup-prefix requires a value"; CLEANUP_PREFIX="$2"; RUN_CLEANUP=true; shift 2 ;;
        --keep-project)          [[ $# -ge 2 ]] || fail "--keep-project requires a value"; KEEP_PROJECTS+=("$2"); shift 2 ;;
        --admin-user)            [[ $# -ge 2 ]] || fail "--admin-user requires a value"; ADMIN_USER="$2"; shift 2 ;;
        --rollback)              RUN_ROLLBACK=true; shift ;;
        --rollback-image)        [[ $# -ge 2 ]] || fail "--rollback-image requires a value"; ROLLBACK_IMAGE="$2"; shift 2 ;;
        --authorization-backup)  [[ $# -ge 2 ]] || fail "--authorization-backup requires a value"; AUTHORIZATION_BACKUP="$2"; shift 2 ;;
        --yes)                   ASSUME_YES=true; shift ;;
        -h|--help)               usage; exit 0 ;;
        *)                        fail "unknown option: $1" ;;
    esac
done

[[ "$RUN_GRANT_ACCESS" = false || "$RUN_AUTHENTICATED" = true ]] ||
    fail "--grant-access requires --authenticated"

command -v podman >/dev/null || fail "podman is required"
command -v curl >/dev/null || fail "curl is required"
command -v jq >/dev/null || fail "jq is required"
[[ -f "$MANIFEST" ]] || fail "manifest not found: $MANIFEST"

printf '== Safe deployment checks ==\n'
"$SCRIPT_DIR/verify_firewall.sh" "$HOST_PORT"
"$SCRIPT_DIR/verify_container_config.sh"
"$CONTAINER_DIR/scripts/authorization.sh" integrity-check

printf '\n== NGINX and systemd checks ==\n'
if [[ "$EUID" -eq 0 ]]; then
    nginx -t
elif sudo -n -v >/dev/null 2>&1; then
    sudo nginx -t
else
    printf '%s\n' 'WARN  NGINX configuration check skipped; run sudo nginx -t as an operator'
fi
if [[ -z "${XDG_RUNTIME_DIR:-}" ]]; then
    XDG_RUNTIME_DIR="/run/user/$(id -u)"
    export XDG_RUNTIME_DIR
fi
[[ -d "$XDG_RUNTIME_DIR" ]] || fail "user runtime directory is unavailable: $XDG_RUNTIME_DIR"
systemctl --user is-active --quiet "$SERVICE_NAME" || fail "user service is not active: $SERVICE_NAME"
printf 'User service is active: %s\n' "$SERVICE_NAME"

manifest_name="/tmp/authorization-verification-$$.yaml"
cleanup_manifest() {
    podman exec "$CONTAINER_NAME" rm -f "$manifest_name" >/dev/null 2>&1 || true
}
trap cleanup_manifest EXIT
podman exec -i "$CONTAINER_NAME" tee "$manifest_name" >/dev/null < "$MANIFEST"
printf '\n== Manifest reconciliation ==\n'
"$CONTAINER_DIR/scripts/authorization.sh" reconcile "$manifest_name"

if [[ "$RUN_AUTHENTICATED" = true ]]; then
    [[ -n "$PROJECT_A" && -n "$PROJECT_B" ]] || fail "authenticated access requires both projects"
    [[ -n "$PRINCIPAL_A" && -n "$PRINCIPAL_B" ]] || fail "authenticated access requires both principals"
    if [[ "$RUN_GRANT_ACCESS" = true ]]; then
        [[ "$PRINCIPAL_A" != "$PRINCIPAL_B" ]] || fail "authenticated principals must be different"
        [[ "$PROJECT_A" != "$PROJECT_B" ]] || fail "authenticated projects must be different"
        printf '\n== Fixture grants ==\n'
        "$CONTAINER_DIR/scripts/authorization.sh" grant \
            --resource-type project --locator "$PROJECT_A" \
            --subject-type principal --subject-id "$PRINCIPAL_A" \
            --role viewer --actor verification-check
        "$CONTAINER_DIR/scripts/authorization.sh" grant \
            --resource-type project --locator "$PROJECT_B" \
            --subject-type principal --subject-id "$PRINCIPAL_B" \
            --role viewer --actor verification-check
    fi
    printf '\n== Authenticated access ==\n'
    "$SCRIPT_DIR/verify_authenticated_access.sh" \
        --base-url "$BASE_URL" \
        --principal-a "$PRINCIPAL_A" \
        --principal-b "$PRINCIPAL_B" \
        --project-a "$PROJECT_A" \
        --project-b "$PROJECT_B"
else
    printf '\nAuthenticated access: SKIPPED (pass --authenticated with two principals and projects)\n'
fi

if [[ "$RUN_CLEANUP" = true ]]; then
    [[ -n "$CLEANUP_PREFIX" ]] || fail "cleanup prefix cannot be empty"
    read -rsp "Password for $ADMIN_USER: " admin_password
    printf '\n'
    mapfile -t projects < <(
        "$CONTAINER_DIR/scripts/authorization.sh" list-resources --json |
            jq -r --arg prefix "$CLEANUP_PREFIX" \
                '.[] | select(.resource_type == "project" and .lifecycle_state == "active" and (.locator | startswith($prefix))) | .locator'
    )
    if ((${#KEEP_PROJECTS[@]} > 0)); then
        filtered_projects=()
        for project in "${projects[@]}"; do
            keep=false
            for keep_project in "${KEEP_PROJECTS[@]}"; do
                [[ "$project" = "$keep_project" ]] && keep=true
            done
            [[ "$keep" = false ]] && filtered_projects+=("$project")
        done
        projects=("${filtered_projects[@]}")
    fi
    ((${#projects[@]} > 0)) || fail "no active project matches cleanup prefix: $CLEANUP_PREFIX"
    printf 'Projects selected for deletion:\n'
    printf '  %s\n' "${projects[@]}"
    if [[ "$ASSUME_YES" = false ]]; then
        read -r -p 'Delete these projects through the application? [y/N] ' confirmation
        [[ "$confirmation" =~ ^[Yy]$ ]] || { unset admin_password; printf 'Cleanup cancelled.\n'; exit 0; }
    fi
    for project in "${projects[@]}"; do
        encoded_project="$(jq -rn --arg value "$project" '$value | @uri')"
        response_code="$(curl -sS -u "$ADMIN_USER:$admin_password" \
            -X DELETE -o /dev/null -w '%{http_code}' \
            "$BASE_URL/api/v1/projects/$encoded_project")"
        printf '%s -> HTTP %s\n' "$project" "$response_code"
        [[ "$response_code" = 204 ]] || fail "cleanup failed for $project (HTTP $response_code)"
    done
    unset admin_password
else
    printf 'Cleanup: SKIPPED (pass --cleanup-prefix PREFIX to opt in)\n'
fi

if [[ "$RUN_ROLLBACK" = true ]]; then
    [[ -n "$ROLLBACK_IMAGE" ]] || fail "--rollback-image is required with --rollback"
    [[ -n "$AUTHORIZATION_BACKUP" ]] || fail "--authorization-backup is required with --rollback"
    printf '\n== Rollback exercise ==\n'
    rollback_args=(
        --image "$ROLLBACK_IMAGE"
        --authorization-backup "$AUTHORIZATION_BACKUP"
        --manifest "$MANIFEST"
        --host-port "$HOST_PORT"
    )
    [[ "$ASSUME_YES" = true ]] && rollback_args+=(--yes)
    "$SCRIPT_DIR/rollback_exercise.sh" "${rollback_args[@]}"
else
    printf 'Rollback: SKIPPED (pass --rollback to opt in)\n'
fi

printf '\nVerification bundle completed. Record the output with the deployment date and host.\n'