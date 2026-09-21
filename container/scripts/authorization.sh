#!/usr/bin/env bash
# Run authorization administration commands against the deployed container.
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"

# shellcheck source=load-env.sh
. "$SCRIPT_DIR/load-env.sh"

CONTAINER_NAME="${CONTAINER_NAME:-shape-shifter}"
DATA_DIR="${DATA_DIR:-$ROOT_DIR/../container-data}"
BACKUP_DIR="${AUTHORIZATION_BACKUP_DIR:-$DATA_DIR/backups}"
CONTAINER_BACKUP_DIR="/app/backups"
HOST_ACTOR="${AUTHORIZATION_ACTOR:-$(id -un)}"

# The image installs locked dependencies only (uv sync --no-install-project), so
# the [project.scripts] entry points do not exist inside it. Run the same CLI as
# a module instead: the image sets PYTHONPATH=/app and has python on PATH.
CONTAINER_CLI=(python -m backend.app.scripts.authorization)

usage() {
    cat <<'EOF'
Usage: container/scripts/authorization.sh [OPTIONS] COMMAND [ARGUMENTS...]

Run sead-authorization inside the deployed Shape Shifter container.
Authorization commands and their options are passed through unchanged.

Wrapper options:
  --container-name NAME  Container to administer (default: $CONTAINER_NAME)
  --backup-dir DIR       Host directory for authorization backups
  -h, --help             Show this help message

Mutating commands use the deployment host username as the default audit actor;
pass --actor explicitly or set AUTHORIZATION_ACTOR to override it.

Convenience commands:
  backup                 Create a timestamped authorization database backup
  restore BACKUP         Restore a backup after stopping the application and
                         checking the restored database before restarting it
    import-manifest FILE   Import a host-side JSON or YAML manifest into the
                                                 running container
    export-manifest FILE   Export active top-level resources and grants from the
                                                 running container as JSON or YAML

Web users (run on the deployment host):
    The htpasswd username must exactly match the case-sensitive principal ID used
    in authorization grants and administrator configuration.
    sudo htpasswd /etc/nginx/htpasswd/shape-shifter USER       Add or update a user
    sudo cut -d: -f1 /etc/nginx/htpasswd/shape-shifter         List users
    sudo htpasswd -D /etc/nginx/htpasswd/shape-shifter USER    Delete a user

Group membership (run on the proxy host):
    NGINX derives the group header from the authenticated user name and this file.
    One line per member: "USER GROUP[,GROUP...];". Group IDs are case-sensitive and
    must match the IDs used in group grants.
    sudoedit /etc/nginx/authz/groups.d/shape-shifter.conf      Edit membership
    sudo nginx -t && sudo systemctl reload nginx               Apply the change

Examples:
  container/scripts/authorization.sh list-grants --json
  container/scripts/authorization.sh list-audit-events --json
  container/scripts/authorization.sh integrity-check
  container/scripts/authorization.sh backup
  container/scripts/authorization.sh restore authorization-20260916-120000.sqlite3
  container/scripts/authorization.sh grant --resource-type project \
    --locator example --subject-type principal --subject-id user \
    --role viewer --actor operator
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --container-name)
            [[ $# -ge 2 ]] || { echo "--container-name requires a value." >&2; exit 1; }
            CONTAINER_NAME="$2"
            shift 2
            ;;
        --backup-dir)
            [[ $# -ge 2 ]] || { echo "--backup-dir requires a value." >&2; exit 1; }
            BACKUP_DIR="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        --)
            shift
            break
            ;;
        *)
            break
            ;;
    esac
done

command -v podman >/dev/null || { echo "podman is required." >&2; exit 1; }

container_is_running() {
    [[ "$(podman container inspect --format '{{.State.Status}}' "$CONTAINER_NAME" 2>/dev/null || true)" = "running" ]]
}

require_running_container() {
    if ! container_is_running; then
        echo "Container is not running: $CONTAINER_NAME" >&2
        exit 1
    fi
}

run_cli() {
    require_running_container
    local command_name="${1:-}"
    shift || true
    local -a command_args=("$@")
    case "$command_name" in
        grant|revoke|grant-application-role|revoke-application-role)
            local has_actor=false
            local argument
            for argument in "${command_args[@]}"; do
                if [[ "$argument" = "--actor" || "$argument" = --actor=* ]]; then
                    has_actor=true
                    break
                fi
            done
            if [[ "$has_actor" = false ]]; then
                command_args+=(--actor "$HOST_ACTOR")
            fi
            ;;
    esac
    podman exec "$CONTAINER_NAME" "${CONTAINER_CLI[@]}" "$command_name" "${command_args[@]}"
}

backup_database() {
    require_running_container
    mkdir -p "$BACKUP_DIR"
    local backup_name="authorization-$(date +%Y%m%d-%H%M%S).sqlite3"
    podman exec -i "$CONTAINER_NAME" "${CONTAINER_CLI[@]}" backup "$CONTAINER_BACKUP_DIR/$backup_name"
    echo "Authorization backup written to $BACKUP_DIR/$backup_name"
}

restore_database() {
    local backup_name="${1:-}"
    [[ -n "$backup_name" ]] || { echo "restore requires a backup filename." >&2; exit 1; }
    [[ "$backup_name" != */* && "$backup_name" != "." && "$backup_name" != ".." ]] || {
        echo "restore accepts a filename from --backup-dir, not a path." >&2
        exit 1
    }
    [[ -f "$BACKUP_DIR/$backup_name" ]] || { echo "Backup not found: $BACKUP_DIR/$backup_name" >&2; exit 1; }
    [[ "${2:-}" = "" ]] || { echo "restore accepts exactly one backup filename." >&2; exit 1; }
    container_is_running || { echo "Container is not running: $CONTAINER_NAME" >&2; exit 1; }
    local running_image
    running_image="$(podman container inspect --format '{{.Config.Image}}' "$CONTAINER_NAME")"
    [[ -n "$running_image" ]] || { echo "Cannot determine image for: $CONTAINER_NAME" >&2; exit 1; }

    read -r -p "Stop $CONTAINER_NAME and restore $backup_name? [y/N] " confirmation
    [[ "$confirmation" =~ ^[Yy]$ ]] || { echo "Restore cancelled."; exit 0; }

    podman stop "$CONTAINER_NAME"
    if ! podman run --rm \
        --env-file "$DATA_DIR/backend.env" \
        --volume "$DATA_DIR/state:/app/state:rw" \
        --volume "$BACKUP_DIR:$CONTAINER_BACKUP_DIR:rw" \
        "$running_image" "${CONTAINER_CLI[@]}" restore "$CONTAINER_BACKUP_DIR/$backup_name"; then
        echo "Restore failed; $CONTAINER_NAME remains stopped." >&2
        exit 1
    fi

    if ! podman run --rm \
        --env-file "$DATA_DIR/backend.env" \
        --volume "$DATA_DIR/state:/app/state:rw" \
        --volume "$BACKUP_DIR:$CONTAINER_BACKUP_DIR:rw" \
        "$running_image" "${CONTAINER_CLI[@]}" integrity-check; then
        echo "Integrity check failed; $CONTAINER_NAME remains stopped." >&2
        exit 1
    fi

    podman start "$CONTAINER_NAME"
    echo "Authorization database restored and $CONTAINER_NAME restarted."
}

import_manifest() {
    local manifest_path="${1:-}"
    [[ -n "$manifest_path" ]] || { echo "import-manifest requires a manifest path." >&2; exit 1; }
    [[ -f "$manifest_path" ]] || { echo "Manifest not found: $manifest_path" >&2; exit 1; }
    [[ "${2:-}" = "" ]] || { echo "import-manifest accepts exactly one manifest path." >&2; exit 1; }
    require_running_container
    podman exec -i "$CONTAINER_NAME" "${CONTAINER_CLI[@]}" migrate --manifest /dev/stdin < "$manifest_path"
}

export_manifest() {
    local manifest_path="${1:-}"
    [[ -n "$manifest_path" ]] || { echo "export-manifest requires a manifest path." >&2; exit 1; }
    [[ ! -d "$manifest_path" ]] || { echo "Export path must be a file: $manifest_path" >&2; exit 1; }
    [[ "${2:-}" = "" ]] || { echo "export-manifest accepts exactly one manifest path." >&2; exit 1; }
    require_running_container
    local extension="${manifest_path##*.}"
    [[ "$extension" = "$manifest_path" ]] && extension="json"
    local container_manifest_path="/tmp/authorization-export-$$.$extension"
    trap 'podman exec "$CONTAINER_NAME" rm -f "$container_manifest_path" >/dev/null 2>&1 || true' RETURN
    podman exec "$CONTAINER_NAME" "${CONTAINER_CLI[@]}" export-manifest "$container_manifest_path"
    podman cp "$CONTAINER_NAME:$container_manifest_path" "$manifest_path"
}

[[ $# -gt 0 ]] || { usage >&2; exit 1; }

case "$1" in
    backup)
        shift
        [[ $# -eq 0 ]] || { echo "backup does not accept arguments." >&2; exit 1; }
        backup_database
        ;;
    restore)
        shift
        restore_database "$@"
        ;;
    import-manifest)
        shift
        import_manifest "$@"
        ;;
    export-manifest)
        shift
        export_manifest "$@"
        ;;
    *)
        run_cli "$@"
        ;;
esac
