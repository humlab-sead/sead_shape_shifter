#!/usr/bin/env bash
# Enumerate the backend's credentials that were reachable while the backend
# answered on the LAN address, and produce a rotation (or approved-exception)
# record with one row per credential. Names and redacted targets only; no
# credential value is ever printed.
#
# The LAN exposure happened when the backend was published on every interface
# before its port was restricted to loopback. The credentials in play were the
# backend's own: the PostgreSQL password file and any credential-like variable
# in the runtime environment. This script lists those sources (names only),
# then emits a rotation record the operator completes by saving the output and
# passing --rotated / --declined on a later run for each row.
#
# The script reads only. It never changes a credential, file, container, image,
# or configuration, and it never prints a credential value. Exits non-zero while
# any credential has no recorded rotation or approved exception, so the check
# cannot be missed.
#
# Run as the deployment user, for example:
#   sudo -u test-shape-shifter.sead.se -H bash container/scripts/verify/verify_credential_rotation.sh
#
# Environment:
#   DATA_DIR        deployment data directory (default: ../container-data)
#   CONTAINER_NAME  container to inspect (default: shape-shifter)
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../load-env.sh
if [[ -f "$SCRIPT_DIR/../load-env.sh" ]]; then
    . "$SCRIPT_DIR/../load-env.sh"
fi

DATA_DIR="${DATA_DIR:-$SCRIPT_DIR/../../container-data}"
CONTAINER_NAME="${CONTAINER_NAME:-shape-shifter}"

ROTATED=()
DECLINED=()

usage() {
    cat <<EOF
Usage: $(basename -- "$0") [OPTIONS]

Options:
  --rotated LABEL        Mark one credential as rotated (repeatable)
  --declined LABEL=REAS  Mark one credential as rotation declined with the
                         approved exception reason (repeatable)
  -h, --help             Show this help

The script first lists every credential source with its LABEL. Run it once with
no options to see the inventory, rotate the listed credentials, then re-run
passing one --rotated or --declined option per row to record each result.
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --rotated)
            [[ $# -ge 2 ]] || { echo "--rotated requires a LABEL." >&2; exit 2; }
            ROTATED+=("$2"); shift 2 ;;
        --declined)
            [[ $# -ge 2 ]] || { echo "--declined requires LABEL=REASON." >&2; exit 2; }
            DECLINED+=("$2"); shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "unknown option: $1" >&2; usage >&2; exit 2 ;;
    esac
done

info() { printf '\n== %s ==\n' "$*"; }
warn() { printf 'WARN  %s\n' "$*"; }

# label -> description. The label is what the operator passes to --rotated/--declined.
declare -A CREDS=()
declare -a ORDER=()

record() {
    local label="$1" description="$2"
    if [[ -z "${CREDS[$label]+x}" ]]; then
        CREDS[$label]="$description"
        ORDER+=("$label")
    fi
}

# Credential-like variable names. Matches the set used by the other verify
# scripts; values are never read.
NAME_PATTERN='PASSWORD|SECRET|TOKEN|PASSWD|CREDENTIAL|API_KEY|PRIVATE_KEY|SIGNING'

printf 'LAN exposure: the backend answered on the LAN address before its port was\n'
printf 'restricted to loopback. The credentials below are the backend sources\n'
printf 'present now; confirm with the running image revision that the same sources\n'
printf 'existed during the exposure window. The nginx Basic auth file\n'
printf '/etc/nginx/htpasswd/shape-shifter was bypassed, not reachable through the\n'
printf 'backend, and is outside this check.\n'

info "Credential inventory (names and redacted targets only)"

# 1. PostgreSQL password file.
pgpass="$DATA_DIR/.pgpass/.pgpass"
if [[ -r "$pgpass" ]]; then
    printf 'PostgreSQL password file: %s\n' "$pgpass"
    while IFS= read -r line; do
        [[ -n "$line" ]] || continue
        case "$line" in '#'*) continue ;; esac
        target="${line%:*}"   # host:port:database:username; the password field is removed
        printf '  %s:***\n' "$target"
        record "pgpass:$target" "PostgreSQL password for $target"
    done < "$pgpass"
else
    warn "cannot read PostgreSQL password file: $pgpass"
fi

# 2. Runtime environment file (chmod 600; names only).
env_file="$DATA_DIR/backend.env"
if [[ -r "$env_file" ]]; then
    printf 'Runtime environment file: %s\n' "$env_file"
    while IFS= read -r name; do
        [[ -n "$name" ]] || continue
        if [[ "$name" =~ $NAME_PATTERN ]]; then
            printf '  %s\n' "$name"
            record "env:$name" "environment variable $name"
        fi
    done < <(sed 's/=.*//' "$env_file" | grep -Ev '^[[:space:]]*(#|$)' || true)
else
    warn "cannot read runtime environment file: $env_file"
fi

# 3. Container environment variable names (podman, best effort).
if command -v podman >/dev/null 2>&1; then
    printf 'Container environment variable names: %s\n' "$CONTAINER_NAME"
    container_env="$(podman container inspect --format '{{range .Config.Env}}{{println .}}{{end}}' "$CONTAINER_NAME" 2>/dev/null || true)"
    if [[ -n "$container_env" ]]; then
        while IFS= read -r name; do
            [[ -n "$name" ]] || continue
            if [[ "$name" =~ $NAME_PATTERN ]]; then
                printf '  %s\n' "$name"
                record "env:$name" "environment variable $name"
            fi
        done < <(printf '%s\n' "$container_env" | sed 's/=.*//' | sort -u)
    else
        warn "cannot read container '$CONTAINER_NAME' environment (not running under this user?)"
    fi
else
    warn "podman not found; skipped container environment inspection"
fi

if [[ "${#ORDER[@]}" -eq 0 ]]; then
    printf '\nNo credential sources found to rotate. Confirm this against the\n'
    printf 'deployment record before closing the check.\n'
    exit 0
fi

# Index the operator's decisions.
declare -A rotated_set=()
for label in "${ROTATED[@]}"; do rotated_set["$label"]=1; done
declare -A declined_set=()
for entry in "${DECLINED[@]}"; do
    label="${entry%%=*}"
    reason="${entry#*=}"
    [[ "$reason" == "$entry" ]] && reason="(no reason recorded)"
    declined_set["$label"]="$reason"
done

pending=0
info "Rotation record (one row per credential)"
for label in "${ORDER[@]}"; do
    if [[ -n "${rotated_set[$label]+x}" ]]; then
        printf '[x] %-55s rotated\n' "$label"
    elif [[ -n "${declined_set[$label]+x}" ]]; then
        printf '[x] %-55s declined: %s\n' "$label" "${declined_set[$label]}"
    else
        printf '[ ] %-55s pending rotation or approved exception\n' "$label"
        pending=$((pending + 1))
    fi
done

printf '\n'
if [[ "$pending" -gt 0 ]]; then
    printf '%d credential(s) have no recorded rotation or exception. Rotate each\n' "$pending" >&2
    printf 'credential, then re-run passing --rotated LABEL (or --declined LABEL=REASON)\n' >&2
    printf 'per row, and save the final output as the record.\n' >&2
    exit 1
fi
printf 'Every credential has a recorded rotation or approved exception. Save this\n'
printf 'output with the date and operator as the check evidence.\n'
