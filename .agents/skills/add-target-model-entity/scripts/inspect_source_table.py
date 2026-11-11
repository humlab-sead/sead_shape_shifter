"""Report what a standard target-model entity needs for one SEAD source table.

Prints, for a named table: the columns in the declared source of truth, the
declared primary-key and unique constraints, whether the model already covers the
table, which modeled entities reference its columns without declaring a foreign
key, and a draft entity definition.

Run from the repository root with the project environment:

    .venv/bin/python .agents/skills/add-target-model-entity/scripts/inspect_source_table.py tbl_record_types
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

import yaml

REPO_ROOT: Path = Path(__file__).resolve().parents[4]
COLUMNS_CSV: Path = REPO_ROOT / "docs/investigations/sead-target-model-completeness/columns.csv"
CONSTRAINTS_SQL: Path = REPO_ROOT / "docs/sead/05_constraints.sql"
MODEL_PATH: Path = REPO_ROOT / "resources/target_models/sead_standard_model.yml"

TYPE_MAP: dict[str, str] = {
    "integer": "integer",
    "bigint": "integer",
    "smallint": "integer",
    "character varying": "string",
    "text": "string",
    "character": "string",
    "numeric": "decimal",
    "double precision": "decimal",
    "real": "decimal",
    "boolean": "boolean",
    "date": "date",
    "timestamp with time zone": "string",
    "timestamp without time zone": "string",
    "time without time zone": "string",
    "uuid": "uuid",
    "numrange": "numrange",
}
"""Maps a PostgreSQL data type from the export to a target-model column type."""


def load_source_columns(table: str) -> list[dict[str, str]]:
    """Return the exported columns for one table, in ordinal order."""
    with COLUMNS_CSV.open(newline="", encoding="utf-8") as handle:
        rows = [row for row in csv.DictReader(handle) if row["table_name"] == table]
    if not rows:
        raise SystemExit(f"Table '{table}' is not in {COLUMNS_CSV.relative_to(REPO_ROOT)}. Check the name and the file.")
    return sorted(rows, key=lambda row: int(row["ordinal_position"]))


def load_unique_constraints(table: str) -> list[str]:
    """Return primary-key and unique constraint lines that name the table."""
    if not CONSTRAINTS_SQL.exists():
        return []
    pattern = re.compile(r"constraint\s+\S+\s+(primary key|unique)\s*\(([^)]+)\)", re.IGNORECASE)
    found: list[str] = []
    block_table = ""
    for raw_line in CONSTRAINTS_SQL.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        table_match = re.search(r"alter table only public\.(\w+)", line, re.IGNORECASE)
        if table_match:
            block_table = table_match.group(1)
            continue
        if block_table != table:
            continue
        constraint_match = pattern.search(line)
        if constraint_match:
            columns = ", ".join(part.strip() for part in constraint_match.group(2).split(","))
            found.append(f"{constraint_match.group(1).lower()}: {columns}")
    return list(dict.fromkeys(found))


def load_model_entities() -> dict[str, dict]:
    """Return the raw entity definitions from the standard target model."""
    return yaml.safe_load(MODEL_PATH.read_text(encoding="utf-8"))["entities"]


def report_referring_tables(table: str, entities: dict[str, dict]) -> list[tuple[str, str, list[str], bool]]:
    """Return source tables that point at ``table`` with the modeled owner and FK state.

    Each entry is ``(source_table, entity_name, declared_columns, fk_declared)``.
    ``entity_name`` is empty when no entity maps the referring table.
    """
    columns_by_table: dict[str, list[dict[str, str]]] = {}
    with COLUMNS_CSV.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            columns_by_table.setdefault(row["table_name"], []).append(row)

    owners_by_table: dict[str, list[str]] = {}
    for entity_name, spec in entities.items():
        target_table = spec.get("target_table")
        if target_table:
            owners_by_table.setdefault(target_table, []).append(entity_name)

    entity_name_for_table = (owners_by_table.get(table) or [""])[0]

    findings: list[tuple[str, str, list[str], bool]] = []
    for source_table in sorted(columns_by_table):
        referencing = [row for row in columns_by_table[source_table] if row["is_fk"] == "YES" and row["fk_table_name"] == table]
        if not referencing or source_table == table:
            continue
        for referrer in referencing:
            column_name = referrer["column_name"]
            for owner in owners_by_table.get(source_table) or [""]:
                if not owner:
                    findings.append((source_table, "", [column_name], False))
                    continue
                spec = entities[owner]
                declared = column_name in (spec.get("columns") or {})
                fk_declared = any(fk.get("entity") == entity_name_for_table for fk in (spec.get("foreign_keys") or []))
                findings.append((source_table, owner, [column_name] if declared else [], fk_declared))
    return findings


def describe_entity_coverage(table: str, columns: list[dict[str, str]], entities: dict[str, dict]) -> list[str]:
    """Return a description of the model's current coverage of the table."""
    lines: list[str] = []
    owning = [name for name, spec in entities.items() if spec.get("target_table") == table]
    source_names = {row["column_name"] for row in columns}

    if not owning:
        lines.append(f"No entity declares target_table: {table} (this table is a coverage gap).")
        return lines

    for entity_name in owning:
        spec = entities[entity_name]
        declared = set((spec.get("columns") or {}))
        public_id = spec.get("public_id")
        fk_targets = [fk.get("entity") for fk in (spec.get("foreign_keys") or [])]
        lines.append(f"Mapped by entity '{entity_name}' (role={spec.get('role')}, public_id={public_id}).")
        lines.append(f"  Declared foreign keys: {fk_targets or 'none'}")
        missing = sorted(source_names - declared - ({public_id} if public_id else set()))
        extra = sorted(declared - source_names)
        if missing:
            lines.append(f"  Source columns NOT declared by the entity: {missing}")
        if extra:
            lines.append(f"  Declared columns NOT in the source table: {extra}")
        if not missing and not extra:
            lines.append("  Declared columns match the source table (public_id excluded).")
    return lines


def draft_entity(entity_name: str, table: str, columns: list[dict[str, str]], role: str, domain: str, description: str) -> str:
    """Return a draft YAML entity definition built from the source columns."""
    primary_keys = [row for row in columns if row["is_pk"] == "YES"]
    public_id = f"{primary_keys[0]['column_name']}" if primary_keys else f"{entity_name}_id"

    spec: dict[str, object] = {
        "role": role,
        "required": False,
        "description": description,
        "domains": [domain],
        "target_table": table,
        "public_id": public_id,
    }
    declared: dict[str, dict[str, object]] = {}
    references: list[dict[str, object]] = []
    for row in columns:
        name = row["column_name"]
        if name == public_id:
            continue
        column: dict[str, object] = {}
        if row["is_nullable"] == "NO":
            column["required"] = True
        column["type"] = TYPE_MAP.get(row["data_type"], "string")
        column["nullable"] = row["is_nullable"] != "NO"
        declared[name] = column
        if row["is_fk"] == "YES":
            target_entity = row["fk_table_name"]
            references.append({"entity": f"# map {target_entity}", "required": row["is_nullable"] == "NO"})
    spec["columns"] = declared
    if references:
        spec["foreign_keys"] = references
    return yaml.dump({entity_name: spec}, sort_keys=False, default_flow_style=False, width=140)


def main() -> int:
    """Print the inspection report for the requested table."""
    parser = argparse.ArgumentParser(description="Inspect a SEAD source table for target-model modelling.")
    parser.add_argument("table", help="Source table name, for example tbl_record_types")
    parser.add_argument("--entity", help="Entity name to use in the draft definition")
    parser.add_argument("--role", default="classifier", help="Draft role: fact, lookup, classifier, or bridge")
    parser.add_argument("--domain", default="core", help="Draft domain, for example core or abundance")
    parser.add_argument("--description", default="TODO: describe this vocabulary or fact table.", help="Draft description")
    parser.add_argument("--skeleton", action="store_true", help="Print a draft entity definition")
    args = parser.parse_args()

    table = args.table if args.table.startswith("tbl_") else f"tbl_{args.table}"
    columns = load_source_columns(table)
    entities = load_model_entities()

    print(f"== {table} ==")
    print(f"columns: {len(columns)}")
    for row in columns:
        flags = []
        if row["is_pk"] == "YES":
            flags.append("PK")
        if row["is_fk"] == "YES":
            flags.append(f"FK->{row['fk_table_name']}.{row['fk_column_name']}")
        if row["is_nullable"] == "NO":
            flags.append("NOT NULL")
        length = f"({row['character_maximum_length']})" if row["character_maximum_length"] not in ("", "NULL") else ""
        print(f"  {row['column_name']:<32} {row['data_type']}{length:<20} {' '.join(flags)}")

    print("\n== declared constraints ==")
    constraints = load_unique_constraints(table)
    print("\n".join(f"  {line}" for line in constraints) if constraints else "  none found in docs/sead/05_constraints.sql")

    print("\n== model coverage ==")
    coverage = describe_entity_coverage(table, columns, entities)
    print("\n".join(f"  {line}" for line in coverage))

    print("\n== source tables that reference this table ==")
    covered_entity = next((name for name, spec in entities.items() if spec.get("target_table") == table), "")
    if covered_entity:
        print(f"  modelled as entity '{covered_entity}'")
    else:
        print("  not modelled yet; a new entity and these foreign keys are needed")
    referring = report_referring_tables(table, entities)
    if not referring:
        print("  no exported table declares a foreign key to it")
    for source_table, owner, declared, fk_declared in referring:
        if not owner:
            print(f"  {source_table}: no modeled entity covers this table (gap)")
            continue
        column_note = f"column {declared[0]} declared" if declared else "FK column NOT declared"
        fk_note = "FK declared" if fk_declared else "**FK NOT declared**"
        print(f"  {source_table} -> entity '{owner}': {column_note}, {fk_note}")

    if args.skeleton:
        entity_name = args.entity or table.removeprefix("tbl_").rstrip("s")
        print("\n== draft entity (review before use) ==")
        print(draft_entity(entity_name, table, columns, args.role, args.domain, args.description))

    return 0


if __name__ == "__main__":
    sys.exit(main())
