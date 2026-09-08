#!/usr/bin/env bash

set -Eeuo pipefail

usage() {
    cat <<'EOF'
Usage:
  test-readonly-role.sh \
      --role ROLE \
      --database DATABASE \
      --schema SCHEMA \
      --table TABLE \
      --column COLUMN \
      [--host HOST] [--port PORT] [--username USER]

Verifies that a dedicated PostgreSQL read-only role can read the named table
and cannot perform representative write, schema-change, privilege, role-change,
or file-copy operations.

The command connects as an administrator, switches to ROLE with SET ROLE, and
uses the role's effective privileges for each check. Authentication is handled
by psql; use ~/.pgpass, PGPASSFILE, PGPASSWORD, or an interactive password
prompt.
EOF
}

die() {
    printf 'Error: %s\n' "$*" >&2
    exit 2
}

app_role=''
app_database=''
app_schema=''
app_table=''
app_column=''
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
        -t|--table)
            (( $# >= 2 )) || die "$1 requires a value"
            app_table=$2
            shift 2
            ;;
        -c|--column)
            (( $# >= 2 )) || die "$1 requires a value"
            app_column=$2
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

[[ -n $app_role ]] || die '--role is required'
[[ -n $app_database ]] || die '--database is required'
[[ -n $app_schema ]] || die '--schema is required'
[[ -n $app_table ]] || die '--table is required'
[[ -n $app_column ]] || die '--column is required'

command -v psql >/dev/null 2>&1 || die 'psql was not found in PATH'

psql_connection=()
[[ -z $pg_host ]] || psql_connection+=(--host="$pg_host")
[[ -z $pg_port ]] || psql_connection+=(--port="$pg_port")
[[ -z $pg_username ]] || psql_connection+=(--username="$pg_username")

psql_base=(
    psql
    --no-psqlrc
    --set=ON_ERROR_STOP=1
    "${psql_connection[@]}"
    --dbname="$app_database"
    --set=app_role="$app_role"
    --set=app_schema="$app_schema"
    --set=app_table="$app_table"
    --set=app_column="$app_column"
)

run_psql() {
    "${psql_base[@]}"
}

expect_success() {
    if ! run_psql; then
        die 'Expected success'
    fi
}

expect_failure() {
    if run_psql; then
        die 'Expected failure'
    fi
}

expect_success <<'SQL'
SET SESSION AUTHORIZATION :"app_role";
SELECT current_user = :'app_role' AS running_as_role,
       count(*) AS row_count
FROM :"app_schema".:"app_table";
SQL

expect_failure <<'SQL'
SET SESSION AUTHORIZATION :"app_role";
INSERT INTO :"app_schema".:"app_table" DEFAULT VALUES;
SQL

expect_failure <<'SQL'
SET SESSION AUTHORIZATION :"app_role";
UPDATE :"app_schema".:"app_table"
    SET :"app_column" = :"app_column"
 WHERE false;
SQL

expect_failure <<'SQL'
SET SESSION AUTHORIZATION :"app_role";
DELETE FROM :"app_schema".:"app_table"
 WHERE false;
SQL

expect_failure <<'SQL'
SET SESSION AUTHORIZATION :"app_role";
CREATE TABLE shape_shifter_readonly_role_test(id integer);
SQL

expect_failure <<'SQL'
SET SESSION AUTHORIZATION :"app_role";
CREATE SCHEMA shape_shifter_readonly_role_test;
SQL

expect_failure <<'SQL'
SET SESSION AUTHORIZATION :"app_role";
ALTER ROLE postgres NOCREATEDB;
SQL

expect_failure <<'SQL'
SET SESSION AUTHORIZATION :"app_role";
SET ROLE postgres;
SQL

expect_failure <<'SQL'
SET SESSION AUTHORIZATION :"app_role";
COPY (SELECT 1) TO PROGRAM 'cat > /tmp/shape_shifter_readonly_role_test.csv';
SQL

expect_failure <<'SQL'
SET SESSION AUTHORIZATION :"app_role";
BEGIN;
SET TRANSACTION READ WRITE;
INSERT INTO :"app_schema".:"app_table" DEFAULT VALUES;
COMMIT;
SQL

printf 'Verified read-only role %s against %s.%s.%s\n' "$app_role" "$app_database" "$app_schema" "$app_table"
