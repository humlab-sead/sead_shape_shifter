#!/usr/bin/env python3
"""Report deployed ID generators for target-model aggregate children.

Derives aggregate children from the target model, resolves each child's target
table to exactly one schema-qualified relation, and reports whether the deployed
ID generator can support deployment-time ID allocation.

The audit is read-only: it opens a ``default_transaction_read_only=on`` session
and never calls ``nextval``. Sequence mutation and lock checks belong on a
disposable clone, not on the inspected database.

Supported means a positive, non-cycling sequence with ``CACHE 1`` and a usable
column default or identity mode. An enabled insert trigger is reported for
manual review because catalog metadata cannot show whether it rewrites IDs.

Exit status is 0 when every candidate is supported. It is 1 when any candidate
is unsupported or needs manual review, so a release check can fail on it.

Examples:
    PGUSER=sead_ro PGDATABASE=sead_staging PGHOST=db.example.test \
        uv run python scripts/review_staging_id_generators.py \
        resources/target_models/sead_standard_model.yml

    uv run python scripts/review_staging_id_generators.py \
        resources/target_models/sead_standard_model.yml --json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import psycopg
import yaml

PROJECT_ROOT: Path = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.target_model.effective_identity import resolve_aggregate_chain  # noqa: E402
from src.target_model.models import TargetModel  # noqa: E402

DEFAULT_MODEL = PROJECT_ROOT / "resources" / "target_models" / "sead_standard_model.yml"

SUPPORTED_STATUS = "supported"
UNSUPPORTED_STATUS = "unsupported"
MANUAL_REVIEW_STATUS = "manual_review"

SUPPORTED_ID_COLUMN_TYPES = frozenset({"smallint", "integer", "bigint"})

RELATION_QUERY = """
SELECT n.nspname, c.relname, c.oid
FROM pg_class AS c
JOIN pg_namespace AS n ON n.oid = c.relnamespace
WHERE c.relname = %s
  AND c.relkind IN ('r', 'p')
  AND n.nspname NOT IN ('pg_catalog', 'information_schema')
  AND n.nspname !~ '^pg_'
  AND (%s::text IS NULL OR n.nspname = %s::text)
ORDER BY n.nspname
"""

COLUMN_QUERY = """
SELECT a.attname,
       format_type(a.atttypid, a.atttypmod) AS data_type,
       a.attidentity,
       pg_get_expr(d.adbin, d.adrelid) AS default_expression
FROM pg_attribute AS a
LEFT JOIN pg_attrdef AS d ON d.adrelid = a.attrelid AND d.adnum = a.attnum
WHERE a.attrelid = %s
  AND a.attname = %s
  AND a.attnum > 0
  AND NOT a.attisdropped
"""

SEQUENCE_QUERY = """
SELECT sq.seqincrement, sq.seqcycle, sq.seqcache
FROM pg_sequence AS sq
WHERE sq.seqrelid = to_regclass(%s)
"""

TRIGGER_QUERY = """
SELECT t.tgname, t.tgenabled
FROM pg_trigger AS t
WHERE t.tgrelid = %s
  AND NOT t.tgisinternal
  AND (t.tgtype & 4) <> 0
ORDER BY t.tgname
"""


@dataclass(frozen=True, slots=True)
class CandidateChild:
    """One aggregate child derived from effective target-model identity."""

    entity: str
    root_entity: str | None
    root_identity_tracking: str | None
    target_table: str
    public_id: str
    chain_issues: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RelationMatch:
    """One target relation that matched the requested table name."""

    schema: str
    name: str
    oid: int

    @property
    def qualified_name(self) -> str:
        """Return ``schema.table`` for reports."""
        return f"{self.schema}.{self.name}"


@dataclass(frozen=True, slots=True)
class IdColumnInfo:
    """Catalog facts about the candidate's ID column."""

    name: str
    data_type: str
    identity_mode: str
    default_expression: str | None


@dataclass(frozen=True, slots=True)
class SequenceInfo:
    """Catalog facts about the sequence behind the ID column."""

    name: str
    increment: int
    cycles: bool
    cache: int


@dataclass(frozen=True, slots=True)
class TriggerInfo:
    """One INSERT trigger declared on the target relation."""

    name: str
    enabled: bool


@dataclass(frozen=True, slots=True)
class RelationCatalog:
    """Catalog facts read for one candidate relation."""

    matches: tuple[RelationMatch, ...] = ()
    column: IdColumnInfo | None = None
    sequence: SequenceInfo | None = None
    insert_triggers: tuple[TriggerInfo, ...] = ()


@dataclass(frozen=True, slots=True)
class GeneratorReport:
    """Generator support result for one aggregate child."""

    entity: str
    root_entity: str | None
    target_table: str
    public_id: str
    relation: str | None
    status: str
    reasons: tuple[str, ...] = ()
    column_type: str | None = None
    identity_mode: str | None = None
    default_expression: str | None = None
    sequence: str | None = None
    cache: int | None = None

    @property
    def is_supported(self) -> bool:
        """Return ``True`` when deployment-time allocation can use this generator."""
        return self.status == SUPPORTED_STATUS


def load_target_model(model_path: Path) -> TargetModel:
    """Read and validate one target-model YAML file."""
    raw = yaml.safe_load(model_path.read_text(encoding="utf-8"))
    return TargetModel.model_validate(raw)


def candidate_children(target_model: TargetModel) -> tuple[CandidateChild, ...]:
    """Return the aggregate children derived from effective identity.

    Only entities that declare an ``aggregate_parent`` are candidates. Entities
    without one are roots or standalone entities. Chain problems are carried on
    the candidate so the report explains why it cannot be enabled.
    """
    candidates: list[CandidateChild] = []
    for entity_name, entity_spec in target_model.entities.items():
        if entity_spec.aggregate_parent is None:
            continue
        chain = resolve_aggregate_chain(target_model, entity_name)
        candidates.append(
            CandidateChild(
                entity=entity_name,
                root_entity=chain.root_entity,
                root_identity_tracking=chain.root_identity_tracking,
                target_table=entity_spec.target_table or "",
                public_id=entity_spec.public_id or "",
                chain_issues=tuple(issue.code for issue in chain.issues),
            )
        )
    return tuple(sorted(candidates, key=lambda candidate: candidate.entity))


def classify_generator(candidate: CandidateChild, catalog: RelationCatalog) -> GeneratorReport:
    """Return the generator support result for one candidate.

    Checks run in a fixed order and stop reporting unsupported reasons for
    details that cannot exist once an earlier check failed.
    """
    if candidate.chain_issues:
        return _unsupported(
            candidate,
            catalog,
            reasons=tuple(f"invalid_aggregate_chain:{code}" for code in candidate.chain_issues),
        )

    if not candidate.target_table:
        return _unsupported(candidate, catalog, reasons=("missing_target_table",))

    if not catalog.matches:
        return _unsupported(candidate, catalog, reasons=("relation_not_found",))

    if len(catalog.matches) > 1:
        matches = ", ".join(match.qualified_name for match in catalog.matches)
        return _unsupported(candidate, catalog, reasons=(f"ambiguous_relation:{matches}",))

    relation = catalog.matches[0]
    column = catalog.column
    if column is None:
        return _unsupported(candidate, catalog, relation=relation.qualified_name, reasons=(f"missing_id_column:{candidate.public_id}",))

    if column.data_type not in SUPPORTED_ID_COLUMN_TYPES:
        return _unsupported(
            candidate,
            catalog,
            relation=relation.qualified_name,
            column=column,
            reasons=(f"unsupported_id_column_type:{column.data_type}",),
        )

    sequence = catalog.sequence
    has_identity = bool(column.identity_mode)
    has_default = column.default_expression is not None

    if not has_identity and not has_default:
        return _unsupported(candidate, catalog, relation=relation.qualified_name, column=column, reasons=("missing_id_generator",))

    if sequence is None:
        return _unsupported(
            candidate,
            catalog,
            relation=relation.qualified_name,
            column=column,
            reasons=("sequence_not_owned",),
        )

    unsupported_reasons: list[str] = []
    if sequence.increment <= 0:
        unsupported_reasons.append(f"non_positive_increment:{sequence.increment}")
    if sequence.cycles:
        unsupported_reasons.append("cycling_sequence")
    if sequence.cache > 1:
        unsupported_reasons.append(f"sequence_cache_above_one:{sequence.cache}")

    if unsupported_reasons:
        return _unsupported(
            candidate,
            catalog,
            relation=relation.qualified_name,
            column=column,
            sequence=sequence,
            reasons=tuple(unsupported_reasons),
        )

    enabled_triggers = tuple(trigger for trigger in catalog.insert_triggers if trigger.enabled)
    if enabled_triggers:
        return GeneratorReport(
            entity=candidate.entity,
            root_entity=candidate.root_entity,
            target_table=candidate.target_table,
            public_id=candidate.public_id,
            relation=relation.qualified_name,
            status=MANUAL_REVIEW_STATUS,
            reasons=tuple(f"enabled_insert_trigger:{trigger.name}" for trigger in enabled_triggers),
            column_type=column.data_type,
            identity_mode=column.identity_mode or None,
            default_expression=column.default_expression,
            sequence=sequence.name,
            cache=sequence.cache,
        )

    return GeneratorReport(
        entity=candidate.entity,
        root_entity=candidate.root_entity,
        target_table=candidate.target_table,
        public_id=candidate.public_id,
        relation=relation.qualified_name,
        status=SUPPORTED_STATUS,
        column_type=column.data_type,
        identity_mode=column.identity_mode or None,
        default_expression=column.default_expression,
        sequence=sequence.name,
        cache=sequence.cache,
    )


def fetch_relation_catalog(
    connection: psycopg.Connection,
    candidate: CandidateChild,
    schema: str | None = None,
) -> RelationCatalog:
    """Read catalog facts for one candidate relation without changing data."""
    if not candidate.target_table:
        return RelationCatalog()

    schema_name, table_name = _split_target_table(candidate.target_table)
    effective_schema = schema_name or schema

    with connection.cursor() as cursor:
        cursor.execute(RELATION_QUERY, (table_name, effective_schema, effective_schema))
        matches = tuple(RelationMatch(schema=row[0], name=row[1], oid=row[2]) for row in cursor.fetchall())
        if len(matches) != 1:
            return RelationCatalog(matches=matches, insert_triggers=_fetch_insert_triggers(cursor, matches))

        relation = matches[0]
        column = _fetch_id_column(cursor, relation, candidate.public_id)
        sequence = _fetch_sequence(cursor, relation, candidate.public_id) if column is not None else None
        triggers = _fetch_insert_triggers(cursor, matches)

    return RelationCatalog(matches=matches, column=column, sequence=sequence, insert_triggers=triggers)


def _fetch_id_column(cursor: psycopg.Cursor, relation: RelationMatch, public_id: str) -> IdColumnInfo | None:
    """Return the ID column facts, or ``None`` when the column is absent."""
    cursor.execute(COLUMN_QUERY, (relation.oid, public_id))
    row = cursor.fetchone()
    if row is None:
        return None
    return IdColumnInfo(name=row[0], data_type=row[1], identity_mode=row[2] or "", default_expression=row[3])


def _fetch_sequence(cursor: psycopg.Cursor, relation: RelationMatch, public_id: str) -> SequenceInfo | None:
    """Return the sequence owned by the ID column, or ``None`` when none is associated."""
    cursor.execute("SELECT pg_get_serial_sequence(%s, %s)", (relation.qualified_name, public_id))
    sequence_name = cursor.fetchone()[0]
    if sequence_name is None:
        return None

    cursor.execute(SEQUENCE_QUERY, (sequence_name,))
    row = cursor.fetchone()
    if row is None:
        return None
    return SequenceInfo(name=sequence_name, increment=row[0], cycles=row[1], cache=row[2])


def _fetch_insert_triggers(cursor: psycopg.Cursor, matches: tuple[RelationMatch, ...]) -> tuple[TriggerInfo, ...]:
    """Return non-internal INSERT triggers for every matched relation."""
    triggers: list[TriggerInfo] = []
    for relation in matches:
        cursor.execute(TRIGGER_QUERY, (relation.oid,))
        triggers.extend(TriggerInfo(name=row[0], enabled=row[1] in ("O", "A", "R")) for row in cursor.fetchall())
    return tuple(triggers)


def _split_target_table(target_table: str) -> tuple[str | None, str]:
    """Split an optional schema qualifier from a target table name."""
    if "." not in target_table:
        return None, target_table
    schema_name, _, table_name = target_table.partition(".")
    return schema_name, table_name


def _unsupported(
    candidate: CandidateChild,
    catalog: RelationCatalog,
    *,
    reasons: tuple[str, ...],
    relation: str | None = None,
    column: IdColumnInfo | None = None,
    sequence: SequenceInfo | None = None,
) -> GeneratorReport:
    """Return an unsupported report with the catalog facts gathered so far."""
    return GeneratorReport(
        entity=candidate.entity,
        root_entity=candidate.root_entity,
        target_table=candidate.target_table,
        public_id=candidate.public_id,
        relation=relation,
        status=UNSUPPORTED_STATUS,
        reasons=reasons,
        column_type=column.data_type if column else None,
        identity_mode=(column.identity_mode or None) if column else None,
        default_expression=column.default_expression if column else None,
        sequence=sequence.name if sequence else None,
        cache=sequence.cache if sequence else None,
    )


def generator_label(report: GeneratorReport) -> str:
    """Return a short label for the deployed generator."""
    if report.identity_mode == "a":
        return "identity-always"
    if report.identity_mode == "d":
        return "identity-by-default"
    if report.sequence:
        return "serial"
    return "none"


def report_rows(reports: Sequence[GeneratorReport]) -> list[dict[str, Any]]:
    """Return JSON-serializable report rows."""
    rows: list[dict[str, Any]] = []
    for report in reports:
        row = asdict(report)
        row["generator"] = generator_label(report)
        rows.append(row)
    return rows


def print_report(reports: Sequence[GeneratorReport], as_json: bool) -> None:
    """Print the report as JSON or as a fixed-width table."""
    if as_json:
        print(json.dumps(report_rows(reports), indent=2))
        return

    header = ("entity", "relation", "generator", "cache", "status", "reasons")
    rows = [
        (
            report.entity,
            report.relation or "-",
            generator_label(report),
            str(report.cache) if report.cache is not None else "-",
            report.status,
            ",".join(report.reasons) or "-",
        )
        for report in reports
    ]
    widths = [max(len(str(row[index])) for row in (header, *rows)) for index in range(len(header))]
    for row in (header, *rows):
        print("  ".join(str(value).ljust(width) for value, width in zip(row, widths)).rstrip())


def run_audit(model: TargetModel, connection: psycopg.Connection, schema: str | None = None) -> tuple[GeneratorReport, ...]:
    """Return generator reports for every derived candidate."""
    candidates = candidate_children(model)
    return tuple(classify_generator(candidate, fetch_relation_catalog(connection, candidate, schema)) for candidate in candidates)


def connect_read_only(host: str | None, port: int | None, dbname: str | None, user: str | None) -> psycopg.Connection:
    """Open a read-only connection, using libpq defaults for omitted values."""
    parameters: dict[str, Any] = {"autocommit": True, "options": "-c default_transaction_read_only=on"}
    for key, value in (("host", host), ("port", port), ("dbname", dbname), ("user", user)):
        if value is not None:
            parameters[key] = value
    return psycopg.connect(**parameters)


def build_argument_parser() -> argparse.ArgumentParser:
    """Return the command-line parser."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("model", nargs="?", type=Path, default=DEFAULT_MODEL, help="Target-model YAML file.")
    parser.add_argument("--schema", help="Only resolve target tables in this schema. Defaults to any non-system schema.")
    parser.add_argument("--host", help="Database host. Defaults to libpq environment.")
    parser.add_argument("--port", type=int, help="Database port. Defaults to libpq environment.")
    parser.add_argument("--dbname", help="Database name. Defaults to libpq environment.")
    parser.add_argument("--user", help="Database user. Use a read-only role.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of a table.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the audit and return a process exit status."""
    arguments = build_argument_parser().parse_args(argv)
    model = load_target_model(arguments.model)

    with connect_read_only(arguments.host, arguments.port, arguments.dbname, arguments.user) as connection:
        reports = run_audit(model, connection, arguments.schema)

    print_report(reports, arguments.json)
    return 0 if all(report.is_supported for report in reports) else 1


if __name__ == "__main__":
    raise SystemExit(main())
