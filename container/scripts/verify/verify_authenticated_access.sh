#!/usr/bin/env bash
# Verify authenticated access and cross-resource isolation through the proxy
# with two real principals, and record each request/response pair.
#
# Probes, all through the proxy with Basic authentication:
#   - proxy-auth: a request without credentials must be rejected (HTTP 401);
#   - allowed: each principal reads the project it is granted (HTTP 200);
#   - denied: each principal is denied the project it is not granted. Project
#     denial is concealed, so the expected status is HTTP 404, not 403;
#   - isolation: principal A reaches project A but not B, and principal B
#     reaches project B but not A.
#
# Prerequisites, set up before running:
#   - two nginx Basic-auth users, one per principal;
#   - two projects, each granted to exactly one principal (viewer / project:read);
#   - neither principal holds a deployment role that grants read. Such a role
#     reads every project, so it defeats the denied probes.
#
# The script reads the deployment roles of both principals and reports them
# before probing. When a principal does hold a read-granting role, the matching
# denied probe expects 200 and is labelled as an expected privileged read, so
# the transcript records intended behaviour instead of a false isolation
# failure. When the roles cannot be read, the script says so and assumes
# neither principal holds one.
#
# Passwords are read from PRINCIPAL_A_PASSWORD and PRINCIPAL_B_PASSWORD, or
# prompted on a terminal. They are never echoed or logged.
#
# The script sends GET requests only and never changes a project, grant, file,
# container, image, or configuration.
#
# Run as the deployment user, for example:
#   sudo -u test-shape-shifter.sead.se -H bash container/scripts/verify/verify_authenticated_access.sh \
#     --base-url https://test-shape-shifter.sead.se \
#     --principal-a alice --principal-b bob \
#     --project-a project-alice --project-b project-bob
set -euo pipefail

g_base_url="${BASE_URL:-https://test-shape-shifter.sead.se}"
g_principal_a="${PRINCIPAL_A:-}"
g_principal_b="${PRINCIPAL_B:-}"
g_project_a="${PROJECT_A:-}"
g_project_b="${PROJECT_B:-}"
g_container_name="${CONTAINER_NAME:-shape-shifter}"
g_password_a=""
g_password_b=""

usage() {
    cat <<EOF
Usage: $(basename -- "$0") [OPTIONS]

Options:
  --base-url URL      Proxy base URL (default: https://test-shape-shifter.sead.se)
  --principal-a USER  First principal's Basic-auth username (required)
  --principal-b USER  Second principal's Basic-auth username (required)
  --project-a NAME    Project the first principal can read (required)
  --project-b NAME    Project the second principal can read (required)
  -h, --help          Show this help

Passwords come from the environment variables PRINCIPAL_A_PASSWORD and
PRINCIPAL_B_PASSWORD, or from a terminal prompt when they are unset.
Passwords must not contain a colon.
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --base-url)     [[ $# -ge 2 ]] || { echo "--base-url requires a value." >&2; exit 2; }; g_base_url="$2"; shift 2 ;;
        --principal-a)  [[ $# -ge 2 ]] || { echo "--principal-a requires a value." >&2; exit 2; }; g_principal_a="$2"; shift 2 ;;
        --principal-b)  [[ $# -ge 2 ]] || { echo "--principal-b requires a value." >&2; exit 2; }; g_principal_b="$2"; shift 2 ;;
        --project-a)    [[ $# -ge 2 ]] || { echo "--project-a requires a value." >&2; exit 2; }; g_project_a="$2"; shift 2 ;;
        --project-b)    [[ $# -ge 2 ]] || { echo "--project-b requires a value." >&2; exit 2; }; g_project_b="$2"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "unknown option: $1" >&2; usage >&2; exit 2 ;;
    esac
done

[[ -n "$g_principal_a" && -n "$g_principal_b" ]] || { echo "--principal-a and --principal-b are required." >&2; usage >&2; exit 2; }
[[ -n "$g_project_a" && -n "$g_project_b" ]] || { echo "--project-a and --project-b are required." >&2; usage >&2; exit 2; }

command -v curl >/dev/null || { echo "curl is required." >&2; exit 1; }

info() { printf '\n== %s ==\n' "$*"; }

# Read one password into the named variable: environment first, then terminal prompt.
read_password() {
    local label="$1" env_name="$2"
    local -n target="$3"
    if [[ -n "${!env_name:-}" ]]; then
        target="${!env_name}"
        return 0
    fi
    if [[ -t 0 ]]; then
        IFS= read -rs -p "Password for $label: " target
        printf '\n' >&2
        [[ -n "$target" ]] || return 1
        return 0
    fi
    printf 'Password for %s not provided: export %s=... before running.\n' "$label" "$env_name" >&2
    return 1
}

read_password "principal A" PRINCIPAL_A_PASSWORD g_password_a || exit 2
read_password "principal B" PRINCIPAL_B_PASSWORD g_password_b || exit 2

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

# Print the deployment roles of one principal that permit Action.READ, as a
# comma-separated list and an empty line when the principal holds none. Return
# non-zero when the deployment cannot be read, so the caller can say the scope
# was not checked instead of assuming that it is safe. The role-to-action map
# comes from the deployed policy, so this check cannot drift from enforcement.
read_granting_roles() {
    local principal="$1"
    podman exec "$g_container_name" python -c '
import sys

from backend.app.authorization.models import Action, ApplicationRole
from backend.app.authorization.policy import DEPLOYMENT_ROLE_ACTIONS
from backend.app.authorization.repository import SQLiteAuthorizationRepository
from backend.app.core.config import settings

repository = SQLiteAuthorizationRepository(settings.AUTHORIZATION_DATABASE_PATH)
try:
    assigned = repository.list_application_roles(sys.argv[1])
finally:
    repository.close()

known = {role.value for role in ApplicationRole}
read_roles = [
    role
    for role in assigned
    if role in known and Action.READ in DEPLOYMENT_ROLE_ACTIONS.get(ApplicationRole(role), frozenset())
]
print(",".join(read_roles))
' "$principal" 2>/dev/null
}

g_scope_verified=true
g_read_roles_a=""
g_read_roles_b=""

if ! g_read_roles_a="$(read_granting_roles "$g_principal_a")"; then
    g_scope_verified=false
fi
if ! g_read_roles_b="$(read_granting_roles "$g_principal_b")"; then
    g_scope_verified=false
fi

describe_scope() {
    if [[ -n "$2" ]]; then
        printf '%s holds %s, which grants read on every project\n' "$1" "$2"
    else
        printf '%s holds no deployment role that grants read\n' "$1"
    fi
}

g_note_a=""
g_note_b=""
g_expected_denied_a=404
g_expected_denied_b=404
# Both probes are isolation probes until a read-granting deployment role turns
# one of them into an expected privileged read.
g_isolation_directions=2

if [[ "$g_scope_verified" = true ]]; then
    if [[ -n "$g_read_roles_a" ]]; then
        g_expected_denied_a=200
        g_note_a="expected privileged read through $g_read_roles_a"
        g_isolation_directions=$((g_isolation_directions - 1))
    fi
    if [[ -n "$g_read_roles_b" ]]; then
        g_expected_denied_b=200
        g_note_b="expected privileged read through $g_read_roles_b"
        g_isolation_directions=$((g_isolation_directions - 1))
    fi
fi

# label|path-template|expected status|principal (empty = no credentials)|note
g_specs=(
    "proxy-auth|/api/v1/projects/{A}|401||"
    "allowed-A|/api/v1/projects/{A}|200|A|"
    "denied-A|/api/v1/projects/{B}|$g_expected_denied_a|A|$g_note_a"
    "allowed-B|/api/v1/projects/{B}|200|B|"
    "denied-B|/api/v1/projects/{A}|$g_expected_denied_b|B|$g_note_b"
)

expand() { printf '%s' "$1" | sed -e "s/{A}/$g_project_a/g" -e "s/{B}/$g_project_b/g"; }

probe() {
    local url="$1" principal="$2"
    local user pass code
    case "$principal" in
        A) user="$g_principal_a"; pass="$g_password_a" ;;
        B) user="$g_principal_b"; pass="$g_password_b" ;;
        *) user=""; pass="" ;;
    esac
    if [[ -n "$user" ]]; then
        code="$(curl -sS -o "$tmpdir/body" -w '%{http_code}' -u "$user:$pass" "$url" 2>/dev/null || true)"
    else
        code="$(curl -sS -o "$tmpdir/body" -w '%{http_code}' "$url" 2>/dev/null || true)"
    fi
    printf '%s' "$code"
}

body_excerpt() {
    # curl writes no body when it cannot connect, so there may be nothing to read.
    [[ -f "$tmpdir/body" ]] || return 0
    tr '\n' ' ' < "$tmpdir/body" | cut -c1-120
}

g_failures=0

printf 'Authenticated access probe through: %s\n' "$g_base_url"
printf 'Principal A: %s -> project %s\nPrincipal B: %s -> project %s\n' \
    "$g_principal_a" "$g_project_a" "$g_principal_b" "$g_project_b"

info "Principal scope"
if [[ "$g_scope_verified" = true ]]; then
    describe_scope "$g_principal_a" "$g_read_roles_a"
    describe_scope "$g_principal_b" "$g_read_roles_b"
else
    printf 'Deployment roles could not be read: podman, the container, or the\n'
    printf 'authorization store is unavailable. Assuming neither principal holds\n'
    printf 'a role that grants read, so the denied probes expect 404.\n'
fi

info "Request and response pairs"

for spec in "${g_specs[@]}"; do
    label="${spec%%|*}"; rest="${spec#*|}"
    path_template="${rest%%|*}"; rest="${rest#*|}"
    expected="${rest%%|*}"; rest="${rest#*|}"
    principal="${rest%%|*}"; note="${rest#*|}"

    path="$(expand "$path_template")"
    url="$g_base_url$path"
    code="$(probe "$url" "$principal")"

    if [[ "$code" == "$expected" ]]; then
        verdict="PASS"
    else
        verdict="FAIL"
        g_failures=$((g_failures + 1))
    fi

    identity="${principal:-<none>}"
    printf '\n[%s] GET %s\n  as %-28s -> HTTP %s (expect %s)  %s\n' \
        "$label" "$path" "$identity" "$code" "$expected" "$verdict"
    if [[ -n "$note" ]]; then
        printf '    note: %s\n' "$note"
    fi
    printf '    response body: %s\n' "$(body_excerpt)"
done

printf '\n'
if [[ "$g_failures" -gt 0 ]]; then
    printf 'Authenticated access check failed with %d issue(s).\n' "$g_failures" >&2
    exit 1
fi
printf 'Authenticated access passed. Save this output with the date and operator\n'
printf 'as the check evidence, and quote the principal scope above.\n'
if [[ "$g_isolation_directions" -lt 2 ]]; then
    printf '\nCross-resource isolation was verified in %d of 2 directions. The other\n' "$g_isolation_directions"
    printf 'probes were expected privileged reads, because a principal holding a\n'
    printf 'read-granting deployment role reads every project by policy. That is not\n'
    printf 'evidence of isolation; choose principals without such a role to test it.\n'
fi
