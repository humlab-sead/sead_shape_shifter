# YAML Intelligence Feature

## Overview

This feature adds intelligent editing support for YAML files in the Monaco editor, including:
- **Schema-based validation** using JSON Schema
- **Smart autocompletion** for entity names, data sources, and enum values
- **Real-time error detection** for unknown entity references
- **Context-aware suggestions** based on cursor position
- **Dual-mode support** for both full project and single-entity editing

## Implementation Summary

### Components Created

1. **Schemas** (`frontend/src/schemas/`)
   - `projectSchema.json` - Full project configuration schema
   - `entitySchema.json` - Single entity definition schema

2. **Utilities** (`frontend/src/utils/`)
   - `projectYamlValidator.ts` - Custom validation logic with context support
   - `projectYamlCompletions.ts` - Context-aware completion provider

3. **Composables** (`frontend/src/composables/`)
   - `useMonacoYamlIntelligence.ts` - YAML intelligence setup function

4. **Enhanced Components**
   - `YamlEditor.vue` - Updated to support mode and validation context
   - `EntityFormDialog.vue` - Integrated YAML intelligence for entity editing

### Dependencies Added

```json
{
  "monaco-yaml": "^5.1.1",
  "yaml": "^2.3.4"
}
```

## Usage

### Full Project Mode (Default)

```vue
<yaml-editor
  v-model="yamlContent"
  height="600px"
  mode="project"
  :validate-on-change="true"
/>
```

### Single-Entity Mode (with Context)

```vue
<yaml-editor
  v-model="entityYaml"
  height="500px"
  mode="entity"
  :validation-context="validationContext"
  :validate-on-change="true"
/>
```

Where `validationContext` is:

```typescript
const validationContext = computed<ValidationContext>(() => ({
  entityNames: allEntityNames.filter(e => e !== currentEntity),
  dataSourceNames: availableDataSources,
  currentEntityName: currentEntity
}))
```

## Features

### Schema Validation

- Validates YAML structure against JSON Schema
- Provides enum suggestions for fields like `type`, `cardinality`, `how`
- Shows hover documentation for fields

### Custom Validation

- **Entity references**: Validates `depends_on` and `foreign_keys.entity` references
- **Task list references**: Warns about unknown entities in task lists
- **@value expressions**: Validates entity references in `@value:` directives
- **Data source references**: Validates `data_source` field values

### Smart Completions

Context-aware suggestions for:
- Entity names (in `depends_on`, `foreign_keys.entity`, `append`, etc.)
- Data source names (in `data_source` field)
- Join types (`how`: left, inner, outer)
- Cardinality values (many-to-one, one-to-many, etc.)
- Entity types (sql, fixed)

### Error Markers

- **Red underlines** for critical errors (unknown entities, invalid syntax)
- **Yellow underlines** for warnings (deprecated fields, potential issues)
- **Hover tooltips** with detailed error messages

## Architecture

### Context Injection Pattern

For single-entity editing, validation context is injected externally:

```typescript
interface ValidationContext {
  entityNames: string[]        // All entities in project
  dataSourceNames: string[]    // All data sources
  currentEntityName?: string   // Exclude from self-references
}
```

This allows the same validation logic to work in both:
1. **Full project mode**: Context extracted from document
2. **Single-entity mode**: Context provided externally

### Validation Flow

```
User types in editor
       ↓
Monaco onChange event
       ↓
Custom validator runs
       ↓
YAML parser extracts AST
       ↓
Validation rules check references
       ↓
Markers created and displayed
```

## Testing

To test the implementation:

1. **Start frontend dev server**:
   ```bash
   cd frontend && pnpm run dev
   ```

2. **Open a project** in the editor

3. **Test full project mode**:
   - Go to YAML tab in project view
   - Start typing entity definitions
   - Observe autocomplete for entity names, types, etc.

4. **Test single-entity mode**:
   - Click "Edit" on any entity
   - Go to YAML tab in entity dialog
   - Type entity YAML (without wrapper)
   - Autocomplete should suggest other entity names

5. **Test validation**:
   - Type unknown entity name in `depends_on`
   - Should see red underline with error message
   - Hover to see details

## Known Limitations

1. **Position mapping**: Error positions are approximate for `@value:` expressions (would need full AST walk for exact positions)
2. **Performance**: Validation runs on every change (debounced at Monaco level)
3. **Schema completeness**: Schemas cover main fields but may need updates for edge cases

## Future Enhancements

See [docs/YAML_INTELLIGENCE.md](../docs/YAML_INTELLIGENCE.md) for planned enhancements:
- Multi-file `@include:` support
- Advanced expression parsing
- Go-to-definition for entity references
- Rename refactoring
- Performance optimizations (web workers)

## Troubleshooting

### Autocompletion not working

1. Check browser console for errors
2. Verify `monaco-yaml` is installed
3. Ensure mode prop is set correctly

### Validation not running

1. Check `validateOnChange` prop is true
2. Verify validation context is provided (for entity mode)
3. Check browser console for errors

### Slow performance

1. Reduce document size if possible
2. Consider disabling `validateOnChange` for very large files
3. Future: Use web worker for validation

## Contributing

When adding new fields to schemas:

1. Update `projectSchema.json` or `entitySchema.json`
2. Add completion suggestions in `projectYamlCompletions.ts`
3. Add validation logic in `projectYamlValidator.ts` if needed
4. Update this README with new features

## References

- [JSON Schema Draft 7](https://json-schema.org/draft-07/json-schema-release-notes.html)
- [Monaco YAML](https://github.com/remcohaszing/monaco-yaml)
- [Monaco Editor API](https://microsoft.github.io/monaco-editor/api/index.html)
