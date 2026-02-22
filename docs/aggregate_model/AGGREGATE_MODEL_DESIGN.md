# Generic Aggregate Model for Identity Systems

**Status:** Design Phase  
**Version:** 1.0  
**Date:** February 22, 2026  
**Scope:** Generic (Domain-Agnostic)

---

## Executive Summary

This document defines a **generic database model** for tracking aggregate roots and their dependencies within an identity allocation system. The model is domain-agnostic and can be used by any system that needs to:

- **Understand entity hierarchies** - Know which entities are aggregates vs dependents
- **Enforce consistency** - Validate that parent aggregates exist before creating children
- **Optimize allocation** - Batch allocate aggregate + all dependents in correct order
- **Enable topological sorting** - Process entities in dependency order
- **Support cascading operations** - Understand impact of deleting/rolling back aggregates
- **Validate submissions** - Reject invalid entity combinations

**Key Innovation:** The model stores **entity type metadata** (not instance data), enabling the identity system to reason about relationships without coupling to specific domain schemas.

---

## Goals & Non-Goals

### Goals

✅ **Generic Model** - Works for any domain (SEAD, finance, healthcare, etc.)  
✅ **Metadata-Driven** - Stores entity type information, not instance data  
✅ **Hierarchy Support** - Models aggregate roots and their dependents  
✅ **Dependency Tracking** - Captures FK relationships and constraints  
✅ **Versioning** - Supports schema evolution over time  
✅ **Query-Friendly** - Optimized for common identity system operations

### Non-Goals

❌ **Instance Tracking** - Does not replace identity_allocations table  
❌ **Domain Logic** - Does not enforce domain-specific business rules  
❌ **Runtime Discovery** - Metadata is configured, not auto-discovered  
❌ **Cross-System** - Designed for single database schema per deployment

---

## Database Schema

### Core Principles

1. **Entity Types** - Every table that receives external IDs is an "entity type"
2. **Aggregates** - Designate which entity types are aggregate roots
3. **Dependencies** - Model parent-child relationships (FK constraints)
4. **Metadata** - Store table names, column names, validation rules
5. **Versions** - Support schema evolution with versioned entity definitions

### Schema Diagram

```
┌──────────────────────────────────────┐
│ entity_types                          │  ← Registry of all entity types
│ • entity_type_id (PK)                 │
│ • entity_type_key (unique)            │
│ • table_name, pk_column_name          │
│ • is_aggregate (boolean)              │
│ • depth_level (topological)           │
└──────────────────────────────────────┘
              ↓
┌──────────────────────────────────────┐
│ aggregate_definitions                 │  ← Metadata for aggregate roots
│ • aggregate_id (PK)                   │
│ • entity_type_id (FK)                 │
│ • aggregate_priority (order)          │
│ • supports_natural_keys (bool)        │
└──────────────────────────────────────┘
              ↓
┌──────────────────────────────────────┐
│ entity_dependencies                   │  ← Parent-child relationships
│ • dependency_id (PK)                  │
│ • parent_entity_type_id (FK)          │
│ • child_entity_type_id (FK)           │
│ • fk_column_name (in child table)     │
│ • is_required (bool)                  │
│ • cascade_delete (bool)               │
└──────────────────────────────────────┘
```

---

## Table Definitions

### 1. Entity Types Registry

**Purpose:** Central registry of all entity types that participate in the identity system.

```sql
CREATE TABLE IF NOT EXISTS sead_utility.entity_types (
    -- Primary key
    entity_type_id SERIAL PRIMARY KEY,
    
    -- Unique identifier for this entity type (e.g., 'site', 'location', 'sample')
    entity_type_key TEXT NOT NULL UNIQUE,
    
    -- Display name for humans
    display_name TEXT NOT NULL,
    
    -- Domain model metadata
    table_name TEXT NOT NULL,           -- e.g., 'tbl_sites'
    schema_name TEXT NOT NULL DEFAULT 'public',
    pk_column_name TEXT NOT NULL,       -- e.g., 'site_id'
    
    -- External identifier metadata
    external_id_column_name TEXT NULL,  -- e.g., 'site_external_id' (NULL if not yet implemented)
    external_id_type_column_name TEXT NULL,  -- e.g., 'site_external_id_type'
    content_hash_column_name TEXT NULL, -- e.g., 'content_hash'
    
    -- Aggregate classification
    is_aggregate BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Topological sorting metadata
    depth_level INTEGER NULL,           -- 0 = root, 1 = children of root, etc.
    
    -- Natural key support
    supports_natural_keys BOOLEAN NOT NULL DEFAULT FALSE,
    natural_key_pattern TEXT NULL,      -- e.g., 'LAB_CODE|SITE_NAME|YEAR'
    natural_key_columns TEXT[] NULL,    -- e.g., ['lab_code', 'site_name', 'collection_year']
    
    -- Lifecycle status
    status TEXT NOT NULL DEFAULT 'active',  -- 'active', 'deprecated', 'migrating'
    
    -- Schema version tracking
    schema_version INTEGER NOT NULL DEFAULT 1,
    
    -- Audit
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by TEXT NOT NULL DEFAULT CURRENT_USER,
    
    -- Optional metadata
    description TEXT NULL,
    notes TEXT NULL,
    external_data JSONB NULL,
    
    -- Constraints
    CONSTRAINT chk_depth_level CHECK (depth_level >= 0),
    CONSTRAINT chk_status CHECK (status IN ('active', 'deprecated', 'migrating'))
);

-- Indexes
CREATE UNIQUE INDEX uq_entity_type_table 
    ON sead_utility.entity_types(schema_name, table_name);
    
CREATE INDEX idx_entity_types_aggregate 
    ON sead_utility.entity_types(is_aggregate) 
    WHERE is_aggregate = TRUE;
    
CREATE INDEX idx_entity_types_status 
    ON sead_utility.entity_types(status);
    
CREATE INDEX idx_entity_types_depth 
    ON sead_utility.entity_types(depth_level) 
    WHERE depth_level IS NOT NULL;

-- Trigger for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_entity_types_updated_at
    BEFORE UPDATE ON sead_utility.entity_types
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Comments
COMMENT ON TABLE sead_utility.entity_types IS 
    'Registry of all entity types that participate in the identity allocation system. Stores metadata about tables, columns, and aggregate classification.';
    
COMMENT ON COLUMN sead_utility.entity_types.entity_type_key IS 
    'Unique identifier for this entity type (e.g., "site", "location", "sample"). Used in API calls and configuration.';
    
COMMENT ON COLUMN sead_utility.entity_types.depth_level IS 
    'Topological depth: 0 = no dependencies (root aggregate), 1 = child of root, etc. NULL = not yet calculated.';
    
COMMENT ON COLUMN sead_utility.entity_types.natural_key_columns IS 
    'Array of column names used to construct natural keys. Example: ["lab_code", "site_name", "year"]';
```

---

### 2. Aggregate Definitions

**Purpose:** Designates which entity types are aggregate roots and stores aggregate-specific metadata.

```sql
CREATE TABLE IF NOT EXISTS sead_utility.aggregate_definitions (
    -- Primary key
    aggregate_id SERIAL PRIMARY KEY,
    
    -- Link to entity type
    entity_type_id INTEGER NOT NULL UNIQUE,
    
    -- Aggregate metadata
    aggregate_priority INTEGER NOT NULL DEFAULT 100,  -- Lower = process first
    
    -- Identity allocation strategy
    supports_natural_keys BOOLEAN NOT NULL DEFAULT FALSE,
    default_id_type TEXT NOT NULL DEFAULT 'uuid',  -- 'uuid' or 'natural_key'
    
    -- Validation rules
    require_content_hash BOOLEAN NOT NULL DEFAULT FALSE,
    allow_bulk_allocation BOOLEAN NOT NULL DEFAULT TRUE,
    max_batch_size INTEGER NULL DEFAULT 1000,
    
    -- Lifecycle management
    supports_updates BOOLEAN NOT NULL DEFAULT FALSE,  -- Phase 2: change detection
    supports_soft_delete BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- External system hints
    typical_submission_size INTEGER NULL,  -- Expected avg records per submission
    
    -- Audit
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Optional metadata
    description TEXT NULL,
    notes TEXT NULL,
    external_data JSONB NULL,
    
    -- Foreign key
    CONSTRAINT fk_entity_type FOREIGN KEY (entity_type_id) 
        REFERENCES sead_utility.entity_types(entity_type_id) ON DELETE CASCADE,
    
    -- Constraints
    CONSTRAINT chk_aggregate_priority CHECK (aggregate_priority > 0),
    CONSTRAINT chk_default_id_type CHECK (default_id_type IN ('uuid', 'natural_key')),
    CONSTRAINT chk_max_batch_size CHECK (max_batch_size IS NULL OR max_batch_size > 0)
);

-- Indexes
CREATE INDEX idx_aggregates_priority 
    ON sead_utility.aggregate_definitions(aggregate_priority);
    
CREATE INDEX idx_aggregates_natural_keys 
    ON sead_utility.aggregate_definitions(supports_natural_keys) 
    WHERE supports_natural_keys = TRUE;

-- Trigger for updated_at
CREATE TRIGGER trg_aggregate_definitions_updated_at
    BEFORE UPDATE ON sead_utility.aggregate_definitions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Comments
COMMENT ON TABLE sead_utility.aggregate_definitions IS 
    'Designates which entity types are aggregate roots and stores aggregate-specific configuration for identity allocation.';
    
COMMENT ON COLUMN sead_utility.aggregate_definitions.aggregate_priority IS 
    'Processing priority: lower values processed first. Use for topological ordering (e.g., location=10, site=20, sample=30).';
    
COMMENT ON COLUMN sead_utility.aggregate_definitions.supports_updates IS 
    'Phase 2 feature: whether this aggregate supports change detection and UPDATE operations via content hash comparison.';
```

---

### 3. Entity Dependencies (Relationships)

**Purpose:** Models parent-child relationships between entity types based on foreign key constraints.

```sql
CREATE TABLE IF NOT EXISTS sead_utility.entity_dependencies (
    -- Primary key
    dependency_id SERIAL PRIMARY KEY,
    
    -- Parent-child relationship
    parent_entity_type_id INTEGER NOT NULL,
    child_entity_type_id INTEGER NOT NULL,
    
    -- Dependency metadata
    dependency_type TEXT NOT NULL DEFAULT 'foreign_key',  -- 'foreign_key', 'composition', 'aggregation'
    
    -- Foreign key details (in child table)
    fk_column_name TEXT NOT NULL,       -- e.g., 'location_id' in tbl_sites
    fk_constraint_name TEXT NULL,       -- e.g., 'fk_sites_location'
    
    -- Cardinality
    cardinality TEXT NOT NULL DEFAULT 'many_to_one',  -- 'one_to_one', 'one_to_many', 'many_to_one', 'many_to_many'
    
    -- Constraint enforcement
    is_required BOOLEAN NOT NULL DEFAULT TRUE,  -- Is FK nullable?
    cascade_delete BOOLEAN NOT NULL DEFAULT FALSE,
    cascade_rollback BOOLEAN NOT NULL DEFAULT TRUE,
    
    -- Allocation hints
    allocate_together BOOLEAN NOT NULL DEFAULT FALSE,  -- Should parent+child be allocated atomically?
    
    -- Audit
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Optional metadata
    description TEXT NULL,
    notes TEXT NULL,
    external_data JSONB NULL,
    
    -- Foreign keys
    CONSTRAINT fk_parent_entity_type FOREIGN KEY (parent_entity_type_id) 
        REFERENCES sead_utility.entity_types(entity_type_id) ON DELETE CASCADE,
        
    CONSTRAINT fk_child_entity_type FOREIGN KEY (child_entity_type_id) 
        REFERENCES sead_utility.entity_types(entity_type_id) ON DELETE CASCADE,
    
    -- Prevent duplicate dependencies
    CONSTRAINT uq_dependency UNIQUE (parent_entity_type_id, child_entity_type_id, fk_column_name),
    
    -- Prevent self-referencing (use separate table for hierarchies)
    CONSTRAINT chk_no_self_reference CHECK (parent_entity_type_id != child_entity_type_id),
    
    -- Constraints
    CONSTRAINT chk_dependency_type CHECK (dependency_type IN ('foreign_key', 'composition', 'aggregation')),
    CONSTRAINT chk_cardinality CHECK (cardinality IN ('one_to_one', 'one_to_many', 'many_to_one', 'many_to_many'))
);

-- Indexes
CREATE INDEX idx_dependencies_parent 
    ON sead_utility.entity_dependencies(parent_entity_type_id);
    
CREATE INDEX idx_dependencies_child 
    ON sead_utility.entity_dependencies(child_entity_type_id);
    
CREATE INDEX idx_dependencies_cascade 
    ON sead_utility.entity_dependencies(cascade_delete, cascade_rollback);
    
CREATE INDEX idx_dependencies_allocate_together
    ON sead_utility.entity_dependencies(allocate_together)
    WHERE allocate_together = TRUE;

-- Trigger for updated_at
CREATE TRIGGER trg_entity_dependencies_updated_at
    BEFORE UPDATE ON sead_utility.entity_dependencies
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Comments
COMMENT ON TABLE sead_utility.entity_dependencies IS 
    'Models parent-child relationships between entity types. Used for topological sorting, validation, and cascade operations.';
    
COMMENT ON COLUMN sead_utility.entity_dependencies.dependency_type IS 
    'Type of relationship: foreign_key (standard DB FK), composition (strong ownership), aggregation (weak reference).';
    
COMMENT ON COLUMN sead_utility.entity_dependencies.allocate_together IS 
    'Hint: should parent+child IDs be allocated in same API call for atomicity?';
```

---

## Supporting Views

### 1. Aggregate Hierarchy View

**Purpose:** Flattened view of all aggregates with their direct children.

```sql
CREATE OR REPLACE VIEW sead_utility.v_aggregate_hierarchy AS
SELECT 
    a.aggregate_id,
    a.aggregate_priority,
    
    -- Parent (aggregate) details
    et_parent.entity_type_id AS parent_entity_type_id,
    et_parent.entity_type_key AS parent_entity_key,
    et_parent.table_name AS parent_table_name,
    et_parent.pk_column_name AS parent_pk_column,
    et_parent.depth_level AS parent_depth,
    
    -- Child details (if any)
    et_child.entity_type_id AS child_entity_type_id,
    et_child.entity_type_key AS child_entity_key,
    et_child.table_name AS child_table_name,
    et_child.pk_column_name AS child_pk_column,
    et_child.depth_level AS child_depth,
    
    -- Dependency details
    d.dependency_id,
    d.fk_column_name AS child_fk_column,
    d.is_required AS child_fk_required,
    d.cascade_delete,
    d.allocate_together
    
FROM sead_utility.aggregate_definitions a
JOIN sead_utility.entity_types et_parent 
    ON a.entity_type_id = et_parent.entity_type_id
LEFT JOIN sead_utility.entity_dependencies d 
    ON et_parent.entity_type_id = d.parent_entity_type_id
LEFT JOIN sead_utility.entity_types et_child 
    ON d.child_entity_type_id = et_child.entity_type_id
    
WHERE et_parent.status = 'active'
ORDER BY a.aggregate_priority, et_parent.depth_level, et_child.depth_level;

COMMENT ON VIEW sead_utility.v_aggregate_hierarchy IS 
    'Flattened view of aggregate roots with their immediate children. Used for allocation planning and validation.';
```

### 2. Entity Dependency Graph View

**Purpose:** Recursive view showing full dependency chains.

```sql
CREATE OR REPLACE VIEW sead_utility.v_entity_dependency_graph AS
WITH RECURSIVE dependency_tree AS (
    -- Base case: root entities (no parents)
    SELECT 
        et.entity_type_id,
        et.entity_type_key,
        et.table_name,
        et.is_aggregate,
        et.depth_level,
        NULL::INTEGER AS parent_entity_type_id,
        NULL::TEXT AS parent_entity_key,
        0 AS tree_depth,
        ARRAY[et.entity_type_id] AS path,
        et.entity_type_key::TEXT AS path_string
    FROM sead_utility.entity_types et
    WHERE et.status = 'active'
      AND NOT EXISTS (
          SELECT 1 
          FROM sead_utility.entity_dependencies d 
          WHERE d.child_entity_type_id = et.entity_type_id
      )
    
    UNION ALL
    
    -- Recursive case: children
    SELECT 
        et_child.entity_type_id,
        et_child.entity_type_key,
        et_child.table_name,
        et_child.is_aggregate,
        et_child.depth_level,
        dt.entity_type_id AS parent_entity_type_id,
        dt.entity_type_key AS parent_entity_key,
        dt.tree_depth + 1,
        dt.path || et_child.entity_type_id,
        dt.path_string || ' → ' || et_child.entity_type_key
    FROM dependency_tree dt
    JOIN sead_utility.entity_dependencies d 
        ON dt.entity_type_id = d.parent_entity_type_id
    JOIN sead_utility.entity_types et_child 
        ON d.child_entity_type_id = et_child.entity_type_id
    WHERE et_child.entity_type_id != ALL(dt.path)  -- Prevent cycles
)
SELECT * FROM dependency_tree
ORDER BY tree_depth, entity_type_key;

COMMENT ON VIEW sead_utility.v_entity_dependency_graph IS 
    'Recursive view showing full dependency chains from root aggregates to all descendants. Detects cycles.';
```

### 3. Allocation Statistics View

**Purpose:** Aggregate-level statistics from identity_allocations table.

```sql
CREATE OR REPLACE VIEW sead_utility.v_aggregate_allocation_stats AS
SELECT 
    et.entity_type_id,
    et.entity_type_key,
    et.table_name,
    a.aggregate_priority,
    
    -- Allocation counts
    COUNT(ia.allocation_uuid) AS total_allocations,
    COUNT(DISTINCT ia.submission_uuid) AS submission_count,
    COUNT(ia.allocation_uuid) FILTER (WHERE ia.status = 'allocated') AS allocated_count,
    COUNT(ia.allocation_uuid) FILTER (WHERE ia.status = 'committed') AS committed_count,
    COUNT(ia.allocation_uuid) FILTER (WHERE ia.status = 'rolled_back') AS rolled_back_count,
    
    -- ID type distribution
    COUNT(ia.allocation_uuid) FILTER (WHERE ia.external_id_type = 'uuid') AS uuid_count,
    COUNT(ia.allocation_uuid) FILTER (WHERE ia.external_id_type = 'natural_key') AS natural_key_count,
    
    -- Temporal
    MIN(ia.created_at) AS first_allocation_at,
    MAX(ia.created_at) AS last_allocation_at,
    
    -- Current state
    MAX(ia.alloc_integer_id) AS max_allocated_id
    
FROM sead_utility.entity_types et
JOIN sead_utility.aggregate_definitions a 
    ON et.entity_type_id = a.entity_type_id
LEFT JOIN sead_utility.identity_allocations ia 
    ON et.table_name = ia.table_name 
   AND et.pk_column_name = ia.column_name
    
WHERE et.status = 'active'
GROUP BY et.entity_type_id, et.entity_type_key, et.table_name, a.aggregate_priority
ORDER BY a.aggregate_priority;

COMMENT ON VIEW sead_utility.v_aggregate_allocation_stats IS 
    'Aggregate-level statistics showing allocation counts, ID types, and current state per aggregate root.';
```

---

## PostgreSQL Functions

### 1. Calculate Topological Depth

**Purpose:** Automatically calculate and set depth_level for all entity types.

```sql
CREATE OR REPLACE FUNCTION sead_utility.calculate_topological_depth()
RETURNS TABLE(
    entity_type_id INTEGER,
    entity_type_key TEXT,
    depth_level INTEGER
) AS $$
DECLARE
    v_max_depth INTEGER := 0;
    v_affected_rows INTEGER;
BEGIN
    -- Reset all depth levels
    UPDATE sead_utility.entity_types SET depth_level = NULL;
    
    -- Iteratively assign depths
    FOR v_max_depth IN 0..100 LOOP
        IF v_max_depth = 0 THEN
            -- Set depth 0: entities with no parents
            UPDATE sead_utility.entity_types et
            SET depth_level = 0
            WHERE et.depth_level IS NULL
              AND NOT EXISTS (
                  SELECT 1 
                  FROM sead_utility.entity_dependencies d 
                  WHERE d.child_entity_type_id = et.entity_type_id
              );
        ELSE
            -- Set depth N: entities whose parents are all at depth < N
            UPDATE sead_utility.entity_types et
            SET depth_level = v_max_depth
            WHERE et.depth_level IS NULL
              AND EXISTS (
                  SELECT 1 
                  FROM sead_utility.entity_dependencies d
                  WHERE d.child_entity_type_id = et.entity_type_id
              )
              AND NOT EXISTS (
                  SELECT 1
                  FROM sead_utility.entity_dependencies d
                  JOIN sead_utility.entity_types et_parent 
                      ON d.parent_entity_type_id = et_parent.entity_type_id
                  WHERE d.child_entity_type_id = et.entity_type_id
                    AND (et_parent.depth_level IS NULL OR et_parent.depth_level >= v_max_depth)
              );
        END IF;
        
        GET DIAGNOSTICS v_affected_rows = ROW_COUNT;
        EXIT WHEN v_affected_rows = 0;
    END LOOP;
    
    -- Return results
    RETURN QUERY 
    SELECT et.entity_type_id, et.entity_type_key, et.depth_level
    FROM sead_utility.entity_types et
    WHERE et.status = 'active'
    ORDER BY et.depth_level NULLS LAST, et.entity_type_key;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION sead_utility.calculate_topological_depth() IS 
    'Calculates and sets depth_level for all entity types based on dependency relationships. Depth 0 = no parents.';
```

### 2. Validate Entity Submission

**Purpose:** Validate that a submission contains entities in correct order.

```sql
CREATE OR REPLACE FUNCTION sead_utility.validate_entity_submission(
    p_submission_uuid UUID,
    p_entity_types TEXT[]  -- Array of entity_type_keys in submission
)
RETURNS TABLE(
    is_valid BOOLEAN,
    error_code TEXT,
    error_message TEXT,
    missing_parent_types TEXT[]
) AS $$
DECLARE
    v_child_type TEXT;
    v_parent_types TEXT[];
    v_missing_parents TEXT[];
BEGIN
    -- Check each entity type has its required parents
    FOREACH v_child_type IN ARRAY p_entity_types LOOP
        -- Get required parent types
        SELECT ARRAY_AGG(DISTINCT et_parent.entity_type_key)
        INTO v_parent_types
        FROM sead_utility.entity_types et_child
        JOIN sead_utility.entity_dependencies d 
            ON et_child.entity_type_id = d.child_entity_type_id
        JOIN sead_utility.entity_types et_parent 
            ON d.parent_entity_type_id = et_parent.entity_type_id
        WHERE et_child.entity_type_key = v_child_type
          AND d.is_required = TRUE
          AND et_parent.status = 'active';
        
        -- Check if parents are in submission
        IF v_parent_types IS NOT NULL THEN
            SELECT ARRAY_AGG(parent_type)
            INTO v_missing_parents
            FROM UNNEST(v_parent_types) AS parent_type
            WHERE parent_type != ALL(p_entity_types);
            
            IF v_missing_parents IS NOT NULL THEN
                RETURN QUERY SELECT 
                    FALSE,
                    'MISSING_PARENT_ENTITIES'::TEXT,
                    format('Entity type "%s" requires parent types %s which are missing from submission', 
                           v_child_type, v_missing_parents::TEXT),
                    v_missing_parents;
                RETURN;
            END IF;
        END IF;
    END LOOP;
    
    -- All checks passed
    RETURN QUERY SELECT TRUE, NULL::TEXT, NULL::TEXT, NULL::TEXT[];
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION sead_utility.validate_entity_submission IS 
    'Validates that a submission contains all required parent entities before allocating child entities.';
```

### 3. Get Allocation Order

**Purpose:** Return entity types in correct allocation order (topologically sorted).

```sql
CREATE OR REPLACE FUNCTION sead_utility.get_allocation_order(
    p_entity_types TEXT[]  -- Array of entity_type_keys to sort
)
RETURNS TABLE(
    allocation_order INTEGER,
    entity_type_key TEXT,
    entity_type_id INTEGER,
    table_name TEXT,
    is_aggregate BOOLEAN,
    depth_level INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ROW_NUMBER() OVER (ORDER BY et.depth_level, 
                                    CASE WHEN et.is_aggregate THEN 0 ELSE 1 END,
                                    a.aggregate_priority NULLS LAST,
                                    et.entity_type_key)::INTEGER AS allocation_order,
        et.entity_type_key,
        et.entity_type_id,
        et.table_name,
        et.is_aggregate,
        et.depth_level
    FROM sead_utility.entity_types et
    LEFT JOIN sead_utility.aggregate_definitions a 
        ON et.entity_type_id = a.entity_type_id
    WHERE et.entity_type_key = ANY(p_entity_types)
      AND et.status = 'active'
    ORDER BY allocation_order;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION sead_utility.get_allocation_order IS 
    'Returns entity types in correct allocation order: depth-first, aggregates before dependents, sorted by priority.';
```

---

## Usage Examples

### Example 1: Register Entity Types (Domain-Specific)

**Note:** Entity type registration is domain-specific. The SQL structure below shows the generic pattern, but actual entity types, table names, and dependencies will vary by domain.

**For SEAD-specific implementation**, see [SEAD_AGGREGATE_MODEL.md](./SEAD_AGGREGATE_MODEL.md) which includes:
- Complete SEAD entity analysis (5 primary aggregates + 7 dependents)
- Data population scripts with SEAD table names
- Natural key patterns for SEAD entities
- FK dependency definitions

**Generic Pattern:**
```sql
-- Step 1: Register entity types
INSERT INTO {schema}.entity_types 
    (entity_type_key, display_name, table_name, pk_column_name, is_aggregate, supports_natural_keys)
VALUES
    ('{aggregate_root_key}', '{DisplayName}', '{table_name}', '{pk_column}', TRUE, {true|false}),
    ('{child_entity_key}', '{ChildName}', '{child_table}', '{child_pk}', FALSE, {true|false});

-- Step 2: Define aggregate priorities
INSERT INTO {schema}.aggregate_definitions 
    (entity_type_id, aggregate_priority, supports_natural_keys)
SELECT entity_type_id, 
       {priority_value},  -- e.g., 10, 20, 30...
       supports_natural_keys
FROM {schema}.entity_types
WHERE is_aggregate = TRUE;

-- Step 3: Define dependencies (FK relationships)
INSERT INTO {schema}.entity_dependencies 
    (parent_entity_type_id, child_entity_type_id, fk_column_name, is_required)
VALUES
    ((SELECT entity_type_id FROM {schema}.entity_types WHERE entity_type_key = '{parent_key}'),
     (SELECT entity_type_id FROM {schema}.entity_types WHERE entity_type_key = '{child_key}'),
     '{fk_column_name}', {true|false});

-- Step 4: Calculate topological depths
SELECT * FROM {schema}.calculate_topological_depth();

-- Step 5: Verify results
SELECT entity_type_key, is_aggregate, depth_level 
FROM {schema}.entity_types 
ORDER BY depth_level, aggregate_priority;
```

**Example Domains:**

**Finance:**
- Aggregates: `account` (depth 0) → `transaction` (depth 1) → `line_item` (depth 2)
- Dependencies: transaction.account_id → account, line_item.transaction_id → transaction

**Healthcare:**
- Aggregates: `patient` (depth 0) → `encounter` (depth 1) → `observation` (depth 2)
- Dependencies: encounter.patient_id → patient, observation.encounter_id → encounter

**E-commerce:**
- Aggregates: `customer` (depth 0) → `order` (depth 1) → `order_line` (depth 2) → `shipment` (depth 3)
- Dependencies: order.customer_id → customer, order_line.order_id → order, shipment.order_line_id → order_line

### Example 2: Validate Submission

```sql
-- Validate a submission containing sites (child) without locations (parent)
SELECT * FROM sead_utility.validate_entity_submission(
    'a3e4f567-e89b-12d3-a456-426614174000'::UUID,
    ARRAY['site', 'sample_group']  -- Missing 'location'!
);

-- Expected output:
-- is_valid | error_code              | error_message                | missing_parent_types
-- ---------|-------------------------|------------------------------|--------------------
-- false    | MISSING_PARENT_ENTITIES | Entity type "site" requires... | {location}
```

### Example 3: Get Allocation Order

```sql
-- Get correct order for allocating multiple entity types
SELECT * FROM sead_utility.get_allocation_order(
    ARRAY['analysis_entity', 'site', 'location', 'physical_sample', 'sample_group']
);

-- Expected output (sorted by depth, aggregate priority):
-- allocation_order | entity_type_key  | depth_level
-- -----------------|------------------|------------
-- 1                | location         | 0
-- 2                | site             | 1
-- 3                | sample_group     | 2
-- 4                | physical_sample  | 3
-- 5                | analysis_entity  | 4
```

### Example 4: Query Aggregate Hierarchy

```sql
-- View aggregate hierarchy
SELECT 
    parent_entity_key,
    parent_depth,
    child_entity_key,
    child_depth,
    child_fk_column,
    child_fk_required
FROM sead_utility.v_aggregate_hierarchy
WHERE parent_entity_key IN ('location', 'site')
ORDER BY parent_depth, child_depth;

-- Expected output:
-- parent_entity_key | parent_depth | child_entity_key | child_depth | child_fk_column | child_fk_required
-- ------------------|--------------|------------------|-------------|-----------------|------------------
-- location          | 0            | site             | 1           | location_id     | t
-- site              | 1            | sample_group     | 2           | site_id         | t
-- site              | 1            | feature          | 2           | site_id         | t
```

### Example 5: Get Allocation Statistics

```sql
-- View allocation statistics per aggregate
SELECT 
    entity_type_key,
    aggregate_priority,
    total_allocations,
    uuid_count,
    natural_key_count,
    committed_count,
    first_allocation_at,
    last_allocation_at
FROM sead_utility.v_aggregate_allocation_stats
ORDER BY aggregate_priority;
```

---

## Integration with Identity Allocation API

### API Enhancement: Validate Submission

**Endpoint:** `POST /api/v1/identity/submissions/{submission_id}/validate`

**Request:**
```json
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

**Response (Error):**
```json
{
  "is_valid": false,
  "error": {
    "code": "MISSING_PARENT_ENTITIES",
    "message": "Entity type 'site' requires parent 'location' which is missing",
    "missing_parents": ["location"]
  }
}
```

### API Enhancement: Allocate with Dependencies

**Endpoint:** `POST /api/v1/identity/submissions/{submission_id}/allocate-recursive`

**Description:** Allocate IDs for an aggregate + all its dependents in correct topological order.

**Request:**
```json
{
  "aggregate_type": "site",
  "allocations": [
    {
      "external_id": "a3e4f567-...",
      "external_id_type": "uuid",
      "dependents": {
        "sample_group": [
          {"external_id": "b4f5g678-..."},
          {"external_id": "c5g6h789-..."}
        ],
        "feature": [
          {"external_id": "d6h7i890-..."}
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
      "external_id": "a3e4f567-...",
      "sead_id": 12345
    },
    {
      "entity_type": "sample_group",
      "external_id": "b4f5g678-...",
      "sead_id": 67890
    },
    {
      "entity_type": "sample_group",
      "external_id": "c5g6h789-...",
      "sead_id": 67891
    },
    {
      "entity_type": "feature",
      "external_id": "d6h7i890-...",
      "sead_id": 23456
    }
  ]
}
```

---

## Migration Strategy

### Phase 1: Schema Deployment (Week 1)

**Tasks:**
1. Deploy `entity_types`, `aggregate_definitions`, `entity_dependencies` tables
2. Deploy supporting views and functions
3. Create initial data load script (entity type registration)

**Deliverables:**
- DDL scripts for all tables/views/functions
- Data migration script (INSERT statements)
- Unit tests for validation functions

### Phase 2: Data Population (Week 2)

**Tasks:**
1. Register domain entity types (aggregates + dependents)
2. Define all FK dependencies based on schema analysis
3. Calculate topological depths using provided function
4. Validate hierarchy correctness (no cycles, consistent depths)

**Deliverables:**
- Populated metadata tables (entity_types, aggregate_definitions, entity_dependencies)
- Validation reports showing correct depth calculations
- Documentation of domain-specific entities and relationships

**Domain-Specific Note:** See domain implementation documents (e.g., SEAD_AGGREGATE_MODEL.md) for entity lists and dependency graphs specific to your database schema.

### Phase 3: API Integration (Week 3-4)

**Tasks:**
1. Update identity allocation API to use aggregate model
2. Add validation endpoints
3. Add allocation order endpoints
4. Update ingester to query allocation order

**Deliverables:**
- Updated API endpoints
- Integration tests
- API documentation

### Phase 4: Production Rollout (Week 5)

**Tasks:**
1. Deploy to staging
2. Run pilot submissions
3. Performance tuning
4. Deploy to production

---

## Benefits

### 1. Self-Documenting System

The aggregate model serves as **live documentation** of entity relationships:
- Developers query `v_aggregate_hierarchy` to understand dependencies
- API automatically enforces correct allocation order
- No need to maintain separate documentation

### 2. Validation at API Layer

The identity API can **reject invalid submissions** before allocation:
- Missing parent entities detected early
- Prevents orphaned child records
- Reduces debugging time

### 3. Optimized Allocation

The system can **batch allocate** aggregate + dependents:
- Single transaction for related entities
- Atomic success/failure
- Improved performance

### 4. Future-Proof

The model supports **future enhancements**:
- Phase 2: Change detection per aggregate
- Phase 3: Soft deletes with cascade rules
- Phase 4: Cross-system entity linking

### 5. Domain Agnostic

The model is **reusable** across domains:
- Finance: Account → Transaction → LineItem
- Healthcare: Patient → Encounter → Observation
- E-commerce: Order → OrderLine → Shipment

---

## Appendices

### Appendix A: Natural Key Patterns (Generic)

**General Format:**
```sql
natural_key_columns = ARRAY['column1', 'column2', 'column3']
natural_key_pattern = 'LABEL1|LABEL2|LABEL3'  -- Human-readable description
```

**Domain Examples:**

**Finance - Account:**
```sql
natural_key_columns = ARRAY['institution_code', 'account_type', 'account_number']
natural_key_pattern = 'INSTITUTION|TYPE|NUMBER'
example = 'BANK_ABC|CHECKING|1234567890'
```

**Healthcare - Patient:**
```sql
natural_key_columns = ARRAY['mrn', 'facility_code']
natural_key_pattern = 'MRN|FACILITY'
example = 'MRN123456|HOSP_A'
```

**E-commerce - Order:**
```sql
natural_key_columns = ARRAY['store_id', 'order_date', 'order_sequence']
natural_key_pattern = 'STORE|DATE|SEQ'
example = 'STORE_42|2025-02-22|00123'
```

**For domain-specific natural key patterns**, see implementation documents (e.g., SEAD_AGGREGATE_MODEL.md for SEAD natural keys).

### Appendix B: Decision Tree - Is This an Aggregate?

```
┌─────────────────────────────────────────────┐
│ Does this entity have independent meaning?  │
│ (Can it exist without a parent?)            │
└─────────────┬───────────────────────────────┘
              │
        ┌─────┴─────┐
       YES          NO  → Not an aggregate (dependent entity)
        │
        ▼
┌─────────────────────────────────────────────┐
│ Is this entity submitted by external        │
│ systems as a primary data entry point?      │
└─────────────┬───────────────────────────────┘
              │
        ┌─────┴─────┐
       YES          NO  → Probably not an aggregate (reference data)
        │
        ▼
┌─────────────────────────────────────────────┐
│ Does this entity have child entities that   │
│ depend on it?                                │
└─────────────┬───────────────────────────────┘
              │
        ┌─────┴─────┐
       YES          NO  → Might be aggregate (check domain expert)
        │
        ▼
    ✅ AGGREGATE ROOT
```

### Appendix C: SQL Query Patterns

**Get all children of an aggregate:**
```sql
SELECT 
    child.entity_type_key,
    child.table_name,
    d.fk_column_name,
    d.is_required
FROM sead_utility.entity_types parent
JOIN sead_utility.entity_dependencies d 
    ON parent.entity_type_id = d.parent_entity_type_id
JOIN sead_utility.entity_types child 
    ON d.child_entity_type_id = child.entity_type_id
WHERE parent.entity_type_key = 'site'
ORDER BY child.depth_level;
```

**Get all ancestors of an entity:**
```sql
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

**Check for circular dependencies:**
```sql
-- This should return empty (no cycles)
SELECT DISTINCT entity_type_key
FROM sead_utility.v_entity_dependency_graph
WHERE entity_type_id = ANY(path[1:array_length(path, 1) - 1]);
```

---

## Conclusion

This generic aggregate model provides a **metadata-driven foundation** for identity allocation systems. By explicitly modeling entity hierarchies and dependencies, the system can:

- **Validate submissions** before allocation
- **Optimize batch operations** with topological sorting
- **Enforce consistency** through FK dependency tracking
- **Support evolution** as new entity types are added
- **Remain domain-agnostic** for reuse in other contexts

The model integrates seamlessly with the existing `identity_allocations` and `submissions` tables, enhancing the identity system without replacing core functionality.

**Next Steps:**
1. Review and approve schema design
2. Deploy to development environment
3. Populate with SEAD entity metadata
4. Update identity allocation API
5. Integrate with Shape Shifter ingester
