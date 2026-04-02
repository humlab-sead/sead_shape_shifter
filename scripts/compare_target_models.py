#!/usr/bin/env python3
"""Compare conformance validation results between original and extended target models."""

import sys
from pathlib import Path

import yaml

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.model import ShapeShiftProject
from src.target_model.conformance import TargetModelConformanceValidator
from src.target_model.models import TargetModel


def load_yaml(path: Path) -> dict:
    """Load YAML file."""
    with open(path) as f:
        return yaml.safe_load(f)


def load_target_model(path: Path) -> TargetModel:
    """Load and parse target model."""
    data = load_yaml(path)
    return TargetModel.model_validate(data)


def load_project(path: Path) -> ShapeShiftProject:
    """Load ShapeShiftProject from YAML file."""
    cfg = load_yaml(path)
    return ShapeShiftProject(cfg=cfg, filename=str(path))


def validate_project(project: ShapeShiftProject, target_model: TargetModel) -> dict:
    """Run conformance validation and return results."""
    validator = TargetModelConformanceValidator()
    issues = validator.validate(target_model, project)
    
    # Group errors by entity
    entity_errors = {}
    for issue in issues:
        entity = issue.entity or "unknown"
        if entity not in entity_errors:
            entity_errors[entity] = []
        entity_errors[entity].append({
            "code": issue.code,
            "message": issue.message,
            "entity": issue.entity,
        })
    
    return {
        "total_errors": len(issues),
        "entity_count": len(entity_errors),
        "entity_errors": entity_errors,
        "errors": issues,
    }


def print_validation_summary(name: str, results: dict):
    """Print validation results summary."""
    print(f"\n{'=' * 80}")
    print(f"{name}")
    print(f"{'=' * 80}")
    print(f"Total errors: {results['total_errors']}")
    print(f"Entities with errors: {results['entity_count']}")
    
    if results['entity_errors']:
        print("\nErrors by entity:")
        for entity, entity_errors in sorted(results['entity_errors'].items()):
            print(f"  {entity}: {len(entity_errors)} error(s)")
            for err in entity_errors[:3]:  # Show first 3 errors per entity
                print(f"    - {err['message']}")
            if len(entity_errors) > 3:
                print(f"    ... and {len(entity_errors) - 3} more")


def main():
    """Compare conformance validation between original and extended target models."""
    # Paths
    original_model_path = project_root / "target_models" / "specs" / "sead_standard_model.yml"
    extended_model_path = project_root / "target_models" / "specs" / "sead_standard_model.yml"
    arbodat_project_path = project_root / "tests" / "test_data" / "projects" / "arbodat" / "shapeshifter.yml"
    
    # Load models
    print("Loading target models...")
    original_model = load_target_model(original_model_path)
    extended_model = load_target_model(extended_model_path)
    
    print(f"Original model: {original_model.model.name} v{original_model.model.version}")
    print(f"  Entities: {len(original_model.entities)}")
    
    print(f"Extended model: {extended_model.model.name} v{extended_model.model.version}")
    print(f"  Entities: {len(extended_model.entities)}")
    
    # Load project
    print(f"\nLoading Arbodat project...")
    project = load_project(arbodat_project_path)
    print(f"  Project entities: {len(project.entities)}")
    
    # Validate against original model
    print("\nValidating against original target model...")
    original_results = validate_project(project, original_model)
    
    # Validate against extended model
    print("Validating against extended target model...")
    extended_results = validate_project(project, extended_model)
    
    # Print summaries
    print_validation_summary("ORIGINAL MODEL (v2.0.0)", original_results)
    print_validation_summary("EXTENDED MODEL (v2.1.0)", extended_results)
    
    # Compare
    print(f"\n{'=' * 80}")
    print("COMPARISON")
    print(f"{'=' * 80}")
    
    error_change = extended_results['total_errors'] - original_results['total_errors']
    if original_results['total_errors'] > 0:
        change_pct = (error_change / original_results['total_errors']) * 100
    else:
        change_pct = 0
    
    if error_change > 0:
        print(f"Error change: +{error_change} ({change_pct:+.1f}%)")
        print("  ⚠️  Extended model found MORE issues (more comprehensive validation)")
    elif error_change < 0:
        print(f"Error reduction: {-error_change} ({-change_pct:.1f}% improvement)")
        print("  ✅ Extended model resolved issues")
    else:
        print("No change in error count")
    
    print(f"Original entities with errors: {original_results['entity_count']}")
    print(f"Extended entities with errors: {extended_results['entity_count']}")
    
    # New entities covered
    original_entities = set(original_model.entities.keys())
    extended_entities = set(extended_model.entities.keys())
    new_entities = extended_entities - original_entities
    
    print(f"\nNew entities in extended model ({len(new_entities)}):")
    for entity in sorted(new_entities):
        in_project = "✓ in project" if project.has_table(entity) else "  not in project"
        has_error = "❌ has error" if entity in extended_results['entity_errors'] else ""
        print(f"  - {entity:30s} {in_project:15s} {has_error}")
    
    # New errors introduced by extended model
    original_problem_entities = set(original_results['entity_errors'].keys())
    extended_problem_entities = set(extended_results['entity_errors'].keys())
    new_problem_entities = extended_problem_entities - original_problem_entities
    fixed_entities = original_problem_entities - extended_problem_entities
    
    if new_problem_entities:
        print(f"\nNew entities with errors in extended model ({len(new_problem_entities)}):")
        for entity in sorted(new_problem_entities):
            errors = extended_results['entity_errors'][entity]
            print(f"  - {entity}: {len(errors)} error(s)")
            for err in errors[:2]:
                print(f"      {err['code']}: {err['message']}")
    
    if fixed_entities:
        print(f"\nEntities that now pass validation ({len(fixed_entities)}):")
        for entity in sorted(fixed_entities):
            print(f"  - {entity}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
