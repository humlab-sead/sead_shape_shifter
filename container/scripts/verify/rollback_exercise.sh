#!/usr/bin/env bash
# Exercise rollback to a recorded image and authorization database backup.
set -Eeuo pipefail

g_script_dir="$(CDPATH='' cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
g_container_dir="$(CDPATH='' cd -- "$g_script_dir/../.." && pwd)"

# shellcheck source=../load-env.sh
# shellcheck disable=SC1091
. "$g_container_dir/scripts/load-env.sh"

g_container_name="${CONTAINER_NAME:-shape-shifter}"
g_compose_project_name="${COMPOSE_PROJECT_NAME:-shapeshifter}"
g_config_dir="${CONFIG_DIR:-$g_container_dir/../config}"
g_data_dir="${DATA_DIR:-$g_container_dir/../container-data}"
g_backup_dir="${AUTHORIZATION_BACKUP_DIR:-$g_data_dir/backups}"
g_host_port="${HOST_PORT:-8012}"
g_evidence_dir=""
g_image=""
g_authorization_backup=""
g_manifest=""
g_confirmed=false
g_expected_image_id=""
# The image installs dependencies only, so the [project.scripts] entry points do
# not exist inside it. Run the same CLI as a module: the image sets
# PYTHONPATH=/app and has python on PATH.
g_container_cli=(python -m backend.app.scripts.authorization)

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

Runtime configuration is read from CONFIG_DIR/backend.env and mutable data and
state from DATA_DIR. Both default to the home-root siblings config and
container-data, and can be overridden with CONFIG_DIR and DATA_DIR.
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
            g_image="$2"
            shift 2
            ;;
        --authorization-backup)
            [[ $# -ge 2 ]] || fail "--authorization-backup requires a value"
            g_authorization_backup="$2"
            shift 2
            ;;
        --manifest)
            [[ $# -ge 2 ]] || fail "--manifest requires a value"
            g_manifest="$2"
            shift 2
            ;;
        --backup-dir)
            [[ $# -ge 2 ]] || fail "--backup-dir requires a value"
            g_backup_dir="$2"
            shift 2
            ;;
        --evidence-dir)
            [[ $# -ge 2 ]] || fail "--evidence-dir requires a value"
            g_evidence_dir="$2"
            shift 2
            ;;
        --container-name)
            [[ $# -ge 2 ]] || fail "--container-name requires a value"
            g_container_name="$2"
            shift 2
            ;;
        --host-port)
            [[ $# -ge 2 ]] || fail "--host-port requires a value"
            g_host_port="$2"
            shift 2
            ;;
        --yes)
            g_confirmed=true
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

[[ -n "$g_image" ]] || { usage >&2; fail "--image is required"; }
[[ -n "$g_authorization_backup" ]] || { usage >&2; fail "--authorization-backup is required"; }
[[ -n "$g_manifest" ]] || { usage >&2; fail "--manifest is required"; }
command -v podman >/dev/null || fail "podman is required"
command -v podman-compose >/dev/null || fail "podman-compose is required"
[[ -f "$g_config_dir/backend.env" ]] || fail "backend environment file not found: $g_config_dir/backend.env"
[[ -f "$g_manifest" ]] || fail "authorization manifest not found: $g_manifest"

if [[ "$g_authorization_backup" = */* ]]; then
    g_backup_path="$g_authorization_backup"
else
    g_backup_path="$g_backup_dir/$g_authorization_backup"
fi
[[ -f "$g_backup_path" ]] || fail "authorization backup not found: $g_backup_path"
[[ -f "$g_manifest" ]] || fail "authorization manifest not found: $g_manifest"
g_backup_path="$(CDPATH='' cd -- "$(dirname -- "$g_backup_path")" && pwd)/$(basename -- "$g_backup_path")"
g_manifest="$(CDPATH='' cd -- "$(dirname -- "$g_manifest")" && pwd)/$(basename -- "$g_manifest")"

if [[ -z "$g_evidence_dir" ]]; then
    g_evidence_dir="$g_data_dir/backups/rollback-$(date +%Y%m%d-%H%M%S)"
fi
mkdir -p "$g_evidence_dir"
g_evidence_log="$g_evidence_dir/rollback-exercise.log"
exec > >(tee -a "$g_evidence_log") 2>&1

printf 'Rollback exercise started: %s\n' "$(date --iso-8601=seconds)"
printf 'Container: %s\nImage: %s\nBackup: %s\nManifest: %s\n' \
    "$g_container_name" "$g_image" "$g_backup_path" "$g_manifest"

container_state() {
    podman container inspect --format '{{.State.Status}}' "$g_container_name" 2>/dev/null || true
}

record_image_identity() {
    printf '\n== Recorded image identity ==\n'
    podman image exists "$g_image" || fail "recorded image is not available locally: $g_image"
    g_expected_image_id="$(podman image inspect --format '{{.Id}}' "$g_image")"
    podman image inspect --format \
        'Image={{.Id}}\nRepoDigests={{.RepoDigests}}\nLabels={{json .Config.Labels}}' "$g_image"
}

compose_down() {
    CONFIG_DIR="$g_config_dir" CONTAINER_DATA_DIR="$g_data_dir" HOST_PORT="$g_host_port" IMAGE_NAME="$g_image" \
        podman-compose -f "$g_container_dir/podman-compose.yml" \
        -p "$g_compose_project_name" down
}

compose_up() {
    CONFIG_DIR="$g_config_dir" CONTAINER_DATA_DIR="$g_data_dir" HOST_PORT="$g_host_port" IMAGE_NAME="$g_image" \
        podman-compose -f "$g_container_dir/podman-compose.yml" \
    -p "$g_compose_project_name" up -d --no-build
}

run_admin() {
    podman run --rm \
        --user 0 \
        --workdir /app \
        --env-file "$g_config_dir/backend.env" \
        --volume "$g_data_dir/state:/app/state:rw" \
        "$g_image" "${g_container_cli[@]}" "$@"
}

run_restore() {
    podman run --rm \
        --user 0 \
        --workdir /app \
        --env-file "$g_config_dir/backend.env" \
        --volume "$g_data_dir/state:/app/state:rw" \
        --volume "$g_backup_path:/app/rollback-backup:ro" \
    "$g_image" sh -c \
    'cp /app/rollback-backup /tmp/rollback.sqlite3 && python -m backend.app.scripts.authorization restore /tmp/rollback.sqlite3'
}

run_reconcile() {
    podman run --rm \
        --user 0 \
        --workdir /app \
        --env-file "$g_config_dir/backend.env" \
        --volume "$g_data_dir/state:/app/state:rw" \
        --volume "$g_manifest:/app/rollback-manifest:ro" \
        "$g_image" "${g_container_cli[@]}" reconcile /app/rollback-manifest
}

wait_for_health() {
    local health_url="http://127.0.0.1:${g_host_port}/api/v1/health"
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

# Report the failing command, then the state needed to diagnose the rollback.
# Diagnostic only: the exit status and the evidence path behaviour are unchanged.
on_error() {
    local status="$1" source_file="$2" line="$3" failed_command="$4"
    printf '\nCommand failed: %s:%s: %s (exit %s)\n' "$source_file" "$line" "$failed_command" "$status" >&2
    printf 'Rollback exercise failed with exit status %d.\n' "$status" >&2
    printf 'Service state: %s\n' "$(container_state)" >&2
    printf 'Evidence: %s\n' "$g_evidence_dir" >&2
    exit "$status"
}
trap 'on_error $? "${BASH_SOURCE[0]}" "$LINENO" "${BASH_COMMAND%% *}"' ERR

if [[ "$g_confirmed" = false ]]; then
    read -r -p "Stop $g_container_name and restore the recorded rollback state? [y/N] " confirmation
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
actual_image_id="$(podman container inspect --format '{{.Image}}' "$g_container_name")"
printf 'Running image ID: %s\n' "$actual_image_id"
[[ "$actual_image_id" = "$g_expected_image_id" ]] || fail "running image does not match the recorded image"
printf 'Container state: %s\n' "$(container_state)"
[[ "$(container_state)" = running ]] || fail "container is not running after rollback"

printf '\nRollback exercise passed. Evidence: %s\n' "$g_evidence_dir"