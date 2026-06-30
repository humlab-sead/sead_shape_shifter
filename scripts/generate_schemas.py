#!/usr/bin/env python3
"""Generate JSON schemas from Pydantic models for frontend Monaco editor autocomplete.

This script generates JSON Schema Draft 7 compliant schemas from backend
Pydantic models for use in the frontend Monaco YAML editor.

Run from project root:
    python scripts/generate_schemas.py              # Generate and write
    python scripts/generate_schemas.py --check      # Check if in sync (CI)
    python scripts/generate_schemas.py --print      # Print to stdout

The generated schemas are used ONLY for Monaco editor autocomplete, not validation.
Validation happens in the backend using the actual Pydantic models.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "frontend" / "src" / "schemas"
JSON_SCHEMA_VERSION = "http://json-schema.org/draft-07/schema#"
REF_TEMPLATE = "#/$defs/{model}"
SCRIPT_COMMAND = "python scripts/generate_schemas.py"

# Add backend to path
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.models.entity import Entity
from backend.app.models.project import Project
from src.loaders.driver_metadata import DriverSchemaRegistry
from src.target_model.models import TargetModel

SCHEMA_CONFIG: dict[str, dict[str, Any]] = {
    "entitySchema.json": {
        "model": Entity,
        "title": "ShapeShifter Entity Definition",
        "description": "Schema for a single entity definition (table/view/query configuration)",
        "remove_required": ["name"],
        "add_loader_options": True,
        "field_patches": {
            "public_id": {
                "set_if_missing": {
                    "pattern": ".*_id$",
                    "examples": ["sample_type_id", "location_id"],
                }
            },
            "type": {
                "apply_if": {"enum": True},
                "set": {
                    "description": (
                        "Entity source type: "
                        "entity (derived from another entity), "
                        "sql (database query), "
                        "fixed (hardcoded values), "
                        "csv/xlsx/openpyxl (file sources)"
                    )
                },
            },
        },
    },
    "projectSchema.json": {
        "model": Project,
        "title": "ShapeShifter Project Configuration",
        "description": "Schema for Shape Shifter project configuration files",
        "remove_required": [],
        "field_patches": {},
    },
    "targetModelSchema.json": {
        "model": TargetModel,
        "title": "ShapeShifter Target Model Specification",
        "description": "Schema for target model specifications defining target database schema constraints and entity relationships",
        "remove_required": [],
        "field_patches": {},
    },
}


_FIELD_TYPE_TO_JSON_SCHEMA: dict[str, str] = {
    "string": "string",
    "integer": "integer",
    "boolean": "boolean",
    "password": "string",
    "file_path": "string",
}


def build_loader_options_schema() -> dict[str, Any]:
    """Build the options property schema from registered file-loader DriverSchemas.

    Returns a JSON Schema object with a oneOf array, one entry per unique file
    loader (aliases are deduplicated by schema.driver). Database loaders are
    excluded because they use data_source + query, not options.
    """
    all_schemas = DriverSchemaRegistry.all()

    seen_drivers: set[str] = set()
    one_of: list[dict[str, Any]] = []

    for driver_schema in all_schemas.values():
        if driver_schema.category != "file":
            continue
        if driver_schema.driver in seen_drivers:
            continue
        seen_drivers.add(driver_schema.driver)

        properties: dict[str, Any] = {}
        required: list[str] = []

        for field in driver_schema.fields:
            prop: dict[str, Any] = {"type": _FIELD_TYPE_TO_JSON_SCHEMA.get(field.type, "string")}
            if field.description:
                prop["description"] = field.description
            if field.default is not None:
                prop["default"] = field.default
            properties[field.name] = prop
            if field.required:
                required.append(field.name)

        entry: dict[str, Any] = {
            "description": f"Options for type: {driver_schema.driver}",
            "properties": properties,
        }
        if required:
            entry["required"] = required

        one_of.append(entry)

    return {
        "type": "object",
        "description": "Loader-specific options. Required keys depend on entity type.",
        "oneOf": one_of,
    }


def apply_field_patches(properties: dict[str, Any], field_patches: dict[str, Any]) -> None:
    """Apply configured field-level schema patches in-place."""
    for field_name, patch_config in field_patches.items():
        field_schema = properties.get(field_name)
        if not field_schema:
            continue

        apply_if = patch_config.get("apply_if", {})
        if apply_if.get("enum") and "enum" not in field_schema:
            continue

        for key, value in patch_config.get("set_if_missing", {}).items():
            if key not in field_schema:
                field_schema[key] = value

        for key, value in patch_config.get("set", {}).items():
            field_schema[key] = value


def clean_schema(schema: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """Clean and customize schema for Monaco editor use."""
    schema["$schema"] = JSON_SCHEMA_VERSION
    schema["title"] = config["title"]
    schema["description"] = config["description"]

    required = schema.get("required")
    if isinstance(required, list):
        for field_name in config.get("remove_required", []):
            if field_name in required:
                required.remove(field_name)

    properties = schema.get("properties")
    if isinstance(properties, dict):
        apply_field_patches(properties, config.get("field_patches", {}))

        if config.get("add_loader_options") and "options" in properties:
            properties["options"] = build_loader_options_schema()

    return schema


def build_schema(model: type[Any], config: dict[str, Any]) -> dict[str, Any]:
    """Generate and customize JSON schema for a single model."""
    schema = model.model_json_schema(
        mode="serialization",
        by_alias=True,
        ref_template=REF_TEMPLATE,
    )
    return clean_schema(schema, config)


def generate_schemas(output_dir: Path | None = None, print_only: bool = False) -> dict[str, dict[str, Any]]:
    """Generate JSON schemas from configured Pydantic models.

    Args:
        output_dir: Directory to write schemas to (None for print_only)
        print_only: If True, print to stdout instead of writing files

    Returns:
        Dict mapping filename to schema content
    """
    schemas: dict[str, dict[str, Any]] = {}

    for filename, config in SCHEMA_CONFIG.items():
        model = config["model"]
        schemas[filename] = build_schema(model, config)

    if print_only:
        print(json.dumps(schemas, indent=2))
        return schemas

    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)

        for filename, schema in schemas.items():
            path = output_dir / filename
            with path.open("w", encoding="utf-8") as f:
                json.dump(schema, f, indent=2)
                f.write("\n")  # Ensure newline at EOF

            print(f"✓ Generated {path}")

    return schemas


def check_schemas_in_sync(schemas_dir: Path) -> bool:
    """Check if committed schemas match generated schemas.

    Returns:
        True if in sync, False otherwise
    """
    generated = generate_schemas(output_dir=None)

    all_match = True

    for filename, generated_schema in generated.items():
        file_path = schemas_dir / filename

        if not file_path.exists():
            print(f"❌ {filename} does not exist", file=sys.stderr)
            all_match = False
            continue

        with file_path.open("r", encoding="utf-8") as f:
            committed_schema = json.load(f)

        generated_json = json.dumps(generated_schema, indent=2, sort_keys=True)
        committed_json = json.dumps(committed_schema, indent=2, sort_keys=True)

        if generated_json != committed_json:
            print(f"❌ {filename} is out of sync with Pydantic models", file=sys.stderr)
            print(f"   Run: {SCRIPT_COMMAND}", file=sys.stderr)
            all_match = False
        else:
            print(f"✓ {filename} is in sync")

    return all_match


def print_schema_summary(schemas: dict[str, dict[str, Any]]) -> None:
    """Print summary information for generated schemas."""
    print("\nSchema Summary:")
    for filename, schema in schemas.items():
        prop_count = len(schema.get("properties", {}))
        print(f"{filename}: {prop_count} properties")

    entity_schema = schemas.get("entitySchema.json", {})
    entity_properties = entity_schema.get("properties", {})

    if entity_properties:
        print("\nEntity properties:")
        for prop in sorted(entity_properties.keys()):
            print(f"  - {prop}")


def build_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Generate JSON schemas from Pydantic models",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  # Generate schemas (default)
  {SCRIPT_COMMAND}

  # Check if schemas are in sync (for CI)
  {SCRIPT_COMMAND} --check

  # Print schemas to stdout
  {SCRIPT_COMMAND} --print
        """,
    )

    parser.add_argument("--check", action="store_true", help="Check if committed schemas match generated schemas (exits 1 if out of sync)")

    parser.add_argument("--print", action="store_true", help="Print schemas to stdout instead of writing files")

    parser.add_argument("--output", type=Path, help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})")

    return parser


def main() -> int:
    """Main entry point."""
    parser = build_parser()
    args = parser.parse_args()

    output_dir = args.output or DEFAULT_OUTPUT_DIR

    if args.check:
        print("Checking if schemas are in sync with Pydantic models...\n")
        if check_schemas_in_sync(output_dir):
            print("\n✓ All schemas are in sync!")
            return 0

        print("\n❌ Schemas are out of sync. Please regenerate.", file=sys.stderr)
        return 1

    if args.print:
        generate_schemas(output_dir=None, print_only=True)
        return 0

    print("Generating JSON schemas from Pydantic models...\n")
    schemas = generate_schemas(output_dir=output_dir)

    print_schema_summary(schemas)

    print("\n✓ Done! Schemas generated successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
