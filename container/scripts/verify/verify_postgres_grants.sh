#!/usr/bin/env bash
# Verify the release host's PostgreSQL read-only grants and the authorization SQLite store.
#
# Two pieces of evidence, matching the handoff check "PostgreSQL grants for the
# release host":
#   1. Catalog queries — runs scripts/postgres/verify_readonly_role.sql against
#      the release database, which fails unless the role can SELECT every table
#      in the schema, has no elevated role attributes, no role memberships, no
#      owned objects, no schema CREATE, and no write or privilege-management
#      access (direct or via PUBLIC).
#   2. File listing — prints the authorization SQLite store location, ownership,
#      and mode, and fails when the mode is not owner-only (600).
#
# The script changes nothing.
#
# Usage:
#   verify_postgres_grants.sh --database DATABASE [--role ROLE] [--schema SCHEMA]
#       [--host HOST] [--port PORT] [--username USER]
#       [--verify-sql PATH] [--sqlite PATH]
#
# Defaults: --role sead_ro, --schema public. The database is required. psql
# authentication uses ~/.pgpass, PGPASSFILE, PGPASSWORD, or an interactive
# prompt, exactly like scripts/postgres/create-readonly-role.sh.
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# shellcheck source=../load-env.sh
if [[ -f "$SCRIPT_DIR/../load-env.sh" ]]; then
    . "$SCRIPT_DIR/../load-env.sh"
fi

app_role="${PG_APP_ROLE:-sead_ro}"
app_database="${PG_APP_DATABASE:-}"
app_schema="${PG_APP_SCHEMA:-public}"
pg_host="${PG_HOST:-}"
pg_port="${PG_PORT:-}"
pg_username="${PG_USERNAME:-}"
verify_sql="${VERIFY_READONLY_SQL:-$ROOT_DIR/scripts/postgres/verify_readonly_role.sql}"
sqlite_path="${AUTHORIZATION_SQLITE_PATH:-}"
failures=0

info() { printf '\n== %s ==\n' "$*"; }
pass() { printf 'PASS  %s\n' "$*"; }
fail() { printf 'FAIL  %s\n' "$*" >&2; failures=$((failures + 1)); }
warn() { printf 'WARN  %s\n' "$*"; }

usage() {
    cat <<EOF
Usage: $(basename -- "$0") --database DATABASE [OPTIONS]

Options:
  --database DATABASE  Release database to verify against (required)
  --role ROLE          Read-only role to verify (default: sead_ro)
  --schema SCHEMA      Schema to verify (default: public)
  --host HOST          PostgreSQL host passed to psql
  --port PORT          PostgreSQL port passed to psql
  --username USER      PostgreSQL user passed to psql
  --verify-sql PATH    Path to verify_readonly_role.sql
  --sqlite PATH        Authorization SQLite store to inspect
  -h, --help           Show this help

Environment:
  PG_APP_DATABASE, PG_APP_ROLE, PG_APP_SCHEMA, PG_HOST, PG_PORT, PG_USERNAME,
  VERIFY_READONLY_SQL, AUTHORIZATION_SQLITE_PATH
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --database) [[ $# -ge 2 ]] || { echo "--database requires a value." >&2; exit 2; }; app_database="$2"; shift 2 ;;
        --role)     [[ $# -ge 2 ]] || { echo "--role requires a value." >&2; exit 2; }; app_role="$2"; shift 2 ;;
        --schema)   [[ $# -ge 2 ]] || { echo "--schema requires a value." >&2; exit 2; }; app_schema="$2"; shift 2 ;;
        --host)     [[ $# -ge 2 ]] || { echo "--host requires a value." >&2; exit 2; }; pg_host="$2"; shift 2 ;;
        --port)     [[ $# -ge 2 ]] || { echo "--port requires a value." >&2; exit 2; }; pg_port="$2"; shift 2 ;;
        --username) [[ $# -ge 2 ]] || { echo "--username requires a value." >&2; exit 2; }; pg_username="$2"; shift 2 ;;
        --verify-sql) [[ $# -ge 2 ]] || { echo "--verify-sql requires a value." >&2; exit 2; }; verify_sql="$2"; shift 2 ;;
        --sqlite)   [[ $# -ge 2 ]] || { echo "--sqlite requires a value." >&2; exit 2; }; sqlite_path="$2"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "unknown option: $1" >&2; usage >&2; exit 2 ;;
    esac
done

[[ -n "$app_database" ]] || fail "database is required (--database or PG_APP_DATABASE)"
command -v psql >/dev/null 2>&1 || fail "psql was not found in PATH"

if [[ -z "$sqlite_path" && -n "${DATA_DIR:-}" ]]; then
    sqlite_path="$DATA_DIR/state/authorization.sqlite3"
fi

info "PostgreSQL read-only role verification"
printf 'Role: %s  Database: %s  Schema: %s\n' "$app_role" "$app_database" "$app_schema"
if [[ -n "$app_database" && -f "$verify_sql" ]]; then
    psql_args=(--no-psqlrc --set=ON_ERROR_STOP=1)
    [[ -z "$pg_host" ]] || psql_args+=(--host="$pg_host")
    [[ -z "$pg_port" ]] || psql_args+=(--port="$pg_port")
    [[ -z "$pg_username" ]] || psql_args+=(--username="$pg_username")
    psql_args+=(--dbname="$app_database" --set=app_role="$app_role" --set=app_schema="$app_schema" --file="$verify_sql")
    if psql "${psql_args[@]}"; then
        pass "role '$app_role' is read-only against schema '$app_schema' in '$app_database'"
    else
        fail "role verification failed"
    fi
elif [[ ! -f "$verify_sql" ]]; then
    fail "verify SQL not found: $verify_sql (pass --verify-sql)"
fi

info "Authorization SQLite store"
if [[ -z "$sqlite_path" ]]; then
    warn "no SQLite store path known; pass --sqlite to inspect it"
elif [[ ! -e "$sqlite_path" ]]; then
    fail "SQLite store not found: $sqlite_path"
else
    stat -c '  path=%n owner=%U(%u):%G(%g) mode=%a size=%s' "$sqlite_path"
    mode="$(stat -c '%a' "$sqlite_path")"
    if [[ "$mode" == "600" ]]; then
        pass "store is owner-only (mode 600)"
    else
        fail "store mode is $mode; expected 600"
    fi
fi

printf '\n'
if [[ "$failures" -gt 0 ]]; then
    printf 'Verification failed with %d issue(s).\n' "$failures" >&2
    exit 1
fi
printf 'PostgreSQL grants and SQLite store verification passed. Record this output with the date and host.\n'
