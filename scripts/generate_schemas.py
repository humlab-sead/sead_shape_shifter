#!/usr/bin/env python3
"""Generate JSON schemas from Pydantic models for frontend Monaco editor autocomplete.

This script generates JSON Schema Draft 7 compliant schemas from the backend
Pydantic models (Entity, Project) for use in the frontend Monaco YAML editor.

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

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.models.entity import Entity
from backend.app.models.project import Project


def clean_schema(schema: dict, title: str, description: str) -> dict:
    """Clean and customize schema for Monaco editor use."""
    # Set JSON Schema version and metadata
    schema['$schema'] = 'http://json-schema.org/draft-07/schema#'
    schema['title'] = title
    schema['description'] = description
    
    # Remove 'name' from Entity required fields (it's API-only metadata)
    if 'required' in schema and 'name' in schema.get('required', []):
        schema['required'].remove('name')
    
    # Add helpful examples/hints for common fields
    if 'properties' in schema:
        props = schema['properties']
        
        # Add pattern hint for public_id
        if 'public_id' in props and 'pattern' not in props['public_id']:
            props['public_id']['pattern'] = '.*_id$'
            props['public_id']['examples'] = ['sample_type_id', 'location_id']
        
        # Add enum description for type
        if 'type' in props and 'enum' in props['type']:
            props['type']['description'] = (
                'Entity source type: '
                'entity (derived from another entity), '
                'sql (database query), '
                'fixed (hardcoded values), '
                'csv/xlsx/openpyxl (file sources)'
            )
    
    return schema


def generate_schemas(output_dir: Path | None = None, print_only: bool = False) -> dict[str, dict]:
    """Generate JSON schemas from Pydantic models.
    
    Args:
        output_dir: Directory to write schemas to (None for print_only)
        print_only: If True, print to stdout instead of writing files
        
    Returns:
        Dict mapping filename to schema content
    """
    
    # Generate Entity schema
    entity_schema = Entity.model_json_schema(
        mode='serialization',
        by_alias=True,
        ref_template='#/$defs/{model}',
    )
    
    entity_schema = clean_schema(
        entity_schema,
        title='ShapeShifter Entity Definition',
        description='Schema for a single entity definition (table/view/query configuration)'
    )
    
    # Generate Project schema  
    project_schema = Project.model_json_schema(
        mode='serialization',
        by_alias=True,
        ref_template='#/$defs/{model}',
    )
    
    project_schema = clean_schema(
        project_schema,
        title='ShapeShifter Project Configuration',
        description='Schema for Shape Shifter project configuration files'
    )
    
    schemas = {
        'entitySchema.json': entity_schema,
        'projectSchema.json': project_schema,
    }
    
    if print_only:
        print(json.dumps({k: v for k, v in schemas.items()}, indent=2))
        return schemas
    
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        
        for filename, schema in schemas.items():
            path = output_dir / filename
            with path.open('w') as f:
                json.dump(schema, f, indent=2)
                f.write('\n')  # Ensure newline at EOF
            
            print(f"✓ Generated {path}")
    
    return schemas


def check_schemas_in_sync(schemas_dir: Path) -> bool:
    """Check if committed schemas match generated schemas.
    
    Returns:
        True if in sync, False otherwise
    """
    # Generate schemas in memory
    generated = generate_schemas(output_dir=None)
    
    # Compare with committed files
    all_match = True
    
    for filename, gen_schema in generated.items():
        file_path = schemas_dir / filename
        
        if not file_path.exists():
            print(f"❌ {filename} does not exist", file=sys.stderr)
            all_match = False
            continue
        
        with file_path.open('r') as f:
            committed_schema = json.load(f)
        
        # Normalize for comparison (remove trailing whitespace differences)
        gen_json = json.dumps(gen_schema, indent=2, sort_keys=True)
        committed_json = json.dumps(committed_schema, indent=2, sort_keys=True)
        
        if gen_json != committed_json:
            print(f"❌ {filename} is out of sync with Pydantic models", file=sys.stderr)
            print(f"   Run: python scripts/generate_schemas.py", file=sys.stderr)
            all_match = False
        else:
            print(f"✓ {filename} is in sync")
    
    return all_match


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Generate JSON schemas from Pydantic models',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate schemas (default)
  python scripts/generate_schemas.py
  
  # Check if schemas are in sync (for CI)
  python scripts/generate_schemas.py --check
  
  # Print schemas to stdout
  python scripts/generate_schemas.py --print
        """
    )
    
    parser.add_argument(
        '--check',
        action='store_true',
        help='Check if committed schemas match generated schemas (exits 1 if out of sync)'
    )
    
    parser.add_argument(
        '--print',
        action='store_true',
        help='Print schemas to stdout instead of writing files'
    )
    
    parser.add_argument(
        '--output',
        type=Path,
        help='Output directory (default: frontend/src/schemas)'
    )
    
    args = parser.parse_args()
    
    # Determine output directory
    if args.output:
        output_dir = args.output
    else:
        output_dir = Path(__file__).parent.parent / 'frontend' / 'src' / 'schemas'
    
    # Check mode
    if args.check:
        print("Checking if schemas are in sync with Pydantic models...\n")
        if check_schemas_in_sync(output_dir):
            print("\n✓ All schemas are in sync!")
            return 0
        else:
            print("\n❌ Schemas are out of sync. Please regenerate.", file=sys.stderr)
            return 1
    
    # Print mode
    if args.print:
        generate_schemas(output_dir=None, print_only=True)
        return 0
    
    # Generate mode (default)
    print("Generating JSON schemas from Pydantic models...\n")
    schemas = generate_schemas(output_dir)
    
    # Print summary
    print("\nSchema Summary:")
    print(f"Entity properties: {len(schemas['entitySchema.json'].get('properties', {}))}")
    print(f"Project properties: {len(schemas['projectSchema.json'].get('properties', {}))}")
    
    # List entity properties for verification
    print("\nEntity properties:")
    for prop in sorted(schemas['entitySchema.json'].get('properties', {}).keys()):
        print(f"  - {prop}")
    
    print("\n✓ Done! Schemas generated successfully.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
