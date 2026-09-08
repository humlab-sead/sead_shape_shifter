\set ON_ERROR_STOP on

\if :{?app_role}
\else
    \echo 'Required psql variable: app_role'
    \quit 2
\endif
\if :{?app_schema}
\else
    \echo 'Required psql variable: app_schema'
    \quit 2
\endif

SELECT set_config('shape_shifter.verify_role', :'app_role', false);
SELECT set_config('shape_shifter.verify_schema', :'app_schema', false);

DO $$
DECLARE
    role_oid oid;
    relation_name text;
    app_role text := current_setting('shape_shifter.verify_role');
    app_schema text := current_setting('shape_shifter.verify_schema');
BEGIN
    SELECT oid INTO role_oid FROM pg_roles WHERE rolname = app_role;
    IF role_oid IS NULL THEN
        RAISE EXCEPTION 'Role % does not exist', app_role;
    END IF;

    IF EXISTS (
        SELECT 1 FROM pg_roles
        WHERE rolname = app_role
          AND (rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls OR rolinherit)
    ) THEN
        RAISE EXCEPTION 'Role % has elevated attributes', app_role;
    END IF;

    IF EXISTS (SELECT 1 FROM pg_auth_members WHERE member = role_oid) THEN
        RAISE EXCEPTION 'Role % is a member of another role', app_role;
    END IF;

    IF EXISTS (SELECT 1 FROM pg_database WHERE datdba = role_oid)
       OR EXISTS (SELECT 1 FROM pg_namespace WHERE nspowner = role_oid)
       OR EXISTS (SELECT 1 FROM pg_class WHERE relowner = role_oid)
       OR EXISTS (SELECT 1 FROM pg_proc WHERE proowner = role_oid) THEN
        RAISE EXCEPTION 'Role % owns database objects', app_role;
    END IF;

    IF has_schema_privilege(app_role, app_schema, 'CREATE') THEN
        RAISE EXCEPTION 'Role % can create objects in schema %', app_role, app_schema;
    END IF;

    FOR relation_name IN
        SELECT format('%I.%I', app_schema, c.relname)
        FROM pg_class AS c
        JOIN pg_namespace AS n ON n.oid = c.relnamespace
        WHERE n.nspname = app_schema
          AND c.relkind IN ('r', 'p', 'v', 'm', 'f')
    LOOP
        IF NOT has_table_privilege(app_role, relation_name, 'SELECT') THEN
            RAISE EXCEPTION 'Role % cannot SELECT %', app_role, relation_name;
        END IF;
        IF has_table_privilege('public', relation_name, 'INSERT')
           OR has_table_privilege('public', relation_name, 'UPDATE')
           OR has_table_privilege('public', relation_name, 'DELETE')
           OR has_table_privilege('public', relation_name, 'TRUNCATE')
           OR has_table_privilege('public', relation_name, 'REFERENCES')
           OR has_table_privilege('public', relation_name, 'TRIGGER') THEN
            RAISE EXCEPTION 'Role % inherits write or privilege-management access via PUBLIC on %', app_role, relation_name;
        END IF;
        IF has_table_privilege(app_role, relation_name, 'INSERT')
           OR has_table_privilege(app_role, relation_name, 'UPDATE')
           OR has_table_privilege(app_role, relation_name, 'DELETE')
           OR has_table_privilege(app_role, relation_name, 'TRUNCATE')
           OR has_table_privilege(app_role, relation_name, 'REFERENCES')
           OR has_table_privilege(app_role, relation_name, 'TRIGGER') THEN
            RAISE EXCEPTION 'Role % has write or privilege-management access to %', app_role, relation_name;
        END IF;
    END LOOP;
END
$$;

SELECT rolname, rolsuper, rolinherit, rolcreatedb, rolcreaterole, rolreplication, rolbypassrls
FROM pg_roles
WHERE rolname = current_setting('shape_shifter.verify_role');