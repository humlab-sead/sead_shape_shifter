# Reconciliation Persistence Consolidation Proposal

**Author**: Review Date: 2026-06-14  
**Status**: Design Review  
**Scope**: Unify three fragmented mapping persistence paths; prevent data loss from materialized entity edits

---

## Executive Summary

Currently, reconciled links and ID mappings are persisted in separate places with no unified precedence, no synchronization, and no explicit commit semantics. Materialized entities persist edited fixed values on save, but those edits are not synchronized into a single mapping authority. This proposal consolidates mapping persistence into a single sidecar file with explicit commit gates and per-row override support.

---

## Current State Analysis

### 1. Reconciliation Catalog → `<project>-reconciliation.yml`

**Read/Write Path**:
- Write: [backend/app/services/reconciliation/mapping_manager.py:92](backend/app/services/reconciliation/mapping_manager.py#L92) — YAML dump after auto-reconcile
- Read: [backend/app/services/reconciliation/mapping_manager.py:74](backend/app/services/reconciliation/mapping_manager.py#L74) — EntityMappingManager.load_catalog()
- Fields persisted: `metadata` (source, target, thresholds), `links` array (source_value → target_id + confidence)

**Current Behavior**:
- Links written immediately after successful auto-reconciliation match.
- No explicit "commit" step; mutation → immediate persistence.
- Stored separately per entity/target_field (no conflict between concurrent reconciliation jobs).
- No synchronization with mapping sidecar storage.

**Status**: ✅ Auto-save works; ❌ no commit semantics; ❌ isolated from materialization.

---

### 2. Legacy Mapping in `shapeshifter.yml` `options.mapping` (Out of Scope)

**Current Reality**:
- No active project data depends on `options.mapping`.
- This path has no automated write flow and is not part of the proposed design.
- No migration work is required for this proposal.

**Legacy Example**:
```yaml
options:
  mappings:
    taxon:
      local_key: "PCODE"
      remote_key: "taxon_id"
      mapping:
        "PLANT001": 101
        "PLANT002": 102
```

**Status**: Ignored by this design.

---

### 3. Materialized Entity public_id Assignment

**Read/Write Path**:
- Write: [backend/app/services/materialization_service.py:296](backend/app/services/materialization_service.py#L296) writes `public_id` to materialized entity config in shapeshifter.yml
- Read: [backend/app/services/materialization_service.py:72](backend/app/services/materialization_service.py#L72) (in unmaterialize_entity) reads original config to restore it

**Current Behavior**:
- When materializing entity E with columns [id, name, value, SEAD_taxon_id]:
  1. Original entity config is backed up.
  2. Materialized config created with `public_id: "SEAD_taxon_id"` (from original).
  3. User can edit materialized entity rows in the UI (add/remove rows, edit values).
  4. Saved rows are persisted in the materialized fixed-value entity.
  5. Sidecar mapping links are not automatically replaced from the saved materialized values.

**Gap**: User assigns SEAD ID 42 to a taxon row and saves the materialized entity, but the sidecar mapping may still hold older links for that entity.

**Status**: ✅ Materialized fixed values persist on save; ❌ no deterministic sidecar replacement from materialized save; ❌ no unified mapping precedence.

---

## Requirement-by-Requirement Analysis

### REQ #1: User-Assigned Value Overrides All Other Sources ✅ Feasible

**What it means**: If a user manually edits `public_id` in a materialized entity row, that value should win over:
- Auto-reconciled matches in reconciliation catalog
- Batch mappings in mapping sidecar file
- Default business-key lookups

**Current Support**: None. public_id is read-only; no per-row edit UI.

**Design Feasibility**: 
- Add per-row `public_id` column to materialized DataFrame (editable in UI).
- On save, extract all rows where `public_id` is not NULL and write to mapping file.
- On normalization, check mapping file first; use its values (highest priority).
- **Risk**: Requires UI changes; per-row overrides multiply the mapping file size.

**Recommendation**: 
- ✅ Implement with per-row tracking in mapping sidecar.
- Add `source: "manual"` to distinguish user overrides from reconciliation matches.
- Store in format: `{local_key_value: {source: "manual", target_id: 42, notes: "..."}}`

---

### REQ #2: Links from Sidecar Storage Applied in Normalization ✅ Core Requirement

**Interpretation**:
- Normalization must resolve ID links from `<project>-mapping.yml`.
- Committed sidecar links are authoritative for mapped `public_id` values.
- Draft links (`committed_at: null`) are not applied.

**Recommendation**:
- Add sidecar lookup during normalization before final entity storage.
- Apply precedence in sidecar by provenance (`manual` before other committed sources).
- Remove `options.mapping` from the normalization design path.

---

### REQ #3: Target Field Must Be Entity's public_id ✅ Partially Implemented

**Current**: Target field alignment is not enforced consistently across mapping sources.

**Gap**: 
```python
# Current: target field may diverge from entity public_id
mapping_record = {"local_key": "PCODE", "public_id": "arbitrary_col", ...}
```

**Design Decision**: 
- At project load, validate that each entity mapping in sidecar uses the entity `public_id`.
- Raise ValidationError if mismatch; fail fast at config load time.

**Recommendation**:
- ✅ Add sidecar validation when loading mapping catalog.
- Ensure EntityConfig includes `public_id` before sidecar links are applied.
- Error message: `"Mapping for entity '{entity}' specifies public_id '{mapping_public_id}', but entity public_id is '{public_id}'. Keys must match."`

---

### REQ #4: Local Key Should Be Business Key (Not public_id or system_id) ✅ Reasonable

**Current**: `local_key` in mapping data is not validated as a business key.

**Gap**:
```python
# Current: could accidentally use system_id or public_id as the match key
mapping_record = {"local_key": "system_id", ...}  # <- Bad, allows reuse
```

**Design Decision**:
- Validate that sidecar `local_key` is NOT system_id, public_id, or any auto-generated column.
- Validate that `local_key` exists in entity's `keys` (business key list) if available.
- Warn if `local_key` is not in `keys` (allow override with explicit flag).

**Recommendation**:
- ✅ Add validation in mapping catalog load + project validation.
- Provide clear error: `"Mapping local_key '{local_key}' must not be '{forbidden}'. Use a business key from entity.keys: {entity.keys}"`
- Store mapping in catalog with provenance: `{local_key: "PCODE", source: "business_key"}`

---

### REQ #5: Reconciliation Links Require Explicit Export ✅ Phase 1 Only

**Current**: Links are auto-saved immediately after matching. No explicit commit.

**Gap**: Users cannot explicitly copy accepted reconciliation links into sidecar mapping as a controlled operation.

**Design Decision**:
- Keep this proposal limited to explicit export.
- Reconciliation output remains auto-saved in reconciliation catalog.
- User-triggered export copies selected links from reconciliation catalog to mapping sidecar.
  
**Recommendation**:
- ✅ Add explicit export endpoint (copy only) from reconciliation catalog to mapping sidecar.
- Export flow:
  1. User chooses entity/field and link set.
  2. System copies links to mapping sidecar with reconciliation provenance.
  3. Normalization uses sidecar links per precedence rules.

**Implementation Note**: Draft/committed states, review UI, status model changes, audit logging, and rollback are deferred to [docs/proposals/RECONCILIATION_FUTURE_IMPROVEMENTS.md](docs/proposals/RECONCILIATION_FUTURE_IMPROVEMENTS.md).

---

### REQ #6: Materialized Entity Save Replaces Sidecar Links ✅ Simplified

**Current**: Materialized entity edits are persisted as fixed values on save, but sidecar links are not deterministically replaced from that saved state.

**Gap**: Sidecar and saved materialized values can diverge for the same entity.

**Design Decision**:
- On save_materialized_entity endpoint, extract all rows with non-NULL public_id.
- Replace existing sidecar manual links for that entity with extracted links from the saved materialized entity.
- Write replacement entries as: `{local_key_value: {source: "manual", target_id: public_id_value, ...}}`
- Mark as `source: "manual"` (highest precedence, REQ #1).

**Recommendation**:
- ✅ Implement extraction logic in MaterializationService.save_materialized_entity().
- ✅ Use replace-on-save semantics for entity-level sidecar manual links.
- Create new endpoint: `PATCH /projects/{project}/mapping/from-materialized/{entity}` (replacement only).
- Keep behavior deterministic: latest saved materialized state is authoritative for that entity's manual links.

**Risk**: Replacement may remove older manual links that are intentionally absent from the current saved materialized entity.

---

### REQ #7: Move Mappings from shapeshifter.yml to Sidecar File ✅ Desirable, Phased

**Current**: Mapping persistence should be sidecar-based; `options.mapping` is treated as legacy and ignored.

**Gap**:
- Mixing config (what to do) with data (which values to rewrite) in one file.
- Mappings can be very large (100k+ entries); slows YAML load.
- Difficult to version or audit large mappings separately.

**Design Decision**: New sidecar file: `<project>-mapping.yml`

---

## Mapping Sidecar Schema (Detailed)

### File Structure

```yaml
version: "2.0"
metadata:
  created_at: "2026-06-14T10:00:00Z"
  updated_at: "2026-06-14T12:00:00Z"
  project: "my_project"

entities:
  taxon:
    # Entity-level metadata
    local_key: "PCODE"                           # Single-column key
    public_id: "taxon_id"                        # Target column name
    entity_type: "primary"                       # "primary" | "link_entity" | "derived"
    description: "Taxon entities from ArboDAT"
    
    # Link entries: {local_key_value: Link}
    links:
      "PLANT001":
        target_id: 101
        source: "manual"                         # "manual" | "reconciliation" | "import"
        confidence: 1.0                          # 0.0–1.0; null if N/A
        created_at: "2026-06-10T08:00:00Z"
        committed_at: "2026-06-14T10:00:00Z"     # null if not yet committed
        notes: "User manually assigned SEAD taxon ID 101"
        created_by: "roger@humlab.gu.se"
        reviewed_by: null
        
      "PLANT002":
        target_id: 102
        source: "reconciliation"
        confidence: 0.98
        created_at: "2026-06-14T09:00:00Z"
        committed_at: "2026-06-14T11:00:00Z"
        notes: "Auto-matched via reconciliation service (species name match)"
        created_by: "reconciliation-service"
        reviewed_by: "roger@humlab.gu.se"
        
      "PLANT003":
        target_id: null                          # No match yet (draft state)
        source: "reconciliation"
        confidence: 0.72
        created_at: "2026-06-14T12:00:00Z"
        committed_at: null                       # Draft; not yet committed
        notes: "Partial match; requires review"
        created_by: "reconciliation-service"
        reviewed_by: null

  sample:
    # Multi-column compound key
    local_key: ["site_code", "sample_num"]      # Order matters for composite key
    public_id: "sead_sample_id"
    entity_type: "primary"
    description: "Samples from field surveys"
    
    links:
      "SITE001|SAM001":                          # Composite key: "{site_code}|{sample_num}"
        target_id: 5001
        source: "manual"
        confidence: 1.0
        created_at: "2026-06-12T14:00:00Z"
        committed_at: "2026-06-12T16:00:00Z"
        notes: "User assigned based on original field notes"
        created_by: "fieldteam@humlab.gu.se"
        reviewed_by: null

  ecofact:
    local_key: "ecofact_code"
    public_id: "sead_ecofact_id"
    entity_type: "derived"
    description: "Ecological facts (derived from sample analysis)"
    
    links:
      "ECO-CHARCOAL-001":
        target_id: 8042
        source: "import"                         # Imported from external system
        confidence: 0.95
        created_at: "2026-06-01T10:00:00Z"
        committed_at: "2026-06-01T11:00:00Z"
        notes: "Imported from legacy SEAD database"
        created_by: "migration-script"
        reviewed_by: "roger@humlab.gu.se"
```

---

### Schema Details

#### Top-Level Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `version` | string | ✅ Yes | Schema version (e.g., "2.0"). Used for migrations. |
| `metadata` | object | ✅ Yes | File-level metadata (creation, migration history, etc.). |
| `entities` | object | ✅ Yes | Map of entity_name → EntityMapping. |

#### Metadata Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `created_at` | ISO 8601 | ✅ Yes | File creation timestamp. |
| `updated_at` | ISO 8601 | ✅ Yes | Last modification timestamp. |
| `project` | string | ✅ Yes | Project name (for audit).

#### EntityMapping Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `local_key` | string \| string[] | ✅ Yes | Single column name or ordered list of column names for compound keys. |
| `public_id` | string | ✅ Yes | Target column name (must match entity's public_id in shapeshifter.yml). |
| `entity_type` | string | ✅ Yes | "primary" \| "link_entity" \| "derived" (for UI grouping and validation). |
| `description` | string | ❌ No | Human-readable description. |
| `links` | object | ✅ Yes | Map of local_key_value → Link object. |

#### Link Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `target_id` | int \| null | ✅ Yes | SEAD/target ID; null if draft/unmatched. |
| `source` | string | ✅ Yes | "manual" \| "reconciliation" \| "import" (for provenance & precedence). |
| `confidence` | float \| null | ❌ No | 0.0–1.0; null if N/A (e.g., manual overrides). |
| `created_at` | ISO 8601 | ✅ Yes | When link was first created. |
| `committed_at` | ISO 8601 \| null | ✅ Yes | When link was committed to permanent storage; null if draft. |
| `notes` | string | ❌ No | User/system notes (why link was created, review comments). |
| `created_by` | string | ✅ Yes | User email or system identifier (for audit). |
| `reviewed_by` | string \| null | ❌ No | Reviewer email (if applicable). |

---

### Composite Key Encoding

For multi-column local keys, use a stable separator (pipe `|`):

```yaml
sample:
  local_key: ["site_code", "sample_num"]
  links:
    "SITE001|SAM001":      # site_code=SITE001, sample_num=SAM001
      target_id: 5001
      ...
    "SITE001|SAM002":
      target_id: 5002
      ...
```

**Rationale**: Pipes are uncommon in business keys; easily parsed and indexed.

**Edge cases**:
- If a business key contains `|`, escape it: `SITE\|001|SAM001` (decode before lookup).
- For null values in keys, use special string `<NULL>`: `SITE001|<NULL>`.

---

### Import/Export Formats

The sidecar file is primarily YAML, but support additional formats for large projects:

| Format | Use Case | File | Pros | Cons |
|--------|----------|------|------|------|
| **YAML** | Default; < 5MB | `<project>-mapping.yml` | Human-readable, git-friendly | Slow to parse large files |
| **JSON** | API responses | In-memory only | Fast parsing, standard | Less readable |
| **CSV** (bulk export) | Spreadsheet review | `<project>-mapping.csv` | Excel-friendly | No nested metadata |
| **Parquet** (future) | Very large projects (> 50MB) | `<project>-mapping.parquet` | Efficient I/O, column compression | Requires binary tools |

---

### Precedence & Conflict Resolution

**During normalization**, apply links in this order (first match wins):

```
1. Check mapping sidecar for local_key_value
   a. If source="manual" & committed_at is set   → Use (highest priority)
   b. If source="reconciliation" & committed_at   → Use
   c. If source="import" & committed_at           → Use
    d. If committed_at is NULL (draft)             → Skip to step 2

2. Check reconciliation catalog (if exists)
   a. If EntityResolutionSet exists & committed   → Use
   b. If EntityResolutionSet exists but draft     → Skip (not authoritative yet)

3. No match found                                  → Leave public_id empty/unset
```

**Write-time sync rule** (when syncing from a saved materialized entity):

```
FOR entity E:
  1. Extract all non-NULL public_id rows from saved materialized entity E.
  2. Drop existing sidecar manual links for entity E.
  3. Insert extracted links as source="manual".
  4. Keep reconciliation/import links unchanged unless explicitly replaced by commit/import flows.
```

---

### Python Models

```python
# src/reconciliation/mapping_model.py

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field

class LinkSource(str, Enum):
    """Source of a mapping link."""
    MANUAL = "manual"                 # User-assigned
    RECONCILIATION = "reconciliation" # Auto-matched
    IMPORT = "import"                 # Loaded from external import flow

class EntityType(str, Enum):
    """Entity classification for UI and validation."""
    PRIMARY = "primary"               # Main entity (taxon, sample)
    LINK_ENTITY = "link_entity"       # M:N junction
    DERIVED = "derived"               # Computed from other entities

class Link(BaseModel):
    """A single local→target ID mapping."""
    target_id: Optional[int] = None
    source: LinkSource
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    created_at: datetime
    committed_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_by: str
    reviewed_by: Optional[str] = None

class EntityMapping(BaseModel):
    """Mapping configuration and links for one entity."""
    local_key: Union[str, list[str]]  # Single or compound key
    public_id: str
    entity_type: EntityType = EntityType.PRIMARY
    description: Optional[str] = None
    links: dict[str, Link] = Field(default_factory=dict)

class Metadata(BaseModel):
    """File-level metadata."""
    created_at: datetime
    updated_at: datetime
    project: str

class MappingCatalog(BaseModel):
    """Root mapping sidecar structure."""
    version: str = "2.0"
    metadata: Metadata
    entities: dict[str, EntityMapping]

    def get_link(self, entity_name: str, local_key_value: str) -> Optional[Link]:
        """Retrieve a link by entity and local key value."""
        entity = self.entities.get(entity_name)
        return entity.links.get(local_key_value) if entity else None

    def set_link(self, entity_name: str, local_key_value: str, link: Link) -> None:
        """Set or update a link."""
        if entity_name not in self.entities:
            raise KeyError(f"Entity '{entity_name}' not found in mapping catalog")
        self.entities[entity_name].links[local_key_value] = link
        self.metadata.updated_at = datetime.utcnow()

    def committed_links_by_entity(self, entity_name: str) -> dict[str, Link]:
        """Return only committed links for an entity."""
        entity = self.entities.get(entity_name)
        if not entity:
            return {}
        return {k: v for k, v in entity.links.items() if v.committed_at is not None}

    def draft_links_by_entity(self, entity_name: str) -> dict[str, Link]:
        """Return only draft (uncommitted) links for an entity."""
        entity = self.entities.get(entity_name)
        if not entity:
            return {}
        return {k: v for k, v in entity.links.items() if v.committed_at is None}
```

---

### File Size & Performance Considerations

**Estimated sizes** (for a typical project with 20 entities):

| Scenario | Avg Links per Entity | Total Links | YAML Size | Load Time (parsing) |
|----------|----------------------|-------------|-----------|---------------------|
| Small (pilot) | 100 | 2,000 | ~200 KB | < 10 ms |
| Medium (production) | 5,000 | 100,000 | ~10 MB | ~50 ms |
| Large (multi-year) | 50,000 | 1,000,000 | ~100 MB | ~500 ms |

**Optimization strategies**:

1. **In-memory cache** (API layer):
   - Load mapping on project open; keep in memory.
   - Invalidate on save; reload from disk.
   - Reduces I/O for repeat normalizations.

2. **Indexing** (for large files):
   - Pre-compute entity → links map on load.
   - Use hash for O(1) local_key lookups.
   - Already implicit in YAML dict structure.

3. **Compression** (for > 50MB):
   - Consider gzip: `<project>-mapping.yml.gz`
   - Reduces disk footprint by ~80%.
   - Add decompression logic to loader.

4. **Archival** (cleanup strategy):
   - Move links older than N days to `<project>-mapping-archive.yml`.
   - Keeps "active" mapping file small and fast.

---

### API Endpoints (Mapping CRUD)

```
# List all links for an entity
GET    /projects/{project}/mapping/{entity}
       → Returns: { links: {...}, metadata: {...} }

# Get a single link
GET    /projects/{project}/mapping/{entity}/{local_key_value}
       → Returns: { link: Link, entity_mapping: EntityMapping }

# Create/update a link (manual override)
PUT    /projects/{project}/mapping/{entity}/{local_key_value}
       Body: { target_id: 101, notes: "...", reviewed_by: "..." }
       → Returns: { link: Link, status: "created" | "updated" }

# Bulk sync from materialized entity
PATCH  /projects/{project}/mapping/from-materialized/{entity}
  Body: { extracted_links: [...] }
       → Returns: { links_added: N, links_updated: M, status: "ok" }

# Commit draft links (from reconciliation)
POST   /projects/{project}/mapping/commit
       Body: { entity: "taxon", links: [...] }
       → Returns: { committed_count: N, audit_id: "...", status: "ok" }

# Delete a link
DELETE /projects/{project}/mapping/{entity}/{local_key_value}
       → Returns: { status: "deleted", link: Link }

# Export mapping to CSV
GET    /projects/{project}/mapping/export?format=csv&entity=taxon
       → Returns: CSV file download

# Import mapping from CSV
POST   /projects/{project}/mapping/import
       Files: { file: <CSV file> }
       → Returns: { imported: N, errors: [...], status: "ok" }
```

---

### Storage & Loading

**Loading behavior**:
- On project load, check for `<project>-mapping.yml`.
- If exists, parse YAML and load into MappingCatalog.
- If not exists (new project), create empty MappingCatalog.
- Cache in memory for performance (invalidate on save).

---

## Recommendation

- ✅ Implement sidecar structure as detailed above.
- ✅ Support compound local_keys (ordered list syntax).
- ✅ Add provenance fields: `source`, `committed_at`, `created_by`, `reviewed_by`.
- ✅ Implement Python models (Pydantic v2).
- ✅ Expose API endpoints for mapping CRUD.
- ✅ Plan for file compression if projects exceed 50MB.
- ⚠️ Deprecate manual YAML edits; enforce API-only writes in Phase 2.

---

## Proposed Architecture

### Read/Write Precedence (Highest to Lowest)

```
1. Mapping Sidecar File (<project>-mapping.yml)
   ├── Manual overrides (source: "manual")          ← REQ #6
  ├── Exported reconciliation links                ← REQ #5
    └── Imported links (source: "import")           ← REQ #7

2. Reconciliation Catalog (<project>-reconciliation.yml)
  ├── Auto-saved reconciliation output
   └── Entity metadata (thresholds, etc.)

3. Project Configuration (shapeshifter.yml)
   ├── Entity keys (local_key config for mapping)
   └── public_id definition                         ← REQ #3
```

### Data Flow on Normalization

```
Load Project YAML
  ↓
Validate mapping metadata (REQ #3, #4)
  ↓
Load Mapping Sidecar File (if exists)
  ↓
For each entity:
  1. Extract public_id column (auto-generated or user-configured)
  2. Load materialized entity (if any)
  3. Check mapping sidecar for local_key matches
     - If found (source: "manual" or "committed"):   → Apply, highest priority (REQ #1)
     - If found (source: "reconciliation"):          → Apply, lower priority
     - If not found:                                  → Continue to next step
  4. Store processed entity with public_id values
  ↓
On Save Materialized Entity:
  1. Extract rows where public_id is not NULL/empty (REQ #6)
  2. Replace entity manual links in mapping sidecar
  3. Write to <project>-mapping.yml with source: "manual"
  4. Persist updated mapping to disk
```

---

## Implementation Roadmap

### Phase 0: Mapping Sidecar Schema and Models (1 sprint)

**Deliverables**:
- [ ] Define mapping sidecar schema and Pydantic models (`src/reconciliation/mapping_model.py`).
- [ ] Implement `MappingManager` (CRUD + sidecar I/O, load/save `<project>-mapping.yml`).
- [ ] Add sidecar validation: `public_id` alignment and `local_key` business-key checks (REQ #3, #4).
- [ ] Add tests: schema load/save, validation errors, compound key encoding.

**Risk**: Schema design decisions here constrain all downstream phases.

### Phase 1: Replace `options.mapping` with Sidecar Storage (2–3 sprints)

**Deliverables**:
- [ ] Add `MappingService` to API (list, get, put, delete link endpoints).
- [ ] Integrate sidecar lookup into normalization pipeline (REQ #2).
- [ ] Implement extraction logic in `MaterializationService.save_materialized_entity()` with replace-on-save semantics (REQ #6).
- [ ] Add "Sync to Mapping" endpoint (`PATCH /projects/{project}/mapping/from-materialized/{entity}`).
- [ ] Update `ProjectMapper` to validate mapping configuration against project schema.
- [ ] Add tests: normalization with sidecar links, materialized replace-on-save, conflict-free sync.

**Risk**: Normalization pipeline integration must not break existing entity processing.

### Phase 2: Export Reconciliation Links to Sidecar (1–2 sprints)

**Deliverables**:
- [ ] Add explicit "Export to Mapping" endpoint (copy reconciliation catalog links to sidecar).
- [ ] Expose export action in reconciliation UI.
- [ ] Add tests: export flow, provenance preserved, no overwrite of existing manual links.

**Risk**: Precedence rules must correctly favour existing manual sidecar links over exported reconciliation links.



---

## Decision Record

| Decision                                     | Rationale                                           | Alternative Considered                       |
|----------------------------------------------|-----------------------------------------------------|----------------------------------------------|
| **One mapping sidecar file per project**     | Simplified versioning, single source of truth.      | Separate files per entity (more fragmented). |
| **Provenance fields (source, committed_at)** | Audit trail; easy to understand why mapping exists. | No metadata (loses context).                 |
| **Compound local_key support**               | Real entities have multi-column business keys.      | Single-column only (limits use cases).       |
| **Manual overrides win (precedence)**        | User intent should never be silently overridden.    | Auto-reconciliation wins (loses user work).  |
| **Replace-on-save for manual links**         | Deterministic sync from saved materialized entity.  | Merge with conflict prompts (more complex).  |
| **Phased implementation**                    | Reduces risk; allows early feedback.                | Big bang (harder to debug).                  |

---

## Risks & Mitigations

| Risk                                    | Impact                                                   | Mitigation                                                             |
|-----------------------------------------|----------------------------------------------------------|------------------------------------------------------------------------|
| **Mapping file size explosion**         | Slow I/O; merge conflicts in version control.            | Implement cleanup (deduplicate, remove old entries); archive strategy. |
| **User unaware of precedence**          | Manual overrides silently ignored if mapping not synced. | Add UI hints; auto-sync by default; warn if stale.                     |
| **Reconciliation workflow expansion**   | Advanced review lifecycle may add complexity later.       | Keep current scope to explicit export; track advanced workflow separately. |

| **Compound local_key complexity**       | Harder to display/edit in UI.                            | Phase 1: single-column only; add compound key support in Phase 2.      |

---

## Conclusion

Your proposal addresses a real data-loss gap in the materialization workflow. The seven requirements are **feasible and well-motivated**. 

**Key decisions**:
1. ✅ Consolidate into a single mapping sidecar file (REQ #7).
2. ✅ Enforce precedence with sidecar-first mapping and explicit reconciliation export (REQ #1, #2, #5).
3. ✅ Validate remote_key and local_key at config load time (REQ #3, #4).
4. ✅ Extract user edits from materialized entities and persist to mapping (REQ #6).
5. ✅ Keep reconciliation workflow in this proposal to explicit export only.
6. ⚠️ Defer advanced reconciliation lifecycle features to [docs/proposals/RECONCILIATION_FUTURE_IMPROVEMENTS.md](docs/proposals/RECONCILIATION_FUTURE_IMPROVEMENTS.md).

**Note**: Since reconciliation workflows and project-specific mappings have not been used in production projects yet, there is **no backward compatibility requirement**. The sidecar file is a fresh start, and `options.mapping` is out of scope for this design.

**Implementation Priority**: Phase 0 (schema + models) → Phase 1 (sidecar storage + materialization) → Phase 2 (reconciliation export).

**Estimated Effort**: 4–6 sprints (assuming 2-week sprints; 2–3 months).

