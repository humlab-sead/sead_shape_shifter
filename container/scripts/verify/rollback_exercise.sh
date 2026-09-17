#!/usr/bin/env bash
# Exercise rollback to a recorded image and authorization database backup.
set -Eeuo pipefail

SCRIPT_DIR="$(CDPATH='' cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
CONTAINER_DIR="$(CDPATH='' cd -- "$SCRIPT_DIR/../.." && pwd)"

# shellcheck source=../load-env.sh
# shellcheck disable=SC1091
. "$CONTAINER_DIR/scripts/load-env.sh"

CONTAINER_NAME="${CONTAINER_NAME:-shape-shifter}"
COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-shapeshifter}"
DATA_DIR="${DATA_DIR:-$CONTAINER_DIR/../container-data}"
BACKUP_DIR="${AUTHORIZATION_BACKUP_DIR:-$DATA_DIR/backups}"
HOST_PORT="${HOST_PORT:-8012}"
EVIDENCE_DIR=""
IMAGE=""
AUTHORIZATION_BACKUP=""
MANIFEST=""
CONFIRMED=false
EXPECTED_IMAGE_ID=""

usage() {
    cat <<'EOF'
Usage: container/scripts/verify/rollback_exercise.sh \
  --image IMAGE --authorization-backup FILE --manifest FILE [OPTIONS]

Restore a recorded image and authorization database backup, then verify the
authorization database, manifest reconciliation, image identity, and health.

Required options:
  --image IMAGE                    Recorded Podman image reference or digest
  --authorization-backup FILE      Backup filename or path below the backup dir
  --manifest FILE                  Reviewed authorization manifest

Options:
  --backup-dir DIR                 Host backup directory (default: DATA_DIR/backups)
  --evidence-dir DIR               Directory for the command transcript
  --container-name NAME            Container name (default: shape-shifter)
  --host-port PORT                 Published host port (default: 8012)
  --yes                            Skip the confirmation prompt
  -h, --help                       Show this help message

The service remains stopped when restore, integrity, reconciliation, or startup
verification fails. Run this as the deployment user from container/.
EOF
}

fail() {
    printf 'FAIL: %s\n' "$*" >&2
    exit 1
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --image)
            [[ $# -ge 2 ]] || fail "--image requires a value"
            IMAGE="$2"
            shift 2
            ;;
        --authorization-backup)
            [[ $# -ge 2 ]] || fail "--authorization-backup requires a value"
            AUTHORIZATION_BACKUP="$2"
            shift 2
            ;;
        --manifest)
            [[ $# -ge 2 ]] || fail "--manifest requires a value"
            MANIFEST="$2"
            shift 2
            ;;
        --backup-dir)
            [[ $# -ge 2 ]] || fail "--backup-dir requires a value"
            BACKUP_DIR="$2"
            shift 2
            ;;
        --evidence-dir)
            [[ $# -ge 2 ]] || fail "--evidence-dir requires a value"
            EVIDENCE_DIR="$2"
            shift 2
            ;;
        --container-name)
            [[ $# -ge 2 ]] || fail "--container-name requires a value"
            CONTAINER_NAME="$2"
            shift 2
            ;;
        --host-port)
            [[ $# -ge 2 ]] || fail "--host-port requires a value"
            HOST_PORT="$2"
            shift 2
            ;;
        --yes)
            CONFIRMED=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            fail "unknown argument: $1"
            ;;
    esac
done

[[ -n "$IMAGE" ]] || { usage >&2; fail "--image is required"; }
[[ -n "$AUTHORIZATION_BACKUP" ]] || { usage >&2; fail "--authorization-backup is required"; }
[[ -n "$MANIFEST" ]] || { usage >&2; fail "--manifest is required"; }
command -v podman >/dev/null || fail "podman is required"
command -v podman-compose >/dev/null || fail "podman-compose is required"
[[ -f "$DATA_DIR/backend.env" ]] || fail "backend environment file not found: $DATA_DIR/backend.env"
[[ -f "$MANIFEST" ]] || fail "authorization manifest not found: $MANIFEST"

if [[ "$AUTHORIZATION_BACKUP" = */* ]]; then
    BACKUP_PATH="$AUTHORIZATION_BACKUP"
else
    BACKUP_PATH="$BACKUP_DIR/$AUTHORIZATION_BACKUP"
fi
[[ -f "$BACKUP_PATH" ]] || fail "authorization backup not found: $BACKUP_PATH"
[[ -f "$MANIFEST" ]] || fail "authorization manifest not found: $MANIFEST"
BACKUP_PATH="$(CDPATH='' cd -- "$(dirname -- "$BACKUP_PATH")" && pwd)/$(basename -- "$BACKUP_PATH")"
MANIFEST="$(CDPATH='' cd -- "$(dirname -- "$MANIFEST")" && pwd)/$(basename -- "$MANIFEST")"

if [[ -z "$EVIDENCE_DIR" ]]; then
    EVIDENCE_DIR="$DATA_DIR/backups/rollback-$(date +%Y%m%d-%H%M%S)"
fi
mkdir -p "$EVIDENCE_DIR"
EVIDENCE_LOG="$EVIDENCE_DIR/rollback-exercise.log"
exec > >(tee -a "$EVIDENCE_LOG") 2>&1

printf 'Rollback exercise started: %s\n' "$(date --iso-8601=seconds)"
printf 'Container: %s\nImage: %s\nBackup: %s\nManifest: %s\n' \
    "$CONTAINER_NAME" "$IMAGE" "$BACKUP_PATH" "$MANIFEST"

container_state() {
    podman container inspect --format '{{.State.Status}}' "$CONTAINER_NAME" 2>/dev/null || true
}

record_image_identity() {
    printf '\n== Recorded image identity ==\n'
    podman image exists "$IMAGE" || fail "recorded image is not available locally: $IMAGE"
    EXPECTED_IMAGE_ID="$(podman image inspect --format '{{.Id}}' "$IMAGE")"
    podman image inspect --format \
        'Image={{.Id}}\nRepoDigests={{.RepoDigests}}\nLabels={{json .Config.Labels}}' "$IMAGE"
}

compose_down() {
    CONTAINER_DATA_DIR="$DATA_DIR" HOST_PORT="$HOST_PORT" IMAGE_NAME="$IMAGE" \
        podman-compose -f "$CONTAINER_DIR/podman-compose.yml" \
        -p "$COMPOSE_PROJECT_NAME" down
}

compose_up() {
    CONTAINER_DATA_DIR="$DATA_DIR" HOST_PORT="$HOST_PORT" IMAGE_NAME="$IMAGE" \
        podman-compose -f "$CONTAINER_DIR/podman-compose.yml" \
        -p "$COMPOSE_PROJECT_NAME" up -d
}

run_admin() {
    podman run --rm \
        --env-file "$DATA_DIR/backend.env" \
        --volume "$DATA_DIR/state:/app/state:rw" \
        "$IMAGE" sead-authorization "$@"
}

run_restore() {
    podman run --rm \
        --env-file "$DATA_DIR/backend.env" \
        --volume "$DATA_DIR/state:/app/state:rw" \
        --volume "$BACKUP_PATH:/app/rollback-backup:ro" \
        "$IMAGE" sead-authorization restore /app/rollback-backup
}

run_reconcile() {
    podman run --rm \
        --env-file "$DATA_DIR/backend.env" \
        --volume "$DATA_DIR/state:/app/state:rw" \
        --volume "$MANIFEST:/app/rollback-manifest:ro" \
        "$IMAGE" sead-authorization reconcile /app/rollback-manifest
}

wait_for_health() {
    local health_url="http://127.0.0.1:${HOST_PORT}/api/v1/health"
    local attempts=0
    while (( attempts < 60 )); do
        if curl --fail --silent --show-error "$health_url" >/dev/null; then
            printf 'Health check passed: %s\n' "$health_url"
            return 0
        fi
        sleep 1
        attempts=$((attempts + 1))
    done
    fail "health check timed out: $health_url"
}

on_error() {
    local status=$?
    printf '\nRollback exercise failed with exit status %d.\n' "$status" >&2
    printf 'Service state: %s\n' "$(container_state)" >&2
    printf 'Evidence: %s\n' "$EVIDENCE_DIR" >&2
    exit "$status"
}
trap on_error ERR

if [[ "$CONFIRMED" = false ]]; then
    read -r -p "Stop $CONTAINER_NAME and restore the recorded rollback state? [y/N] " confirmation
    [[ "$confirmation" =~ ^[Yy]$ ]] || { printf 'Rollback exercise cancelled.\n'; exit 0; }
fi

record_image_identity
printf '\n== Stopping current deployment ==\n'
compose_down

printf '\n== Restoring authorization database ==\n'
run_restore

printf '\n== Checking authorization database integrity ==\n'
run_admin integrity-check

printf '\n== Reconciling authorization manifest ==\n'
run_reconcile

printf '\n== Starting recorded image ==\n'
compose_up

printf '\n== Verifying resulting service ==\n'
wait_for_health
actual_image_id="$(podman container inspect --format '{{.Image}}' "$CONTAINER_NAME")"
printf 'Running image ID: %s\n' "$actual_image_id"
[[ "$actual_image_id" = "$EXPECTED_IMAGE_ID" ]] || fail "running image does not match the recorded image"
printf 'Container state: %s\n' "$(container_state)"
[[ "$(container_state)" = running ]] || fail "container is not running after rollback"

printf '\nRollback exercise passed. Evidence: %s\n' "$EVIDENCE_DIR"