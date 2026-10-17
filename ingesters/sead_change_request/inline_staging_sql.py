"""Transactional inline staging SQL for deployment-time ID allocation.

The renderer produces one statement per list element, so the artifact can be
executed statement by statement. The deploy body runs in one transaction that:

1. verifies every staged target relation, ID column, and ID generator against the
   supported contract;
2. locks the sorted union of child-allocation and SIMS sequence-synchronization
   tables in ``SHARE ROW EXCLUSIVE`` mode;
3. loads staged rows into ``ON COMMIT DROP`` temporary tables that keep local
   identifiers and local foreign keys beside the target columns;
4. synchronizes stale sequences, allocates one ID per pending child row, and
   records every local-to-target mapping in one table;
5. resolves foreign keys and checks complete ``unique_sets`` against staged and
   target rows;
6. inserts target rows in dependency order and advances SIMS-synchronized
   sequences.

No target row is written before the checks succeed.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from ingesters.sead_change_request.contracts import ChangeRequestPackage, ChangeRequestTable, ChangeRowState
from ingesters.sead_change_request.sql_rendering import (
    quote_identifier,
    quote_qualified_relation,
    quote_string,
    render_literal,
    renderable_columns,
)
from src.target_model.insert_dependencies import build_insert_plan
from src.target_model.models import EntitySpec, TargetModel

STAGING_TABLE_PREFIX = "_shape_shifter_stage_"
ID_MAP_TABLE = "_shape_shifter_id_map"
LOCAL_ID_COLUMN = "_local_system_id"
LOCAL_FK_PREFIX = "_local_"

SUPPORT_BLOCK = "shape_shifter_staging_support"
SEQUENCE_SYNC_BLOCK = "shape_shifter_staging_sequence_sync"
ID_MAP_BLOCK = "shape_shifter_staging_id_map"
FOREIGN_KEY_BLOCK = "shape_shifter_staging_foreign_keys"
UNIQUE_SET_BLOCK = "shape_shifter_staging_unique_sets"
INSERT_BLOCK = "shape_shifter_staging_inserts"

PENDING_ROW_STATES: frozenset[ChangeRowState] = frozenset({ChangeRowState.PENDING_DEPLOYMENT_ID})
ALLOCATED_ROW_STATES: frozenset[ChangeRowState] = frozenset({ChangeRowState.NEWLY_ALLOCATED_ENTITY})


@dataclass(frozen=True, slots=True)
class StagedEntityPlan:
    """Rendering facts for one staged entity."""

    entity_name: str
    spec: EntitySpec
    table: ChangeRequestTable
    qualified_relation: str
    load_columns: tuple[str, ...]
    insert_columns: tuple[str, ...]
    foreign_key_columns: tuple[str, ...]
    available_columns: frozenset[str]
    pending_rows: tuple[object, ...]
    loads_public_id: bool
    allocates_public_id: bool

    @property
    def writes_public_id(self) -> bool:
        """Return ``True`` when the insert must supply the identity column."""
        return self.loads_public_id or self.allocates_public_id

    @property
    def staging_relation(self) -> str:
        """Return the quoted temporary relation name."""
        return quote_identifier(STAGING_TABLE_PREFIX + self.entity_name)

    @property
    def local_fk_columns(self) -> tuple[str, ...]:
        """Return the staging-only local foreign key column names."""
        return tuple(f"{LOCAL_FK_PREFIX}{column}" for column in self.foreign_key_columns)

    @property
    def public_id(self) -> str:
        """Return the target identity column name."""
        return str(self.spec.public_id)


def render_inline_staging_deploy(
    change_package: ChangeRequestPackage,
    target_model: TargetModel,
    target_schema: str,
) -> list[str]:
    """Return the ordered statements for one inline staging deployment."""
    plans = _build_entity_plans(change_package, target_model, target_schema)
    if not plans:
        return []

    insert_order = _resolve_insert_order(plans, target_model)
    statements: list[str] = []
    statements.extend(_render_support_check(plans))
    statements.extend(_render_table_locks(plans))
    for plan in plans:
        statements.extend(_render_create_staging_table(plan))
        statements.append(_render_load_staging_rows(plan))
    statements.append(_render_id_map_table())
    statements.extend(_render_known_id_mappings(change_package))
    for plan in plans:
        if plan.pending_rows:
            statements.append(_render_sequence_sync_block(plan))
    for plan in plans:
        if plan.pending_rows:
            statements.append(_render_allocate_pending_ids(plan))
    statements.append(_render_id_map_integrity_check())
    for plan in plans:
        if plan.pending_rows:
            statements.append(_render_apply_allocated_ids(plan))
    for plan in plans:
        statements.extend(_render_resolve_foreign_keys(plan, target_model))
    for plan in plans:
        required_check = _render_required_foreign_key_check(plan, target_model)
        if required_check is not None:
            statements.append(required_check)
    for plan in plans:
        statements.extend(_render_unique_set_checks(plan))
    for plan in insert_order:
        statements.append(_render_target_insert(plan))
    for plan in plans:
        if plan.spec.synchronize_sequence_after_insert and plan.loads_public_id:
            statements.append(_render_sequence_sync_block(plan))
    return statements


def _block(lines: list[str]) -> str:
    """Join the lines of one SQL statement."""
    return "\n".join(lines)


def _build_entity_plans(
    change_package: ChangeRequestPackage,
    target_model: TargetModel,
    target_schema: str,
) -> list[StagedEntityPlan]:
    """Return one rendering plan per staged entity."""
    plans: list[StagedEntityPlan] = []
    for entity_name in sorted(change_package.tables):
        table = change_package.tables[entity_name]
        spec = target_model.entities.get(entity_name)
        if spec is None or not spec.target_table or not spec.public_id:
            raise ValueError(f"Entity '{entity_name}' needs target_table and public_id metadata for inline staging")

        pending_rows = tuple(table.frame.index[table.row_states.isin(PENDING_ROW_STATES)])
        foreign_key_columns = _foreign_key_columns(spec, target_model, table)
        excluded = set(foreign_key_columns) | {spec.public_id}

        plans.append(
            StagedEntityPlan(
                entity_name=entity_name,
                spec=spec,
                table=table,
                qualified_relation=quote_qualified_relation(target_schema, spec.target_table),
                load_columns=tuple(renderable_columns(table.frame, excluded)),
                insert_columns=tuple(renderable_columns(table.frame, {spec.public_id})),
                foreign_key_columns=tuple(sorted(foreign_key_columns)),
                available_columns=frozenset(renderable_columns(table.frame, set())),
                pending_rows=pending_rows,
                loads_public_id=bool(table.row_states.isin(ALLOCATED_ROW_STATES).any()),
                allocates_public_id=bool(pending_rows),
            )
        )
    return plans


def _foreign_key_columns(spec: EntitySpec, target_model: TargetModel, table: ChangeRequestTable) -> set[str]:
    """Return staged columns that hold local parent references."""
    columns: set[str] = set()
    for foreign_key in spec.foreign_keys:
        remote_spec = target_model.entities.get(foreign_key.entity)
        if remote_spec is None or not remote_spec.public_id:
            continue
        if remote_spec.public_id in table.frame.columns:
            columns.add(remote_spec.public_id)
    return columns


def _resolve_insert_order(plans: list[StagedEntityPlan], target_model: TargetModel) -> list[StagedEntityPlan]:
    """Return the plans in dependency order, rejecting selected insert cycles."""
    plan_by_entity = {plan.entity_name: plan for plan in plans}
    present_optional: list[tuple[str, str]] = []
    for plan in plans:
        for foreign_key in plan.spec.foreign_keys:
            if foreign_key.required or foreign_key.via is not None:
                continue
            remote_spec = target_model.entities.get(foreign_key.entity)
            if remote_spec is None or not remote_spec.public_id or foreign_key.entity not in plan_by_entity:
                continue
            if remote_spec.public_id in plan.foreign_key_columns:
                present_optional.append((plan.entity_name, foreign_key.entity))

    insert_plan = build_insert_plan(target_model, plan_by_entity, present_optional_foreign_keys=present_optional)
    if insert_plan.cycles:
        rendered_cycles = "; ".join(" -> ".join(cycle) for cycle in insert_plan.cycles)
        raise ValueError(f"Staged insert dependency cycle detected: {rendered_cycles}")
    return [plan_by_entity[entity_name] for entity_name in insert_plan.order]


def _render_support_check(plans: list[StagedEntityPlan]) -> list[str]:
    """Return a block that rejects unsupported relations, columns, or generators."""
    values = ",\n                ".join(
        f"({quote_string(plan.entity_name)}, {quote_string(plan.qualified_relation)}, {quote_string(plan.public_id)})" for plan in plans
    )
    lines = [
        f"DO ${SUPPORT_BLOCK}$",
        "DECLARE",
        "    target_entity text;",
        "    target_relation text;",
        "    target_column text;",
        "    target_sequence text;",
        "    sequence_increment bigint;",
        "    sequence_cycles boolean;",
        "    sequence_cache bigint;",
        "    insert_trigger text;",
        "BEGIN",
        "    FOR target_entity, target_relation, target_column IN",
        f"        SELECT * FROM (VALUES {values}) AS targets(entity, relation, column_name)",
        "    LOOP",
        "        IF to_regclass(target_relation) IS NULL THEN",
        "            RAISE EXCEPTION 'Staged relation % does not exist', target_relation;",
        "        END IF;",
        "        IF NOT EXISTS (",
        "            SELECT 1 FROM pg_attribute",
        "            WHERE attrelid = target_relation::regclass AND attname = target_column",
        "              AND attnum > 0 AND NOT attisdropped",
        "        ) THEN",
        "            RAISE EXCEPTION 'Staged target column %.% does not exist', target_relation, target_column;",
        "        END IF;",
        "        target_sequence := pg_get_serial_sequence(target_relation, target_column);",
        "        IF target_sequence IS NULL THEN",
        "            RAISE EXCEPTION 'No ID generator is associated with %.%', target_relation, target_column;",
        "        END IF;",
        "        SELECT seqincrement, seqcycle, seqcache INTO sequence_increment, sequence_cycles, sequence_cache",
        "        FROM pg_sequence WHERE seqrelid = target_sequence::regclass;",
        "        IF sequence_increment IS NULL OR sequence_increment <= 0 THEN",
        "            RAISE EXCEPTION 'Sequence % for %.% must use a positive increment',",
        "                target_sequence, target_relation, target_column;",
        "        END IF;",
        "        IF sequence_cycles THEN",
        "            RAISE EXCEPTION 'Sequence % for %.% must not cycle', target_sequence, target_relation, target_column;",
        "        END IF;",
        "        IF sequence_cache > 1 THEN",
        "            RAISE EXCEPTION 'Sequence % for %.% must use CACHE 1', target_sequence, target_relation, target_column;",
        "        END IF;",
        "        SELECT trigger_row.tgname INTO insert_trigger FROM pg_trigger AS trigger_row",
        "        WHERE trigger_row.tgrelid = target_relation::regclass AND NOT trigger_row.tgisinternal",
        "          AND trigger_row.tgenabled IN ('O', 'A', 'R') AND (trigger_row.tgtype & 4) <> 0",
        "        LIMIT 1;",
        "        IF insert_trigger IS NOT NULL THEN",
        "            RAISE EXCEPTION 'Staged relation % has an enabled INSERT trigger %; support is not confirmed',",
        "                target_relation, insert_trigger;",
        "        END IF;",
        "    END LOOP;",
        "END",
        f"${SUPPORT_BLOCK}$;",
    ]
    return [_block(lines)]


def _render_table_locks(plans: list[StagedEntityPlan]) -> list[str]:
    """Return sorted table locks covering allocation and SIMS synchronization targets."""
    lock_targets: set[str] = {plan.qualified_relation for plan in plans if plan.pending_rows or plan.spec.synchronize_sequence_after_insert}
    return [f"LOCK TABLE {relation} IN SHARE ROW EXCLUSIVE MODE;" for relation in sorted(lock_targets)]


def _render_create_staging_table(plan: StagedEntityPlan) -> list[str]:
    """Return statements that create one empty staging table shaped like the target."""
    statements = [
        f"CREATE TEMP TABLE {plan.staging_relation} ON COMMIT DROP AS SELECT * FROM {plan.qualified_relation} WITH NO DATA;",
        f"ALTER TABLE {plan.staging_relation} ADD COLUMN {quote_identifier(LOCAL_ID_COLUMN)} bigint;",
    ]
    statements.extend(
        f"ALTER TABLE {plan.staging_relation} ADD COLUMN {quote_identifier(column)} bigint;" for column in plan.local_fk_columns
    )
    return statements


def _render_load_staging_rows(plan: StagedEntityPlan) -> str:
    """Return one INSERT that loads the staged rows with local identifiers.

    A known identity is loaded with the row. A pending identity is left out and
    filled from the allocation map, and a default-generated identity stays out so
    the target default applies.
    """
    loaded_columns = list(plan.load_columns)
    if plan.loads_public_id:
        loaded_columns.append(plan.public_id)
    column_names = [*loaded_columns, LOCAL_ID_COLUMN, *plan.local_fk_columns]
    identifiers = ", ".join(quote_identifier(column) for column in column_names)

    value_rows: list[str] = []
    for row_index in plan.table.frame.index:
        row_values = [render_literal(plan.table.frame.at[row_index, column]) for column in loaded_columns]
        row_values.append(render_literal(_local_key(plan.table.frame, row_index)))
        row_values.extend(render_literal(plan.table.frame.at[row_index, column]) for column in plan.foreign_key_columns)
        value_rows.append("(" + ", ".join(row_values) + ")")

    values = ",\n".join(value_rows)
    return f"INSERT INTO {plan.staging_relation} ({identifiers}) VALUES\n{values};"


def _render_id_map_table() -> str:
    """Return the statement that creates the local-to-target mapping table."""
    return (
        f"CREATE TEMP TABLE {quote_identifier(ID_MAP_TABLE)} "
        "(entity_name text NOT NULL, local_system_id bigint NOT NULL, target_id bigint NOT NULL) ON COMMIT DROP;"
    )


def _render_known_id_mappings(change_package: ChangeRequestPackage) -> list[str]:
    """Return the INSERT that seeds the map with known target IDs."""
    mappings = change_package.known_id_mappings
    if not mappings:
        return []

    value_rows = ", ".join(f"({quote_string(mapping.entity_name)}, {mapping.system_id}, {mapping.target_id})" for mapping in mappings)
    return [f"INSERT INTO {quote_identifier(ID_MAP_TABLE)} (entity_name, local_system_id, target_id) VALUES {value_rows};"]


def _render_sequence_sync_block(plan: StagedEntityPlan) -> str:
    """Return a block that advances a stale sequence past the highest existing ID."""
    lines = [
        f"DO ${SEQUENCE_SYNC_BLOCK}_{plan.entity_name}$",
        "DECLARE",
        f"    target_relation regclass := {quote_string(plan.qualified_relation)}::regclass;",
        f"    target_column text := {quote_string(plan.public_id)};",
        "    target_sequence text;",
        "    sequence_value bigint;",
        "    table_max_id bigint;",
        "BEGIN",
        "    target_sequence := pg_get_serial_sequence(target_relation::text, target_column);",
        "    IF target_sequence IS NULL THEN",
        "        RAISE EXCEPTION 'No PostgreSQL sequence is associated with %.%', target_relation, target_column;",
        "    END IF;",
        "    EXECUTE format('SELECT last_value FROM %s', target_sequence::regclass) INTO sequence_value;",
        "    EXECUTE format('SELECT COALESCE(MAX(%I), 0) FROM %s', target_column, target_relation) INTO table_max_id;",
        "    IF sequence_value <= table_max_id THEN",
        "        PERFORM setval(target_sequence::regclass, table_max_id, true);",
        "    END IF;",
        "END",
        f"${SEQUENCE_SYNC_BLOCK}_{plan.entity_name}$;",
    ]
    return _block(lines)


def _render_allocate_pending_ids(plan: StagedEntityPlan) -> str:
    """Return the statement that allocates one target ID per pending child row."""
    lines = [
        f"INSERT INTO {quote_identifier(ID_MAP_TABLE)} (entity_name, local_system_id, target_id)",
        f"SELECT {quote_string(plan.entity_name)}, {quote_identifier(LOCAL_ID_COLUMN)},",
        f"       nextval(pg_get_serial_sequence({quote_string(plan.qualified_relation)}, {quote_string(plan.public_id)}))",
        f"FROM {plan.staging_relation}",
        f"ORDER BY {quote_identifier(LOCAL_ID_COLUMN)};",
    ]
    return _block(lines)


def _render_id_map_integrity_check() -> str:
    """Return a block that rejects duplicate or conflicting local mappings."""
    id_map = quote_identifier(ID_MAP_TABLE)
    lines = [
        f"DO ${ID_MAP_BLOCK}$",
        "BEGIN",
        "    IF EXISTS (",
        "        SELECT 1 FROM (",
        "            SELECT entity_name, local_system_id, count(*) AS row_count, count(DISTINCT target_id) AS target_count",
        f"            FROM {id_map}",
        "            GROUP BY entity_name, local_system_id",
        "        ) AS grouped",
        "        WHERE grouped.row_count > 1 OR grouped.target_count > 1",
        "    ) THEN",
        "        RAISE EXCEPTION 'Staged local identity maps to more than one target ID';",
        "    END IF;",
        "END",
        f"${ID_MAP_BLOCK}$;",
    ]
    return _block(lines)


def _render_apply_allocated_ids(plan: StagedEntityPlan) -> str:
    """Return the statement that copies allocated IDs into the staging table."""
    lines = [
        f"UPDATE {plan.staging_relation} AS staged SET {quote_identifier(plan.public_id)} = mapped.target_id",
        f"FROM {quote_identifier(ID_MAP_TABLE)} AS mapped",
        f"WHERE mapped.entity_name = {quote_string(plan.entity_name)}",
        f"  AND mapped.local_system_id = staged.{quote_identifier(LOCAL_ID_COLUMN)};",
    ]
    return _block(lines)


def _render_resolve_foreign_keys(plan: StagedEntityPlan, target_model: TargetModel) -> list[str]:
    """Return statements that resolve local parent references to target IDs."""
    statements: list[str] = []
    for column in plan.foreign_key_columns:
        remote_entity = _remote_entity_for_column(plan.spec, target_model, column)
        if remote_entity is None:
            continue
        statements.append(
            _block(
                [
                    f"UPDATE {plan.staging_relation} AS staged SET {quote_identifier(column)} = mapped.target_id",
                    f"FROM {quote_identifier(ID_MAP_TABLE)} AS mapped",
                    f"WHERE mapped.entity_name = {quote_string(remote_entity)}",
                    f"  AND mapped.local_system_id = staged.{quote_identifier(LOCAL_FK_PREFIX + column)};",
                ]
            )
        )
    return statements


def _render_required_foreign_key_check(plan: StagedEntityPlan, target_model: TargetModel) -> str | None:
    """Return a block that rejects unresolved required foreign keys."""
    required_columns = _required_foreign_key_columns(plan, target_model)
    if not required_columns:
        return None

    lines = [f"DO ${FOREIGN_KEY_BLOCK}_{plan.entity_name}$", "BEGIN"]
    for column in required_columns:
        lines.extend(
            [
                f"    IF EXISTS (SELECT 1 FROM {plan.staging_relation} WHERE {quote_identifier(column)} IS NULL) THEN",
                "        RAISE EXCEPTION 'Staged rows for % have an unresolved required foreign key %',",
                f"            {quote_string(plan.entity_name)}, {quote_string(column)};",
                "    END IF;",
            ]
        )
    lines.extend(["END", f"${FOREIGN_KEY_BLOCK}_{plan.entity_name}$;"])
    return _block(lines)


def _required_foreign_key_columns(plan: StagedEntityPlan, target_model: TargetModel) -> list[str]:
    """Return required-foreign-key columns that staged rows must resolve."""
    columns: list[str] = []
    for foreign_key in plan.spec.foreign_keys:
        remote_spec = target_model.entities.get(foreign_key.entity)
        if remote_spec is None or not remote_spec.public_id or remote_spec.public_id not in plan.foreign_key_columns:
            continue
        required = foreign_key.required or (
            foreign_key.required_when is not None and foreign_key.required_when.has_new_rows == plan.entity_name
        )
        if required:
            columns.append(remote_spec.public_id)
    return columns


def _render_unique_set_checks(plan: StagedEntityPlan) -> list[str]:
    """Return blocks that reject duplicate complete unique sets."""
    statements: list[str] = []
    for index, unique_set in enumerate(plan.spec.unique_sets):
        if any(column not in plan.available_columns for column in unique_set):
            continue
        statements.append(_render_single_unique_set_check(plan, unique_set, index))
    return statements


def _render_single_unique_set_check(plan: StagedEntityPlan, unique_set: list[str], index: int) -> str:
    """Return one staged-versus-staged and staged-versus-target check."""
    identifiers = ", ".join(quote_identifier(column) for column in unique_set)
    not_null = " AND ".join(f"staged.{quote_identifier(column)} IS NOT NULL" for column in unique_set)
    compare = " AND ".join(f"target.{quote_identifier(column)} = staged.{quote_identifier(column)}" for column in unique_set)
    rendered_set = quote_string(", ".join(unique_set))
    block = f"{UNIQUE_SET_BLOCK}_{plan.entity_name}_{index}"
    lines = [
        f"DO ${block}$",
        "BEGIN",
        "    IF EXISTS (",
        f"        SELECT 1 FROM {plan.staging_relation} AS staged WHERE {not_null}",
        f"        GROUP BY {identifiers} HAVING count(*) > 1",
        "    ) THEN",
        "        RAISE EXCEPTION 'Staged rows for % duplicate unique_set (%)',",
        f"            {quote_string(plan.entity_name)}, {rendered_set};",
        "    END IF;",
        "    IF EXISTS (",
        f"        SELECT 1 FROM {plan.staging_relation} AS staged",
        f"        WHERE {not_null}",
        f"          AND EXISTS (SELECT 1 FROM {plan.qualified_relation} AS target WHERE {compare})",
        "    ) THEN",
        "        RAISE EXCEPTION 'Staged rows for % match an existing target row on unique_set (%)',",
        f"            {quote_string(plan.entity_name)}, {rendered_set};",
        "    END IF;",
        "END",
        f"${block}$;",
    ]
    return _block(lines)


def _render_target_insert(plan: StagedEntityPlan) -> str:
    """Return a block that inserts staged rows into the target table."""
    column_names = list(plan.insert_columns)
    if plan.writes_public_id:
        column_names.append(plan.public_id)
    identifiers = ", ".join(quote_identifier(column) for column in column_names)
    insert_sql = f"INSERT INTO {plan.qualified_relation} ({identifiers})"
    select_sql = f"SELECT {identifiers} FROM {plan.staging_relation} ORDER BY {quote_identifier(LOCAL_ID_COLUMN)}"
    block = f"{INSERT_BLOCK}_{plan.entity_name}"
    lines = [
        f"DO ${block}$",
        "DECLARE",
        "    overriding_clause text := '';",
        f"    insert_prefix text := {quote_string(insert_sql)};",
        f"    insert_query text := {quote_string(select_sql)};",
        "BEGIN",
        f"    IF EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid = {quote_string(plan.qualified_relation)}::regclass",
        f"                 AND attname = {quote_string(plan.public_id)} AND attidentity = 'a') THEN",
        "        overriding_clause := ' OVERRIDING SYSTEM VALUE';",
        "    END IF;",
        "    EXECUTE insert_prefix || overriding_clause || ' ' || insert_query;",
        "END",
        f"${block}$;",
    ]
    return _block(lines)


def _local_key(frame: pd.DataFrame, row_index: object) -> object:
    """Return the local identity of one row, using ``system_id`` or the index."""
    if "system_id" in frame.columns:
        return frame.at[row_index, "system_id"]
    return row_index


def _remote_entity_for_column(spec: EntitySpec, target_model: TargetModel, column: str) -> str | None:
    """Return the entity whose public ID names the given foreign key column."""
    for foreign_key in spec.foreign_keys:
        remote_spec = target_model.entities.get(foreign_key.entity)
        if remote_spec is not None and remote_spec.public_id == column:
            return foreign_key.entity
    return None
