#!/usr/bin/env bash
# Create a disposable project and its temporary authorization creator role.
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
G_TEMPLATE_DIR="$SCRIPT_DIR/disposable-project"
G_CREATOR_PRINCIPAL=""
G_UNAUTHORIZED_PRINCIPAL=""
G_ACTOR="$(id -un)"
G_PROJECT_CREATED=false
G_ROLE_GRANTED=false

usage() {
    cat <<'EOF'
Usage: setup.sh [OPTIONS]

Create a disposable project for endpoint-containment verification. The project
is registered through the API, so its authorization resource is created too.
No nginx user or password is created.

Options:
  --api-url URL                    Local backend URL (default: http://127.0.0.1:8012)
  --project-name NAME              Project name
  --template-dir DIR               Directory containing shapeshifter.yml
  --creator-principal PRINCIPAL    Temporary application principal
  --unauthorized-principal ID      Principal with no project grant
  --actor ID                       Authorization audit actor
  -h, --help                       Show this help
EOF
}

fail() {
    printf 'FAIL: %s\n' "$*" >&2
    exit 1
}

cleanup_on_error() {
    local status=$?
    [[ "$status" -eq 0 ]] && return 0
    if [[ "$G_PROJECT_CREATED" = true ]]; then
        curl -fsS -o /dev/null -H "X-Authenticated-User: $G_CREATOR_PRINCIPAL" \
            -X DELETE "$G_API_URL/api/v1/projects/$G_PROJECT_NAME" 2>/dev/null || true
    fi
    if [[ "$G_ROLE_GRANTED" = true ]]; then
        "$AUTHORIZATION_SCRIPT" revoke-application-role \
            --principal-id "$G_CREATOR_PRINCIPAL" --role project_creator \
            --actor "$G_ACTOR" --yes --non-interactive >/dev/null 2>&1 || true
    fi
    exit "$status"
}
trap cleanup_on_error EXIT

while [[ $# -gt 0 ]]; do
    case "$1" in
        --api-url)                  [[ $# -ge 2 ]] || fail "--api-url requires a value"; G_API_URL="$2"; shift 2 ;;
        --project-name)             [[ $# -ge 2 ]] || fail "--project-name requires a value"; G_PROJECT_NAME="$2"; shift 2 ;;
        --template-dir)             [[ $# -ge 2 ]] || fail "--template-dir requires a value"; G_TEMPLATE_DIR="$2"; shift 2 ;;
        --creator-principal)        [[ $# -ge 2 ]] || fail "--creator-principal requires a value"; G_CREATOR_PRINCIPAL="$2"; shift 2 ;;
        --unauthorized-principal)   [[ $# -ge 2 ]] || fail "--unauthorized-principal requires a value"; G_UNAUTHORIZED_PRINCIPAL="$2"; shift 2 ;;
        --actor)                    [[ $# -ge 2 ]] || fail "--actor requires a value"; G_ACTOR="$2"; shift 2 ;;
        -h|--help) usage; trap - EXIT; exit 0 ;;
        *) fail "unknown argument: $1" ;;
    esac
done

[[ -n "$G_PROJECT_NAME" ]] || fail "--project-name is required"
[[ -n "$G_CREATOR_PRINCIPAL" ]] || fail "--creator-principal is required"
[[ -n "$G_UNAUTHORIZED_PRINCIPAL" ]] || fail "--unauthorized-principal is required"
[[ "$G_CREATOR_PRINCIPAL" != "$G_UNAUTHORIZED_PRINCIPAL" ]] || fail "creator and unauthorized principals must differ"
[[ -f "$G_TEMPLATE_DIR/shapeshifter.yml" ]] || fail "template not found: $G_TEMPLATE_DIR/shapeshifter.yml"
command -v curl >/dev/null || fail "curl is required"
command -v yq >/dev/null || fail "yq is required"
[[ -x "$AUTHORIZATION_SCRIPT" ]] || fail "authorization wrapper is not executable: $AUTHORIZATION_SCRIPT"

project_name_pattern='^[A-Za-z0-9][A-Za-z0-9_-]*$'
[[ "$G_PROJECT_NAME" =~ $project_name_pattern ]] || fail "project name contains unsupported characters"

existing_roles_file="$(mktemp)"
trap 'rm -f "$existing_roles_file"' RETURN
if "$AUTHORIZATION_SCRIPT" list-application-roles --json > "$existing_roles_file"; then
    # mikefarah yq exits 1 with "no matches found" when the temporary principal
    # has no role yet, which is the expected case; keep that message out of the log.
    if PRINCIPAL="$G_CREATOR_PRINCIPAL" yq -e '.[] | select(.principal_id == strenv(PRINCIPAL) and .role == "project_creator")' "$existing_roles_file" >/dev/null 2>&1; then
        fail "creator principal already has project_creator; use a unique temporary principal"
    fi
else
    fail "could not inspect existing application roles"
fi

template_file="$(mktemp)"
request_file="$(mktemp)"
trap 'rm -f "$existing_roles_file" "$template_file" "$request_file"' RETURN

# yq on the deployment host is mikefarah yq v4, which has no --arg flag: pass the
# project name through the environment and read it with strenv().
PROJECT="$G_PROJECT_NAME" yq eval '.metadata.name = strenv(PROJECT)' \
    "$G_TEMPLATE_DIR/shapeshifter.yml" > "$template_file"
python3 - "$template_file" "$request_file" <<'PY'
import json
import sys
from pathlib import Path

Path(sys.argv[2]).write_text(json.dumps({"yaml_content": Path(sys.argv[1]).read_text()}))
PY

printf 'Granting project_creator to %s\n' "$G_CREATOR_PRINCIPAL"
"$AUTHORIZATION_SCRIPT" grant-application-role \
    --principal-id "$G_CREATOR_PRINCIPAL" --role project_creator --actor "$G_ACTOR"
G_ROLE_GRANTED=true

printf 'Creating registered project: %s\n' "$G_PROJECT_NAME"
curl -fsS -o /dev/null -w 'Project creation HTTP status: %{http_code}\n' -H 'Content-Type: application/json' \
    -H "X-Authenticated-User: $G_CREATOR_PRINCIPAL" \
    -X POST "$G_API_URL/api/v1/projects" \
    --data "{\"name\":\"$G_PROJECT_NAME\",\"entities\":{}}"
G_PROJECT_CREATED=true

printf 'Loading project template through the API\n'
curl -fsS -o /dev/null -w 'Template update HTTP status: %{http_code}\n' -H 'Content-Type: application/json' \
    -H "X-Authenticated-User: $G_CREATOR_PRINCIPAL" \
    -X PUT "$G_API_URL/api/v1/projects/$G_PROJECT_NAME/raw-yaml" \
    --data-binary "@$request_file"

printf 'Disposable project created: %s\n' "$G_PROJECT_NAME"
printf 'Creator principal: %s\n' "$G_CREATOR_PRINCIPAL"
printf 'Unauthorized principal: %s\n' "$G_UNAUTHORIZED_PRINCIPAL"
printf 'Template: %s\n' "$G_TEMPLATE_DIR/shapeshifter.yml"
trap - EXIT
rm -f "$template_file" "$request_file"
