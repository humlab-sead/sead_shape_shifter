#!/usr/bin/env bash

set -Eeuo pipefail

usage() {
    cat <<'EOF'
Usage:
  create-readonly-role.sh \
      --role ROLE \
      --database DATABASE \
      --schema SCHEMA \
    [--owner OWNER] \
      [--host HOST] [--port PORT] [--username USER]

Creates a new PostgreSQL login role with SELECT access to all current tables
in SCHEMA and to future tables created there by OWNER. If OWNER is omitted,
the script uses the owner of the public schema.

The command fails if ROLE already exists. Authentication is handled by psql;
use ~/.pgpass, PGPASSFILE, PGPASSWORD, or an interactive password prompt.

The `app_owner` is the PostgreSQL role that creates new tables in the target
database. The script uses that role as the source for ALTER DEFAULT
PRIVILEGES, so future tables created by that owner automatically grant SELECT
to `app_role`.

EOF
}

die() {
    printf 'Error: %s\n' "$*" >&2
    exit 2
}

app_role=''
app_database=''
app_schema=''
app_owner=''
pg_host=''
pg_port=''
pg_username=''

while (( $# > 0 )); do
    case "$1" in
        -r|--role)
            (( $# >= 2 )) || die "$1 requires a value"
            app_role=$2
            shift 2
            ;;
        -d|--database)
            (( $# >= 2 )) || die "$1 requires a value"
            app_database=$2
            shift 2
            ;;
        -s|--schema)
            (( $# >= 2 )) || die "$1 requires a value"
            app_schema=$2
            shift 2
            ;;
        -o|--owner)
            (( $# >= 2 )) || die "$1 requires a value"
            app_owner=$2
            shift 2
            ;;
        -h|--host)
            (( $# >= 2 )) || die "$1 requires a value"
            pg_host=$2
            shift 2
            ;;
        -p|--port)
            (( $# >= 2 )) || die "$1 requires a value"
            pg_port=$2
            shift 2
            ;;
        -U|--username)
            (( $# >= 2 )) || die "$1 requires a value"
            pg_username=$2
            shift 2
            ;;
        --help)
            usage
            exit 0
            ;;
        --)
            shift
            (( $# == 0 )) || die "unexpected positional arguments: $*"
            ;;
        -*)
            die "unknown option: $1"
            ;;
        *)
            die "unexpected positional argument: $1"
            ;;
    esac
done

[[ -n $app_role ]]     || die '--role is required'
[[ -n $app_database ]] || die '--database is required'
[[ -n $app_schema ]]   || die '--schema is required'

command -v psql >/dev/null 2>&1 || die 'psql was not found in PATH'

psql_connection=()
[[ -z $pg_host ]]     || psql_connection+=(--host="$pg_host")
[[ -z $pg_port ]]     || psql_connection+=(--port="$pg_port")
[[ -z $pg_username ]] || psql_connection+=(--username="$pg_username")

if [[ -z $app_owner ]]; then
    app_owner=$(
        psql \
            --no-psqlrc \
            --set=ON_ERROR_STOP=1 \
            "${psql_connection[@]}" \
            --dbname="$app_database" \
            --tuples-only \
            --no-align \
            --quiet \
            --set=app_schema=public <<'SQL'
SELECT pg_get_userbyid(nspowner)
FROM pg_namespace
WHERE nspname = :'app_schema';
SQL
    )

    [[ -n $app_owner ]] || die 'could not determine owner of schema public'
fi

psql \
    --no-psqlrc \
    --set=ON_ERROR_STOP=1 \
    "${psql_connection[@]}" \
    --dbname="$app_database" \
    --set=app_role="$app_role" \
    --set=app_database="$app_database" \
    --set=app_schema="$app_schema" \
    --set=app_owner="$app_owner" <<'SQL'

SELECT current_database() = :'app_database' AS connected_to_target
\gset

\if :connected_to_target
\else
    \echo 'Must be connected to database' :app_database
    \quit 2
\endif

BEGIN;

-- Deliberately fails if this cluster-wide role already exists.
CREATE ROLE :"app_role"
    LOGIN
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOINHERIT
    NOREPLICATION
    NOBYPASSRLS;

GRANT CONNECT
    ON DATABASE :"app_database"
    TO :"app_role";

GRANT USAGE
    ON SCHEMA :"app_schema"
    TO :"app_role";

GRANT SELECT
    ON ALL TABLES IN SCHEMA :"app_schema"
    TO :"app_role";

ALTER DEFAULT PRIVILEGES
    FOR ROLE :"app_owner"
    IN SCHEMA :"app_schema"
    GRANT SELECT ON TABLES TO :"app_role";

COMMIT;

\echo 'Created read-only role' :app_role 'for database' :app_database 'and schema' :app_schema
SQL
