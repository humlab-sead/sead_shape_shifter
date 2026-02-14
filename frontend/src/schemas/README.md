# JSON Schemas for Monaco Editor

These JSON Schema files provide **autocomplete and IntelliSense** for the Monaco YAML editor in the Shape Shifter frontend.

## Files

- **entitySchema.json** - Schema for entity definitions
- **projectSchema.json** - Schema for project configuration

## Usage

These schemas are consumed by `useMonacoYamlIntelligence.ts` composable to configure the Monaco YAML editor with autocomplete suggestions.

**Important:** These schemas are for **editor UX only**. Actual validation happens server-side using the Pydantic models in `backend/app/models/`.

## Auto-Generation

These files are **automatically generated** from the Pydantic models to ensure they stay in sync with the backend API:

```bash
# Regenerate schemas from Pydantic models
make generate-schemas

# Validate schemas are in sync (for CI)
make check-schemas
```

**Never edit these files manually** - they will be overwritten. Instead, update the source Pydantic models:
- `backend/app/models/entity.py`
- `backend/app/models/project.py`

## Source of Truth

The **single source of truth** for entity and project structure is the backend Pydantic models. These JSON schemas are derived representations optimized for Monaco editor autocomplete.

See [docs/JSON_SCHEMA_GENERATION.md](../../../docs/JSON_SCHEMA_GENERATION.md) for detailed information.
