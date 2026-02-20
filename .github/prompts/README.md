# Shape Shifter Prompt Catalog

Reusable prompt templates for common development tasks. Copy and customize as needed.

## Quick Access

**Analysis Prompts**:
- [Entity Validation](analysis/entity-validation.md) - Validate entity configuration
- [Dependency Check](analysis/dependency-check.md) - Analyze entity dependencies
- [YAML Review](analysis/yaml-review.md) - Review shapeshifter.yml files

**Implementation Prompts**:
- [Add Backend Endpoint](implementation/add-endpoint.md) - Create new API endpoint
- [Add Validator](implementation/add-validator.md) - Create constraint validator
- [Add Data Loader](implementation/add-loader.md) - Create data source loader

**Testing Prompts**:
- [Core Tests](testing/core-test.md) - Test core processing pipeline
- [Backend Tests](testing/backend-test.md) - Test backend services/endpoints
- [Frontend Tests](testing/frontend-test.md) - Test Vue components

## Usage

1. **Open prompt file** from this catalog
2. **Copy the template** to Copilot Chat
3. **Replace placeholders** (marked with `{VARIABLE}`)
4. **Submit** to get targeted assistance

## VS Code Tips

### Pin Frequently Used Prompts
Right-click prompt file → **Add to Favorites** for quick access

### Create Snippets
Add to **User Snippets** for ultra-fast access:
```json
{
  "Shape Shifter: Entity Validation": {
    "prefix": "ss-validate",
    "body": [
      "Analyze entity ${1:name} following docs/AI_VALIDATION_GUIDE.md"
    ]
  }
}
```

### Keyboard Shortcuts
- `Ctrl+Shift+P` → "Chat: Open Chat"
- Paste prompt template
- `Ctrl+Enter` to submit

## Project Context

All prompts reference:
- **AGENTS.md** - Architectural patterns and conventions
- **docs/AI_VALIDATION_GUIDE.md** - Entity validation rules
- **docs/CONFIGURATION_GUIDE.md** - Complete YAML reference
- **docs/TESTING_GUIDE.md** - Testing procedures

## Contributing

Add new prompts following the pattern:
1. Create `.md` file in appropriate category
2. Include clear description and checklist
3. Use `{PLACEHOLDER}` syntax for variables
4. Reference relevant documentation
5. Update this README with new prompt
