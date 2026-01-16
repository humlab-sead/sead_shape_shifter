# Project YAML Intelligence: Monaco Editor Enhancement

**Practical implementation guide** for adding intelligent editing features to Shape Shifter project YAML files in Monaco Editor. Focus on high-value, low-effort improvements using JSON Schema + targeted custom validators.

---

## Approach: JSON Schema + Custom Domain Validators

**Estimated effort:** 1 week  
**Value delivery:** 80-90% of full custom implementation  
**Maintenance:** Low (schema-driven)

### Strategy

1. Use **JSON Schema** for structural validation (built-in Monaco support via `monaco-yaml`)
2. Add **custom validators** only for domain-specific cross-references
3. Enhance with **targeted autocompletion** for entity/data source names
4. Provide **hover documentation** for directives and common fields

---

## Required Packages

```json
{
  "dependencies": {
    "monaco-editor": "^0.45.0",
    "yaml": "^2.3.4",
    "monaco-yaml": "^5.1.1"
  }
}
```

---

## High-Level Architecture

```
┌─────────────────────────────────────────┐
│  Monaco Editor (YAML mode)              │
├─────────────────────────────────────────┤
│  monaco-yaml (JSON Schema validation)  │ ← Built-in structure validation
├─────────────────────────────────────────┤
│  Custom Domain Validators               │ ← Entity references, @value expressions
│  - validateEntityReferences()           │
│  - validateTaskListReferences()         │
│  - extractValueExpressions()            │
├─────────────────────────────────────────┤
│  Custom Completion Provider             │ ← Entity names, data sources
│  Custom Hover Provider                  │ ← Directive help, field docs
└─────────────────────────────────────────┘
```

---

## Phase 1: JSON Schema Setup (2-3 days)

### Step 1: Create Project Schema

Create `frontend/src/schemas/projectSchema.json`:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "ShapeShifter Project Configuration",
  "type": "object",
  "required": ["metadata", "entities"],
  "properties": {
    "metadata": {
      "type": "object",
      "required": ["name", "type", "version"],
      "properties": {
        "name": { "type": "string", "description": "Unique project identifier" },
        "type": { "enum": ["shapeshifter-project"], "description": "Project type identifier" },
        "version": { "type": "string", "pattern": "^\\d+\\.\\d+\\.\\d+$", "description": "Semantic version (e.g., 1.0.0)" },
        "description": { "type": "string", "description": "Project description" }
      }
    },
    "entities": {
      "type": "object",
      "description": "Entity definitions map",
      "patternProperties": {
        "^[a-zA-Z_][a-zA-Z0-9_]*$": {
          "type": "object",
          "properties": {
            "type": { 
              "enum": ["sql", "fixed"], 
              "description": "Entity source type: sql (database query) or fixed (hardcoded values)"
            },
            "data_source": { "type": "string", "description": "Reference to data source in options.data_sources" },
            "depends_on": { 
              "type": "array", 
              "items": { "type": "string" },
              "description": "List of entity names this entity depends on"
            },
            "foreign_keys": {
              "type": "array",
              "description": "Foreign key relationships",
              "items": {
                "type": "object",
                "properties": {
                  "entity": { "type": "string", "description": "Referenced entity name" },
                  "local_keys": { "oneOf": [{ "type": "array" }, { "type": "string" }] },
                  "remote_keys": { "oneOf": [{ "type": "array" }, { "type": "string" }] },
                  "how": { "enum": ["left", "inner", "outer"], "description": "Join type" },
                  "constraints": {
                    "type": "object",
                    "properties": {
                      "cardinality": { 
                        "enum": ["many-to-one", "one-to-many", "one-to-one", "many-to-many"],
                        "description": "Relationship cardinality"
                      },
                      "allow_unmatched_left": { "type": "boolean" },
                      "allow_null_keys": { "type": "boolean" }
                    }
                  }
                }
              }
            }
          }
        }
      }
    },
    "task_list": {
      "type": "object",
      "properties": {
        "required_entities": { 
          "type": "array", 
          "items": { "type": "string" },
          "description": "Entities that must be completed"
        },
        "completed": { "type": "array", "items": { "type": "string" } },
        "ignored": { "type": "array", "items": { "type": "string" } }
      }
    }
  }
}
```

### Step 2: Configure Monaco YAML

Install and configure `monaco-yaml`:

```typescript
// frontend/src/composables/useMonacoYamlIntelligence.ts
import { configureMonacoYaml } from 'monaco-yaml'
import projectSchema from '@/schemas/projectSchema.json'

export function setupYamlIntelligence() {
  configureMonacoYaml(monaco, {
    enableSchemaRequest: false,
    schemas: [
      {
        uri: 'http://shapeshifter/project-schema.json',
        fileMatch: ['*.yml', '*.yaml'],
        schema: projectSchema
      }
    ]
  })
}
```

**Result:** Automatic structural validation, enum autocomplete, hover documentation for standard fields.

---

## Phase 2: Custom Domain Validators (3-4 days)

### Core Validation Module

Create `frontend/src/utils/projectYamlValidator.ts`:

```typescript
import * as YAML from 'yaml'
import type monaco from 'monaco-editor'

interface DocIndex {
  entityNames: string[]
  dataSourceNames: string[]
  entities: Record<string, any>
}

export function validateProjectYaml(text: string, model: monaco.editor.ITextModel): monaco.editor.IMarkerData[] {
  const markers: monaco.editor.IMarkerData[] = []
  
  try {
    const doc = YAML.parseDocument(text)
    const data = doc.toJSON()
    const index = buildIndex(data)
    
    // Validate entity references
    markers.push(...validateEntityReferences(data, index, doc))
    
    // Validate task list references
    markers.push(...validateTaskListReferences(data, index, doc))
    
    // Validate @value expressions
    markers.push(...validateValueExpressions(data, index, doc))
    
  } catch (error) {
    // YAML parse errors handled by monaco-yaml
  }
  
  return markers
}

function buildIndex(data: any): DocIndex {
  return {
    entityNames: Object.keys(data.entities || {}),
    dataSourceNames: Object.keys(data.options?.data_sources || {}),
    entities: data.entities || {}
  }
}

function validateEntityReferences(data: any, index: DocIndex, doc: YAML.Document): monaco.editor.IMarkerData[] {
  const markers: monaco.editor.IMarkerData[] = []
  
  for (const [entityName, entity] of Object.entries(index.entities)) {
    // Check depends_on references
    if (entity.depends_on) {
      for (const dep of entity.depends_on) {
        if (!index.entityNames.includes(dep)) {
          markers.push(createMarker(
            findNodePosition(doc, ['entities', entityName, 'depends_on']),
            `Unknown entity '${dep}' in depends_on`,
            'Error'
          ))
        }
      }
    }
    
    // Check foreign_keys.entity references
    if (entity.foreign_keys) {
      for (const fk of entity.foreign_keys) {
        if (fk.entity && !index.entityNames.includes(fk.entity)) {
          markers.push(createMarker(
            findNodePosition(doc, ['entities', entityName, 'foreign_keys']),
            `Unknown entity '${fk.entity}' in foreign_keys`,
            'Error'
          ))
        }
      }
    }
  }
  
  return markers
}

function validateTaskListReferences(data: any, index: DocIndex, doc: YAML.Document): monaco.editor.IMarkerData[] {
  const markers: monaco.editor.IMarkerData[] = []
  const taskList = data.task_list
  
  if (!taskList) return markers
  
  const checkArray = (arrayName: string) => {
    const entities = taskList[arrayName] || []
    for (const entity of entities) {
      if (!index.entityNames.includes(entity)) {
        markers.push(createMarker(
          findNodePosition(doc, ['task_list', arrayName]),
          `Unknown entity '${entity}' in task_list.${arrayName}`,
          'Warning'
        ))
      }
    }
  }
  
  checkArray('required_entities')
  checkArray('completed')
  checkArray('ignored')
  
  return markers
}

function validateValueExpressions(data: any, index: DocIndex, doc: YAML.Document): monaco.editor.IMarkerData[] {
  const markers: monaco.editor.IMarkerData[] = []
  
  // Simple regex to extract entity references from @value expressions
  const valueExprPattern = /@value:\s*entities\.(\w+)/g
  const text = JSON.stringify(data)
  
  let match
  while ((match = valueExprPattern.exec(text)) !== null) {
    const entityName = match[1]
    if (!index.entityNames.includes(entityName)) {
      // Note: Position mapping from JSON string is approximate
      markers.push({
        severity: monaco.MarkerSeverity.Error,
        message: `Unknown entity '${entityName}' in @value expression`,
        startLineNumber: 1,
        startColumn: 1,
        endLineNumber: 1,
        endColumn: 1
      })
    }
  }
  
  return markers
}

function createMarker(position: any, message: string, severity: 'Error' | 'Warning'): monaco.editor.IMarkerData {
  return {
    severity: severity === 'Error' ? monaco.MarkerSeverity.Error : monaco.MarkerSeverity.Warning,
    message,
    startLineNumber: position?.line || 1,
    startColumn: position?.col || 1,
    endLineNumber: position?.line || 1,
    endColumn: position?.col || 100
  }
}

function findNodePosition(doc: YAML.Document, path: string[]): { line: number; col: number } | null {
  // Walk YAML AST to find node at path and return its range
  // Simplified - implement full path traversal using doc.get() and node ranges
  return null
}
```

---

## Phase 3: Enhanced Autocompletion (2 days)

### Smart Completions for Entity Names

```typescript
// frontend/src/utils/projectYamlCompletions.ts
import type monaco from 'monaco-editor'
import * as YAML from 'yaml'

export function registerProjectCompletions(monacoInstance: typeof monaco) {
  monacoInstance.languages.registerCompletionItemProvider('yaml', {
    provideCompletionItems: (model, position) => {
      const textUntilPosition = model.getValueInRange({
        startLineNumber: position.lineNumber,
        startColumn: 1,
        endLineNumber: position.lineNumber,
        endColumn: position.column
      })
      
      const suggestions: monaco.languages.CompletionItem[] = []
      
      // Parse current document to get entity names
      const fullText = model.getValue()
      const index = extractEntityNames(fullText)
      
      // Detect context and provide suggestions
      if (textUntilPosition.includes('depends_on:')) {
        suggestions.push(...createEntitySuggestions(index.entityNames, monacoInstance))
      } else if (textUntilPosition.includes('data_source:')) {
        suggestions.push(...createDataSourceSuggestions(index.dataSourceNames, monacoInstance))
      } else if (textUntilPosition.match(/entity:\s*$/)) {
        suggestions.push(...createEntitySuggestions(index.entityNames, monacoInstance))
      }
      
      return { suggestions }
    }
  })
}

function extractEntityNames(text: string): { entityNames: string[], dataSourceNames: string[] } {
  try {
    const data = YAML.parse(text)
    return {
      entityNames: Object.keys(data?.entities || {}),
      dataSourceNames: Object.keys(data?.options?.data_sources || {})
    }
  } catch {
    return { entityNames: [], dataSourceNames: [] }
  }
}

function createEntitySuggestions(entityNames: string[], monaco: typeof monaco): monaco.languages.CompletionItem[] {
  return entityNames.map(name => ({
    label: name,
    kind: monaco.languages.CompletionItemKind.Reference,
    insertText: name,
    documentation: `Entity: ${name}`
  }))
}

function createDataSourceSuggestions(dsNames: string[], monaco: typeof monaco): monaco.languages.CompletionItem[] {
  return dsNames.map(name => ({
    label: name,
    kind: monaco.languages.CompletionItemKind.Reference,
    insertText: name,
    documentation: `Data source: ${name}`
  }))
}
```

---

## Integration in Vue Component

```typescript
// In your YAML editor component (e.g., YamlTab.vue)
import { onMounted, onBeforeUnmount } from 'vue'
import { setupYamlIntelligence } from '@/composables/useMonacoYamlIntelligence'
import { validateProjectYaml } from '@/utils/projectYamlValidator'
import { registerProjectCompletions } from '@/utils/projectYamlCompletions'

onMounted(() => {
  // Phase 1: JSON Schema validation
  setupYamlIntelligence()
  
  // Phase 3: Custom completions
  registerProjectCompletions(monaco)
  
  // Phase 2: Custom domain validators
  const validateDebounced = debounce(() => {
    const markers = validateProjectYaml(editor.getValue(), model)
    monaco.editor.setModelMarkers(model, 'project-yaml-custom', markers)
  }, 300)
  
  editor.onDidChangeModelContent(validateDebounced)
})
```

---

## Acceptance Criteria

**Must have (80% value):**
1. ✅ Enum autocomplete for `type`, `cardinality`, `how` fields
2. ✅ Error markers for unknown entity references in `depends_on`
3. ✅ Error markers for unknown entity references in `foreign_keys.entity`
4. ✅ Warning markers for unknown entities in `task_list` arrays
5. ✅ Autocomplete entity names in `depends_on` and `foreign_keys.entity`
6. ✅ Autocomplete data source names in `data_source` field
7. ✅ Hover documentation for schema-defined fields

**Nice to have (Phase 3):**
- Entity name extraction from `@value:` expressions with validation
- Hover info showing entity type/data_source for references
- Typo detection for common field name mistakes (`contraints` → `constraints`)

---

## Future Enhancements (20% remaining value)

### Multi-file Support
- Resolve `@include:` directives and validate across files
- Cmd+Click navigation to included files
- Cross-file entity reference validation
- Global symbol search across project files

### Advanced Expression Parsing
- Full `@value:` expression evaluation with AST parsing
- Autocomplete for field names after `entities.<name>.`
- Validation of concatenation syntax (`keys + ['ChronoDat']`)
- Expression hover showing resolved value preview

### IDE-like Features
- Go-to-definition for entity references (jump to entity definition)
- Rename symbol (entity name) with all references updated
- Find all references to an entity across file
- Quick fixes for common errors (add missing entity, fix typo)
- Code actions: "Extract to new entity", "Inline entity reference"

### Performance Optimization
- Web worker for validation on large files (1000+ lines)
- Incremental parsing (only re-validate changed sections)
- Caching of parsed AST between edits
- Streaming validation for multi-megabyte files

### Advanced Validation
- Cyclic dependency detection in entity graph
- Cardinality constraint validation against actual data
- SQL query syntax validation for `query` fields
- Data source connection validation

---

## Extension: Single-Entity Editing Mode

Shape Shifter's `EntityFormDialog` component has a **YAML tab** for editing individual entities. Supporting YAML intelligence there requires **context injection** since the entity YAML is isolated from the full project.

### Architecture: Context-Aware Validation

The key insight: validators and completions need **external context** instead of extracting it from the document.

```typescript
// frontend/src/utils/projectYamlValidator.ts

export interface ValidationContext {
  entityNames: string[]           // All entities in project
  dataSourceNames: string[]       // All data sources
  currentEntityName?: string      // Exclude from self-references
}

export function validateProjectYaml(
  text: string, 
  model: monaco.editor.ITextModel,
  context?: ValidationContext  // NEW: optional external context
): monaco.editor.IMarkerData[] {
  const markers: monaco.editor.IMarkerData[] = []
  
  try {
    const doc = YAML.parseDocument(text)
    const data = doc.toJSON()
    
    // Use provided context OR build from document
    const index = context 
      ? buildIndexFromContext(context)
      : buildIndex(data)  // Full project mode
    
    markers.push(...validateEntityReferences(data, index, doc))
    markers.push(...validateValueExpressions(data, index, doc))
  } catch (error) {
    // Handle errors
  }
  
  return markers
}

function buildIndexFromContext(context: ValidationContext): DocIndex {
  return {
    entityNames: context.entityNames,
    dataSourceNames: context.dataSourceNames,
    entities: {}  // Single entity mode - no full entity map
  }
}
```

### Dual Schema Support

Create separate schema for single-entity editing (without project wrapper):

```json
// frontend/src/schemas/entitySchema.json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "ShapeShifter Entity Definition",
  "description": "Schema for a single entity (no wrapper)",
  "type": "object",
  "properties": {
    "type": { 
      "enum": ["sql", "fixed"], 
      "description": "Entity source type"
    },
    "data_source": { 
      "type": "string", 
      "description": "Reference to data source in options.data_sources" 
    },
    "surrogate_id": { "type": "string" },
    "keys": { "oneOf": [{ "type": "array" }, { "type": "string" }] },
    "columns": { "oneOf": [{ "type": "array" }, { "type": "string" }] },
    "query": { "type": "string" },
    "depends_on": { 
      "type": "array", 
      "items": { "type": "string" },
      "description": "Entity names this entity depends on"
    },
    "foreign_keys": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "entity": { "type": "string", "description": "Referenced entity name" },
          "local_keys": { "oneOf": [{ "type": "array" }, { "type": "string" }] },
          "remote_keys": { "oneOf": [{ "type": "array" }, { "type": "string" }] },
          "how": { "enum": ["left", "inner", "outer"] },
          "constraints": {
            "type": "object",
            "properties": {
              "cardinality": { 
                "enum": ["many-to-one", "one-to-many", "one-to-one", "many-to-many"]
              },
              "allow_unmatched_left": { "type": "boolean" },
              "allow_null_keys": { "type": "boolean" }
            }
          }
        }
      }
    },
    "filters": { "type": "object" },
    "unnest": { "type": "object" },
    "append": { "type": "array" },
    "extra_columns": { "type": "object" }
  }
}
```

### Modified Setup with Mode Selection

```typescript
// frontend/src/composables/useMonacoYamlIntelligence.ts
import { configureMonacoYaml } from 'monaco-yaml'
import projectSchema from '@/schemas/projectSchema.json'
import entitySchema from '@/schemas/entitySchema.json'

export interface YamlIntelligenceOptions {
  mode: 'project' | 'entity'
  context?: ValidationContext
}

export function setupYamlIntelligence(options: YamlIntelligenceOptions) {
  const schema = options.mode === 'project' 
    ? projectSchema 
    : entitySchema
    
  configureMonacoYaml(monaco, {
    enableSchemaRequest: false,
    schemas: [
      {
        uri: `http://shapeshifter/${options.mode}-schema.json`,
        fileMatch: ['*.yml', '*.yaml'],
        schema: schema
      }
    ]
  })
}
```

### Context-Aware Completion Provider

```typescript
// frontend/src/utils/projectYamlCompletions.ts

export function registerProjectCompletions(
  monacoInstance: typeof monaco,
  contextProvider?: () => ValidationContext  // NEW: callback for latest context
) {
  monacoInstance.languages.registerCompletionItemProvider('yaml', {
    provideCompletionItems: (model, position) => {
      const textUntilPosition = model.getValueInRange({
        startLineNumber: position.lineNumber,
        startColumn: 1,
        endLineNumber: position.lineNumber,
        endColumn: position.column
      })
      
      const suggestions: monaco.languages.CompletionItem[] = []
      
      // Get context from external source OR parse document
      let index: { entityNames: string[], dataSourceNames: string[] }
      
      if (contextProvider) {
        const context = contextProvider()
        index = {
          entityNames: context.entityNames,
          dataSourceNames: context.dataSourceNames
        }
      } else {
        const fullText = model.getValue()
        index = extractEntityNames(fullText)
      }
      
      // Context-based suggestions (same logic as before)
      if (textUntilPosition.includes('depends_on:')) {
        suggestions.push(...createEntitySuggestions(index.entityNames, monacoInstance))
      } else if (textUntilPosition.includes('data_source:')) {
        suggestions.push(...createDataSourceSuggestions(index.dataSourceNames, monacoInstance))
      } else if (textUntilPosition.match(/entity:\s*$/)) {
        suggestions.push(...createEntitySuggestions(index.entityNames, monacoInstance))
      }
      
      return { suggestions }
    }
  })
}
```

### Enhanced YamlEditor Component

```vue
<!-- frontend/src/components/common/YamlEditor.vue -->
<script setup lang="ts">
import { setupYamlIntelligence } from '@/composables/useMonacoYamlIntelligence'
import { validateProjectYaml } from '@/utils/projectYamlValidator'
import { registerProjectCompletions } from '@/utils/projectYamlCompletions'
import type { ValidationContext } from '@/utils/projectYamlValidator'

interface Props {
  modelValue: string
  height?: string
  mode?: 'project' | 'entity'  // NEW
  validationContext?: ValidationContext  // NEW
  validateOnChange?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  height: '400px',
  mode: 'project',
  validateOnChange: false
})

onMounted(() => {
  // Configure schema based on mode
  setupYamlIntelligence({ 
    mode: props.mode,
    context: props.validationContext 
  })
  
  // Register completions with context provider
  registerProjectCompletions(
    monaco,
    props.validationContext 
      ? () => props.validationContext!  // Use external context
      : undefined  // Parse from document
  )
  
  // Validation with context
  const validateDebounced = debounce(() => {
    const markers = validateProjectYaml(
      editor.getValue(), 
      model,
      props.validationContext  // Pass context to validator
    )
    monaco.editor.setModelMarkers(model, 'yaml-custom', markers)
  }, 300)
  
  editor.onDidChangeModelContent(validateDebounced)
})

// Re-validate when context changes
watch(() => props.validationContext, () => {
  if (props.validationContext) {
    const markers = validateProjectYaml(
      editor.getValue(), 
      model,
      props.validationContext
    )
    monaco.editor.setModelMarkers(model, 'yaml-custom', markers)
  }
}, { deep: true })
</script>
```

### Integration in EntityFormDialog

```vue
<!-- frontend/src/components/entities/EntityFormDialog.vue -->
<template>
  <v-window-item value="yaml">
    <v-alert type="info" variant="tonal" density="compact" class="mb-4">
      <div class="text-caption">
        <v-icon icon="mdi-information" size="small" class="mr-1" />
        Edit the entity in YAML format. Changes will be synced with the form editor.
      </div>
    </v-alert>

    <yaml-editor
      v-model="yamlContent"
      height="500px"
      mode="entity"  <!-- NEW: specify entity mode -->
      :validation-context="validationContext"  <!-- NEW: pass context -->
      :validate-on-change="true"
      @validate="handleYamlValidation"
      @change="handleYamlChange"
    />

    <v-alert v-if="yamlError" type="error" density="compact" variant="tonal" class="mt-2">
      {{ yamlError }}
    </v-alert>
  </v-window-item>
</template>

<script setup lang="ts">
import type { ValidationContext } from '@/utils/projectYamlValidator'
import { useProjectStore } from '@/stores'

const projectStore = useProjectStore()

// Build validation context from current project state
const validationContext = computed<ValidationContext>(() => ({
  entityNames: entities.value
    .filter(e => e.name !== formData.value.name)  // Exclude self
    .map(e => e.name),
  dataSourceNames: Object.keys(
    projectStore.currentProject?.options?.data_sources || {}
  ),
  currentEntityName: formData.value.name
}))
</script>
```

### Benefits

1. **Code reuse**: Same validators/completions work for both modes
2. **Live context**: Context updates automatically when entities/data sources change
3. **Self-reference prevention**: Current entity excluded from autocomplete suggestions
4. **Consistent UX**: Same editing experience in both project and entity views

---

## Estimated Timeline

| Phase | Effort | Value Delivered |
|-------|--------|-----------------|
| Phase 1: JSON Schema | 2-3 days | 50% |
| Phase 2: Custom Validators | 3-4 days | 20% |
| Phase 3: Enhanced Completions | 2 days | 5% |
| **Phase 4: Single-Entity Mode** | **1 day** | **15%** |
| **Total MVP** | **~1.5 weeks** | **90%** |
| Future Enhancements | 2-3 weeks | 10% |

**Key changes for Phase 4:**
- Add `ValidationContext` interface and parameter (+30 lines)
- Create `entitySchema.json` (new file, ~100 lines)
- Add mode selection to `useMonacoYamlIntelligence` (+20 lines)
- Add context support to `YamlEditor.vue` (+40 lines)
- Compute context in `EntityFormDialog.vue` (+10 lines)
- Update completion provider with callback (+20 lines)

**Total additional effort: 1 day**

---

## Recommendation

**Proceed with Phases 1-4** for maximum ROI. This delivers 90% of the value in <2 weeks with support for both full-project and single-entity editing. The context injection pattern is clean and maintainable.

**Defer Future Enhancements** until user feedback indicates which features provide the most value in practice. Many advanced IDE features may not be needed for typical YAML editing workflows.
