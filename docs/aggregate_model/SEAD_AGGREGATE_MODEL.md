# SEAD Aggregate Model Implementation

**Status:** Implementation Ready  
**Version:** 1.0  
**Date:** February 22, 2026  
**Scope:** SEAD-Specific Implementation

**Related Documents:**
- [AGGREGATE_MODEL_DESIGN.md](./AGGREGATE_MODEL_DESIGN.md) - Generic model design
- [../new_ingester/SEAD_IDENTITY_SYSTEM.md](../new_ingester/SEAD_IDENTITY_SYSTEM.md) - Identity system design
- [../new_ingester/SEAD_IDENTITY_IMPLEMENTATION.md](../new_ingester/SEAD_IDENTITY_IMPLEMENTATION.md) - Identity implementation

---

## Executive Summary

This document provides **SEAD-specific implementation details** for the Generic Aggregate Model, including:

- **Entity Analysis** - Which SEAD tables are aggregates vs dependents
- **Data Population** - SQL scripts to register SEAD entities in the aggregate model
- **Natural Key Patterns** - SEAD-specific business key formats
- **Usage Examples** - Validation, allocation ordering, and queries using SEAD data
- **Deployment Plan** - Phased rollout for SEAD staging and production

**Prerequisites:** Deploy generic aggregate model schema first (see [AGGREGATE_MODEL_DESIGN.md](./AGGREGATE_MODEL_DESIGN.md)).

---

## SEAD Entity Analysis

Based on SEAD database schema analysis (100+ tables), the following entities are classified as **aggregate roots** or **dependents**:

### Primary Aggregates (Priority Phase 1)

These 5 entities are the core data submission entry points and should receive external ID support first:

| Entity Type       | Table Name              | PK Column            | Priority | Natural Keys? | Rationale                          |
|-------------------|-------------------------|----------------------|----------|---------------|-----------------------------------|
| `location`        | `tbl_locations`         | `location_id`        | 10       | ✅ Yes        | Geographic root, no dependencies  |
| `site`            | `tbl_sites`             | `site_id`            | 20       | ✅ Yes        | Archaeological site, depends on location |
| `sample_group`    | `tbl_sample_groups`     | `sample_group_id`    | 30       | ❌ No         | Collection context                |
| `physical_sample` | `tbl_physical_samples`  | `physical_sample_id` | 40       | ✅ Yes        | Core analytical specimen          |
| `analysis_entity` | `tbl_analysis_entities` | `analysis_entity_id` | 50       | ❌ No         | Measurement/observation context   |

**Priority Rationale:**
- Lower number = more fundamental (allocate first)
- Numbers allow inserting intermediate aggregates later (e.g., 15 for region)
- Gaps of 10 provide buffer for future additions

---

### Secondary Aggregates (Already Have UUIDs)

These entities already have UUID columns and can integrate with minimal changes:

| Entity Type          | Table Name              | UUID Column             | Priority | Notes                              |
|----------------------|-------------------------|-------------------------|----------|------------------------------------|
| `bibliography`       | `tbl_biblio`            | `biblio_uuid`           | 5        | Root reference data                |
| `dataset`            | `tbl_datasets`          | `dataset_uuid`          | 60       | Research dataset publication       |
| `dataset_master`     | `tbl_dataset_masters`   | `master_set_uuid`       | 55       | Master dataset registry            |
| `aggregate_dataset`  | `tbl_aggregate_datasets`| `aggregate_dataset_uuid`| 65       | Composite datasets                 |
| `ecocode_system`     | `tbl_ecocode_systems`   | `ecocode_system_uuid`   | 15       | Ecological coding framework        |
| `method`             | `tbl_methods`           | `method_uuid`           | 12       | Analytical methodology             |
| `geochronology`      | `tbl_geochronology`     | `geochron_uuid`         | 35       | Dating information                 |
| `relative_age`       | `tbl_relative_ages`     | `relative_age_uuid`     | 33       | Relative age periods               |
| `rdb_system`         | `tbl_rdb_systems`       | `rdb_system_uuid`       | 16       | Red list database system           |

**Integration Strategy:** These tables already support external IDs (UUIDs). Update to use `external_id` column name for consistency with new aggregates.

---

### Dependent Entities (Not Aggregates)

These entities depend on aggregates and don't require external IDs (use parent's context):

| Entity Type               | Table Name                  | Parent Aggregate   | FK Column           |
|---------------------------|-----------------------------|--------------------| --------------------|
| `feature`                 | `tbl_features`              | `site`             | `site_id`           |
| `horizon`                 | `tbl_horizons`              | `sample_group`     | `sample_group_id`   |
| `analysis_value`          | `tbl_analysis_values`       | `analysis_entity`  | `analysis_entity_id`|
| `analysis_note`           | `tbl_analysis_notes`        | `analysis_entity`  | `analysis_entity_id`|
| `dendro`                  | `tbl_dendro`                | `physical_sample`  | `physical_sample_id`|
| `ceramics`                | `tbl_ceramics`              | `physical_sample`  | `physical_sample_id`|
| `isotope`                 | `tbl_isotopes`              | `analysis_entity`  | `analysis_entity_id`|

**Rationale:** These are owned by aggregates and have no independent meaning. They inherit identity context from parents.

---

### Lookup/Reference Tables (Not in Model)

These are configuration data, not submitted by external systems:

- `tbl_*_types` (activity_types, age_types, contact_types, etc.)
- `tbl_*_lookup` (ceramics_lookup, dendro_lookup, etc.)
- `tbl_colours`, `tbl_dimensions`, `tbl_identification_levels`, etc.

**Rationale:** Static reference data managed separately, not part of data submission workflow.

---

## Data Population Scripts

### Step 1: Register Phase 1 Aggregates

```sql
-- Register primary SEAD entity types (Phase 1 aggregates)
INSERT INTO sead_utility.entity_types 
    (entity_type_key, display_name, table_name, pk_column_name, is_aggregate, supports_natural_keys, description)
VALUES
    ('location', 'Location', 'tbl_locations', 'location_id', TRUE, TRUE, 
     'Geographic entities - countries, regions, specific locations'),
    
    ('site', 'Site', 'tbl_sites', 'site_id', TRUE, TRUE, 
     'Archaeological or sampling sites with geographic context'),
    
    ('sample_group', 'Sample Group', 'tbl_sample_groups', 'sample_group_id', TRUE, FALSE, 
     'Collection context grouping multiple physical samples'),
    
    ('physical_sample', 'Physical Sample', 'tbl_physical_samples', 'physical_sample_id', TRUE, TRUE, 
     'Core analytical specimen - tangible sample collected from site'),
    
    ('analysis_entity', 'Analysis Entity', 'tbl_analysis_entities', 'analysis_entity_id', TRUE, FALSE, 
     'Measurement or observation context for analytical results');

-- Define aggregate priorities and allocation rules
INSERT INTO sead_utility.aggregate_definitions 
    (entity_type_id, aggregate_priority, supports_natural_keys, allow_bulk_allocation, typical_submission_size, description)
SELECT 
    et.entity_type_id,
    CASE et.entity_type_key
        WHEN 'location'        THEN 10
        WHEN 'site'            THEN 20
        WHEN 'sample_group'    THEN 30
        WHEN 'physical_sample' THEN 40
        WHEN 'analysis_entity' THEN 50
    END AS aggregate_priority,
    et.supports_natural_keys,
    TRUE AS allow_bulk_allocation,
    CASE et.entity_type_key
        WHEN 'location'        THEN 50
        WHEN 'site'            THEN 100
        WHEN 'sample_group'    THEN 200
        WHEN 'physical_sample' THEN 500
        WHEN 'analysis_entity' THEN 1000
    END AS typical_submission_size,
    et.description
FROM sead_utility.entity_types et
WHERE et.is_aggregate = TRUE;
```

### Step 2: Register Dependent Entities

```sql
-- Register dependent entities (not aggregates, owned by parents)
INSERT INTO sead_utility.entity_types 
    (entity_type_key, display_name, table_name, pk_column_name, is_aggregate, supports_natural_keys, description)
VALUES
    ('feature', 'Feature', 'tbl_features', 'feature_id', FALSE, FALSE, 
     'Archaeological feature at a site'),
    
    ('horizon', 'Horizon', 'tbl_horizons', 'horizon_id', FALSE, FALSE, 
     'Stratigraphic horizon within sample group'),
    
    ('analysis_value', 'Analysis Value', 'tbl_analysis_values', 'analysis_value_id', FALSE, FALSE, 
     'Measured value from analysis'),
    
    ('analysis_note', 'Analysis Note', 'tbl_analysis_notes', 'analysis_note_id', FALSE, FALSE, 
     'Annotation for analysis entity'),
    
    ('dendro', 'Dendrochronology', 'tbl_dendro', 'dendro_id', FALSE, FALSE, 
     'Dendrochronological analysis of physical sample'),
    
    ('ceramics', 'Ceramics Analysis', 'tbl_ceramics', 'ceramics_id', FALSE, FALSE, 
     'Ceramic material analysis of physical sample'),
    
    ('isotope', 'Isotope Analysis', 'tbl_isotopes', 'isotope_id', FALSE, FALSE, 
     'Isotopic measurements from analysis');
```

### Step 3: Define Dependencies (FK Relationships)

```sql
-- Model parent-child relationships based on SEAD foreign keys
INSERT INTO sead_utility.entity_dependencies 
    (parent_entity_type_id, child_entity_type_id, fk_column_name, is_required, cascade_delete, description)
VALUES
    -- site depends on location
    ((SELECT entity_type_id FROM sead_utility.entity_types WHERE entity_type_key = 'location'),
     (SELECT entity_type_id FROM sead_utility.entity_types WHERE entity_type_key = 'site'),
     'location_id', TRUE, FALSE, 'Site must belong to a location'),
    
    -- sample_group depends on site
    ((SELECT entity_type_id FROM sead_utility.entity_types WHERE entity_type_key = 'site'),
     (SELECT entity_type_id FROM sead_utility.entity_types WHERE entity_type_key = 'sample_group'),
     'site_id', TRUE, FALSE, 'Sample group collected at specific site'),
    
    -- physical_sample depends on sample_group
    ((SELECT entity_type_id FROM sead_utility.entity_types WHERE entity_type_key = 'sample_group'),
     (SELECT entity_type_id FROM sead_utility.entity_types WHERE entity_type_key = 'physical_sample'),
     'sample_group_id', TRUE, FALSE, 'Physical sample belongs to sample group'),
    
    -- analysis_entity depends on physical_sample
    ((SELECT entity_type_id FROM sead_utility.entity_types WHERE entity_type_key = 'physical_sample'),
     (SELECT entity_type_id FROM sead_utility.entity_types WHERE entity_type_key = 'analysis_entity'),
     'physical_sample_id', TRUE, FALSE, 'Analysis performed on physical sample'),
    
    -- feature depends on site
    ((SELECT entity_type_id FROM sead_utility.entity_types WHERE entity_type_key = 'site'),
     (SELECT entity_type_id FROM sead_utility.entity_types WHERE entity_type_key = 'feature'),
     'site_id', TRUE, FALSE, 'Feature located at site'),
    
    -- horizon depends on sample_group
    ((SELECT entity_type_id FROM sead_utility.entity_types WHERE entity_type_key = 'sample_group'),
     (SELECT entity_type_id FROM sead_utility.entity_types WHERE entity_type_key = 'horizon'),
     'sample_group_id', TRUE, FALSE, 'Horizon part of stratigraphic sequence'),
    
    -- analysis_value depends on analysis_entity
    ((SELECT entity_type_id FROM sead_utility.entity_types WHERE entity_type_key = 'analysis_entity'),
     (SELECT entity_type_id FROM sead_utility.entity_types WHERE entity_type_key = 'analysis_value'),
     'analysis_entity_id', TRUE, FALSE, 'Analysis value from specific analysis'),
    
    -- analysis_note depends on analysis_entity
    ((SELECT entity_type_id FROM sead_utility.entity_types WHERE entity_type_key = 'analysis_entity'),
     (SELECT entity_type_id FROM sead_utility.entity_types WHERE entity_type_key = 'analysis_note'),
     'analysis_entity_id', TRUE, FALSE, 'Note about analysis entity'),
    
    -- dendro depends on physical_sample
    ((SELECT entity_type_id FROM sead_utility.entity_types WHERE entity_type_key = 'physical_sample'),
     (SELECT entity_type_id FROM sead_utility.entity_types WHERE entity_type_key = 'dendro'),
     'physical_sample_id', TRUE, FALSE, 'Dendro analysis of wood sample'),
    
    -- ceramics depends on physical_sample
    ((SELECT entity_type_id FROM sead_utility.entity_types WHERE entity_type_key = 'physical_sample'),
     (SELECT entity_type_id FROM sead_utility.entity_types WHERE entity_type_key = 'ceramics'),
     'physical_sample_id', TRUE, FALSE, 'Ceramics analysis of ceramic sample'),
    
    -- isotope depends on analysis_entity
    ((SELECT entity_type_id FROM sead_utility.entity_types WHERE entity_type_key = 'analysis_entity'),
     (SELECT entity_type_id FROM sead_utility.entity_types WHERE entity_type_key = 'isotope'),
     'analysis_entity_id', TRUE, FALSE, 'Isotope measurement from analysis');
```

### Step 4: Calculate Topological Depths

```sql
-- Calculate and assign depths based on dependencies
SELECT * FROM sead_utility.calculate_topological_depth();

-- Verify results
SELECT 
    entity_type_key, 
    is_aggregate, 
    depth_level,
    CASE 
        WHEN is_aggregate THEN (SELECT aggregate_priority FROM sead_utility.aggregate_definitions WHERE entity_type_id = et.entity_type_id)
        ELSE NULL
    END AS priority
FROM sead_utility.entity_types et
WHERE status = 'active'
ORDER BY depth_level, priority NULLS LAST, entity_type_key;
```

**Expected Output:**
```
entity_type_key  | is_aggregate | depth_level | priority
-----------------|--------------|-------------|----------
location         | t            | 0           | 10
site             | t            | 1           | 20
feature          | f            | 2           | NULL
sample_group     | t            | 2           | 30
horizon          | f            | 3           | NULL
physical_sample  | t            | 3           | 40
ceramics         | f            | 4           | NULL
dendro           | f            | 4           | NULL
analysis_entity  | t            | 4           | 50
analysis_note    | f            | 5           | NULL
analysis_value   | f            | 5           | NULL
isotope          | f            | 5           | NULL
```

---

## Natural Key Patterns

### Location (Geographic Entity)

**Pattern:** `COUNTRY_CODE|REGION|LOCATION_NAME`  
**Columns:** `['country_code', 'region_name', 'location_name']`

**Examples:**
```
SWE|Norrland|Abisko
NOR|Trøndelag|Trondheim
FIN|Lapland|Rovaniemi
```

**SQL Registration:**
```sql
UPDATE sead_utility.entity_types
SET natural_key_pattern = 'COUNTRY|REGION|LOCATION',
    natural_key_columns = ARRAY['country_code', 'region_name', 'location_name']
WHERE entity_type_key = 'location';
```

---

### Site (Archaeological/Sampling Site)

**Pattern:** `LAB_CODE|SITE_NAME|COLLECTION_YEAR`  
**Columns:** `['lab_code', 'site_name', 'collection_year']`

**Examples:**
```
LAB_SWEDEN|Abisko_Site_A|2025
LAB_NORWAY|Trondheim_Harbor|2024
LAB_DENMARK|Copenhagen_Middelalderbyen|2023
```

**SQL Registration:**
```sql
UPDATE sead_utility.entity_types
SET natural_key_pattern = 'LAB|SITE|YEAR',
    natural_key_columns = ARRAY['lab_code', 'site_name', 'collection_year']
WHERE entity_type_key = 'site';
```

---

### Physical Sample

**Pattern:** `LAB_CODE|SAMPLE_CODE|SUB_SAMPLE_ID`  
**Columns:** `['lab_code', 'sample_code', 'sub_sample_id']`

**Examples:**
```
LAB_SWEDEN|AS2025-001|A
LAB_NORWAY|TRHB2024-042|B1
LAB_DENMARK|CPMB2023-137|C
```

**SQL Registration:**
```sql
UPDATE sead_utility.entity_types
SET natural_key_pattern = 'LAB|SAMPLE|SUB',
    natural_key_columns = ARRAY['lab_code', 'sample_code', 'sub_sample_id']
WHERE entity_type_key = 'physical_sample';
```

---

## Usage Examples

### Example 1: ValidateSEAD Submission

```sql
-- Validate a dendro submission (sites + samples)
SELECT * FROM sead_utility.validate_entity_submission(
    'a3e4f567-e89b-12d3-a456-426614174000'::UUID,
    ARRAY['site', 'sample_group', 'physical_sample', 'dendro']
);

-- Expected output: Success (all parents present)
-- is_valid | error_code | error_message | missing_parent_types
-- ----------|------------|---------------|--------------------
-- true      | NULL       | NULL          | NULL
```

```sql
-- Validate submission missing location (error case)
SELECT * FROM sead_utility.validate_entity_submission(
    'b4f5g678-e89b-12d3-a456-426614174001'::UUID,
    ARRAY['site', 'sample_group']  -- Missing 'location'!
);

-- Expected output: Error
-- is_valid | error_code              | error_message                           | missing_parent_types
-- ---------|-------------------------|----------------------------------------|--------------------
-- false    | MISSING_PARENT_ENTITIES | Entity type "site" requires parent...  | {location}
```

---

### Example 2: Get SEAD Allocation Order

```sql
-- Get correct order for complex SEAD submission
SELECT * FROM sead_utility.get_allocation_order(
    ARRAY['analysis_entity', 'site', 'location', 'physical_sample', 'sample_group', 'dendro']
);
```

**Expected output (sorted by depth, aggregate priority):**
```
allocation_order | entity_type_key  | depth_level | is_aggregate
-----------------|------------------|-------------|-------------
1                | location         | 0           | t
2                | site             | 1           | t
3                | sample_group     | 2           | t
4                | physical_sample  | 3           | t
5                | analysis_entity  | 4           | t
6                | dendro           | 4           | f
```

**Use Case:** Shape Shifter ingester calls this to determine entity processing order before SQL generation.

---

### Example 3: Query SEAD Aggregate Hierarchy

```sql
-- View all children of 'site' aggregate
SELECT 
    parent_entity_key,
    parent_depth,
    child_entity_key,
    child_depth,
    child_fk_column,
    child_fk_required
FROM sead_utility.v_aggregate_hierarchy
WHERE parent_entity_key = 'site'
ORDER BY child_depth;
```

**Expected output:**
```
parent_entity_key | parent_depth | child_entity_key | child_depth | child_fk_column  | child_fk_required
------------------|--------------|------------------|-------------|------------------|------------------
site              | 1            | feature          | 2           | site_id          | t
site              | 1            | sample_group     | 2           | site_id          | t
```

---

### Example 4: Get All Ancestors of Analysis Entity

```sql
-- Trace full dependency chain for analysis_entity
WITH RECURSIVE ancestors AS (
    -- Base case
    SELECT 
        et.entity_type_id,
        et.entity_type_key,
        0 AS depth
    FROM sead_utility.entity_types et
    WHERE et.entity_type_key = 'analysis_entity'
    
    UNION ALL
    
    -- Recursive case
    SELECT 
        et_parent.entity_type_id,
        et_parent.entity_type_key,
        a.depth + 1
    FROM ancestors a
    JOIN sead_utility.entity_dependencies d 
        ON a.entity_type_id = d.child_entity_type_id
    JOIN sead_utility.entity_types et_parent 
        ON d.parent_entity_type_id = et_parent.entity_type_id
)
SELECT * FROM ancestors ORDER BY depth DESC;
```

**Expected output:**
```
entity_type_key  | depth
-----------------|------
location         | 4
site             | 3
sample_group     | 2
physical_sample  | 1
analysis_entity  | 0
```

---

### Example 5: Get Allocation Statistics

```sql
-- View allocation statistics per SEAD aggregate
SELECT 
    entity_type_key,
    aggregate_priority,
    total_allocations,
    uuid_count,
    natural_key_count,
    committed_count,
    max_allocated_id,
    first_allocation_at,
    last_allocation_at
FROM sead_utility.v_aggregate_allocation_stats
ORDER BY aggregate_priority;
```

---

## API Integration

### Endpoint: Validate SEAD Submission

**Request:**
```http
POST /api/v1/identity/submissions/a3e4f567-e89b-12d3-a456/validate
Content-Type: application/json

{
  "entity_types": ["site", "sample_group", "physical_sample"]
}
```

**Response (Success):**
```json
{
  "is_valid": true,
  "allocation_order": [
    {"order": 1, "entity_type": "site", "depth": 1},
    {"order": 2, "entity_type": "sample_group", "depth": 2},
    {"order": 3, "entity_type": "physical_sample", "depth": 3}
  ]
}
```

**Response (Error - Missing Location):**
```json
{
  "is_valid": false,
  "error": {
    "code": "MISSING_PARENT_ENTITIES",
    "message": "Entity type 'site' requires parent 'location' which is missing from submission",
    "missing_parents": ["location"],
    "suggestion": "Add 'location' entities to submission or ensure they already exist in SEAD"
  }
}
```

---

### Endpoint: Allocate with SEAD Dependencies

**Request:**
```http
POST /api/v1/identity/submissions/a3e4f567-e89b-12d3-a456/allocate-recursive
Content-Type: application/json

{
  "aggregate_type": "site",
  "allocations": [
    {
      "external_id": "LAB_SWEDEN|Abisko_Site_A|2025",
      "external_id_type": "natural_key",
      "dependents": {
        "sample_group": [
          {"external_id": "b4f5g678-e89b-12d3-a456-426614174001"},
          {"external_id": "c5g6h789-e89b-12d3-a456-426614174002"}
        ],
        "feature": [
          {"external_id": "d6h7i890-e89b-12d3-a456-426614174003"}
        ]
      }
    }
  ]
}
```

**Response:**
```json
{
  "allocations": [
    {
      "entity_type": "site",
      "external_id": "LAB_SWEDEN|Abisko_Site_A|2025",
      "external_id_type": "natural_key",
      "sead_id": 12345
    },
    {
      "entity_type": "sample_group",
      "external_id": "b4f5g678-e89b-12d3-a456-426614174001",
      "external_id_type": "uuid",
      "sead_id": 67890
    },
    {
      "entity_type": "sample_group",
      "external_id": "c5g6h789-e89b-12d3-a456-426614174002",
      "external_id_type": "uuid",
      "sead_id": 67891
    },
    {
      "entity_type": "feature",
      "external_id": "d6h7i890-e89b-12d3-a456-426614174003",
      "external_id_type": "uuid",
      "sead_id": 23456
    }
  ]
}
```

---

## Deployment Plan

### Phase 1: Staging Deployment (Week 1)

**Tasks:**
1. Deploy generic aggregate model schema to SEAD staging
2. Run SEAD data population scripts
3. Calculate topological depths
4. Run validation queries

**Deliverables:**
- Populated `entity_types` table (5 aggregates + 7 dependents)
- Populated `aggregate_definitions` table (5 aggregates)
- Populated `entity_dependencies` table (12 relationships)
- Validation report showing correct depths

**Success Criteria:**
- All SEAD entities registered
- Depths correctly calculated (location=0, site=1, sample_group=2, physical_sample=3, analysis_entity=4)
- No circular dependencies detected
- Validation function works with test data

---

### Phase 2: API Integration (Week 2)

**Tasks:**
1. Update Identity Allocation API to use aggregate model
2. Add validation endpoints
3. Add allocation order endpoints
4. Update SEAD ingester to query validation

**Deliverables:**
- `/api/v1/identity/submissions/{id}/validate` endpoint
- `/api/v1/identity/submissions/{id}/allocate-recursive` endpoint
- Updated ingester code
- Integration tests

**Success Criteria:**
- API correctly validates SEAD entity combinations
- API rejects submissions with missing parents
- Ingester uses validation before allocation
- Performance acceptable (< 50ms per validation)

---

### Phase 3: Pilot Submissions (Week 3)

**Tasks:**
1. Run 3-5 pilot SEAD submissions through staging
2. Monitor validation effectiveness
3. Performance tuning
4. Bug fixes and adjustments

**Test Submissions:**
- Dendro submission (location → site → sample_group → physical_sample → dendro)
- Ceramics submission (location → site → sample_group → physical_sample → ceramics)
- Isotope submission (all entities through analysis_entity → isotope)
- Complex submission (multiple aggregates + dependents)
- Error case (missing location)

**Success Criteria:**
- 100% valid submissions pass validation
- 100% invalid submissions rejected with clear error messages
- No performance degradation vs baseline
- Zero data integrity issues

---

### Phase 4: Production Deployment (Week 4)

**Tasks:**
1. Deploy to SEAD production
2. Monitor initial submissions
3. Document lessons learned
4. Plan Phase 2 entities (secondary aggregates with UUIDs)

**Success Criteria:**
- 10+ successful production submissions
- < 5% validation false positives
- Positive feedback from data providers
- Performance within targets

---

## Maintenance

### Adding New SEAD Entity Types

When new entity types need external ID support:

1. **Register entity type:**
   ```sql
   INSERT INTO sead_utility.entity_types (entity_type_key, table_name, pk_column_name, is_aggregate, supports_natural_keys)
   VALUES ('new_entity', 'tbl_new_entity', 'new_entity_id', TRUE/FALSE, TRUE/FALSE);
   ```

2. **If aggregate, define priority:**
   ```sql
   INSERT INTO sead_utility.aggregate_definitions (entity_type_id, aggregate_priority)
   SELECT entity_type_id, 25  -- Choose appropriate priority
   FROM sead_utility.entity_types WHERE entity_type_key = 'new_entity';
   ```

3. **Model dependencies:**
   ```sql
   INSERT INTO sead_utility.entity_dependencies (parent_entity_type_id, child_entity_type_id, fk_column_name)
   VALUES (parent_id, child_id, 'fk_column');
   ```

4. **Recalculate depths:**
   ```sql
   SELECT * FROM sead_utility.calculate_topological_depth();
   ```

5. **Test validation:**
   ```sql
   SELECT * FROM sead_utility.validate_entity_submission(test_uuid, ARRAY['new_entity', ...]);
   ```

---

## Testing

### Unit Tests

```sql
-- Test 1: Verify all SEAD aggregates registered
SELECT COUNT(*) FROM sead_utility.entity_types WHERE is_aggregate = TRUE;
-- Expected: 5

-- Test 2: Verify priorities are unique
SELECT aggregate_priority, COUNT(*) 
FROM sead_utility.aggregate_definitions 
GROUP BY aggregate_priority 
HAVING COUNT(*) > 1;
-- Expected: 0 rows

-- Test 3: Verify no circular dependencies
SELECT DISTINCT entity_type_key
FROM sead_utility.v_entity_dependency_graph
WHERE entity_type_id = ANY(path[1:array_length(path, 1) - 1]);
-- Expected: 0 rows

-- Test 4: Verify depth consistency
SELECT d.child_entity_type_id
FROM sead_utility.entity_dependencies d
JOIN sead_utility.entity_types et_parent ON d.parent_entity_type_id = et_parent.entity_type_id
JOIN sead_utility.entity_types et_child ON d.child_entity_type_id = et_child.entity_type_id
WHERE et_child.depth_level <= et_parent.depth_level;
-- Expected: 0 rows (all children deeper than parents)
```

---

## Troubleshooting

### Issue: Validation Rejects Valid Submission

**Symptom:** API returns `MISSING_PARENT_ENTITIES` but parent exists in database

**Diagnosis:**
```sql
-- Check if parent entity type is registered
SELECT * FROM sead_utility.entity_types WHERE entity_type_key = 'suspected_missing_parent';

-- Check if dependency is modeled
SELECT * FROM sead_utility.entity_dependencies d
JOIN sead_utility.entity_types et_child ON d.child_entity_type_id = et_child.entity_type_id
WHERE et_child.entity_type_key = 'failing_entity';
```

**Solution:** Model the dependency relationship if missing, or verify parent is included in submission.

---

### Issue: Allocation Order Incorrect

**Symptom:** Child entities allocated before parents

**Diagnosis:**
```sql
-- Check depth levels
SELECT entity_type_key, depth_level, is_aggregate
FROM sead_utility.entity_types
ORDER BY depth_level;

-- Recalculate if needed
SELECT * FROM sead_utility.calculate_topological_depth();
```

**Solution:** Depths auto-calculate based on dependencies. Verify dependencies are correctly modeled.

---

## Conclusion

The SEAD aggregate model implementation provides structure and validation for the SEAD identity allocation system. By explicitly modeling entity hierarchies (5 primary aggregates with 7 dependents), the system can:

- **Validate submissions** - Reject invalid entity combinations early
- **Optimize allocation** - Process entities in correct topological order
- **Simplify ingester** - Query allocation order instead of managing dependency logic
- **Support evolution** - Add new entity types without code changes

**Next Steps:**
1. Deploy Phase 1 aggregates to staging
2. Run pilot submissions
3. Deploy to production
4. Plan Phase 2: Secondary aggregates (entities with existing UUIDs)
5. Plan Phase 3: Additional dependents and relationships

**Maintenance Contact:** SEAD development team
