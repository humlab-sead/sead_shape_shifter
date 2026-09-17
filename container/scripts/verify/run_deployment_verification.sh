#!/usr/bin/env bash
# Orchestrate deployment verification checks for a local deployment user.
set -Eeuo pipefail

g_script_dir="$(CDPATH='' cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
g_local_verify_dir="$g_script_dir"
g_options_file=""

g_deploy_user=""
g_container_dir=""
g_data_dir=""
g_evidence_dir=""
g_database=""
g_role="sead_ro"
g_schema="public"
g_project=""
g_base_url=""
g_principal_a="${PRINCIPAL_A:-}"
g_principal_b="${PRINCIPAL_B:-}"
g_project_a="${PROJECT_A:-}"
g_project_b="${PROJECT_B:-}"
g_since="24h"
g_db_log=""
g_service_name="shape-shifter"
g_run_authenticated=false
g_run_rollback=false
g_rollback_image=""
g_authorization_backup=""
g_authorization_manifest=""
g_host_port=""
g_container_name=""
g_compose_project_name=""
g_last_status=0
g_failures=0
g_warnings=0

usage() {
    cat <<'EOF'
Usage: container/scripts/verify/run_deployment_verification.sh \
    --options-file FILE [--deploy-user USER --database DATABASE --project PROJECT] [OPTIONS]

Run the deployment verification checks for a rootless Podman environment on
this host. Checks that need the deployment user's Podman and credential context
run through sudo as that user. Host checks run as the invoking user.

Required options:
    --deploy-user USER          Local deployment user (or options file)
    --database DATABASE         Release PostgreSQL database (or options file)
    --project PROJECT           Existing disposable project (or options file)

Options:
    --options-file FILE         YAML runtime options file
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
    g_warnings=$((g_warnings + 1))
}

command -v yq >/dev/null || fail "yq is required"

# Find the options file before parsing the full CLI so YAML values become
# defaults and every explicit CLI option remains an override.
for argument_index in "$@"; do
    case "$argument_index" in
        --options-file)
            options_file_pending=true
            ;;
        --options-file=*)
            g_options_file="${argument_index#*=}"
            ;;
        *)
            if [[ "${options_file_pending:-false}" = true ]]; then
                g_options_file="$argument_index"
                options_file_pending=false
            fi
            ;;
    esac
done

if [[ -n "$g_options_file" ]]; then
    [[ -f "$g_options_file" ]] || fail "options file not found: $g_options_file"
    yq eval '.' "$g_options_file" >/dev/null || fail "invalid YAML options file: $g_options_file"

    option_value() {
        local path="$1" fallback="$2" value
        value="$(yq eval -r "${path} // \"\"" "$g_options_file")"
        if [[ -n "$value" ]]; then
            printf '%s' "$value"
        else
            printf '%s' "$fallback"
        fi
    }

    g_deploy_user="$(option_value '.deploy_user' "$g_deploy_user")"
    g_container_dir="$(option_value '.container_dir' "$g_container_dir")"
    g_data_dir="$(option_value '.data_dir' "$g_data_dir")"
    g_evidence_dir="$(option_value '.evidence_dir' "$g_evidence_dir")"
    g_database="$(option_value '.database' "$g_database")"
    g_role="$(option_value '.role' "$g_role")"
    g_schema="$(option_value '.schema' "$g_schema")"
    g_project="$(option_value '.project' "$g_project")"
    g_base_url="$(option_value '.base_url' "$g_base_url")"
    g_principal_a="$(option_value '.principal_a' "$g_principal_a")"
    g_principal_b="$(option_value '.principal_b' "$g_principal_b")"
    g_project_a="$(option_value '.project_a' "$g_project_a")"
    g_project_b="$(option_value '.project_b' "$g_project_b")"
    g_since="$(option_value '.since' "$g_since")"
    g_db_log="$(option_value '.db_log' "$g_db_log")"
    g_service_name="$(option_value '.service_name' "$g_service_name")"
    g_rollback_image="$(option_value '.rollback_image' "$g_rollback_image")"
    g_authorization_backup="$(option_value '.authorization_backup' "$g_authorization_backup")"
    g_authorization_manifest="$(option_value '.manifest' "$g_authorization_manifest")"
    g_host_port="$(option_value '.host_port' "$g_host_port")"
    g_container_name="$(option_value '.container_name' "$g_container_name")"
    g_compose_project_name="$(option_value '.compose_project' "$g_compose_project_name")"

    authenticated_value="$(yq eval -r '.authenticated | select(. != null) | tostring' "$g_options_file")"
    rollback_value="$(yq eval -r '.rollback | select(. != null) | tostring' "$g_options_file")"
    [[ -z "$authenticated_value" ]] || g_run_authenticated="$authenticated_value"
    [[ -z "$rollback_value" ]] || g_run_rollback="$rollback_value"
fi

while [[ $# -gt 0 ]]; do
    case "$1" in
        --deploy-user)          [[ $# -ge 2 ]] || fail "--deploy-user requires a value"; g_deploy_user="$2"; shift 2 ;;
        --database)             [[ $# -ge 2 ]] || fail "--database requires a value"; g_database="$2"; shift 2 ;;
        --project)              [[ $# -ge 2 ]] || fail "--project requires a value"; g_project="$2"; shift 2 ;;
        --options-file)         [[ $# -ge 2 ]] || fail "--options-file requires a value"; g_options_file="$2"; shift 2 ;;
        --container-dir)        [[ $# -ge 2 ]] || fail "--container-dir requires a value"; g_container_dir="$2"; shift 2 ;;
        --data-dir)             [[ $# -ge 2 ]] || fail "--data-dir requires a value"; g_data_dir="$2"; shift 2 ;;
        --evidence-dir)         [[ $# -ge 2 ]] || fail "--evidence-dir requires a value"; g_evidence_dir="$2"; shift 2 ;;
        --base-url)             [[ $# -ge 2 ]] || fail "--base-url requires a value"; g_base_url="$2"; shift 2 ;;
        --principal-a)          [[ $# -ge 2 ]] || fail "--principal-a requires a value"; g_principal_a="$2"; shift 2 ;;
        --principal-b)          [[ $# -ge 2 ]] || fail "--principal-b requires a value"; g_principal_b="$2"; shift 2 ;;
        --project-a)            [[ $# -ge 2 ]] || fail "--project-a requires a value"; g_project_a="$2"; shift 2 ;;
        --project-b)            [[ $# -ge 2 ]] || fail "--project-b requires a value"; g_project_b="$2"; shift 2 ;;
        --role)                 [[ $# -ge 2 ]] || fail "--role requires a value"; g_role="$2"; shift 2 ;;
        --schema)               [[ $# -ge 2 ]] || fail "--schema requires a value"; g_schema="$2"; shift 2 ;;
        --since)                [[ $# -ge 2 ]] || fail "--since requires a value"; g_since="$2"; shift 2 ;;
        --db-log)               [[ $# -ge 2 ]] || fail "--db-log requires a value"; g_db_log="$2"; shift 2 ;;
        --service-name)         [[ $# -ge 2 ]] || fail "--service-name requires a value"; g_service_name="$2"; shift 2 ;;
        --authenticated)        g_run_authenticated=true; shift ;;
        --rollback)             g_run_rollback=true; shift ;;
        --rollback-image)       [[ $# -ge 2 ]] || fail "--rollback-image requires a value"; g_rollback_image="$2"; shift 2 ;;
        --authorization-backup) [[ $# -ge 2 ]] || fail "--authorization-backup requires a value"; g_authorization_backup="$2"; shift 2 ;;
        --manifest)             [[ $# -ge 2 ]] || fail "--manifest requires a value"; g_authorization_manifest="$2"; shift 2 ;;
        --host-port)            [[ $# -ge 2 ]] || fail "--host-port requires a value"; g_host_port="$2"; shift 2 ;;
        --container-name)       [[ $# -ge 2 ]] || fail "--container-name requires a value"; g_container_name="$2"; shift 2 ;;
        --compose-project)      [[ $# -ge 2 ]] || fail "--compose-project requires a value"; g_compose_project_name="$2"; shift 2 ;;
        -h|--help)              usage; exit 0 ;;
        *)                      fail "unknown option: $1" ;;
    esac
done

[[ -n "$g_deploy_user" ]] || { usage >&2; fail "--deploy-user is required"; }
[[ -n "$g_database" ]] || { usage >&2; fail "--database is required"; }
[[ -n "$g_project" ]] || { usage >&2; fail "--project is required"; }
if [[ "$g_run_rollback" = true ]]; then
    [[ -n "$g_rollback_image" ]] || fail "--rollback-image is required with --rollback"
    [[ -n "$g_authorization_backup" ]] || fail "--authorization-backup is required with --rollback"
    [[ -n "$g_authorization_manifest" ]] || fail "--manifest is required with --rollback"
fi
command -v sudo >/dev/null || fail "sudo is required"
command -v getent >/dev/null || fail "getent is required"

if [[ "$(id -u)" -ne 0 ]]; then
    sudo -v || fail "sudo authentication failed"
fi

user_record="$(getent passwd "$g_deploy_user" || true)"
[[ -n "$user_record" ]] || fail "deployment user not found: $g_deploy_user"
g_user_home="$(printf '%s\n' "$user_record" | cut -d: -f6)"
[[ -n "$g_user_home" && -d "$g_user_home" ]] || fail "deployment user home not found: $g_user_home"

g_container_dir="${g_container_dir:-$g_user_home/container}"
[[ -d "$g_container_dir" ]] || fail "container directory not found: $g_container_dir"
g_target_verify_dir="$g_container_dir/scripts/verify"
[[ -d "$g_target_verify_dir" ]] || fail "verification directory not found: $g_target_verify_dir"

target_run() {
    sudo -n -u "$g_deploy_user" -H -- "$@"
}

if [[ -z "$g_data_dir" || -z "$g_host_port" || -z "$g_container_name" || -z "$g_compose_project_name" ]]; then
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
        ' _ "$g_container_dir"
    )
    [[ "${#target_config[@]}" -eq 4 ]] || fail "could not resolve deployment configuration"
    g_data_dir="${g_data_dir:-${target_config[0]}}"
    g_host_port="${g_host_port:-${target_config[1]}}"
    g_container_name="${g_container_name:-${target_config[2]}}"
    g_compose_project_name="${g_compose_project_name:-${target_config[3]}}"
fi

if [[ "$g_data_dir" != /* ]]; then
    g_data_dir="$g_container_dir/${g_data_dir#./}"
fi
[[ -f "$g_data_dir/backend.env" ]] || fail "backend environment file not found: $g_data_dir/backend.env"

if [[ -z "$g_evidence_dir" ]]; then
    g_evidence_dir="$PWD/deployment-verification-$(date +%Y%m%d-%H%M%S)"
fi
mkdir -p "$g_evidence_dir"
if [[ -n "$g_options_file" ]]; then
    cp -- "$g_options_file" "$g_evidence_dir/options.yml"
fi
g_summary_file="$g_evidence_dir/summary.txt"
: > "$g_summary_file"

record_result() {
    local name="$1" status="$2" log="$3"
    printf '%-32s %s\n' "$name" "$status" | tee -a "$g_summary_file"
    if [[ "$status" != PASS* ]]; then
        g_failures=$((g_failures + 1))
    fi
    printf 'Evidence: %s\n' "$log"
}

run_target_check() {
    local name="$1" script="$2" log status
    shift 2
    log="$g_evidence_dir/${name}.log"
    printf '\n== %s ==\n' "$name"
    if target_run "$g_target_verify_dir/$script" "$@" 2>&1 | tee "$log"; then
        status=0
    else
        status="${PIPESTATUS[0]}"
    fi
    if [[ "$status" -eq 0 ]]; then
        record_result "$name" PASS "$log"
    else
        record_result "$name" "FAIL ($status)" "$log"
    fi
    g_last_status="$status"
    return 0
}

run_host_check() {
    local name="$1" script="$2" log status
    shift 2
    log="$g_evidence_dir/${name}.log"
    printf '\n== %s ==\n' "$name"
    if "$g_local_verify_dir/$script" "$@" 2>&1 | tee "$log"; then
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

printf 'Deployment verification for %s\n' "$g_deploy_user" | tee "$g_summary_file"
printf 'Container: %s\nData: %s\nPort: %s\nOptions: %s\nEvidence: %s\n' \
    "$g_container_dir" "$g_data_dir" "${g_host_port:-deployment-config}" "${g_options_file:-<cli/defaults>}" "$g_evidence_dir" | tee -a "$g_summary_file"

run_host_check firewall verify_firewall.sh "$g_host_port"
run_target_check container-config verify_container_config.sh
run_target_check postgres-grants verify_postgres_grants.sh \
    --database "$g_database" --role "$g_role" --schema "$g_schema" \
    --sqlite "$g_data_dir/state/authorization.sqlite3"
run_target_check credential-rotation verify_credential_rotation.sh
run_target_check endpoint-containment verify_endpoint_containment.sh \
    --base-url "http://127.0.0.1:${g_host_port}" --project "$g_project"

# Container logs require the target user's rootless Podman context. Host logs
# are collected separately because the target user is not assumed to have sudo.
run_target_check container-logs verify_logs.sh --since "$g_since" --container-name "$g_container_name"
host_log_args=(--since "$g_since" --container-name "$g_container_name")
[[ -n "$g_db_log" ]] && host_log_args+=(--db-log "$g_db_log")
run_host_check host-logs verify_logs.sh "${host_log_args[@]}"

if [[ "$g_run_authenticated" = true ]]; then
    [[ -n "$g_base_url" ]] || fail "--base-url is required with --authenticated"
    [[ -n "$g_principal_a" && -n "$g_principal_b" ]] || fail "--principal-a and --principal-b are required with --authenticated"
    [[ -n "$g_project_a" && -n "$g_project_b" ]] || fail "--project-a and --project-b are required with --authenticated"
    auth_args=()
    auth_args+=(--base-url "$g_base_url")
    auth_args+=(--principal-a "$g_principal_a")
    auth_args+=(--principal-b "$g_principal_b")
    auth_args+=(--project-a "$g_project_a")
    auth_args+=(--project-b "$g_project_b")
    run_target_check authenticated-access verify_authenticated_access.sh "${auth_args[@]}"
else
    warn "authenticated-access skipped; pass --authenticated with PRINCIPAL_A, PRINCIPAL_B, PROJECT_A, and PROJECT_B"
fi

if [[ "$g_run_rollback" = true ]]; then
    service_was_active=false
    if target_run systemctl --user is-active --quiet "$g_service_name"; then
        service_was_active=true
        printf '\n== Stopping user service before rollback ==\n'
        target_run systemctl --user stop "$g_service_name"
    fi

    rollback_evidence="$g_data_dir/backups/verification-rollback-$(date +%Y%m%d-%H%M%S)"
    rollback_args=(
        --image "$g_rollback_image"
        --authorization-backup "$g_authorization_backup"
        --manifest "$g_authorization_manifest"
        --host-port "$g_host_port"
        --container-name "$g_container_name"
        --evidence-dir "$rollback_evidence"
    )
    run_target_check rollback-exercise rollback_exercise.sh "${rollback_args[@]}"

    rollback_status="$g_last_status"
    if [[ "$service_was_active" = true && "$rollback_status" -eq 0 ]]; then
        printf '\n== Restarting user service ==\n'
        if target_run systemctl --user start "$g_service_name"; then
            printf 'User service restarted: %s\n' "$g_service_name"
        else
            warn "rollback passed but user service could not be restarted: $g_service_name"
        fi
    elif [[ "$service_was_active" = true ]]; then
        warn "user service remains stopped because verification failed"
    fi
else
    printf '\nRollback skipped. Use --rollback only during the approved rollback window.\n'
fi

printf '\n== Summary ==\n'
cat "$g_summary_file"
printf 'Warnings: %d\nFailures: %d\nEvidence: %s\n' "$g_warnings" "$g_failures" "$g_evidence_dir"

if [[ "$g_failures" -gt 0 ]]; then
    exit 1
fi