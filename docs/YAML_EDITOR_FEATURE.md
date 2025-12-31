# YAML Editor Feature Documentation

## Overview

The YAML Editor feature provides a dual-mode editing experience for entity, similar to VS Code's settings editor. Users can seamlessly switch between a visual form editor and a raw YAML code editor.

## Feature Highlights

✅ **Dual-Mode Editing**
- Form Editor for guided, field-by-field editing
- YAML Editor for direct code manipulation
- Automatic synchronization between modes

✅ **Professional Code Editing**
- Monaco Editor integration (same as VS Code)
- Syntax highlighting for YAML
- Real-time error detection
- Line numbers and error markers

✅ **Bidirectional Sync**
- Form changes automatically convert to YAML
- Valid YAML updates form fields when switching tabs
- No data loss during mode transitions

✅ **Validation**
- Real-time YAML syntax validation
- Clear error messages with line numbers
- Prevents invalid data from being saved

## User Interface

### Entity Edit Dialog Tabs

```
┌─────────────────────────────────────────────────────┐
│  Edit Entity: sample_type              [X] [Save]   │
├─────────────────────────────────────────────────────┤
│  [Form] [YAML]                                       │
├─────────────────────────────────────────────────────┤
│                                                      │
│  Form Editor (Default):                             │
│  ┌────────────────────────────────────────────┐    │
│  │ Entity Name: [sample_type____________]     │    │
│  │ Entity Type: [data          ▼]            │    │
│  │ Natural Keys: [key1, key2_____________]    │    │
│  │ Surrogate ID: [sample_type_id_________]    │    │
│  │ Columns:     [col1, col2, col3________]    │    │
│  └────────────────────────────────────────────┘    │
│                                                      │
│  YAML Editor (Advanced):                            │
│  ┌────────────────────────────────────────────┐    │
│  │ 1  sample_type:                            │    │
│  │ 2    type: data                            │    │
│  │ 3    keys: [key1, key2]                    │    │
│  │ 4    surrogate_id: sample_type_id          │    │
│  │ 5    columns: [col1, col2, col3]           │    │
│  └────────────────────────────────────────────┘    │
│                                                      │
│                               [Cancel] [Save]       │
└─────────────────────────────────────────────────────┘
```

## Implementation Details

### Architecture

**Component Hierarchy:**
```
EntityFormDialog.vue (Parent)
├── v-tabs (Tab Navigation)
│   ├── Form Tab
│   └── YAML Tab
└── v-window (Tab Content)
    ├── v-window-item (Form Editor)
    │   └── v-form with input fields
    └── v-window-item (YAML Editor)
        └── YamlEditor.vue (Reusable Component)
```

### YamlEditor Component

**File:** `frontend/src/components/common/YamlEditor.vue`

**Purpose:** Reusable YAML code editor with validation

**Features:**
- Monaco Editor integration
- Real-time syntax validation using `js-yaml`
- Configurable height and read-only mode
- Emits validation events for parent component

**Props:**
```typescript
interface Props {
  modelValue: string        // YAML content (v-model binding)
  height?: string          // Editor height (default: '400px')
  readonly?: boolean       // Read-only mode (default: false)
  validateOnChange?: boolean // Auto-validate (default: true)
}
```

**Emits:**
```typescript
const emit = defineEmits<{
  'update:modelValue': [value: string]
  'validate': [result: { valid: boolean; error: string | null }]
  'change': [value: string]
}>()
```

**Validation Logic:**
```typescript
function validateYaml(content: string): { valid: boolean; error: string | null } {
  if (!content.trim()) {
    return { valid: true, error: null }
  }
  
  try {
    yaml.load(content)
    return { valid: true, error: null }
  } catch (error: any) {
    const message = error.message || 'Invalid YAML syntax'
    return { valid: false, error: message }
  }
}
```

### EntityFormDialog Integration

**File:** `frontend/src/components/entities/EntityFormDialog.vue`

**State Variables:**
```typescript
// YAML editor state
const activeTab = ref('form')
const yamlContent = ref('')
const yamlError = ref<string | null>(null)
const yamlValid = ref(true)
```

**Conversion Functions:**

**Form → YAML:**
```typescript
function formDataToYaml(): string {
  const entityData: Record<string, any> = {
    [entityName.value]: {
      type: entityType.value,
    }
  }
  
  // Add optional fields only if they have values
  const entity = entityData[entityName.value]
  
  if (naturalKeys.value) {
    entity.keys = naturalKeys.value.split(',').map(k => k.trim()).filter(Boolean)
  }
  
  if (surrogateId.value) {
    entity.surrogate_id = surrogateId.value
  }
  
  if (columns.value) {
    entity.columns = columns.value.split(',').map(c => c.trim()).filter(Boolean)
  }
  
  // ... handle other fields (source, depends_on, foreign_keys, etc.)
  
  return yaml.dump(entityData, { 
    indent: 2, 
    lineWidth: 100,
    noRefs: true 
  })
}
```

**YAML → Form:**
```typescript
function yamlToFormData(yamlString: string): void {
  try {
    const parsed = yaml.load(yamlString) as Record<string, any>
    
    if (!parsed || typeof parsed !== 'object') {
      throw new Error('Invalid YAML structure')
    }
    
    // Get first entity key
    const entityKey = Object.keys(parsed)[0]
    const entity = parsed[entityKey]
    
    // Update form fields
    entityName.value = entityKey
    entityType.value = entity.type || 'data'
    naturalKeys.value = entity.keys?.join(', ') || ''
    surrogateId.value = entity.surrogate_id || ''
    columns.value = entity.columns?.join(', ') || ''
    
    // ... update other fields
    
    yamlError.value = null
  } catch (error: any) {
    yamlError.value = error.message
    yamlValid.value = false
  }
}
```

**Tab Switching Logic:**
```typescript
// Sync form to YAML when switching to YAML tab
watch(activeTab, (newTab, oldTab) => {
  if (newTab === 'yaml' && oldTab !== 'yaml') {
    // Switching TO yaml tab - convert form data to YAML
    yamlContent.value = formDataToYaml()
    yamlError.value = null
  } else if (oldTab === 'yaml' && newTab !== 'yaml') {
    // Switching FROM yaml tab - validate and sync to form
    if (yamlValid.value) {
      yamlToFormData(yamlContent.value)
    }
  }
})
```

**Dialog Initialization:**
```typescript
// Reset form when dialog opens
watch(
  () => props.modelValue,
  (newValue) => {
    if (newValue) {
      error.value = null
      formRef.value?.resetValidation()
      suggestions.value = null
      showSuggestions.value = false
      yamlError.value = null
      
      // Initialize YAML content from form data in edit mode
      if (props.mode === 'edit') {
        yamlContent.value = formDataToYaml()
      }
    }
  }
)
```

## User Workflows

### Workflow 1: Form-First Editing

1. User clicks "Edit Entity" button
2. Dialog opens with **Form tab** active
3. User fills in form fields (Entity Name, Type, etc.)
4. User clicks **YAML tab** to see generated YAML
5. YAML editor shows converted entity
6. User can edit YAML directly or switch back to Form
7. Click **Save** to persist changes

### Workflow 2: YAML-First Editing

1. User clicks "Edit Entity" button
2. Dialog opens with Form tab active
3. User clicks **YAML tab** immediately
4. User edits YAML directly (copy/paste, bulk edit)
5. Real-time validation shows any syntax errors
6. User clicks **Form tab** to see parsed form fields
7. Form fields populated from valid YAML
8. Click **Save** to persist changes

### Workflow 3: Copy-Paste from Documentation

1. User finds entity example in docs
2. Opens entity editor and switches to **YAML tab**
3. Copies YAML from documentation
4. Pastes into YAML editor
5. Validation confirms syntax is correct
6. Switches to **Form tab** to review/adjust fields
7. Click **Save** to add entity to configuration

## Error Handling

### YAML Syntax Errors

**Display:**
- Red error banner above YAML editor
- Error message with line number
- Clear description of syntax issue

**Example:**
```
⚠ YAML Syntax Error: bad indentation of a mapping entry at line 3, column 5
```

**Prevention:**
- User cannot switch away from YAML tab with invalid syntax
- Save button disabled when YAML is invalid
- Form won't be corrupted by invalid YAML

### Form Validation Errors

**Display:**
- Red error text under invalid form fields
- Validation triggered on input blur
- Summary of errors prevents Save action

**Example:**
```
Entity Name: [               ]
⚠ Entity name is required
```

## Benefits

### For Beginners

✅ **Form Editor advantages:**
- Guided field-by-field editing
- Prevents syntax errors
- Clear labels and descriptions
- Dropdown selections for enums
- Immediate field validation

### For Advanced Users

✅ **YAML Editor advantages:**
- Direct code manipulation
- Copy/paste entire configurations
- Bulk editing multiple fields
- Familiar text editor interface
- No form field limitations

### For All Users

✅ **Flexibility:**
- Choose editing mode based on task
- Switch modes without losing work
- Learn YAML by comparing Form and YAML views
- Use Form for safety, YAML for speed

## Testing

### Manual Testing Checklist

**Form to YAML Sync:**
- [ ] Fill form fields and switch to YAML tab
- [ ] Verify all form values appear correctly in YAML
- [ ] Edit YAML and switch back to Form
- [ ] Verify form fields updated from YAML

**YAML Validation:**
- [ ] Enter invalid YAML syntax
- [ ] Verify error message appears
- [ ] Verify cannot switch to Form tab
- [ ] Fix YAML and verify error clears

**Dialog Open/Close:**
- [ ] Open entity for editing
- [ ] Verify Form tab is default
- [ ] Verify YAML content initialized
- [ ] Close without saving
- [ ] Reopen and verify state reset

**Save Behavior:**
- [ ] Edit in Form, save, verify persisted
- [ ] Edit in YAML, save, verify persisted
- [ ] Edit in both tabs, save, verify latest changes

### Automated Testing

**Unit Tests (YamlEditor.vue):**
```typescript
describe('YamlEditor', () => {
  it('validates YAML syntax on change', () => {
    // Test validation logic
  })
  
  it('emits update:modelValue on editor change', () => {
    // Test v-model binding
  })
  
  it('displays error message for invalid YAML', () => {
    // Test error display
  })
  
  it('respects readonly prop', () => {
    // Test read-only mode
  })
})
```

**Integration Tests (EntityFormDialog.vue):**
```typescript
describe('EntityFormDialog YAML Integration', () => {
  it('converts form data to YAML on tab switch', () => {
    // Test formDataToYaml()
  })
  
  it('updates form fields from valid YAML', () => {
    // Test yamlToFormData()
  })
  
  it('prevents tab switch with invalid YAML', () => {
    // Test validation prevents switch
  })
  
  it('initializes YAML content in edit mode', () => {
    // Test initial YAML generation
  })
})
```

## Dependencies

### NPM Packages

```json
{
  "dependencies": {
    "monaco-editor": "^0.52.0",
    "@guolao/vue-monaco-editor": "^1.5.6",
    "js-yaml": "^4.1.0"
  },
  "devDependencies": {
    "@types/js-yaml": "^4.0.9"
  }
}
```

**monaco-editor:**
- Professional code editor
- Syntax highlighting
- Error markers
- Auto-completion

**@guolao/vue-monaco-editor:**
- Vue 3 wrapper for Monaco Editor
- Composition API support
- TypeScript types

**js-yaml:**
- YAML parsing and serialization
- Validation and error reporting
- Wide YAML spec support

## Future Enhancements

### Planned Features

**Backend Validation Endpoint:**
```typescript
POST /api/v1/projects/{name}/entities/validate-yaml
{
  "yaml": "entity_name:\n  type: data\n  ..."
}

Response:
{
  "valid": true,
  "errors": [],
  "suggestions": [
    "Consider adding surrogate_id for better performance"
  ]
}
```

**Monaco Editor Features:**
- Auto-completion for entity names
- Hover tooltips with field descriptions
- Go-to-definition for entity references
- Schema validation hints

**Advanced Sync:**
- Track which fields changed
- Preserve comments in YAML
- Format YAML with user preferences
- Diff viewer between Form and YAML

**User Preferences:**
- Default tab (Form or YAML)
- Auto-format YAML on save
- Editor theme (light/dark)
- Font size and family

## Related Documentation

- [User Guide](./USER_GUIDE.md) - General entity editing workflows
- [UI Architecture](./UI_ARCHITECTURE.md) - Frontend architecture details
- [Entity State Management](./ENTITY_STATE_MANAGEMENT.md) - State management patterns
- [Project Guide](./CONFIGURATION_GUIDE.md) - YAML configuration reference

## Support

For issues or questions about the YAML editor feature:

1. Check validation error messages for syntax issues
2. Review YAML configuration examples in docs
3. Use Form editor for guided editing
4. Report bugs with specific YAML examples that fail

## Version History

- **v0.2.0** (December 2025) - Initial YAML editor implementation
  - Dual-mode Form/YAML editing
  - Real-time validation
  - Bidirectional synchronization
  - Monaco Editor integration
