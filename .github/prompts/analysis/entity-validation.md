# Entity Validation Prompt

Analyze entity configuration following Shape Shifter's three-tier identity system and validation rules.

## Prompt Template

```
Analyze the entity "{ENTITY_NAME}" in {PROJECT_FILE} following docs/AI_VALIDATION_GUIDE.md:

### Identity System Check
- [ ] `system_id` is standardized to "system_id" (required)
- [ ] `public_id` exists if entity has FK children or appears in mappings.yml
- [ ] `public_id` column name must end with "_id"
- [ ] `keys` defined for business key matching (optional but recommended)

### Foreign Key Validation
- [ ] All FK relationships use `system_id` values (not external IDs)
- [ ] FK column names match parent's `public_id` column name
- [ ] `local_keys` and `remote_keys` defined correctly
- [ ] No circular dependencies in FK chain
- [ ] Parent entities exist and are processed first

### Data Source & Type
- [ ] Entity type (fixed/derived) matches usage pattern
- [ ] Data source name exists in data_sources section
- [ ] For SQL sources: query or table name specified
- [ ] For fixed sources: values array provided
- [ ] Column mappings align with data source schema

### Unnest Configuration (if present)
- [ ] `key_columns` exist in source data
- [ ] `value_columns` specified for melting
- [ ] `method` is valid (standard/pairs)
- [ ] Result column names don't conflict

### Reconciliation (if present)
- [ ] `strategy` specified (map_to_remote/load_from_remote)
- [ ] `remote_key` matches `public_id`
- [ ] Mapping file exists in mappings/ directory

### Common Anti-Patterns to Check
- ❌ FK values referencing external IDs instead of system_id
- ❌ Missing public_id when entity has FK children
- ❌ Circular FK dependencies
- ❌ Invalid data source references
- ❌ Missing required fields (system_id, data_source, type)

Provide:
1. List of validation errors (MUST fix)
2. Warnings (SHOULD review)
3. Suggestions for improvement
```

## Example Usage

```
Analyze the entity "site" in projects/dendro/shapeshifter.yml following docs/AI_VALIDATION_GUIDE.md:
[... full checklist ...]
```

## Related Documentation
- [AI_VALIDATION_GUIDE.md](../../docs/AI_VALIDATION_GUIDE.md)
- [CONFIGURATION_GUIDE.md](../../docs/CONFIGURATION_GUIDE.md)
- [Three-Tier Identity System](../../AGENTS.md#three-tier-identity-system)
