#!/usr/bin/env bash
# Delete a disposable project and its temporary authorization creator role.
set -Eeuo pipefail

# Report where a command failed before set -e ends the script. Diagnostic only:
# fail helpers, EXIT cleanup, and exit codes are unchanged. Only the command
# word is printed; arguments can carry credentials.
report_failure() {
    local status="$1" source_file="$2" line="$3" failed_command="$4"
    printf 'error: %s:%s: %s failed with exit code %s\n' "$source_file" "$line" "$failed_command" "$status" >&2
}
trap 'report_failure $? "${BASH_SOURCE[0]}" "$LINENO" "${BASH_COMMAND%% *}"' ERR

SCRIPT_DIR="$(CDPATH='' cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
AUTHORIZATION_SCRIPT="$SCRIPT_DIR/../authorization.sh"

G_API_URL="http://127.0.0.1:8012"
G_PROJECT_NAME=""
G_CREATOR_PRINCIPAL=""
G_ACTOR="$(id -un)"

usage() {
    cat <<'EOF'
Usage: teardown.sh [OPTIONS]

Delete a disposable project and revoke its temporary project-creator role.

Options:
  --api-url URL                 Local backend URL (default: http://127.0.0.1:8012)
  --project-name NAME           Disposable project name
  --creator-principal PRINCIPAL Temporary application principal
  --actor ID                    Authorization audit actor
  -h, --help                    Show this help
EOF
}

fail() {
    printf 'FAIL: %s\n' "$*" >&2
    exit 1
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --api-url)                [[ $# -ge 2 ]] || fail "--api-url requires a value"; G_API_URL="$2"; shift 2 ;;
        --project-name)           [[ $# -ge 2 ]] || fail "--project-name requires a value"; G_PROJECT_NAME="$2"; shift 2 ;;
        --creator-principal)      [[ $# -ge 2 ]] || fail "--creator-principal requires a value"; G_CREATOR_PRINCIPAL="$2"; shift 2 ;;
        --actor)                  [[ $# -ge 2 ]] || fail "--actor requires a value"; G_ACTOR="$2"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) fail "unknown argument: $1" ;;
    esac
done

[[ -n "$G_PROJECT_NAME" ]] || fail "--project-name is required"
[[ -n "$G_CREATOR_PRINCIPAL" ]] || fail "--creator-principal is required"
command -v curl >/dev/null || fail "curl is required"
[[ -x "$AUTHORIZATION_SCRIPT" ]] || fail "authorization wrapper is not executable: $AUTHORIZATION_SCRIPT"

cleanup_failed=false
delete_status="$(curl -sS -o /dev/null -w '%{http_code}' \
    -H "X-Authenticated-User: $G_CREATOR_PRINCIPAL" \
    -X DELETE "$G_API_URL/api/v1/projects/$G_PROJECT_NAME" || true)"
if [[ "$delete_status" != "204" && "$delete_status" != "404" ]]; then
    cleanup_failed=true
    printf 'WARN: could not delete project: %s (HTTP %s)\n' "$G_PROJECT_NAME" "$delete_status" >&2
else
    printf 'Project deletion HTTP status: %s\n' "$delete_status"
fi

if ! "$AUTHORIZATION_SCRIPT" revoke-application-role \
    --principal-id "$G_CREATOR_PRINCIPAL" --role project_creator \
    --actor "$G_ACTOR" --yes --non-interactive; then
    cleanup_failed=true
    printf 'WARN: could not revoke application role from: %s\n' "$G_CREATOR_PRINCIPAL" >&2
fi

if [[ "$cleanup_failed" = true ]]; then
    exit 1
fi
printf 'Disposable project deleted: %s\n' "$G_PROJECT_NAME"
printf 'Creator principal cleaned up: %s\n' "$G_CREATOR_PRINCIPAL"
