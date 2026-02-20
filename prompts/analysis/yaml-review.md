# YAML Configuration Review Prompt

Comprehensive review of shapeshifter.yml project files.

## Prompt Template

```
Review {PROJECT_FILE} for correctness and best practices:

### 1. Project Metadata
- [ ] `name` is unique and descriptive
- [ ] `description` explains project purpose
- [ ] `version` follows semantic versioning
- [ ] `workspace` path is valid

### 2. Data Sources Section
- [ ] All sources have unique names
- [ ] Required driver fields present (host, dbname, etc.)
- [ ] Environment variables properly formatted: ${VAR_NAME}
- [ ] Connection strings valid for driver type
- [ ] Optional parameters appropriate for driver

### 3. Entities Section
- [ ] All entities follow three-tier identity system
- [ ] Entity names are snake_case
- [ ] No duplicate entity names
- [ ] Required fields present for entity type
- [ ] Foreign keys reference existing entities
- [ ] No circular dependencies

### 4. Mappings Section (if present)
- [ ] Mapping files exist in mappings/ directory
- [ ] `remote_key` matches entity's `public_id`
- [ ] `local_keys` match entity's `keys` configuration
- [ ] File paths are relative to workspace

### 5. Cross-References
- [ ] All data_source names reference defined sources
- [ ] All FK entity references exist
- [ ] All unnest source_entity references exist
- [ ] Column names in FK match between entities

### 6. Environment Variables & Directives
- [ ] `${ENV_VAR}` syntax correct
- [ ] `@include: path/to/file.yml` paths valid
- [ ] `@value: data_sources.source_name.field` paths valid
- [ ] No unresolved references

### 7. Best Practices
- [ ] Fixed entities use fixed data source
- [ ] Consistent naming conventions
- [ ] Public IDs follow `{entity}_id` pattern
- [ ] Business keys defined for important entities
- [ ] Comments explain complex configurations

### 8. Performance Considerations
- [ ] SQL queries optimized (no SELECT *)
- [ ] Data source queries have reasonable limits
- [ ] Deep dependency chains avoided (depth < 5)
- [ ] Unnest operations target specific columns

Provide:
1. **Critical Issues** - Must fix before processing
2. **Warnings** - Should review
3. **Improvements** - Nice to have
4. **Summary** - Overall config quality score
```

## Example Usage

```
Review projects/dendro/shapeshifter.yml for correctness and best practices:
[... full review ...]
```

## Quick Validation Checklist

For rapid validation, use this condensed version:

```
Quick validation check for {PROJECT_FILE}:
- Identity system correct?
- FK relationships valid?
- Data sources defined?
- Any circular dependencies?
- Environment variables resolvable?
```

## Related Documentation
- [CONFIGURATION_GUIDE.md](../../docs/CONFIGURATION_GUIDE.md)
- [AI_VALIDATION_GUIDE.md](../../docs/AI_VALIDATION_GUIDE.md)
