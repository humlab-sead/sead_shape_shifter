# Proposal: Entity Semantic Roles (Fact vs Lookup Distinction)

## Status

- **Proposed feature**
- **Scope**: Configuration schema, validation layer
- **Goal**: Make fact-versus-lookup intent explicit to enable better validation and prevent identity confusion

## Summary

Add an optional `role` field to entity configuration with values `lookup` and `fact`. This enables validators to catch common modeling errors (e.g., fact entities reusing lookup identifiers) and makes domain modeling intent explicit without overloading the existing `type` field.

## Problem

In complex target models with lookup tables and fact tables, the distinction between these two roles is currently implicit. Authors communicate intent only through naming conventions, foreign key structure, and comments.

This leads to configuration mistakes that are syntactically valid but semantically wrong:

**Example from Arbodat relative-dating scenario:**

```yaml
# Lookup table - defines age categories
relative_ages:
  type: sql
  public_id: relative_age_id
  keys: [archdat]

# Fact table - records which samples have which ages
relative_dating:
  type: sql
  public_id: relative_age_id  # ❌ Accidentally reused lookup's public_id!
  foreign_keys:
    - entity: relative_ages
      local_keys: [ArchDat]
      remote_keys: [archdat]
```

The fact entity mistakenly uses the lookup's `public_id` as its own identity. This is a semantic error that validators cannot currently detect because the distinction between lookup and fact is not declared.

Additional problems:
- No validation that lookups have stable keys suitable for referencing
- No coverage checks that fact values resolve in referenced lookups
- Difficult to auto-generate accurate data dictionaries
- Reconciliation UI cannot prioritize lookups for external matching

## Scope

- Add optional `role` field to entity schema (`"lookup" | "fact" | null`)
- Enable role-aware validation rules
- Support coverage checks in future phases
- Preserve backward compatibility (role is optional)

## Non-Goals

- Changing the semantics of the existing `type` field
- Making `role` required (it remains optional)
- Supporting other role types beyond lookup/fact in initial implementation
- Automatic role inference (authors must declare explicitly)

## Current Behavior

Entity `type` field serves a different purpose - it describes the **data source**:

```typescript
export type EntityType = 'entity' | 'sql' | 'fixed' | 'csv' | 'xlsx' | 'openpyxl'
```

The `type` field is heavily used in data loading and validation pipelines. Lookup tables and fact tables can be sourced from the same data source type (e.g., both from `sql`).

Semantic roles (what purpose the entity serves) are orthogonal to source types (where data comes from).

## Proposed Design

### Schema Change

Add optional `role` field to entity configuration:

```yaml
relative_ages:
  type: sql                    # Data source (unchanged)
  role: lookup                 # Semantic role (new)
  public_id: relative_age_id
  keys: [archdat]

relative_dating:
  type: sql
  role: fact
  public_id: relative_dating_id  # Own identity, not lookup's
  foreign_keys:
    - entity: relative_ages
      local_keys: [ArchDat]
      remote_keys: [archdat]
```

### Validation Rules

#### Phase 1: Role Requirements

When `role: lookup`:
- **ERROR** if `public_id` is missing (lookups are meant to be referenced)
- **ERROR** if `keys` is missing (lookups need stable identity)
- **WARNING** if duplicate key values detected
- **INFO** if no other entities reference this lookup

When `role: fact`:
- **ERROR** if `public_id` matches a referenced lookup's `public_id` (identity confusion)
- **WARNING** if entity has no foreign keys (orphaned fact table?)

#### Phase 2: Coverage Checks (Future)

Support coverage validation on foreign keys:

```yaml
relative_dating:
  role: fact
  foreign_keys:
    - entity: relative_ages
      local_keys: [ArchDat]
      remote_keys: [archdat]
      coverage: required  # All ArchDat values must exist in lookup
```

### When to Use Each Role

**Use `role: lookup`** when:
- Entity defines reference/master data (species, methods, locations, age categories)
- Entity is referenced by multiple other entities
- Values are relatively stable and curated
- You want validation to enforce `public_id` and stable `keys`

**Use `role: fact`** when:
- Entity records observations, measurements, or events
- Entity references multiple lookups or parent entities
- You want validation to catch lookup identity confusion
- You want coverage checks against referenced lookups (future)

**Omit `role`** when:
- Entity is an intermediate transformation
- Entity is a merged parent or aggregate
- Entity purpose is unclear or mixed
- Special validation is not needed

## Alternatives Considered

### Alternative A: Add `type: lookup` to existing `type` field

```yaml
relative_ages:
  type: lookup  # Overload existing field
```

**Rejected because:**
- Conflates data source with semantic role
- `type` field is heavily used in data loading pipelines
- Lookup and fact can both come from same source type (e.g., `sql`)
- Creates migration complexity and backward compatibility issues

### Alternative B: Add `lookup_refs` configuration block

Original Proposal 2 from umbrella document suggested:

```yaml
relative_dating:
  type: fact
  lookup_refs:
    - raw_column: ArchDat
      lookup_entity: relative_ages
      lookup_key: archdat
```

**Deferred because:**
- `lookup_refs` duplicates information already in `foreign_keys`
- Role distinction is more fundamental than specific lookup reference syntax
- Can be added later if needed, building on role foundation

## Risks And Tradeoffs

### Risks
- Authors may misunderstand when to use each role
- Role semantics may evolve as more use cases emerge
- Validation rules may be too strict for some edge cases

### Mitigation
- Make `role` optional - no change required for existing projects
- Document clear guidance in USER_GUIDE.md and CONFIGURATION_GUIDE.md
- Use WARNING level for most checks, ERROR only for clear mistakes
- Provide examples in documentation

### Tradeoffs
- Additional field adds minor complexity to schema
- Requires author effort to classify entities
- Benefit: Prevents costly modeling errors early in development

## Testing And Validation

### Unit Tests
- Test role validation rules (require public_id for lookups, etc.)
- Test identity confusion detection (fact reusing lookup public_id)
- Test coverage check parsing (future phase)

### Integration Tests
- Test Arbodat relative-dating scenario with roles specified
- Verify validation catches known bad patterns
- Test role omitted scenarios (should pass without errors)

### Documentation Tests
- Add role field to entity schema documentation
- Update USER_GUIDE.md core concepts section
- Add examples to CONFIGURATION_GUIDE.md

## Acceptance Criteria

- [ ] `role` field added to entity schema (Pydantic models, TypeScript types, JSON schema)
- [ ] Phase 1 validation rules implemented and tested
- [ ] Existing projects without `role` continue to work (backward compatible)
- [ ] Documentation updated (USER_GUIDE.md, CONFIGURATION_GUIDE.md)
- [ ] Arbodat scenario validates correctly with roles specified
- [ ] Identity confusion error catches fact reusing lookup public_id

## Recommended Delivery Order

1. **Schema foundation** - Add `role` field to models (backend, frontend, core)
2. **Basic validation** - Implement Phase 1 validation rules
3. **Identity confusion detection** - Add cross-entity validation for public_id reuse
4. **Documentation** - Update guides with examples
5. **Phase 2 (future)** - Coverage checks on foreign keys

## Open Questions

- Should we support other role values beyond `lookup` and `fact`? (e.g., `dimension`, `aggregate`, `bridge`)
- Should role be inferrable from entity structure, or always explicit?
- Should missing role be WARNING in strict validation mode?

## Final Recommendation

Implement the `role` field as specified with Phase 1 validation rules. The field should be:
- **Optional** - no migration burden for existing projects
- **Explicit** - authors declare intent, no automatic inference
- **Extensible** - design allows future role types if needed
- **Clear separation** - keeps `type` for data source, `role` for semantic purpose

This provides immediate value (identity confusion detection) with a clear path to future enhancements (coverage checks, better reconciliation, accurate data dictionaries).

The change is minimal, backward compatible, and directly addresses the Arbodat relative-dating problem case.
