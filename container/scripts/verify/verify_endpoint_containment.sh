#!/usr/bin/env bash
# Confirm the execution, raw YAML mutation, data-source creation, and ingester
# endpoints reject unauthenticated and unauthorized calls, so no separate
# endpoint disablement is required. Issues one unauthenticated and one
# unauthorized request per group and records each request/response pair.
#
# Unauthenticated requests must be rejected by the trusted-proxy middleware with
# HTTP 401. Unauthorized requests (a principal with no grant for the resource or
# application action) must be rejected with HTTP 404 for project-scoped routes
# (denial is concealed) and HTTP 403 for the application-scoped data-source
# creation route.
#
# The ingester routes are recorded as application:run_ingesters with enforcement
# pending: authentication still rejects unauthenticated calls, but a principal
# without the run_ingesters application role is NOT yet rejected. This script
# reports that gap instead of treating it as contained.
#
# The script sends requests only; it never changes a credential, file, project,
# container, image, or configuration. Run it against the loopback backend on the
# deployment host with a disposable project so a broken check cannot write to a
# real project.
#
# Run as the deployment user, for example:
#   sudo -u test-shape-shifter.sead.se -H bash container/scripts/verify/verify_endpoint_containment.sh --project <existing-project>
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8012}"
PROJECT="${PROJECT:-}"
UNAUTHORIZED_PRINCIPAL="${UNAUTHORIZED_PRINCIPAL:-containment-probe@example.com}"
IDENTITY_HEADER="${IDENTITY_HEADER:-X-Authenticated-User}"
INGESTER_KEY="${INGESTER_KEY:-containment-probe-ingester}"

usage() {
    cat <<EOF
Usage: $(basename -- "$0") [OPTIONS]

Options:
  --base-url URL              Backend base URL (default: http://127.0.0.1:8012)
  --project NAME              Existing project for project-scoped probes (required)
  --unauthorized-principal ID Principal with no grant for the probes (default: containment-probe@example.com)
  --identity-header NAME      Proxy identity header the backend trusts (default: X-Authenticated-User)
  --ingester-key KEY          Ingester key for the ingester probe; use one that does not exist (default: containment-probe-ingester)
  -h, --help                  Show this help

Environment:
  BASE_URL, PROJECT, UNAUTHORIZED_PRINCIPAL, IDENTITY_HEADER, INGESTER_KEY
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --base-url)              [[ $# -ge 2 ]] || { echo "--base-url requires a value." >&2; exit 2; }; BASE_URL="$2"; shift 2 ;;
        --project)               [[ $# -ge 2 ]] || { echo "--project requires a value." >&2; exit 2; }; PROJECT="$2"; shift 2 ;;
        --unauthorized-principal) [[ $# -ge 2 ]] || { echo "--unauthorized-principal requires a value." >&2; exit 2; }; UNAUTHORIZED_PRINCIPAL="$2"; shift 2 ;;
        --identity-header)       [[ $# -ge 2 ]] || { echo "--identity-header requires a value." >&2; exit 2; }; IDENTITY_HEADER="$2"; shift 2 ;;
        --ingester-key)          [[ $# -ge 2 ]] || { echo "--ingester-key requires a value." >&2; exit 2; }; INGESTER_KEY="$2"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "unknown option: $1" >&2; usage >&2; exit 2 ;;
    esac
done

[[ -n "$PROJECT" ]] || { echo "--project is required (use an existing project)." >&2; usage >&2; exit 2; }

command -v curl >/dev/null || { echo "curl is required." >&2; exit 1; }

info() { printf '\n== %s ==\n' "$*"; }
warn() { printf 'WARN  %s\n' "$*"; }

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

# label|method|path-template|body|expected unauthorized code
SPECS=(
    "execution|POST|/api/v1/projects/{project}/execute|{\"dispatcher_key\":\"csv\",\"target\":\"/tmp/containment-probe\"}|404"
    "raw-yaml|PUT|/api/v1/projects/{project}/raw-yaml|{\"yaml_content\":\"probe\"}|404"
    "data-source-create|POST|/api/v1/data-sources|{\"name\":\"containment-probe\",\"driver\":\"csv\"}|403"
    "ingester|POST|/api/v1/ingesters/{key}/ingest|{\"source\":\"/tmp/containment-probe.xlsx\",\"submission_name\":\"containment-probe\",\"data_types\":\"containment-probe\"}|403"
)

expand() { printf '%s' "$1" | sed -e "s/{project}/$PROJECT/g" -e "s/{key}/$INGESTER_KEY/g"; }

# Probe one request; prints "STATUS <code>" and stores the response body excerpt.
probe() {
    local method="$1" url="$2" identity="$3" body="$4"
    local code
    if [[ -n "$identity" ]]; then
        if [[ -n "$body" ]]; then
            code="$(curl -sS -o "$tmpdir/body" -w '%{http_code}' -X "$method" \
                -H 'Content-Type: application/json' -H "$IDENTITY_HEADER: $identity" \
                --data "$body" "$url" 2>/dev/null || true)"
        else
            code="$(curl -sS -o "$tmpdir/body" -w '%{http_code}' -X "$method" \
                -H "$IDENTITY_HEADER: $identity" "$url" 2>/dev/null || true)"
        fi
    else
        if [[ -n "$body" ]]; then
            code="$(curl -sS -o "$tmpdir/body" -w '%{http_code}' -X "$method" \
                -H 'Content-Type: application/json' --data "$body" "$url" 2>/dev/null || true)"
        else
            code="$(curl -sS -o "$tmpdir/body" -w '%{http_code}' -X "$method" "$url" 2>/dev/null || true)"
        fi
    fi
    printf '%s' "$code"
}

body_excerpt() {
    tr '\n' ' ' < "$tmpdir/body" | cut -c1-120
}

failures=0
unauthed_failed=()

printf 'Containment probe against: %s\n' "$BASE_URL"
printf 'Project: %s\nUnauthorized principal: %s\nIdentity header: %s\nIngester key: %s\n' \
    "$PROJECT" "$UNAUTHORIZED_PRINCIPAL" "$IDENTITY_HEADER" "$INGESTER_KEY"

info "Request and response pairs"

for spec in "${SPECS[@]}"; do
    label="${spec%%|*}"; rest="${spec#*|}"
    method="${rest%%|*}"; rest="${rest#*|}"
    path_template="${rest%%|*}"; rest="${rest#*|}"
    body="${rest%%|*}"; rest="${rest#*|}"
    expected="${rest}"

    path="$(expand "$path_template")"
    url="$BASE_URL$path"

    # Unauthenticated: the trusted-proxy middleware must reject with 401.
    unauth_code="$(probe "$method" "$url" "" "$body")"
    unauth_ok="FAIL"
    [[ "$unauth_code" == "401" ]] && unauth_ok="PASS"

    printf '\n[%s] %s %s\n' "$label" "$method" "$path"
    printf '  unauthenticated           -> HTTP %s (expect 401)  %s\n' "$unauth_code" "$unauth_ok"

    if [[ "$unauth_code" != "401" ]]; then
        printf '  unauthorized             -> skipped (unauthenticated call reached the endpoint)\n'
        unauthed_failed+=("$label")
        failures=$((failures + 1))
        continue
    fi

    # Unauthorized: a principal with no grant must be denied before the handler runs.
    unauthz_code="$(probe "$method" "$url" "$UNAUTHORIZED_PRINCIPAL" "$body")"
    if [[ "$unauthz_code" == "$expected" ]]; then
        unauthz_ok="PASS"
    else
        unauthz_ok="FAIL"
        failures=$((failures + 1))
    fi
    printf '  unauthorized (%s) -> HTTP %s (expect %s)  %s\n' \
        "$UNAUTHORIZED_PRINCIPAL" "$unauthz_code" "$expected" "$unauthz_ok"
    excerpt="$(body_excerpt)"
    printf '    response body: %s\n' "$excerpt"

    if [[ "$label" == "ingester" && "$unauthz_code" != "$expected" ]]; then
        warn "ingester authorization is enforcement-pending: an authenticated principal without run_ingesters still reaches the handler (HTTP $unauthz_code). Separate disablement or enforcement is still required for ingesters."
    fi
done

printf '\n'
if [[ "$failures" -gt 0 ]]; then
    if [[ "${#unauthed_failed[@]}" -gt 0 ]]; then
        printf 'Unauthenticated calls reached the endpoint for: %s. The trusted-proxy\n' "${unauthed_failed[*]}" >&2
        printf 'middleware is not rejecting them; do not rely on these endpoints being\n' >&2
        printf 'contained until the proxy identity is restored.\n' >&2
    fi
    printf 'Endpoint containment check failed with %d issue(s).\n' "$failures" >&2
    exit 1
fi
printf 'Endpoint containment passed: unauthenticated and unauthorized calls are\n'
printf 'rejected for every group, and the ingester enforcement gap is recorded above\n'
printf 'if present. Save this output with the date and operator as the check evidence.\n'
