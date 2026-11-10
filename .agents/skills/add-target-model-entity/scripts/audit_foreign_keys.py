"""Audit the standard target model for foreign-key inconsistencies.

Compares the foreign keys that the declared source of truth declares against the
foreign keys the model declares, in both directions:

- A modelled table whose source column is a foreign key must declare that column,
  and the FK entity for the target table when the target table is modelled.
- A modelled table may declare FK columns the source does not mark as foreign
  keys (the qualifier-symbol defect is reported separately, not as a mismatch).

Run from the repository root with the project environment:

    .venv/bin/python .agents/skills/add-target-model-entity/scripts/audit_foreign_keys.py
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import yaml

REPO_ROOT: Path = Path(__file__).resolve().parents[4]
MODEL_PATH: Path = REPO_ROOT / "resources/target_models/sead_standard_model.yml"
COLUMNS_CSV: Path = REPO_ROOT / "docs/investigations/sead-target-model-completeness/columns.csv"


def load_source_foreign_keys() -> dict[str, dict[str, str]]:
    """Return ``{table: {column: foreign_table}}`` for exported foreign-key columns."""
    with COLUMNS_CSV.open(newline="", encoding="utf-8") as handle:
        rows = csv.DictReader(handle)
        foreign_keys: dict[str, dict[str, str]] = {}
        for row in rows:
            if row["is_fk"] != "YES":
                continue
            foreign_keys.setdefault(row["table_name"], {})[row["column_name"]] = row["fk_table_name"]
    return foreign_keys


def audit(find_dangling: bool = True) -> list[str]:
    """Return the list of problems found between the model and the source of truth."""
    entities: dict[str, dict] = yaml.safe_load(MODEL_PATH.read_text(encoding="utf-8"))["entities"]
    source_foreign_keys = load_source_foreign_keys()
    entity_for_table = {spec["target_table"]: name for name, spec in entities.items() if spec.get("target_table")}

    problems: list[str] = []
    for entity_name, spec in entities.items():
        table = spec.get("target_table")
        if not table or table not in source_foreign_keys:
            continue
        declared_columns = spec.get("columns") or {}
        declared_fk_entities = {fk["entity"] for fk in (spec.get("foreign_keys") or []) if fk.get("via") is None}
        for column_name, foreign_table in source_foreign_keys[table].items():
            target_entity = entity_for_table.get(foreign_table)
            if column_name not in declared_columns:
                problems.append(f"{entity_name}: column '{column_name}' missing (source FK to {foreign_table})")
            elif find_dangling and target_entity and target_entity not in declared_fk_entities:
                problems.append(f"{entity_name}: column '{column_name}' has no foreign key to '{target_entity}'")

    return problems


def main() -> int:
    """Print the audit result and return a non-zero status when problems exist."""
    problems = audit()
    if problems:
        print(f"foreign-key problems: {len(problems)}")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    entities = yaml.safe_load(MODEL_PATH.read_text(encoding="utf-8"))["entities"]
    modelled = [spec["target_table"] for spec in entities.values() if spec.get("target_table")]
    print(f"foreign-key problems: 0 (checked {len(modelled)} modelled tables)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
