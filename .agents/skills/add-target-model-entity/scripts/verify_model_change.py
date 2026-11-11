"""Verify a standard target-model edit and print documentation-ready numbers.

Checks the model specification, recomputes the completeness counts against the
declared source of truth, and can print conformance issue counts for the example
projects whose baselines are pinned in the test suite.

Run from the repository root with the project environment:

    .venv/bin/python .agents/skills/add-target-model-entity/scripts/verify_model_change.py
    .venv/bin/python .agents/skills/add-target-model-entity/scripts/verify_model_change.py --unmapped --conformance
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

import yaml

REPO_ROOT: Path = Path(__file__).resolve().parents[4]
MODEL_PATH: Path = REPO_ROOT / "resources/target_models/sead_standard_model.yml"
COLUMNS_CSV: Path = REPO_ROOT / "docs/investigations/sead-target-model-completeness/columns.csv"
EXAMPLES_DIR: Path = REPO_ROOT / "tests/test_data/examples"

sys.path.insert(0, str(REPO_ROOT))


def is_excluded(table: str) -> bool:
    """Return ``True`` when the completeness surface excludes the table by decision."""
    return table.endswith("colours") or table.endswith("images")


def load_model():
    """Return the parsed standard target model."""
    from src.target_model.models import TargetModel

    raw = yaml.safe_load(MODEL_PATH.read_text(encoding="utf-8"))
    return TargetModel.model_validate(raw)


def export_tables() -> set[str]:
    """Return the exported table names from the declared source of truth."""
    with COLUMNS_CSV.open(newline="", encoding="utf-8") as handle:
        return {row["table_name"] for row in csv.DictReader(handle)}


def report_spec(target_model) -> int:
    """Print spec-validation issues and return the error count."""
    from src.target_model.spec_validator import TargetModelSpecValidator

    issues = TargetModelSpecValidator().validate(target_model)
    print(f"== spec validation ==\n  issues: {len(issues)}")
    for issue in issues:
        print(f"  - {issue.severity} {issue.code} [{issue.entity}] {issue.message}")
    return len([issue for issue in issues if issue.severity == "error"])


def report_counts(target_model, show_unmapped: bool) -> None:
    """Print the completeness counts and the values to paste into the documents."""
    entities = target_model.entities
    target_tables = {spec.target_table for spec in entities.values() if spec.target_table}
    export = export_tables()
    effective = {table for table in export if not is_excluded(table)}
    mapped = target_tables & effective
    unmapped = effective - target_tables
    out_of_source = target_tables - export

    print("\n== completeness counts ==")
    print(f"  model version:                  {target_model.model.version}")
    print(f"  model entities:                 {len(entities)}")
    print(f"  entities with target_table:     {len(target_tables)}")
    print(f"  entities without target_table:  {sorted(name for name, spec in entities.items() if not spec.target_table)}")
    print(f"  exported tables:                {len(export)}")
    print(f"  excluded tables:                {len([table for table in export if is_excluded(table)])}")
    print(f"  effective surface:              {len(effective)}")
    print(f"  mapped:                         {len(mapped)}")
    print(f"  unmapped:                       {len(unmapped)}")
    print(f"  out-of-source:                  {len(out_of_source)}")

    duplicate_targets = Counter(spec.target_table for spec in entities.values() if spec.target_table)
    collisions = {table: count for table, count in duplicate_targets.items() if count > 1}
    print(f"  duplicate target_table values:  {collisions or 'none'}")

    if out_of_source:
        print(f"\n  out-of-source target tables: {sorted(out_of_source)}")
    if show_unmapped:
        print("\n== unmapped tables ==")
        for table in sorted(unmapped):
            print(f"  {table}")


def report_conformance(target_model) -> None:
    """Print conformance issue counts for each loadable example project."""
    from src.model import ShapeShiftProject
    from src.target_model.conformance import TargetModelConformanceValidator

    print("\n== conformance issue counts for example projects ==")
    for project_path in sorted(EXAMPLES_DIR.glob("*.yml")):
        try:
            project = ShapeShiftProject(cfg=yaml.safe_load(project_path.read_text(encoding="utf-8")))
            issues = TargetModelConformanceValidator().validate(target_model, project)
        except Exception as error:  # pylint: disable=broad-except
            print(f"  {project_path.name}: skipped ({type(error).__name__}: {error})")
            continue
        summary = Counter(issue.code for issue in issues)
        rendered = ", ".join(f'"{code}": {count}' for code, count in sorted(summary.items()))
        print(f"  {project_path.name}: {{{rendered}}}")


def main() -> int:
    """Run the verification report."""
    parser = argparse.ArgumentParser(description="Verify a standard target-model edit.")
    parser.add_argument("--unmapped", action="store_true", help="List the unmapped tables")
    parser.add_argument("--conformance", action="store_true", help="Print conformance counts for example projects")
    args = parser.parse_args()

    target_model = load_model()
    errors = report_spec(target_model)
    report_counts(target_model, args.unmapped)
    if args.conformance:
        report_conformance(target_model)

    print(f"\nresult: {'FAIL' if errors else 'OK'}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
