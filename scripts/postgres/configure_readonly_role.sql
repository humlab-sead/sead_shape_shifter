\set ON_ERROR_STOP on

\if :{?app_role}
\else
    \echo 'Required psql variable: app_role'
    \quit 2
\endif

\if :{?app_database}
\else
    \echo 'Required psql variable: app_database'
    \quit 2
\endif

\if :{?app_schema}
\else
    \echo 'Required psql variable: app_schema'
    \quit 2
\endif

\if :{?app_owner}
\else
    \echo 'Required psql variable: app_owner'
    \quit 2
\endif

-- Confirm this session is connected to the requested database.
SELECT current_database() = :'app_database' AS connected_to_target
\gset

\if :connected_to_target
\else
    \echo 'Must be connected to database' :app_database
    \quit 2
\endif

BEGIN;

-- Fail if the requested role already exists.
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