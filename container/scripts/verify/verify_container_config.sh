#!/usr/bin/env bash
# Re-inspect the running Shape Shifter container for mounts, environment, and image contents.
#
# Confirms the container matches the deployed shape in container/podman-compose.yml:
#   - published port is loopback-only (127.0.0.1:8012, never 0.0.0.0 or ::);
#   - only the expected bind mounts exist, none under a sensitive host path;
#   - the .pgpass mount is read-only;
#   - environment variable NAMES are printed without values, so no credential
#     value is written to output;
#   - image labels are present and image history contains no credential-like
#     build command.
#
# The script never changes the container, image, or configuration.
#
# Run as the deployment user, for example:
#   sudo -u test-shape-shifter.sead.se -H bash container/scripts/verify/verify_container_config.sh
#
# Environment:
#   CONTAINER_NAME  container to inspect (default: shape-shifter)
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../load-env.sh
if [[ -f "$SCRIPT_DIR/../load-env.sh" ]]; then
    . "$SCRIPT_DIR/../load-env.sh"
fi

CONTAINER_NAME="${CONTAINER_NAME:-shape-shifter}"
failures=0

info() { printf '\n== %s ==\n' "$*"; }
pass() { printf 'PASS  %s\n' "$*"; }
fail() { printf 'FAIL  %s\n' "$*" >&2; failures=$((failures + 1)); }
warn() { printf 'WARN  %s\n' "$*"; }

# Expected container destinations from podman-compose.yml.
EXPECTED_MOUNTS=(
    /app/projects
    /app/shared
    /app/logs
    /app/output
    /app/backups
    /app/tmp
    /app/state
    /app/.pgpass
)

command -v podman >/dev/null || { echo "podman is required." >&2; exit 1; }

info "Container state"
state="$(podman container inspect --format '{{.State.Status}}' "$CONTAINER_NAME" 2>/dev/null || true)"
image="$(podman container inspect --format '{{.Config.Image}}' "$CONTAINER_NAME" 2>/dev/null || true)"
if [[ -z "$state" ]]; then
    fail "container '$CONTAINER_NAME' not found"
    printf 'Verification failed with %d issue(s).\n' "$failures" >&2
    exit 1
fi
printf 'Container: %s\nState:     %s\nImage:     %s\n' "$CONTAINER_NAME" "${state:-unknown}" "${image:-unknown}"
if [[ "$state" != "running" ]]; then
    fail "container is not running"
else
    pass "container is running"
fi

info "Port publication (expect 127.0.0.1:8012 only)"
ports="$(podman container inspect --format '{{json .NetworkSettings.Ports}}' "$CONTAINER_NAME" 2>/dev/null || true)"
printf '%s\n' "${ports:-<none>}"
if printf '%s' "$ports" | grep -Eq '"HostIp":"(0\.0\.0\.0|::|)"'; then
    fail "a published port listens on a non-loopback address"
else
    pass "published ports are loopback-only"
fi

info "Mounts (expect only the podman-compose.yml bind mounts, .pgpass read-only)"
declare -A seen=()
while IFS='|' read -r source destination mode; do
    [[ -n "$destination" ]] || continue
    seen["$destination"]=1
    printf '  %s -> %s (%s)\n' "$source" "$destination" "${mode:-rw}"
    case "$source" in
        /etc/*|/root/*|/run/secrets*|*/\.ssh*|/var/run/*.sock) fail "sensitive host path mounted: $source" ;;
    esac
    if [[ "$destination" == "/app/.pgpass" && "$mode" != "ro" ]]; then
        fail ".pgpass must be mounted read-only"
    fi
done < <(podman container inspect --format '{{range .Mounts}}{{.Source}}|{{.Destination}}|{{.Mode}}{{println}}{{end}}' "$CONTAINER_NAME" 2>/dev/null || true)

for expected in "${EXPECTED_MOUNTS[@]}"; do
    [[ -n "${seen[$expected]:-}" ]] || warn "expected mount missing: $expected"
done
printf 'Unexpected mounts, if any, appear above; review them.\n'

info "Container environment variable names (values never printed)"
credential_like=""
while IFS= read -r name; do
    [[ -n "$name" ]] || continue
    printf '  %s\n' "$name"
    if [[ "$name" =~ (PASSWORD|SECRET|TOKEN|KEY|PASSWD|CREDENTIAL) ]]; then
        credential_like+="$name "
    fi
done < <(podman container inspect --format '{{range .Config.Env}}{{println .}}{{end}}' "$CONTAINER_NAME" 2>/dev/null | sed 's/=.*//' | sort)
if [[ -n "$credential_like" ]]; then
    warn "credential-like variable names present (values not shown): $credential_like"
else
    pass "no credential-like variable names in the container environment"
fi

info "Image"
if [[ -n "$image" ]]; then
    printf 'Labels:\n'
    podman image inspect --format '{{json .Config.Labels}}' "$image" 2>/dev/null || warn "no image labels"
    printf '\nImage environment variable names:\n'
    podman image inspect --format '{{range .Config.Env}}{{println .}}{{end}}' "$image" 2>/dev/null | sed 's/=.*//' | sort || true
    printf '\nHistory layers whose build command matches a credential pattern (review these manually):\n'
    matches="$(podman image history --no-trunc "$image" 2>/dev/null | grep -Ei 'password|secret|token|passwd|credential' | awk '{print $1}' || true)"
    if [[ -n "$matches" ]]; then
        printf '%s\n' "$matches"
        warn "credential-like text in image history; review the layers above"
    else
        pass "no credential-like text in image history"
    fi
else
    fail "cannot determine the container image"
fi

printf '\n'
if [[ "$failures" -gt 0 ]]; then
    printf 'Verification failed with %d issue(s).\n' "$failures" >&2
    exit 1
fi
printf 'Container configuration re-inspection passed. Record this output with the date and host.\n'
