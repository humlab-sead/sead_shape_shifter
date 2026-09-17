#!/usr/bin/env bash
# Orchestrate deployment verification checks for a local deployment user.
set -Eeuo pipefail

SCRIPT_DIR="$(CDPATH='' cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
LOCAL_VERIFY_DIR="$SCRIPT_DIR"

DEPLOY_USER=""
CONTAINER_DIR=""
DATA_DIR=""
EVIDENCE_DIR=""
DATABASE=""
ROLE="sead_ro"
SCHEMA="public"
PROJECT=""
BASE_URL=""
PRINCIPAL_A="${PRINCIPAL_A:-}"
PRINCIPAL_B="${PRINCIPAL_B:-}"
PROJECT_A="${PROJECT_A:-}"
PROJECT_B="${PROJECT_B:-}"
SINCE="24h"
DB_LOG=""
SERVICE_NAME="shape-shifter"
RUN_AUTHENTICATED=false
RUN_ROLLBACK=false
ROLLBACK_IMAGE=""
AUTHORIZATION_BACKUP=""
AUTHORIZATION_MANIFEST=""
HOST_PORT=""
CONTAINER_NAME=""
COMPOSE_PROJECT_NAME=""
LAST_STATUS=0
failures=0
warnings=0

usage() {
    cat <<'EOF'
Usage: container/scripts/verify/run_deployment_verification.sh \
  --deploy-user USER --database DATABASE --project PROJECT [OPTIONS]

Run the deployment verification checks for a rootless Podman environment on
this host. Checks that need the deployment user's Podman and credential context
run through sudo as that user. Host checks run as the invoking user.

Required options:
  --deploy-user USER          Local deployment user
  --database DATABASE         Release PostgreSQL database
  --project PROJECT           Existing disposable project for endpoint checks

Options:
  --container-dir DIR         Deployment container directory (default: USER home/container)
  --data-dir DIR              Deployment data directory (default: resolved from container/.env)
  --evidence-dir DIR          Local directory for orchestration output
  --base-url URL              Proxy URL for authenticated checks
    --principal-a USER          First principal for authenticated checks
    --principal-b USER          Second principal for authenticated checks
    --project-a NAME            Project first principal can read
    --project-b NAME            Project second principal can read
  --role ROLE                 PostgreSQL role (default: sead_ro)
  --schema SCHEMA             PostgreSQL schema (default: public)
  --since DURATION            Log window (default: 24h)
  --db-log PATH               PostgreSQL log path for log review
  --service-name NAME         User systemd service (default: shape-shifter)
  --authenticated             Run the interactive authenticated-access check
  --rollback                   Run the state-changing rollback exercise
  --rollback-image IMAGE       Recorded image for --rollback
  --authorization-backup FILE Backup for --rollback
  --manifest FILE             Authorization manifest for --rollback
  --host-port PORT             Override the deployment host port
  --container-name NAME       Override the container name
  --compose-project NAME      Override the compose project name
  -h, --help                  Show this help message

The authenticated check may prompt for principal passwords. Rollback is never
included unless --rollback is specified and requires all three rollback inputs.
EOF
}

fail() {
    printf 'FAIL: %s\n' "$*" >&2
    exit 2
}

warn() {
    printf 'WARN: %s\n' "$*" >&2
    warnings=$((warnings + 1))
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --deploy-user)          [[ $# -ge 2 ]] || fail "--deploy-user requires a value"; DEPLOY_USER="$2"; shift 2 ;;
        --database)             [[ $# -ge 2 ]] || fail "--database requires a value"; DATABASE="$2"; shift 2 ;;
        --project)              [[ $# -ge 2 ]] || fail "--project requires a value"; PROJECT="$2"; shift 2 ;;
        --container-dir)        [[ $# -ge 2 ]] || fail "--container-dir requires a value"; CONTAINER_DIR="$2"; shift 2 ;;
        --data-dir)             [[ $# -ge 2 ]] || fail "--data-dir requires a value"; DATA_DIR="$2"; shift 2 ;;
        --evidence-dir)         [[ $# -ge 2 ]] || fail "--evidence-dir requires a value"; EVIDENCE_DIR="$2"; shift 2 ;;
        --base-url)             [[ $# -ge 2 ]] || fail "--base-url requires a value"; BASE_URL="$2"; shift 2 ;;
        --principal-a)          [[ $# -ge 2 ]] || fail "--principal-a requires a value"; PRINCIPAL_A="$2"; shift 2 ;;
        --principal-b)          [[ $# -ge 2 ]] || fail "--principal-b requires a value"; PRINCIPAL_B="$2"; shift 2 ;;
        --project-a)            [[ $# -ge 2 ]] || fail "--project-a requires a value"; PROJECT_A="$2"; shift 2 ;;
        --project-b)            [[ $# -ge 2 ]] || fail "--project-b requires a value"; PROJECT_B="$2"; shift 2 ;;
        --role)                 [[ $# -ge 2 ]] || fail "--role requires a value"; ROLE="$2"; shift 2 ;;
        --schema)               [[ $# -ge 2 ]] || fail "--schema requires a value"; SCHEMA="$2"; shift 2 ;;
        --since)                [[ $# -ge 2 ]] || fail "--since requires a value"; SINCE="$2"; shift 2 ;;
        --db-log)               [[ $# -ge 2 ]] || fail "--db-log requires a value"; DB_LOG="$2"; shift 2 ;;
        --service-name)         [[ $# -ge 2 ]] || fail "--service-name requires a value"; SERVICE_NAME="$2"; shift 2 ;;
        --authenticated)        RUN_AUTHENTICATED=true; shift ;;
        --rollback)             RUN_ROLLBACK=true; shift ;;
        --rollback-image)       [[ $# -ge 2 ]] || fail "--rollback-image requires a value"; ROLLBACK_IMAGE="$2"; shift 2 ;;
        --authorization-backup) [[ $# -ge 2 ]] || fail "--authorization-backup requires a value"; AUTHORIZATION_BACKUP="$2"; shift 2 ;;
        --manifest)             [[ $# -ge 2 ]] || fail "--manifest requires a value"; AUTHORIZATION_MANIFEST="$2"; shift 2 ;;
        --host-port)            [[ $# -ge 2 ]] || fail "--host-port requires a value"; HOST_PORT="$2"; shift 2 ;;
        --container-name)       [[ $# -ge 2 ]] || fail "--container-name requires a value"; CONTAINER_NAME="$2"; shift 2 ;;
        --compose-project)      [[ $# -ge 2 ]] || fail "--compose-project requires a value"; COMPOSE_PROJECT_NAME="$2"; shift 2 ;;
        -h|--help)              usage; exit 0 ;;
        *)                      fail "unknown option: $1" ;;
    esac
done

[[ -n "$DEPLOY_USER" ]] || { usage >&2; fail "--deploy-user is required"; }
[[ -n "$DATABASE" ]] || { usage >&2; fail "--database is required"; }
[[ -n "$PROJECT" ]] || { usage >&2; fail "--project is required"; }
if [[ "$RUN_ROLLBACK" = true ]]; then
    [[ -n "$ROLLBACK_IMAGE" ]] || fail "--rollback-image is required with --rollback"
    [[ -n "$AUTHORIZATION_BACKUP" ]] || fail "--authorization-backup is required with --rollback"
    [[ -n "$AUTHORIZATION_MANIFEST" ]] || fail "--manifest is required with --rollback"
fi
command -v sudo >/dev/null || fail "sudo is required"
command -v getent >/dev/null || fail "getent is required"

if [[ "$(id -u)" -ne 0 ]]; then
    sudo -v || fail "sudo authentication failed"
fi

user_record="$(getent passwd "$DEPLOY_USER" || true)"
[[ -n "$user_record" ]] || fail "deployment user not found: $DEPLOY_USER"
USER_HOME="$(printf '%s\n' "$user_record" | cut -d: -f6)"
[[ -n "$USER_HOME" && -d "$USER_HOME" ]] || fail "deployment user home not found: $USER_HOME"

CONTAINER_DIR="${CONTAINER_DIR:-$USER_HOME/container}"
[[ -d "$CONTAINER_DIR" ]] || fail "container directory not found: $CONTAINER_DIR"
TARGET_VERIFY_DIR="$CONTAINER_DIR/scripts/verify"
[[ -d "$TARGET_VERIFY_DIR" ]] || fail "verification directory not found: $TARGET_VERIFY_DIR"

target_run() {
    sudo -n -u "$DEPLOY_USER" -H -- "$@"
}

if [[ -z "$DATA_DIR" || -z "$HOST_PORT" || -z "$CONTAINER_NAME" || -z "$COMPOSE_PROJECT_NAME" ]]; then
    # shellcheck disable=SC2016
    mapfile -t target_config < <(
        target_run bash -c '
            set -euo pipefail
            cd -- "$1"
            . scripts/load-env.sh
            printf "%s\n" \
                "${DATA_DIR:-$PWD/../container-data}" \
                "${HOST_PORT:-8012}" \
                "${CONTAINER_NAME:-shape-shifter}" \
                "${COMPOSE_PROJECT_NAME:-shapeshifter}"
        ' _ "$CONTAINER_DIR"
    )
    [[ "${#target_config[@]}" -eq 4 ]] || fail "could not resolve deployment configuration"
    DATA_DIR="${DATA_DIR:-${target_config[0]}}"
    HOST_PORT="${HOST_PORT:-${target_config[1]}}"
    CONTAINER_NAME="${CONTAINER_NAME:-${target_config[2]}}"
    COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-${target_config[3]}}"
fi

if [[ "$DATA_DIR" != /* ]]; then
    DATA_DIR="$CONTAINER_DIR/${DATA_DIR#./}"
fi
[[ -f "$DATA_DIR/backend.env" ]] || fail "backend environment file not found: $DATA_DIR/backend.env"

if [[ -z "$EVIDENCE_DIR" ]]; then
    EVIDENCE_DIR="$PWD/deployment-verification-$(date +%Y%m%d-%H%M%S)"
fi
mkdir -p "$EVIDENCE_DIR"
SUMMARY_FILE="$EVIDENCE_DIR/summary.txt"
: > "$SUMMARY_FILE"

record_result() {
    local name="$1" status="$2" log="$3"
    printf '%-32s %s\n' "$name" "$status" | tee -a "$SUMMARY_FILE"
    if [[ "$status" != PASS* ]]; then
        failures=$((failures + 1))
    fi
    printf 'Evidence: %s\n' "$log"
}

run_target_check() {
    local name="$1" script="$2" log status
    shift 2
    log="$EVIDENCE_DIR/${name}.log"
    printf '\n== %s ==\n' "$name"
    if target_run "$TARGET_VERIFY_DIR/$script" "$@" 2>&1 | tee "$log"; then
        status=0
    else
        status="${PIPESTATUS[0]}"
    fi
    if [[ "$status" -eq 0 ]]; then
        record_result "$name" PASS "$log"
    else
        record_result "$name" "FAIL ($status)" "$log"
    fi
    LAST_STATUS="$status"
    return 0
}

run_host_check() {
    local name="$1" script="$2" log status
    shift 2
    log="$EVIDENCE_DIR/${name}.log"
    printf '\n== %s ==\n' "$name"
    if "$LOCAL_VERIFY_DIR/$script" "$@" 2>&1 | tee "$log"; then
        status=0
    else
        status="${PIPESTATUS[0]}"
    fi
    if [[ "$status" -eq 0 ]]; then
        record_result "$name" PASS "$log"
    else
        record_result "$name" "FAIL ($status)" "$log"
    fi
    return 0
}

printf 'Deployment verification for %s\n' "$DEPLOY_USER" | tee "$SUMMARY_FILE"
printf 'Container: %s\nData: %s\nPort: %s\nEvidence: %s\n' \
    "$CONTAINER_DIR" "$DATA_DIR" "$HOST_PORT" "$EVIDENCE_DIR" | tee -a "$SUMMARY_FILE"

run_host_check firewall verify_firewall.sh "$HOST_PORT"
run_target_check container-config verify_container_config.sh
run_target_check postgres-grants verify_postgres_grants.sh \
    --database "$DATABASE" --role "$ROLE" --schema "$SCHEMA" \
    --sqlite "$DATA_DIR/state/authorization.sqlite3"
run_target_check credential-rotation verify_credential_rotation.sh
run_target_check endpoint-containment verify_endpoint_containment.sh \
    --base-url "http://127.0.0.1:${HOST_PORT}" --project "$PROJECT"

# Container logs require the target user's rootless Podman context. Host logs
# are collected separately because the target user is not assumed to have sudo.
run_target_check container-logs verify_logs.sh --since "$SINCE" --container-name "$CONTAINER_NAME"
host_log_args=(--since "$SINCE" --container-name "$CONTAINER_NAME")
[[ -n "$DB_LOG" ]] && host_log_args+=(--db-log "$DB_LOG")
run_host_check host-logs verify_logs.sh "${host_log_args[@]}"

if [[ "$RUN_AUTHENTICATED" = true ]]; then
    [[ -n "$BASE_URL" ]] || fail "--base-url is required with --authenticated"
    [[ -n "$PRINCIPAL_A" && -n "$PRINCIPAL_B" ]] || fail "--principal-a and --principal-b are required with --authenticated"
    [[ -n "$PROJECT_A" && -n "$PROJECT_B" ]] || fail "--project-a and --project-b are required with --authenticated"
    auth_args=()
    auth_args+=(--base-url "$BASE_URL")
    auth_args+=(--principal-a "$PRINCIPAL_A")
    auth_args+=(--principal-b "$PRINCIPAL_B")
    auth_args+=(--project-a "$PROJECT_A")
    auth_args+=(--project-b "$PROJECT_B")
    run_target_check authenticated-access verify_authenticated_access.sh "${auth_args[@]}"
else
    warn "authenticated-access skipped; pass --authenticated with PRINCIPAL_A, PRINCIPAL_B, PROJECT_A, and PROJECT_B"
fi

if [[ "$RUN_ROLLBACK" = true ]]; then
    service_was_active=false
    if target_run systemctl --user is-active --quiet "$SERVICE_NAME"; then
        service_was_active=true
        printf '\n== Stopping user service before rollback ==\n'
        target_run systemctl --user stop "$SERVICE_NAME"
    fi

    rollback_evidence="$DATA_DIR/backups/verification-rollback-$(date +%Y%m%d-%H%M%S)"
    rollback_args=(
        --image "$ROLLBACK_IMAGE"
        --authorization-backup "$AUTHORIZATION_BACKUP"
        --manifest "$AUTHORIZATION_MANIFEST"
        --host-port "$HOST_PORT"
        --container-name "$CONTAINER_NAME"
        --evidence-dir "$rollback_evidence"
    )
    run_target_check rollback-exercise rollback_exercise.sh "${rollback_args[@]}"

    rollback_status="$LAST_STATUS"
    if [[ "$service_was_active" = true && "$rollback_status" -eq 0 ]]; then
        printf '\n== Restarting user service ==\n'
        if target_run systemctl --user start "$SERVICE_NAME"; then
            printf 'User service restarted: %s\n' "$SERVICE_NAME"
        else
            warn "rollback passed but user service could not be restarted: $SERVICE_NAME"
        fi
    elif [[ "$service_was_active" = true ]]; then
        warn "user service remains stopped because verification failed"
    fi
else
    printf '\nRollback skipped. Use --rollback only during the approved rollback window.\n'
fi

printf '\n== Summary ==\n'
cat "$SUMMARY_FILE"
printf 'Warnings: %d\nFailures: %d\nEvidence: %s\n' "$warnings" "$failures" "$EVIDENCE_DIR"

if [[ "$failures" -gt 0 ]]; then
    exit 1
fi