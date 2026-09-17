#!/usr/bin/env bash
# Sweep the deployment logs for credentials, connection strings, SQL text, and filesystem paths.
#
# Gathers the container, nginx, and optionally PostgreSQL logs for the release
# window and greps each source for the four banned classes. Matches are printed
# as "source:category: line" candidates; the operator confirms each one and
# records the excerpts. The script prints the exact searches used, reads logs
# only, and exits non-zero when any candidate matches so the review is not missed.
#
# The "user-supplied newlines cannot forge a record" requirement is a code
# property, not a log sweep; see
# docs/proposals/future/LOG_INJECTION_SANITIZATION.md. Until that is fixed, an
# absolute-path match for the application's own startup line
# "Log directory: <path>" is expected and should be recorded as a non-finding.
#
# Usage:
#   verify_logs.sh [--since 24h] [--container-name shape-shifter]
#       [--nginx-access PATH] [--nginx-error PATH] [--db-log PATH]
set -euo pipefail

CONTAINER_NAME="${CONTAINER_NAME:-shape-shifter}"
SINCE="${SINCE:-24h}"
NGINX_ACCESS_LOG="${NGINX_ACCESS_LOG:-/var/log/nginx/access.log}"
NGINX_ERROR_LOG="${NGINX_ERROR_LOG:-/var/log/nginx/error.log}"
DB_LOG="${DB_LOG:-}"

PATTERN_CREDENTIALS='password|passwd|secret|token|api[-_]?key|bearer [a-z0-9._-]+|basic [a-z0-9+/=]+'
PATTERN_CONNECTION='postgres(ql)?://|jdbc:postgresql|mongodb(\+srv)?://|mysql://|://[^[:space:]]*:[^[:space:]]*@'
PATTERN_SQL='\b(select|insert|update|delete|create|drop|alter|grant|revoke|truncate|merge)\b'
PATTERN_PATH='/(app|data|etc|home|root|var|usr|tmp|run)(/|[[:space:]]|$)'

info() { printf '\n== %s ==\n' "$*"; }
warn() { printf 'WARN  %s\n' "$*"; }

usage() {
    cat <<EOF
Usage: $(basename -- "$0") [OPTIONS]

Options:
  --since DURATION      Release window start for podman logs (default: 24h)
  --container-name NAME Container to read logs from (default: shape-shifter)
  --nginx-access PATH   nginx access log (default: /var/log/nginx/access.log)
  --nginx-error PATH    nginx error log (default: /var/log/nginx/error.log)
  --db-log PATH         PostgreSQL server log to sweep (optional)
  -h, --help            Show this help

Environment:
  CONTAINER_NAME, SINCE, NGINX_ACCESS_LOG, NGINX_ERROR_LOG, DB_LOG
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --since)          [[ $# -ge 2 ]] || { echo "--since requires a value." >&2; exit 2; }; SINCE="$2"; shift 2 ;;
        --container-name) [[ $# -ge 2 ]] || { echo "--container-name requires a value." >&2; exit 2; }; CONTAINER_NAME="$2"; shift 2 ;;
        --nginx-access)   [[ $# -ge 2 ]] || { echo "--nginx-access requires a value." >&2; exit 2; }; NGINX_ACCESS_LOG="$2"; shift 2 ;;
        --nginx-error)    [[ $# -ge 2 ]] || { echo "--nginx-error requires a value." >&2; exit 2; }; NGINX_ERROR_LOG="$2"; shift 2 ;;
        --db-log)         [[ $# -ge 2 ]] || { echo "--db-log requires a value." >&2; exit 2; }; DB_LOG="$2"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "unknown option: $1" >&2; usage >&2; exit 2 ;;
    esac
done

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

container_log="$tmpdir/container.log"
nginx_access="$tmpdir/nginx-access.log"
nginx_error="$tmpdir/nginx-error.log"
db_log="$tmpdir/db.log"
results="$tmpdir/results"
: > "$results"

read_log_file() {
    local source="$1" destination="$2"
    if [[ -r "$source" ]]; then
        cat "$source" > "$destination"
    elif sudo -n cat "$source" > "$destination" 2>/dev/null; then
        :
    else
        return 1
    fi
}

collected=0

info "Collecting logs for the last $SINCE"
if podman logs --since "$SINCE" --timestamps "$CONTAINER_NAME" > "$container_log" 2>/dev/null; then
    [[ -s "$container_log" ]] && { collected=$((collected + 1)); printf '  container: %s line(s)\n' "$(wc -l < "$container_log")"; }
else
    warn "could not read container logs (is the container running under this user?)"
fi

for spec in "access|$NGINX_ACCESS_LOG|$nginx_access" "error|$NGINX_ERROR_LOG|$nginx_error"; do
    label="${spec%%|*}"
    rest="${spec#*|}"
    source="${rest%%|*}"
    destination="${rest#*|}"
    if read_log_file "$source" "$destination"; then
        [[ -s "$destination" ]] && { collected=$((collected + 1)); printf '  nginx %s: %s line(s)\n' "$label" "$(wc -l < "$destination")"; }
    else
        warn "could not read nginx $label log: $source (run with sudo to include it)"
    fi
done

if [[ -n "$DB_LOG" ]]; then
    if read_log_file "$DB_LOG" "$db_log"; then
        [[ -s "$db_log" ]] && { collected=$((collected + 1)); printf '  postgres: %s line(s)\n' "$(wc -l < "$db_log")"; }
    else
        warn "could not read PostgreSQL log: $DB_LOG"
    fi
else
    printf '  postgres: skipped (pass --db-log to include it)\n'
fi

[[ "$collected" -gt 0 ]] || warn "no log sources collected; nothing to sweep"

info "Searches used"
printf '  credentials:      %s\n' "$PATTERN_CREDENTIALS"
printf '  connection strings: %s\n' "$PATTERN_CONNECTION"
printf '  SQL statements:  %s\n' "$PATTERN_SQL"
printf '  filesystem paths: %s\n' "$PATTERN_PATH"

info "Candidate matches (review each; record excerpts)"
for file in "$container_log" "$nginx_access" "$nginx_error" "$db_log"; do
    [[ -s "$file" ]] || continue
    base="$(basename "$file")"
    grep -n -E -i "$PATTERN_CREDENTIALS" "$file" 2>/dev/null | sed "s|^|$base:credentials: |" >> "$results" || true
    grep -n -E -i "$PATTERN_CONNECTION" "$file" 2>/dev/null | sed "s|^|$base:connection-string: |" >> "$results" || true
    grep -n -E -i "$PATTERN_SQL" "$file" 2>/dev/null | sed "s|^|$base:sql: |" >> "$results" || true
    grep -n -E "$PATTERN_PATH" "$file" 2>/dev/null | sed "s|^|$base:path: |" >> "$results" || true
done

matches=0
if [[ -s "$results" ]]; then
    matches="$(wc -l < "$results")"
    cat "$results"
fi

printf '\n'
if [[ "$matches" -gt 0 ]]; then
    printf 'Found %s candidate line(s). Confirm each is a non-finding and record the excerpts.\n' "$matches" >&2
    exit 1
fi
printf 'No candidate matches found in %d collected log source(s).\n' "$collected"
