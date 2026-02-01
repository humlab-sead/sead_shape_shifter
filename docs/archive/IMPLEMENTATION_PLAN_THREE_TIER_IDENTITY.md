# Implementation Plan: Three-Tier Identity System

## Executive Summary

This plan details the implementation of a three-tier identity system to replace the current ambiguous `surrogate_id` field. The new system explicitly separates:
1. **Local Identity** (`system_id`) - Auto-managed project-scoped sequence  
2. **Source Business Keys** (`keys`) - Natural keys from source data (uses existing field)
3. **Target System Identity** (`public_id`) - Remote system mapping

**Key Simplification**: We use the existing `keys` field instead of introducing a new `domain_keys` field, making the model cleaner and more intuitive.

**Timeline**: 5-7 weeks total  
**Complexity**: Medium-High  
**Breaking Changes**: Minimal (no migrations needed, test projects only)

---

## Architectural Review

### Current Problems
1. **Ambiguity**: `surrogate_id` starts as local ID, gets copied to `system_id`, then cleared to become public ID
2. **No source reconciliation**: Can't detect duplicates based on source domain keys
3. **Late mapping**: Users can't assign target IDs until reconciliation phase
4. **Confusing data flow**: Identity transformation logic is obscure

### Proposed Solution
```yaml
entities:
  site:
    type: fixed
    # Local identity (auto-managed) - field specifies column name
    system_id: site_id
    
    # Source business keys (uses existing keys field)
    keys: [bygd, raa_nummer]
    
    # Target system identity - field specifies column name  
    public_id: sead_site_id
    
    # Regular columns
    columns: [site_name, coordinate_system, latitude_dd, longitude_dd]
    
    values:
      - site_id: 1              # Auto-managed local ID
        bygd: "Bkaker"           # Business key 1
        raa_nummer: "274939"    # Business key 2
        sead_site_id: 6745      # Target system ID
        site_name: "Bkaker"
        coordinate_system: "WGS84"
        latitude_dd: 23.2
        longitude_dd: 61.2
```

### Benefits
- **Clarity**: Each identity type has explicit purpose and lifecycle
- **Early mapping**: Users can pre-assign target IDs during entity definition
- **Source deduplication**: Domain keys enable duplicate detection within source data
- **Flexible ingestion**: Supports incoming data with or without target IDs
- **Better audit**: Clear separation makes data lineage transparent

---

## Phase 1: Foundation (Week 1-2)

### Goals
- Rename `surrogate_id` → `system_id` throughout codebase
- Clarify that existing `keys` field represents source business keys
- Maintain backward compatibility
- Update core pipeline to use new terminology

### 1.1 Core Model Changes

**File**: `src/model.py`

```python
# EntityConfig class changes:

@property
def system_id(self) -> str:
    """Get the system-managed local identity column name."""
    # Support both old and new names for backward compatibility
    return self.entity_cfg.get("system_id") or self.entity_cfg.get("surrogate_id", "")

@property
def keys(self) -> list[str]:
    """Get the list of source business key columns."""
    # Already exists - just clarifying its purpose as business keys
    return list(self.entity_cfg.get("keys", []) or [])

@property
def public_id(self) -> str:
    """Get the optional target system identity column name."""
    return self.entity_cfg.get("public_id", "")

def add_system_id_column(self, table: pd.DataFrame) -> pd.DataFrame:
    """Add a `system_id` column to `table` with sequential values 1, 2, 3..."""
    system_id: str = self.system_id
    if not system_id:
        return table
    
    if system_id not in table.columns:
        # Add auto-incrementing system ID
        table = table.reset_index(drop=True).copy()
        table[system_id] = range(1, len(table) + 1)
    
    return table
```

**Testing**:
- Update all existing tests using `surrogate_id` to use `system_id`
- Add tests for backward compatibility (old configs still work)
- Test `keys` field usage as business keys
- Add documentation clarifying `keys` purpose

**Files to modify**:
- `src/model.py` - Add properties, update methods
- `src/normalizer.py` - Replace `surrogate_id` with `system_id`
- `src/transforms/utility.py` - Rename `add_surrogate_id` → `add_system_id`
- `tests/` - Update all test fixtures and assertions

**Estimated effort**: 3 days

### 1.2 Backend Model Updates

**File**: `backend/app/models/entity.py`

```python
class EntityData(BaseModel):
    """Entity configuration data."""
    name: str
    type: str
    system_id: str = ""  # Renamed from surrogate_id
    keys: list[str] = []  # Business keys (already exists)
    columns: list[str] = []
    values: list[list[Any]] | None = None
    # ... rest of fields
    
    class Config:
        # Allow old field name for backward compat during transition
        extra = "allow"
```

**Migration helper**:
```python
@field_validator("system_id", mode="before")
@classmethod
def migrate_surrogate_id(cls, v, info):
    """Support legacy 'surrogate_id' field name."""
    if not v and "surrogate_id" in info.data:
        return info.data["surrogate_id"]
    return v
```

**Testing**:
- API endpoint tests with new fields
- Validation tests for `keys` as business keys
- Backward compatibility tests

**Estimated effort**: 2 days

### 1.3 Frontend Updates

**File**: `frontend/src/components/entities/EntityFormDialog.vue`

```typescript
interface FormData {
  name: string
  type: string
  system_id: string  // Renamed from surrogate_id
  keys: string[]  // Business keys (already exists)
  columns: string[]
  // ... rest
}
```

**UI Changes**:
- Rename "Surrogate ID" label → "System ID Column"
- Update "Keys" field label → "Business Keys (Source Identifiers)"
- Add helper tooltip explaining each identity type
- Clarify that keys are used for duplicate detection and reconciliation

**File**: `frontend/src/components/entities/FixedValuesGrid.vue`

- Make `system_id` column read-only (if present)
- Auto-populate on row add (max + 1)
- Auto-renumber on row delete

**Testing**:
- Manual testing of entity editor
- Test fixed-value grid auto-numbering
- Test backward compat with old YAML

**Estimated effort**: 3 days

### 1.4 Documentation Updates

**Files to update**:
- `docs/CONFIGURATION_GUIDE.md` - Document `system_id` and `domain_keys`
- `README.md` - Update examples
- `.github/copilot-instructions.md` - Update terminology

**Estimated effort**: 1 day

**Phase 1 Total**: ~8 days (reduced from 9 due to using existing keys field)

---

## Phase 2: Public ID Support (Week 3-4)

### Goals
- Add `public_id` field to all layers
- Implement UI for assigning target system IDs
- Add validation for unique public IDs
- Enable fixed-value entities to store public IDs

### 2.1 Core Model Extension

**File**: `src/model.py`

```python
@property
def public_id(self) -> str:
    """Get the target system identity column name (optional)."""
    return self.entity_cfg.get("public_id", "")

@property
def has_public_id(self) -> bool:
    """Check if entity has target system identity mapping."""
    return bool(self.public_id)

def validate_public_ids(self, table: pd.DataFrame) -> list[str]:
    """Validate public_id column for uniqueness and data type."""
    errors = []
    
    if not self.public_id or self.public_id not in table.columns:
        return errors
    
    # Check for duplicates
    public_ids = table[self.public_id].dropna()
    if len(public_ids) != len(public_ids.unique()):
        duplicates = public_ids[public_ids.duplicated()].unique().tolist()
        errors.append(f"Duplicate public_ids found: {duplicates}")
    
    # Check data type (should be coercible to string)
    try:
        table[self.public_id].astype(str)
    except Exception as e:
        errors.append(f"Invalid public_id data type: {e}")
    
    return errors
```

**Testing**:
- Test `public_id` property
- Test validation with duplicate public IDs
- Test validation with invalid data types
- Test optional public ID (not all entities need it)

**Estimated effort**: 2 days

### 2.2 Backend Validation Service

**File**: `backend/app/services/validation_service.py`

```python
def _validate_public_ids(self, entity_name: str, entity_config: EntityConfig) -> list[ValidationError]:
    """Validate public_id uniqueness and format."""
    errors = []
    
    if not entity_config.public_id:
        return errors
    
    if entity_config.type != "fixed":
        # Only fixed entities can pre-define public IDs
        # For derived entities, public_id is the column name added later
        return errors
    
    # Validate unique public IDs in fixed data
    errors.extend(entity_config.validate_public_ids(
        self._get_fixed_data_as_dataframe(entity_config)
    ))
    
    return [
        ValidationError(
            entity=entity_name,
            severity="error",
            category="public_id",
            message=err
        ) for err in errors
    ]
```

**Testing**:
- Test fixed entities with public IDs
- Test derived entities (public_id is column name only)
- Test validation errors are reported correctly

**Estimated effort**: 2 days

### 2.3 Frontend Entity Editor

**File**: `frontend/src/components/entities/EntityFormDialog.vue`

Add three-section layout for identity fields:

```vue
<template>
  <!-- Identity Configuration Section -->
  <v-card-subtitle class="text-subtitle-2 font-weight-bold">
    Identity Configuration
    <v-tooltip location="bottom">
      <template v-slot:activator="{ props }">
        <v-icon v-bind="props" size="small" class="ml-1">mdi-information</v-icon>
      </template>
      <div style="max-width: 400px">
        <strong>System ID:</strong> Auto-managed local identifier (1, 2, 3...)<br>
        <strong>Domain Keys:</strong> Source data columns that uniquely identify this entity<br>
        <strong>Public ID:</strong> Optional mapping to target system's identifier
      </div>
    </v-tooltip>
  </v-card-subtitle>

  <!-- System ID (read-only for fixed, editable for others) -->
  <v-text-field
    v-model="formData.system_id"
    label="System ID Column"
    hint="Auto-managed local identifier column name"
    persistent-hint
    :readonly="formData.type === 'fixed'"
    density="compact"
  />

  <!-- Domain Keys (multi-select) -->
  <v-autocomplete
    v-model="formData.domain_keys"
    :items="availableColumnsForUnnest"
    label="Domain Keys"
    hint="Source columns that uniquely identify this entity"
    persistent-hint
    multiple
    chips
    closable-chips
    density="compact"
  />

  <!-- Public ID (optional) -->
  <v-text-field
    v-model="formData.public_id"
    label="Public ID Column (Optional)"
    hint="Column for target system identifier mapping"
    persistent-hint
    clearable
    density="compact"
  />
</template>
```

**File**: `frontend/src/components/entities/FixedValuesGrid.vue`

Update grid to handle public_id:

```typescript
const allColumns = computed(() => {
  const cols = []
  
  // Add system_id if defined (read-only, auto-numbered)
  if (props.systemId) {
    cols.push({
      field: props.systemId,
      headerName: props.systemId,
      editable: false,
      cellClass: 'system-id-column',
      cellStyle: { backgroundColor: '#f5f5f5' }
    })
  }
  
  // Add domain keys
  props.domainKeys.forEach(key => cols.push({
    field: key,
    headerName: key,
    editable: true,
    cellClass: 'domain-key-column'
  }))
  
  // Add public_id if defined (editable)
  if (props.publicId) {
    cols.push({
      field: props.publicId,
      headerName: props.publicId,
      editable: true,
      cellClass: 'public-id-column',
      cellEditor: 'agTextCellEditor'
    })
  }
  
  // Add regular columns
  props.columns.forEach(col => cols.push({
    field: col,
    headerName: col,
    editable: true
  }))
  
  return cols
})

// Auto-populate system_id on row add
function onRowAdded(event: RowAddedEvent) {
  const maxId = Math.max(0, ...gridApi.value.forEachNode(
    node => node.data[props.systemId] || 0
  ))
  event.data[props.systemId] = maxId + 1
}
```

**Testing**:
- Test UI rendering for all three identity fields
- Test fixed-value grid with system_id auto-numbering
- Test public_id editing in grid
- Test validation errors display

**Estimated effort**: 4 days

**Phase 2 Total**: ~8 days

---

## Phase 3: Reconciliation Integration (Week 5-6)

### Goals
- Update reconciliation workflow to use domain_keys
- Auto-populate public_id from reconciliation results
- Support user override of suggested public IDs
- Add duplicate detection based on domain keys

### 3.1 Deduplication Service

**New file**: `src/transforms/deduplication.py`

```python
import pandas as pd
from loguru import logger

def deduplicate_by_domain_keys(
    df: pd.DataFrame,
    domain_keys: list[str],
    keep: str = "first",
    validate_functional_dependency: bool = True
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """
    Deduplicate DataFrame based on domain keys.
    
    Args:
        df: Input DataFrame
        domain_keys: Columns that uniquely identify rows
        keep: Which duplicate to keep ('first', 'last', False)
        validate_functional_dependency: Check if non-key columns are functionally dependent
    
    Returns:
        Tuple of (deduplicated DataFrame, metadata dict)
    """
    if not domain_keys or not all(k in df.columns for k in domain_keys):
        logger.warning(f"Invalid domain keys: {domain_keys}")
        return df, {"duplicates_found": 0}
    
    # Find duplicates
    duplicates = df[df.duplicated(subset=domain_keys, keep=False)]
    dup_count = len(duplicates)
    
    if dup_count == 0:
        return df, {"duplicates_found": 0}
    
    # Validate functional dependency if requested
    if validate_functional_dependency:
        non_key_cols = [c for c in df.columns if c not in domain_keys]
        for col in non_key_cols:
            # Check if each domain key combo maps to unique value
            grouped = df.groupby(domain_keys)[col].nunique()
            if (grouped > 1).any():
                raise ValueError(
                    f"Functional dependency violation: domain keys {domain_keys} "
                    f"do not uniquely determine column '{col}'"
                )
    
    # Drop duplicates
    deduped = df.drop_duplicates(subset=domain_keys, keep=keep)
    
    return deduped, {
        "duplicates_found": dup_count,
        "duplicates_removed": dup_count - len(deduped) + len(df),
        "rows_after": len(deduped)
    }
```

**Testing**:
- Test with valid domain keys
- Test functional dependency validation
- Test with missing domain keys
- Test with no duplicates

**Estimated effort**: 2 days

### 3.2 Reconciliation Service Updates

**File**: `backend/app/services/reconciliation_service.py`

```python
async def match_by_domain_keys(
    self,
    project_name: str,
    entity_name: str,
    target_service: str
) -> dict[str, Any]:
    """
    Match local entities to target system using domain keys.
    
    Returns mapping of local system_id → suggested public_id
    """
    project = self.project_service.load_project(project_name)
    entity_config = project.entities.get(entity_name)
    
    if not entity_config or not entity_config.domain_keys:
        raise ValueError(f"Entity {entity_name} has no domain keys defined")
    
    # Load local entity data
    local_data = await self.shapeshift_service.preview_entity(
        project_name, entity_name, limit=None
    )
    
    # Query target service with domain key values
    matches = []
    for row in local_data.rows:
        domain_key_values = {k: row.get(k) for k in entity_config.domain_keys}
        
        # Call target service API to find match
        target_matches = await self._query_target_service(
            target_service,
            entity_name,
            domain_key_values
        )
        
        if target_matches:
            matches.append({
                "local_system_id": row.get(entity_config.system_id),
                "domain_keys": domain_key_values,
                "suggested_public_id": target_matches[0]["id"],
                "confidence": target_matches[0].get("confidence", 1.0),
                "alternatives": target_matches[1:] if len(target_matches) > 1 else []
            })
    
    return {
        "entity": entity_name,
        "total_rows": len(local_data.rows),
        "matches_found": len(matches),
        "matches": matches
    }
```

**Testing**:
- Test with valid domain keys
- Test with no matches found
- Test with multiple matches (alternatives)
- Test error handling for missing domain keys

**Estimated effort**: 3 days

### 3.3 Frontend Reconciliation UI

**New component**: `frontend/src/components/reconciliation/DomainKeyMatcher.vue`

```vue
<template>
  <v-card>
    <v-card-title>Domain Key Matching</v-card-title>
    <v-card-text>
      <v-alert type="info" variant="tonal" class="mb-4">
        Matching {{ entityName }} records using domain keys: 
        <strong>{{ domainKeys.join(', ') }}</strong>
      </v-alert>

      <v-data-table
        :headers="headers"
        :items="matches"
        :loading="loading"
      >
        <template #item.action="{ item }">
          <v-btn
            size="small"
            color="primary"
            @click="acceptMatch(item)"
            :disabled="item.accepted"
          >
            {{ item.accepted ? 'Accepted' : 'Accept' }}
          </v-btn>
          <v-btn
            v-if="item.alternatives.length > 0"
            size="small"
            variant="outlined"
            @click="showAlternatives(item)"
          >
            {{ item.alternatives.length }} more
          </v-btn>
        </template>
      </v-data-table>
    </v-card-text>
  </v-card>
</template>
```

**Estimated effort**: 3 days

**Phase 3 Total**: ~8 days

---

## Phase 4: Data Ingestion Support (Week 7)

### Goals
- Support incoming data with pre-existing public IDs
- Use domain keys to detect and merge duplicates
- Preserve valid incoming public IDs

### 4.1 Ingester Updates

**File**: `ingesters/sead/ingester.py`

```python
def validate(self, source: str) -> ValidationResult:
    """Validate source data including domain key checks."""
    errors = []
    warnings = []
    
    # Load source data
    df = pd.read_excel(source)
    
    # Check if entity has domain keys defined
    for entity_name, entity_config in self.project.entities.items():
        if not entity_config.domain_keys:
            warnings.append(
                f"Entity {entity_name} has no domain keys - "
                "duplicate detection will not be available"
            )
            continue
        
        # Check if domain keys exist in source
        missing_keys = [
            k for k in entity_config.domain_keys 
            if k not in df.columns
        ]
        if missing_keys:
            errors.append(
                f"Entity {entity_name}: Missing domain keys in source: "
                f"{missing_keys}"
            )
        
        # Check for duplicates based on domain keys
        dup_count = df.duplicated(subset=entity_config.domain_keys).sum()
        if dup_count > 0:
            warnings.append(
                f"Entity {entity_name}: Found {dup_count} duplicates "
                f"based on domain keys {entity_config.domain_keys}"
            )
    
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings
    )

def ingest(self, source: str) -> IngestionResult:
    """Ingest data with domain key deduplication and public ID preservation."""
    df = pd.read_excel(source)
    
    for entity_name, entity_config in self.project.entities.items():
        # Deduplicate using domain keys
        if entity_config.domain_keys:
            df, dup_info = deduplicate_by_domain_keys(
                df,
                entity_config.domain_keys,
                keep="first"
            )
            logger.info(f"Removed {dup_info['duplicates_removed']} duplicates")
        
        # Preserve existing public IDs if present
        if entity_config.public_id and entity_config.public_id in df.columns:
            # Validate public IDs are unique
            public_ids = df[entity_config.public_id].dropna()
            if len(public_ids) != len(public_ids.unique()):
                raise ValueError(
                    f"Duplicate public IDs found in source data for {entity_name}"
                )
    
    # Continue with normal ingestion...
```

**Testing**:
- Test ingestion with domain key deduplication
- Test preservation of incoming public IDs
- Test error handling for duplicate public IDs
- Test warning for missing domain keys

**Estimated effort**: 3 days

### 4.2 CLI Updates

**File**: `backend/app/scripts/ingest.py`

Add flags for domain key behavior:

```python
@app.command()
def ingest(
    # ... existing params ...
    dedupe_domain_keys: bool = typer.Option(
        True,
        "--dedupe-domain-keys/--no-dedupe-domain-keys",
        help="Deduplicate records based on domain keys"
    ),
    preserve_public_ids: bool = typer.Option(
        True,
        "--preserve-public-ids/--no-preserve-public-ids",
        help="Preserve public IDs from source if present"
    ),
    strict_functional_dependency: bool = typer.Option(
        True,
        "--strict-fd/--no-strict-fd",
        help="Validate functional dependencies when deduplicating"
    )
):
    """Ingest data with domain key support."""
    # Implementation...
```

**Estimated effort**: 2 days

**Phase 4 Total**: ~5 days

---

## Testing Strategy

### Unit Tests
- **Core Model** (`tests/test_model.py`)
  - Test `system_id`, `domain_keys`, `public_id` properties
  - Test backward compatibility with `surrogate_id`
  - Test validation functions
  
- **Deduplication** (`tests/transforms/test_deduplication.py`)
  - Test domain key deduplication
  - Test functional dependency validation
  - Test edge cases (empty domain keys, missing columns)

- **Normalizer** (`tests/test_normalizer.py`)
  - Test system_id auto-population
  - Test integration with domain keys
  - Test public_id handling

### Integration Tests
- **Backend API** (`backend/tests/test_entity_endpoints.py`)
  - Test CRUD operations with new fields
  - Test validation errors
  - Test backward compatibility

- **Reconciliation** (`backend/tests/test_reconciliation_service.py`)
  - Test domain key matching
  - Test public_id assignment
  - Test alternative matches

### End-to-End Tests
- Create sample project with all three identity types
- Test full pipeline: Extract → Dedupe → Link → Store
- Test reconciliation workflow
- Test ingestion with pre-existing public IDs

### Manual Testing Checklist
- [ ] Create entity with domain keys via UI
- [ ] Edit fixed-value entity with system_id auto-numbering
- [ ] Assign public IDs in fixed-value grid
- [ ] Run deduplication based on domain keys
- [ ] Perform reconciliation with domain key matching
- [ ] Ingest data with existing public IDs
- [ ] Load old project YAML (backward compat)

---

## Migration & Backward Compatibility

### Handling Legacy Projects

**File**: `src/configuration/migrations.py` (new)

```python
def migrate_surrogate_id_to_system_id(config: dict) -> dict:
    """
    Migrate old 'surrogate_id' field to 'system_id'.
    
    This is called when loading a project configuration.
    """
    config = copy.deepcopy(config)
    
    for entity_name, entity_config in config.get("entities", {}).items():
        # Rename surrogate_id → system_id
        if "surrogate_id" in entity_config and "system_id" not in entity_config:
            entity_config["system_id"] = entity_config.pop("surrogate_id")
            logger.info(
                f"Migrated {entity_name}: surrogate_id → system_id"
            )
    
    return config
```

Call this in `ConfigFactory.create()`:

```python
@staticmethod
def create(source: ConfigLike) -> ShapeShiftProject:
    """Create configuration from source with automatic migrations."""
    data = ConfigFactory._load_data(source)
    
    # Apply migrations
    data = migrate_surrogate_id_to_system_id(data)
    
    return ShapeShiftProject(data)
```

### Deprecation Strategy
1. **Phase 1**: Support both `surrogate_id` and `system_id` (log warning)
2. **Phase 2-4**: Continue dual support (silent)
3. **Future**: Remove `surrogate_id` support entirely (v2.0.0)

---

## Risk Assessment

### Technical Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Breaking existing projects | High | Low | Backward compat layer + migration |
| Performance regression | Medium | Low | Profile deduplication logic |
| UI complexity | Medium | Medium | Good UX design + tooltips |
| Reconciliation API changes | High | Medium | Version API endpoints |

### Mitigation Strategies
1. **Comprehensive testing** - Unit + integration + E2E
2. **Feature flags** - Enable domain key features progressively
3. **Documentation** - Clear migration guide for users
4. **Rollback plan** - Keep old code path available with config flag

---

## Success Criteria

### Phase 1
- [ ] All tests pass with `system_id` instead of `surrogate_id`
- [ ] Old YAML configs load without errors
- [ ] Domain keys can be defined and validated
- [ ] UI shows new identity sections

### Phase 2
- [ ] Public IDs can be assigned in entity editor
- [ ] Fixed-value grid shows and manages public IDs
- [ ] Validation rejects duplicate public IDs
- [ ] Documentation complete

### Phase 3
- [ ] Reconciliation matches using domain keys
- [ ] Public IDs auto-populated from reconciliation
- [ ] User can override suggestions
- [ ] Deduplication works based on domain keys

### Phase 4
- [ ] Ingestion preserves incoming public IDs
- [ ] Domain key deduplication works in ingesters
- [ ] CLI supports new flags
- [ ] Full E2E workflow tested

---

## Documentation Requirements

### User-Facing
1. **Configuration Guide** update:
   - Explain three identity types
   - Provide YAML examples
   - Migration guide from old format

2. **Tutorial**:
   - "Setting up domain keys for your entities"
   - "Pre-mapping target system IDs"
   - "Using reconciliation with domain keys"

3. **API Documentation**:
   - Update endpoint schemas
   - Add examples with new fields

### Developer-Facing
1. **Architecture docs**:
   - Identity system design
   - Data flow diagrams
   - State transitions

2. **Code comments**:
   - Explain `system_id` vs `public_id` distinction
   - Document deduplication algorithm
   - Clarify backward compatibility logic

---

## Timeline Summary

| Phase | Duration | Key Deliverables |
|-------|----------|------------------|
| Phase 1: Foundation | 2 weeks | system_id rename, domain_keys support |
| Phase 2: Public ID | 2 weeks | public_id field, UI updates, validation |
| Phase 3: Reconciliation | 2 weeks | Domain key matching, auto-population |
| Phase 4: Ingestion | 1 week | Ingester updates, CLI flags |
| **Total** | **7 weeks** | **Full three-tier identity system** |

### Resource Requirements
- **Backend developer**: Full-time, all phases
- **Frontend developer**: Part-time Phase 1-2, full-time Phase 3
- **QA/Testing**: Part-time throughout, full-time Phase 4

---

## Conclusion

This implementation plan provides a comprehensive roadmap for transitioning to a three-tier identity system. The phased approach ensures:
- **Minimal disruption** - Backward compatibility maintained
- **Incremental value** - Each phase delivers usable features
- **Risk management** - Testing and validation at every step
- **Clear success metrics** - Measurable outcomes for each phase

The new system will significantly improve data lineage transparency, enable early reconciliation, and support sophisticated duplicate detection based on source domain keys.
