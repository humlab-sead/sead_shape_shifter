# JSON Schema Generation for Frontend Monaco Editor

## Overview

The JSON schemas in `frontend/src/schemas/` are used **solely for Monaco editor autocomplete** in the YAML editor. They are consumed by `useMonacoYamlIntelligence.ts` to provide IntelliSense when editing project configuration files.

## Current Status

### ❌ Problems with Manual Schemas

The current schemas (`entitySchema.json`, `projectSchema.json`) are **manually maintained** and have become:

1. **Outdated** - Missing new fields:
   - `extra_columns` - Not defined
   - `system_id` / `public_id` - Not included (replaced `surrogate_id`)
   - `materialized` - Missing entirely
   - Various constraint options

2. **Deprecated** - Still includes old fields:
   - `surrogate_id` - Deprecated in favor of `system_id`/`public_id`
   - `surrogate_name` - No longer used

3. **Incomplete** - Missing schema details:
   - Filter types (only `exists_in` defined)
   - Replacement rules (complex nested structure)
   - Nested Pydantic models not fully specified

4. **Brittle** - Must be manually updated whenever:
   - New fields added to Entity/Project Pydantic models
   - Field types change
   - Validation rules updated

### ✅ Solution: Auto-Generated from Pydantic

**Pydantic v2** can automatically generate JSON Schema from models using `model_json_schema()`.

## Relationship Between Schemas and Pydantic Models

```
Backend Pydantic Models          Frontend JSON Schemas
(Source of Truth)                (Auto-Generated)
─────────────────────            ────────────────────

backend/app/models/entity.py     frontend/src/schemas/entitySchema.json
├─ Entity                   ──>  (JSON Schema for autocomplete)
├─ ForeignKeyConfig
├─ FilterConfig
├─ UnnestConfig
└─ AppendConfig

backend/app/models/project.py    frontend/src/schemas/projectSchema.json
├─ Project                  ──>  (JSON Schema for autocomplete)
└─ ProjectMetadata
```

## How It Works

1. **Pydantic Models** (Backend) - Single source of truth
   - Defined in `backend/app/models/entity.py` and `project.py`
   - Include field types, descriptions, validation rules
   - Used by FastAPI for request/response validation

2. **JSON Schema Generation** (Build Step)
   - Script: `scripts/generate_schemas.py`
   - Calls `Entity.model_json_schema()` and `Project.model_json_schema()`
   - Outputs to `frontend/src/schemas/`

3. **Monaco Editor** (Frontend)
   - Imports schemas from `@/schemas/entitySchema.json`
   - Passes to `configureMonacoYaml()` for autocomplete
   - Users get IntelliSense when typing YAML

## Generated vs Manual Comparison

| Aspect | Manual (Current) | Generated (Pydantic) |
|--------|------------------|----------------------|
| **Lines** | entitySchema: 326, projectSchema: 177 | entitySchema: 553, projectSchema: 166 |
| **Completeness** | ❌ Missing ~8 fields | ✅ All 20 Entity fields |
| **Accuracy** | ❌ Includes deprecated | ✅ Always current |
| **Maintenance** | ❌ Manual updates | ✅ Automated |
| **Type Safety** | ❌ Can drift | ✅ Enforced by Pydantic |
| **Nested Models** | ❌ Partial | ✅ Full definitions |

### Example: Entity Fields

**Old Manual Schema (Missing):**
- `system_id`, `public_id` - NOT included
- `extra_columns` - NOT defined
- `materialized` - NOT present
- `check_column_names` - NOT present

**New Generated Schema (Complete):**
```json
{
  "properties": {
    "name": { "type": "string", "description": "Entity name (snake_case)" },
    "type": { "enum": ["entity", "sql", "fixed", "csv", "xlsx", "openpyxl"] },
    "system_id": { "type": "string", "default": "system_id" },
    "public_id": { "type": "string", "pattern": ".*_id$" },
    "extra_columns": { "type": "object", "additionalProperties": {} },
    "check_column_names": { "type": "boolean", "default": true },
    // ... all other fields with full nested schemas
  }
}
```

## Usage in Frontend

**File:** `frontend/src/composables/useMonacoYamlIntelligence.ts`

```typescript
import projectSchema from '@/schemas/projectSchema.json'
import entitySchema from '@/schemas/entitySchema.json'

export function setupYamlIntelligence(monacoInstance, options) {
  const schema = options.mode === 'project' ? projectSchema : entitySchema
  
  configureMonacoYaml(monacoInstance, {
    schemas: [{
      uri: `http://shapeshifter/${options.mode}-schema.json`,
      fileMatch: ['*.yml', '*.yaml'],
      schema: schema  // ← Used for autocomplete only
    }]
  })
}
```

**Key Point:** These schemas are **NOT used for validation**. Project validation happens in the backend using the actual Pydantic models.

## Recommended Workflow

### Developer Workflow

1. **Update Pydantic Model**
   ```python
   # backend/app/models/entity.py
   class Entity(BaseModel):
       new_field: str = Field(..., description="New feature")
   ```

2. **Regenerate Schemas**
   ```bash
   ./scripts/generate_schemas.py
   # or add to Makefile:
   make generate-schemas
   ```

3. **Commit Both**
   ```bash
   git add backend/app/models/entity.py frontend/src/schemas/entitySchema.json
   git commit -m "feat(entity): add new_field"
   ```

### CI/CD Integration

Add schema validation to CI to ensure schemas stay in sync:

```yaml
# .github/workflows/ci.yml
- name: Check schemas are up-to-date
  run: |
    ./scripts/generate_schemas.py --check
    # Fails if generated schemas differ from committed files
```

## Migration Plan

1. ✅ **Create `scripts/generate_schemas.py`** - Done
2. ⏳ **Verify generated schemas** - Compare autocomplete behavior
3. ⏳ **Update schemas** - Replace manual with generated
4. ⏳ **Add to build** - Integrate into Makefile/package.json
5. ⏳ **Add CI check** - Prevent schema drift
6. ⏳ **Document** - Update developer guide

## Limitations

### What Pydantic JSON Schema CANNOT Do

1. **Custom JSON Schema extensions** - If you need Monaco-specific hints beyond JSON Schema Draft 7
2. **Examples** - Pydantic can include examples, but they may be verbose
3. **Ordering** - Properties may not appear in desired UI order

### Workarounds

For custom needs, post-process the generated schema:

```python
# scripts/generate_schemas.py
schema = Entity.model_json_schema()

# Add custom Monaco hints
schema['properties']['type']['x-monaco-suggestions'] = [...]

# Customize descriptions for better UX
schema['properties']['foreign_keys']['description'] = "..."
```

## Testing

**Before:**
```bash
# Manual testing only - open Monaco editor and check autocomplete
```

**After (with generated schemas):**
```bash
# Automated verification
./scripts/generate_schemas.py --check  # Ensure in sync
pytest tests/test_schema_generation.py  # Validate generation logic
```

## Benefits Summary

| Benefit | Impact |
|---------|--------|
| **No drift** | Schemas always match Pydantic models |
| **Less work** | No manual JSON schema updates |
| **Better autocomplete** | All fields + nested models |
| **Type safety** | Pydantic validation enforced |
| **Self-documenting** | Field descriptions from Pydantic |

## Questions Answered

### Q1: Are the schema files used in the frontend?

**Yes**, but **only for Monaco editor autocomplete**. They are imported in `useMonacoYamlIntelligence.ts` and passed to `monaco-yaml` for IntelliSense when editing YAML files. They are **NOT used for validation** (that happens in the backend).

### Q2: What's the relation between JSON schemas and Pydantic models?

**Pydantic models are the source of truth.** The JSON schemas should be auto-generated from Pydantic using `model_json_schema()`. Currently they are manually maintained (outdated/incomplete). The relationship:

```
Pydantic Models (Backend)
    ↓ model_json_schema()
JSON Schemas (Frontend)
    ↓ configureMonacoYaml()
Monaco Autocomplete (UX)
```

### Q3: Should schemas be generated in the backend?

**Yes!** The generation script should live in `backend/` or `scripts/` and run as part of the build process. Schemas should be committed to git but regenerated whenever Pydantic models change.

## Conclusion

**Current State:** Manual schemas are outdated and incomplete.

**Recommended:** Auto-generate from Pydantic models using `scripts/generate_schemas.py`.

**Action Items:**
1. Review generated schemas for Monaco compatibility
2. Replace manual schemas with generated versions
3. Add schema generation to build/CI pipeline
4. Document process in developer guide
