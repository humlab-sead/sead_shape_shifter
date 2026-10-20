# JSON Schemas for Monaco Editor

These JSON Schema files provide **autocomplete and IntelliSense** for the Monaco YAML editor in the Shape Shifter frontend.

## Files

- **entitySchema.json** - Schema for entity definitions
- **projectSchema.json** - Schema for project configuration
- **targetModelSchema.json** - Schema for target model specifications
- **reconciliationSchema.json** - Schema for reconciliation specifications and catalogs

## Usage

These schemas are consumed by `useMonacoYamlIntelligence.ts` composable to configure the Monaco YAML editor with autocomplete suggestions.

**Important:** These schemas are for **editor UX only**. Actual validation happens server-side using the Pydantic models in `backend/app/models/`.

## Auto-Generation

All schemas are **automatically generated** from Pydantic models to keep them in sync with the application models:

```bash
# Regenerate schemas from Pydantic models
make generate-schemas

# Validate schemas are in sync (for CI)
make check-schemas
```

Do not edit the generated schemas manually; update their source Pydantic models instead:
- `backend/app/models/entity.py`
- `backend/app/models/project.py`
- `backend/app/models/reconciliation.py`
- `src/target_model/models.py`

`reconciliationSchema.json` combines `EntityResolutionSet` and `EntityResolutionCatalog` into a `oneOf`, so the editor can assist with both a single specification and a full catalog.

## Source of Truth

The backend Pydantic models are the source of truth for entity, project, target model, and reconciliation data. These JSON schemas provide Monaco editor autocomplete.

See docs/JSON_SCHEMA_GENERATION.md for detailed information.
