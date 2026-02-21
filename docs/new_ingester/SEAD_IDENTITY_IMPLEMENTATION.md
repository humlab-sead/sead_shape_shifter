# SEAD Identity System - Implementation Specification

**Status:** Draft  
**Version:** 2.0  
**Last Updated:** 2026-02-21  
**Related Documents:**
- [SEAD_IDENTITY_SYSTEM.md](./SEAD_IDENTITY_SYSTEM.md) - Design and architecture
- [SEAD_IDENTITY_NFR.md](./SEAD_IDENTITY_NFR.md) - Non-functional requirements
- [SEAD_INGESTER_DESIGN.md](./SEAD_INGESTER_DESIGN.md) - Shape Shifter integration

---

## Executive Summary

This document provides detailed implementation specifications for the SEAD Identity Allocation System, including:

- **Database Schema:** Complete DDL for identity tracking tables and entity table modifications
- **PostgreSQL Functions:** Implementation of allocation, resolution, commit, and rollback operations
- **REST API Specification:** Endpoint definitions with request/response examples
- **Migration Strategy:** 5-phase rollout plan with timelines
- **SQL Examples:** Concrete examples of generated SQL with UUID integration

**Implementation Approach:**
- PostgreSQL 12+ with uuid-ossp extension
- Python REST API (FastAPI/Flask)
- Sqitch for database change control
- OAuth 2.0 + API key authentication

---

## Database Schema Design

### Core Tables

#### 1. Identity Allocations (Central Registry)

**Purpose:** Tracks all UUID → Integer ID mappings with submission context.

```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS sead_utility.identity_allocations (
    -- Primary key for this allocation record
    allocation_uuid UUID NOT NULL DEFAULT uuid_generate_v4() PRIMARY KEY,
    
    -- Target table and column being allocated
    table_name TEXT NOT NULL,           -- e.g., 'tbl_sites'
    column_name TEXT NOT NULL,          -- e.g., 'site_id'
    
    -- The external identifier submitted by the external system
    external_id TEXT NOT NULL,          -- UUID (36 chars) OR natural key (variable length)
    external_id_type TEXT NOT NULL DEFAULT 'uuid',  -- 'uuid' or 'natural_key'
    
    -- The allocated SEAD integer PK
    alloc_integer_id INTEGER NOT NULL,  -- e.g., 12345
    
    -- Submission tracking
    submission_uuid UUID NOT NULL,      -- Links to sead_utility.submissions table
    submission_name TEXT NOT NULL,      -- Human-readable (e.g., "dendro_batch_2026_02")
    
    -- Change request tracking (for Sqitch integration)
    change_request_id TEXT NULL,        -- Sqitch change set ID
    
    -- Optional external metadata (for debugging/audit)
    external_system_id TEXT NULL,       -- Shape Shifter's local system_id (transient)
    external_data JSONB NULL,           -- Arbitrary external context
    
    -- Content hash for change detection (Phase 1: store, Phase 2: use)
    content_hash TEXT NULL,             -- SHA-256 hash (64 chars)
    
    -- Audit fields
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by TEXT NOT NULL DEFAULT CURRENT_USER,
    
    -- Lifecycle status
    status TEXT NOT NULL DEFAULT 'allocated',  -- 'allocated', 'committed', 'rolled_back'
    committed_at TIMESTAMP NULL,
    
    -- Enforce one external_id per table/column combination (idempotency)
    CONSTRAINT uq_identity_allocation UNIQUE (table_name, column_name, external_id),
    
    -- Enforce one integer ID per table/column (no reuse)
    CONSTRAINT uq_allocated_id UNIQUE (table_name, column_name, alloc_integer_id),
    
    -- Foreign key to submissions
    CONSTRAINT fk_submission FOREIGN KEY (submission_uuid) 
        REFERENCES sead_utility.submissions(submission_uuid) ON DELETE CASCADE
);

-- Indexes for common queries
CREATE INDEX idx_identity_allocation_submission 
    ON sead_utility.identity_allocations(submission_uuid);
    
CREATE INDEX idx_identity_allocation_table 
    ON sead_utility.identity_allocations(table_name, column_name);
    
CREATE INDEX idx_identity_allocation_status 
    ON sead_utility.identity_allocations(status);
    
CREATE INDEX idx_identity_allocation_external_id 
    ON sead_utility.identity_allocations(external_id);
    
CREATE INDEX idx_identity_allocation_content_hash 
    ON sead_utility.identity_allocations(content_hash) 
    WHERE content_hash IS NOT NULL;

-- Comments
COMMENT ON TABLE sead_utility.identity_allocations IS 
    'Central registry for external identifier → SEAD integer ID mappings. Supports both UUID and natural key identifiers.';
    
COMMENT ON COLUMN sead_utility.identity_allocations.external_id IS 
    'External identifier: UUID (36 chars, e.g., "a3e4f567-...") or natural key (variable length, e.g., "LAB_CODE|SITE_NAME|2024")';
    
COMMENT ON COLUMN sead_utility.identity_allocations.external_id_type IS 
    'Type of external identifier: "uuid" for UUID v4/v7, "natural_key" for business key concatenation';
    
COMMENT ON COLUMN sead_utility.identity_allocations.content_hash IS 
    'SHA-256 hash of entity data for change detection (Phase 1: store, Phase 2: use for UPDATE vs INSERT)';
```

#### 2. Submissions Tracking

**Purpose:** Groups related allocations into logical submissions for batch operations.

```sql
CREATE TABLE IF NOT EXISTS sead_utility.submissions (
    submission_uuid UUID NOT NULL DEFAULT uuid_generate_v4() PRIMARY KEY,
    submission_name TEXT NOT NULL UNIQUE,
    
    -- Submission metadata
    source_system TEXT NOT NULL,        -- e.g., 'shape_shifter', 'manual_import'
    data_type TEXT NOT NULL,            -- e.g., 'dendro', 'ceramics', 'isotopes'
    
    -- Status tracking
    status TEXT NOT NULL DEFAULT 'pending',  -- 'pending', 'validated', 'committed', 'failed', 'rolled_back'
    
    -- Audit
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by TEXT NOT NULL DEFAULT CURRENT_USER,
    committed_at TIMESTAMP NULL,
    
    -- Link to change control
    change_request_id TEXT NULL,        -- Sqitch change ID
    
    -- Optional metadata
    notes TEXT NULL,
    external_data JSONB NULL,
    
    -- Statistics
    total_allocations INTEGER DEFAULT 0,
    new_allocations INTEGER DEFAULT 0,
    existing_allocations INTEGER DEFAULT 0
);

-- Indexes
CREATE INDEX idx_submissions_status ON sead_utility.submissions(status);
CREATE INDEX idx_submissions_created_at ON sead_utility.submissions(created_at);
CREATE INDEX idx_submissions_source ON sead_utility.submissions(source_system, data_type);

-- Comments
COMMENT ON TABLE sead_utility.submissions IS 
    'Groups related identity allocations into logical submissions for batch operations and rollback.';
```

#### 3. Entity Table Schema Extensions

**Purpose:** Add external identifier columns to existing SEAD entity tables.

**Pattern for all entity tables:**

```sql
-- Example: tbl_sites (repeat for tbl_locations, tbl_sample_groups, etc.)

-- Add external identifier column (Phase 2: Pilot Tables)
ALTER TABLE public.tbl_sites 
    ADD COLUMN site_external_id TEXT NULL;

-- Add external identifier type column
ALTER TABLE public.tbl_sites 
    ADD COLUMN site_external_id_type TEXT NULL DEFAULT 'uuid';

-- Add content hash column (Phase 1: Store hashes)
ALTER TABLE public.tbl_sites
    ADD COLUMN content_hash TEXT NULL;

-- Unique constraint on external_id (once populated)
CREATE UNIQUE INDEX uq_site_external_id 
    ON public.tbl_sites(site_external_id) 
    WHERE site_external_id IS NOT NULL;

-- Index on content hash for change detection
CREATE INDEX idx_site_content_hash
    ON public.tbl_sites(content_hash)
    WHERE content_hash IS NOT NULL;

-- Later: Make NOT NULL after backfilling (Phase 4)
-- ALTER TABLE public.tbl_sites ALTER COLUMN site_external_id SET NOT NULL;

-- Comments
COMMENT ON COLUMN public.tbl_sites.site_external_id IS 
    'External identifier (UUID or natural key) for cross-system integration and idempotent ingestion';
    
COMMENT ON COLUMN public.tbl_sites.site_external_id_type IS 
    'Type of external identifier: "uuid" or "natural_key"';
    
COMMENT ON COLUMN public.tbl_sites.content_hash IS 
    'SHA-256 hash of entity data for change detection (compare to detect UPDATE vs INSERT)';
```

**Priority Tables for Phase 2 (Pilot):**

```sql
-- Aggregate root entities (5 priority tables)
ALTER TABLE public.tbl_locations ADD COLUMN location_external_id TEXT NULL;
ALTER TABLE public.tbl_locations ADD COLUMN location_external_id_type TEXT NULL DEFAULT 'uuid';
ALTER TABLE public.tbl_locations ADD COLUMN content_hash TEXT NULL;

ALTER TABLE public.tbl_sites ADD COLUMN site_external_id TEXT NULL;
ALTER TABLE public.tbl_sites ADD COLUMN site_external_id_type TEXT NULL DEFAULT 'uuid';
ALTER TABLE public.tbl_sites ADD COLUMN content_hash TEXT NULL;

ALTER TABLE public.tbl_sample_groups ADD COLUMN sample_group_external_id TEXT NULL;
ALTER TABLE public.tbl_sample_groups ADD COLUMN sample_group_external_id_type TEXT NULL DEFAULT 'uuid';
ALTER TABLE public.tbl_sample_groups ADD COLUMN content_hash TEXT NULL;

ALTER TABLE public.tbl_physical_samples ADD COLUMN physical_sample_external_id TEXT NULL;
ALTER TABLE public.tbl_physical_samples ADD COLUMN physical_sample_external_id_type TEXT NULL DEFAULT 'uuid';
ALTER TABLE public.tbl_physical_samples ADD COLUMN content_hash TEXT NULL;

ALTER TABLE public.tbl_analysis_entities ADD COLUMN analysis_entity_external_id TEXT NULL;
ALTER TABLE public.tbl_analysis_entities ADD COLUMN analysis_entity_external_id_type TEXT NULL DEFAULT 'uuid';
ALTER TABLE public.tbl_analysis_entities ADD COLUMN content_hash TEXT NULL;
```

---

## PostgreSQL Functions

### 1. Allocate Identity (Idempotent)

**Purpose:** Atomically allocate a SEAD integer ID for a given external identifier.

```sql
CREATE OR REPLACE FUNCTION sead_utility.allocate_identity(
    p_submission_uuid UUID,
    p_submission_name TEXT,
    p_table_name TEXT,
    p_column_name TEXT,
    p_external_id TEXT,                     -- UUID or natural key
    p_external_id_type TEXT DEFAULT 'uuid', -- 'uuid' or 'natural_key'
    p_content_hash TEXT DEFAULT NULL,       -- SHA-256 for change detection
    p_external_system_id TEXT DEFAULT NULL,
    p_external_data JSONB DEFAULT NULL
) RETURNS INTEGER AS $$
/*
 * Allocates a SEAD integer ID for the given external identifier (UUID or natural key).
 * IDEMPOTENT: If external_id already allocated, returns existing ID.
 * THREAD-SAFE: Uses INSERT ... ON CONFLICT for atomic allocation.
 * 
 * Example (UUID):
 *   SELECT sead_utility.allocate_identity(
 *       '123e4567-e89b-12d3-a456-426614174000'::UUID,
 *       'dendro_batch_2026_02',
 *       'tbl_sites',
 *       'site_id',
 *       'a3e4f567-e89b-12d3-a456-426614174001',  -- UUID
 *       'uuid'
 *   );
 * 
 * Example (Natural Key):
 *   SELECT sead_utility.allocate_identity(
 *       '123e4567-e89b-12d3-a456-426614174000'::UUID,
 *       'dendro_batch_2026_02',
 *       'tbl_sites',
 *       'site_id',
 *       'LAB_123|SITE_A|2024',  -- Natural key
 *       'natural_key'
 *   );
 */
DECLARE
    v_allocated_id INTEGER;
    v_next_id INTEGER;
BEGIN
    -- Validate external_id_type
    IF p_external_id_type NOT IN ('uuid', 'natural_key') THEN
        RAISE EXCEPTION 'Invalid external_id_type: %. Must be "uuid" or "natural_key"', p_external_id_type;
    END IF;
    
    -- Check if external_id already allocated
    SELECT alloc_integer_id INTO v_allocated_id
    FROM sead_utility.identity_allocations
    WHERE table_name = p_table_name
      AND column_name = p_column_name
      AND external_id = p_external_id;
    
    IF FOUND THEN
        -- Idempotent: Return existing allocation
        RAISE NOTICE 'External ID % already allocated to %', p_external_id, v_allocated_id;
        RETURN v_allocated_id;
    END IF;
    
    -- Get next available ID
    v_next_id := sead_utility.get_next_id(p_table_name, p_column_name);
    
    -- Allocate (atomic via unique constraint)
    BEGIN
        INSERT INTO sead_utility.identity_allocations (
            submission_uuid,
            submission_name,
            table_name,
            column_name,
            external_id,
            external_id_type,
            alloc_integer_id,
            content_hash,
            external_system_id,
            external_data,
            status
        ) VALUES (
            p_submission_uuid,
            p_submission_name,
            p_table_name,
            p_column_name,
            p_external_id,
            p_external_id_type,
            v_next_id,
            p_content_hash,
            p_external_system_id,
            p_external_data,
            'allocated'
        ) RETURNING alloc_integer_id INTO v_allocated_id;
        
        -- Update submission statistics
        UPDATE sead_utility.submissions
        SET new_allocations = new_allocations + 1,
            total_allocations = total_allocations + 1
        WHERE submission_uuid = p_submission_uuid;
        
    EXCEPTION WHEN unique_violation THEN
        -- Race condition: Another transaction allocated this external_id
        -- Retry read
        SELECT alloc_integer_id INTO v_allocated_id
        FROM sead_utility.identity_allocations
        WHERE table_name = p_table_name
          AND column_name = p_column_name
          AND external_id = p_external_id;
          
        -- Update submission statistics (existing allocation)
        UPDATE sead_utility.submissions
        SET existing_allocations = existing_allocations + 1,
            total_allocations = total_allocations + 1
        WHERE submission_uuid = p_submission_uuid;
    END;
    
    RETURN v_allocated_id;
END;
$$ LANGUAGE plpgsql;

-- Grant execute permission
GRANT EXECUTE ON FUNCTION sead_utility.allocate_identity TO sead_api_user;
```

### 2. Get Next Available ID

**Purpose:** Determine the next available integer ID considering both allocated and existing IDs.

```sql
CREATE OR REPLACE FUNCTION sead_utility.get_next_id(
    p_table_name TEXT,
    p_column_name TEXT
) RETURNS INTEGER AS $$
/*
 * Determines the next available integer ID for a table/column.
 * Considers: 1) Max allocated ID, 2) Max existing ID in target table, 3) Sequence current value.
 * 
 * Example:
 *   SELECT sead_utility.get_next_id('tbl_sites', 'site_id');
 */
DECLARE
    v_max_allocated INTEGER;
    v_max_existing INTEGER;
    v_sequence_current INTEGER;
    v_next_id INTEGER;
    v_query TEXT;
    v_sequence_name TEXT;
BEGIN
    -- Max from allocation tracking
    SELECT COALESCE(MAX(alloc_integer_id), 0) INTO v_max_allocated
    FROM sead_utility.identity_allocations
    WHERE table_name = p_table_name
      AND column_name = p_column_name;
    
    -- Max from actual table data
    v_query := format('SELECT COALESCE(MAX(%I), 0) FROM %I', p_column_name, p_table_name);
    EXECUTE v_query INTO v_max_existing;
    
    -- Try to get sequence current value (if exists)
    -- Assumes sequence naming: seq_<table_name_without_tbl_prefix>
    v_sequence_name := 'seq_' || REPLACE(p_table_name, 'tbl_', '');
    BEGIN
        EXECUTE format('SELECT last_value FROM %I', v_sequence_name) INTO v_sequence_current;
    EXCEPTION WHEN undefined_table THEN
        v_sequence_current := 0;
    END;
    
    -- Next ID is max of all three + 1
    v_next_id := GREATEST(v_max_allocated, v_max_existing, v_sequence_current) + 1;
    
    RAISE NOTICE 'Next ID for %.%: % (allocated: %, existing: %, sequence: %)', 
        p_table_name, p_column_name, v_next_id, v_max_allocated, v_max_existing, v_sequence_current;
    
    RETURN v_next_id;
END;
$$ LANGUAGE plpgsql;

-- Grant execute permission
GRANT EXECUTE ON FUNCTION sead_utility.get_next_id TO sead_api_user;
```

### 3. Batch Allocate (Performance Optimization)

**Purpose:** Allocate IDs for multiple external identifiers in a single transaction.

```sql
CREATE OR REPLACE FUNCTION sead_utility.allocate_identity_batch(
    p_submission_uuid UUID,
    p_submission_name TEXT,
    p_table_name TEXT,
    p_column_name TEXT,
    p_allocations JSONB  -- Array of {external_id, external_id_type, content_hash, external_data}
) RETURNS TABLE(external_id TEXT, alloc_integer_id INTEGER, is_new_allocation BOOLEAN) AS $$
/*
 * Allocates IDs for multiple external identifiers in a single transaction (performance).
 * Returns mapping: external_id → allocated_integer_id + is_new flag
 * 
 * Example:
 *   SELECT * FROM sead_utility.allocate_identity_batch(
 *       '123e4567-e89b-12d3-a456-426614174000'::UUID,
 *       'dendro_batch_2026_02',
 *       'tbl_sites',
 *       'site_id',
 *       '[
 *         {"external_id": "a3e4f567-...", "external_id_type": "uuid"},
 *         {"external_id": "LAB_123|SITE_A|2024", "external_id_type": "natural_key"}
 *       ]'::JSONB
 *   );
 */
DECLARE
    v_allocation JSONB;
    v_ext_id TEXT;
    v_ext_id_type TEXT;
    v_content_hash TEXT;
    v_ext_data JSONB;
    v_allocated_id INTEGER;
    v_was_existing BOOLEAN;
BEGIN
    FOR v_allocation IN SELECT * FROM jsonb_array_elements(p_allocations) LOOP
        v_ext_id := v_allocation->>'external_id';
        v_ext_id_type := COALESCE(v_allocation->>'external_id_type', 'uuid');
        v_content_hash := v_allocation->>'content_hash';
        v_ext_data := v_allocation->'external_data';
        
        -- Check if already exists
        SELECT alloc_integer_id INTO v_allocated_id
        FROM sead_utility.identity_allocations
        WHERE table_name = p_table_name
          AND column_name = p_column_name
          AND sead_utility.identity_allocations.external_id = v_ext_id;
        
        v_was_existing := FOUND;
        
        -- Allocate if new
        IF NOT v_was_existing THEN
            v_allocated_id := sead_utility.allocate_identity(
                p_submission_uuid,
                p_submission_name,
                p_table_name,
                p_column_name,
                v_ext_id,
                v_ext_id_type,
                v_content_hash,
                NULL,  -- external_system_id
                v_ext_data
            );
        END IF;
        
        RETURN QUERY SELECT v_ext_id, v_allocated_id, NOT v_was_existing;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Grant execute permission
GRANT EXECUTE ON FUNCTION sead_utility.allocate_identity_batch TO sead_api_user;
```

### 4. Resolve External ID to Integer

**Purpose:** Look up the allocated integer ID for a given external identifier (used during FK resolution).

```sql
CREATE OR REPLACE FUNCTION sead_utility.resolve_external_id(
    p_table_name TEXT,
    p_column_name TEXT,
    p_external_id TEXT
) RETURNS INTEGER AS $$
/*
 * Looks up the allocated integer ID for a given external identifier.
 * Used during FK resolution.
 * 
 * Example:
 *   SELECT sead_utility.resolve_external_id('tbl_sites', 'site_id', 'a3e4f567-...');
 */
DECLARE
    v_integer_id INTEGER;
BEGIN
    SELECT alloc_integer_id INTO v_integer_id
    FROM sead_utility.identity_allocations
    WHERE table_name = p_table_name
      AND column_name = p_column_name
      AND external_id = p_external_id
      AND status IN ('allocated', 'committed');
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'External ID % not allocated for %.%', p_external_id, p_table_name, p_column_name;
    END IF;
    
    RETURN v_integer_id;
END;
$$ LANGUAGE plpgsql;

-- Grant execute permission
GRANT EXECUTE ON FUNCTION sead_utility.resolve_external_id TO sead_api_user;
```

### 5. Commit Submission

**Purpose:** Mark all allocations for a submission as committed (after successful SQL execution).

```sql
CREATE OR REPLACE FUNCTION sead_utility.commit_submission(
    p_submission_uuid UUID,
    p_change_request_id TEXT DEFAULT NULL
) RETURNS VOID AS $$
/*
 * Marks all allocations for a submission as committed.
 * Called after successful SQL execution.
 * 
 * Example:
 *   SELECT sead_utility.commit_submission('123e4567-e89b-12d3-a456-426614174000'::UUID, 'sqitch_change_001');
 */
DECLARE
    v_count INTEGER;
BEGIN
    -- Update submission status
    UPDATE sead_utility.submissions
    SET status = 'committed',
        committed_at = NOW(),
        change_request_id = p_change_request_id
    WHERE submission_uuid = p_submission_uuid;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Submission % not found', p_submission_uuid;
    END IF;
    
    -- Update allocation status
    UPDATE sead_utility.identity_allocations
    SET status = 'committed',
        committed_at = NOW(),
        change_request_id = p_change_request_id
    WHERE submission_uuid = p_submission_uuid
      AND status = 'allocated';
    
    GET DIAGNOSTICS v_count = ROW_COUNT;
    
    RAISE NOTICE 'Committed submission % (% allocations)', p_submission_uuid, v_count;
END;
$$ LANGUAGE plpgsql;

-- Grant execute permission
GRANT EXECUTE ON FUNCTION sead_utility.commit_submission TO sead_api_user;
```

### 6. Rollback Submission

**Purpose:** Roll back a submission (soft delete by default, hard delete optional).

```sql
CREATE OR REPLACE FUNCTION sead_utility.rollback_submission(
    p_submission_uuid UUID,
    p_delete_allocations BOOLEAN DEFAULT FALSE
) RETURNS VOID AS $$
/*
 * Rolls back a submission.
 * If p_delete_allocations = TRUE, removes allocations (allows ID reuse).
 * If FALSE, marks as 'rolled_back' (preserves audit trail).
 * 
 * Example:
 *   SELECT sead_utility.rollback_submission('123e4567-e89b-12d3-a456-426614174000'::UUID, FALSE);
 */
DECLARE
    v_count INTEGER;
BEGIN
    IF p_delete_allocations THEN
        -- Hard delete: Allow ID reuse
        DELETE FROM sead_utility.identity_allocations
        WHERE submission_uuid = p_submission_uuid
          AND status = 'allocated';
        
        GET DIAGNOSTICS v_count = ROW_COUNT;
        RAISE NOTICE 'Hard deleted % allocations for submission %', v_count, p_submission_uuid;
    ELSE
        -- Soft delete: Preserve audit trail
        UPDATE sead_utility.identity_allocations
        SET status = 'rolled_back'
        WHERE submission_uuid = p_submission_uuid
          AND status = 'allocated';
        
        GET DIAGNOSTICS v_count = ROW_COUNT;
        RAISE NOTICE 'Soft deleted (marked rolled_back) % allocations for submission %', v_count, p_submission_uuid;
    END IF;
    
    -- Update submission status
    UPDATE sead_utility.submissions
    SET status = 'rolled_back'
    WHERE submission_uuid = p_submission_uuid;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Submission % not found', p_submission_uuid;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Grant execute permission
GRANT EXECUTE ON FUNCTION sead_utility.rollback_submission TO sead_api_user;
```

### 7. Detect Changes (Phase 2: Change Detection)

**Purpose:** Compare content hashes to detect if entity data has changed.

```sql
CREATE OR REPLACE FUNCTION sead_utility.detect_change(
    p_table_name TEXT,
    p_external_id TEXT,
    p_new_content_hash TEXT
) RETURNS TEXT AS $$
/*
 * Compares new content hash with stored hash to detect changes.
 * Returns: 'insert' (new), 'update' (changed), 'skip' (unchanged)
 * 
 * Example:
 *   SELECT sead_utility.detect_change('tbl_sites', 'a3e4f567-...', 'abc123...');
 */
DECLARE
    v_existing_hash TEXT;
BEGIN
    -- Get existing content hash
    SELECT content_hash INTO v_existing_hash
    FROM sead_utility.identity_allocations
    WHERE table_name = p_table_name
      AND external_id = p_external_id
      AND status = 'committed';
    
    IF NOT FOUND THEN
        -- New entity
        RETURN 'insert';
    ELSIF v_existing_hash IS NULL THEN
        -- Existing entity without hash (legacy data)
        RETURN 'update';  -- Conservative: assume changed
    ELSIF v_existing_hash = p_new_content_hash THEN
        -- Unchanged
        RETURN 'skip';
    ELSE
        -- Changed
        RETURN 'update';
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Grant execute permission
GRANT EXECUTE ON FUNCTION sead_utility.detect_change TO sead_api_user;
```

---

## REST API Specification

### Base URL
```
https://api.sead.se/v1/identity
```

### Authentication

**Methods:**
1. **OAuth 2.0** (preferred for interactive applications)
   - Client credentials flow for machine-to-machine
   - Authorization code flow for end-users
   
2. **API Keys** (for trusted systems like Shape Shifter)
   - Header: `X-API-Key: <your-api-key>`
   - Scopes: `identity:read`, `identity:write`, `identity:admin`

**Rate Limiting:**
- Standard tier: 1,000 requests/minute
- Premium tier (Shape Shifter): 10,000 requests/minute
- Headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`

### Endpoints

#### 1. Create Submission

**Request:**
```http
POST /api/v1/identity/submissions
Content-Type: application/json
Authorization: Bearer <token>
# OR
X-API-Key: <api-key>

{
  "submission_name": "dendro_batch_2026_02",
  "source_system": "shape_shifter",
  "data_type": "dendro",
  "notes": "Initial import of tree ring data from Swedish sites"
}
```

**Response (201 Created):**
```json
{
  "submission_uuid": "123e4567-e89b-12d3-a456-426614174000",
  "submission_name": "dendro_batch_2026_02",
  "source_system": "shape_shifter",
  "data_type": "dendro",
  "status": "pending",
  "created_at": "2026-02-21T10:30:00Z",
  "created_by": "shape_shifter_api"
}
```

**Errors:**
- **400 Bad Request:** Invalid input (missing required fields, invalid format)
- **409 Conflict:** Submission name already exists
- **401 Unauthorized:** Invalid or missing credentials
- **429 Too Many Requests:** Rate limit exceeded

#### 2. Allocate Single Identity

**Request:**
```http
POST /api/v1/identity/submissions/{submission_uuid}/allocations
Content-Type: application/json

{
  "table_name": "tbl_sites",
  "column_name": "site_id",
  "external_id": "a3e4f567-e89b-12d3-a456-426614174001",
  "external_id_type": "uuid",  // "uuid" or "natural_key"
  "content_hash": "abc123def456...",  // Optional: SHA-256 hash
  "external_system_id": "1",           // Optional: Shape Shifter's system_id
  "external_data": {                   // Optional: Debugging context
    "entity_name": "site",
    "business_key": "Site_A_Norway"
  }
}
```

**Response (200 OK - Idempotent):**
```json
{
  "external_id": "a3e4f567-e89b-12d3-a456-426614174001",
  "external_id_type": "uuid",
  "alloc_integer_id": 12345,
  "table_name": "tbl_sites",
  "column_name": "site_id",
  "status": "allocated",
  "created_at": "2026-02-21T10:31:00Z",
  "is_new_allocation": true  // false if already existed (idempotent)
}
```

**Errors:**
- **400 Bad Request:** Invalid table/column, malformed UUID
- **404 Not Found:** Submission not found
- **500 Internal Server Error:** Database error

#### 3. Batch Allocate Identities

**Request:**
```http
POST /api/v1/identity/submissions/{submission_uuid}/allocations/batch
Content-Type: application/json

{
  "table_name": "tbl_sites",
  "column_name": "site_id",
  "allocations": [
    {
      "external_id": "a3e4f567-e89b-12d3-a456-426614174001",
      "external_id_type": "uuid",
      "content_hash": "abc123...",
      "external_data": {"business_key": "Site_A"}
    },
    {
      "external_id": "LAB_123|SITE_B|2024",
      "external_id_type": "natural_key",
      "content_hash": "def456...",
      "external_data": {"business_key": "Site_B"}
    }
  ]
}
```

**Response (200 OK):**
```json
{
  "allocations": [
    {
      "external_id": "a3e4f567-e89b-12d3-a456-426614174001",
      "external_id_type": "uuid",
      "alloc_integer_id": 12345,
      "is_new_allocation": true
    },
    {
      "external_id": "LAB_123|SITE_B|2024",
      "external_id_type": "natural_key",
      "alloc_integer_id": 12346,
      "is_new_allocation": true
    }
  ],
  "summary": {
    "total": 2,
    "new": 2,
    "existing": 0,
    "duration_ms": 34
  }
}
```

**Performance:** Target < 100ms for 100 allocations (P95)

#### 4. Resolve External ID to Integer

**Request:**
```http
GET /api/v1/identity/submissions/{submission_uuid}/resolve?table_name=tbl_sites&column_name=site_id&external_id=a3e4f567-...
```

**Response (200 OK):**
```json
{
  "external_id": "a3e4f567-e89b-12d3-a456-426614174001",
  "external_id_type": "uuid",
  "alloc_integer_id": 12345,
  "table_name": "tbl_sites",
  "column_name": "site_id",
  "status": "allocated"
}
```

**Response (404 Not Found):**
```json
{
  "error": "external_id_not_allocated",
  "message": "External ID not allocated for tbl_sites.site_id",
  "external_id": "a3e4f567-e89b-12d3-a456-426614174001",
  "table_name": "tbl_sites",
  "column_name": "site_id"
}
```

#### 5. Commit Submission

**Request:**
```http
POST /api/v1/identity/submissions/{submission_uuid}/commit
Content-Type: application/json

{
  "change_request_id": "sqitch_change_001"  // Optional: Link to Sqitch
}
```

**Response (200 OK):**
```json
{
  "submission_uuid": "123e4567-e89b-12d3-a456-426614174000",
  "submission_name": "dendro_batch_2026_02",
  "status": "committed",
  "committed_at": "2026-02-21T11:00:00Z",
  "allocations_committed": 142,
  "change_request_id": "sqitch_change_001"
}
```

**Errors:**
- **404 Not Found:** Submission not found
- **409 Conflict:** Submission already committed or rolled back

#### 6. Rollback Submission

**Request:**
```http
POST /api/v1/identity/submissions/{submission_uuid}/rollback
Content-Type: application/json

{
  "delete_allocations": false,  // true = hard delete, false = soft delete (default)
  "reason": "Validation failed on site names"  // Optional
}
```

**Response (200 OK):**
```json
{
  "submission_uuid": "123e4567-e89b-12d3-a456-426614174000",
  "submission_name": "dendro_batch_2026_02",
  "status": "rolled_back",
  "allocations_affected": 142,
  "deletion_type": "soft"  // "soft" or "hard"
}
```

#### 7. Get Submission Status

**Request:**
```http
GET /api/v1/identity/submissions/{submission_uuid}
```

**Response (200 OK):**
```json
{
  "submission_uuid": "123e4567-e89b-12d3-a456-426614174000",
  "submission_name": "dendro_batch_2026_02",
  "source_system": "shape_shifter",
  "data_type": "dendro",
  "status": "committed",
  "created_at": "2026-02-21T10:30:00Z",
  "committed_at": "2026-02-21T11:00:00Z",
  "statistics": {
    "total_allocations": 142,
    "new_allocations": 138,
    "existing_allocations": 4
  },
  "notes": "Initial import of tree ring data"
}
```

---

## Migration Strategy

### Phase 1: Infrastructure (Weeks 1-2)

**Goal:** Deploy core infrastructure to staging environment.

**Tasks:**
1. Create `sead_utility` schema
   ```sql
   CREATE SCHEMA IF NOT EXISTS sead_utility;
   ```

2. Deploy tables (`identity_allocations`, `submissions`)
   ```bash
   cd sqitch
   sqitch deploy --target staging identity_tracking
   ```

3. Deploy PostgreSQL functions (6 functions above)
   ```bash
   sqitch deploy --target staging identity_functions
   ```

4. Deploy REST API service (FastAPI container)
   ```bash
   docker build -t sead-identity-api:latest .
   docker-compose up -d sead-identity-api
   ```

5. Configure monitoring (Prometheus + Grafana)
   - Metrics: allocation rate, latency, error rate
   - Alerts: error rate > 1%, P95 latency > 500ms

6. Load testing (10,000 allocations/sec target)
   ```bash
   locust -f tests/load_test.py --host https://api.sead.se
   ```

**Success Criteria:**
- ✅ Schema deployed to staging
- ✅ API responding with 200 OK to health check
- ✅ Load test passes: 10,000 req/s, P95 < 100ms
- ✅ Monitoring dashboards operational

### Phase 2: Pilot Tables (Weeks 3-4)

**Goal:** Add external identifier columns to 5 priority aggregate root tables.

**Priority Tables:**
1. `tbl_locations` (aggregate root for geo hierarchy)
2. `tbl_sites` (aggregate root for archaeological sites)
3. `tbl_sample_groups` (aggregate root for sample collections)
4. `tbl_physical_samples` (aggregate root for specimens)
5. `tbl_analysis_entities` (aggregate root for measurements)

**Tasks:**
1. Add external_id columns (nullable initially)
   ```bash
   sqitch deploy --target staging add_external_ids_pilot
   ```

2. Backfill UUIDs for existing data
   ```sql
   UPDATE public.tbl_sites
   SET site_external_id = uuid_generate_v4()::TEXT,
       site_external_id_type = 'uuid'
   WHERE site_external_id IS NULL;
   ```

3. Create unique indexes on external_id
   ```bash
   sqitch deploy --target staging add_external_id_indexes
   ```

4. Test with Shape Shifter on staging data (10 submissions)
   ```bash
   python scripts/test_pilot_ingestion.py --env staging
   ```

5. Monitor for 1 week, collect metrics

**Success Criteria:**
- ✅ All 5 pilot tables have external_id columns
- ✅ 100% of existing rows backfilled with UUIDs
- ✅ Unique constraints enforced
- ✅ Shape Shifter successfully ingested 10 test submissions
- ✅ Zero ID collisions

### Phase 3: Core Tables Rollout (Weeks 5-8)

**Goal:** Extend external identifiers to all 50+ core SEAD tables.

**Tasks:**
1. Generate DDL for remaining tables (automated script)
   ```bash
   python scripts/generate_external_id_migrations.py \
     --tables-file config/core_tables.txt \
     --output sqitch/deploy/add_external_ids_core.sql
   ```

2. Deploy in batches (10 tables per batch, monitor after each)
   ```bash
   sqitch deploy --target staging add_external_ids_batch_01
   # Wait 24 hours, monitor
   sqitch deploy --target staging add_external_ids_batch_02
   # ...
   ```

3. Backfill UUIDs (run during low-traffic hours)
   ```sql
   -- Example for batch backfill
   UPDATE public.tbl_ceramics
   SET ceramic_external_id = uuid_generate_v4()::TEXT,
       ceramic_external_id_type = 'uuid'
   WHERE ceramic_external_id IS NULL
     AND ceramic_id BETWEEN 1 AND 100000;
   ```

4. Update views and stored procedures to handle external_id
   ```bash
   sqitch deploy --target staging update_views_external_id
   ```

5. Documentation and training for SEAD team

**Success Criteria:**
- ✅ All 50+ core tables have external_id columns
- ✅ 100% of existing rows backfilled
- ✅ Views and procedures updated
- ✅ Documentation complete

### Phase 4: Gradual Enforcement (Weeks 9-12)

**Goal:** Make external_id columns mandatory for new records.

**Tasks:**
1. Make external_id NOT NULL for pilot tables
   ```sql
   ALTER TABLE public.tbl_sites 
     ALTER COLUMN site_external_id SET NOT NULL;
   ```

2. Deprecate old allocation methods (add warnings)
   ```python
   @deprecated("Use identity allocation API instead")
   def generate_local_id():
       ...
   ```

3. Update all ingesters to use UUID-based allocation
   - Shape Shifter: Update SEADIdentityAllocator (already planned)
   - Manual import tools: Add UUID generation step
   - External APIs: Update client libraries

4. Performance tuning based on production metrics
   - Optimize batch allocation queries
   - Add read replicas for high-read scenarios
   - Tune connection pool sizes

**Success Criteria:**
- ✅ NOT NULL constraints on pilot tables
- ✅ All ingesters using new API
- ✅ Old methods deprecated (warnings logged)
- ✅ Performance meets targets (< 100ms P95)

### Phase 5: Production Deployment (Week 13+)

**Goal:** Promote to production with fallback plan.

**Tasks:**
1. Production deployment (blue-green strategy)
   ```bash
   # Deploy new API alongside old
   kubectl apply -f k8s/identity-api-deployment.yaml
   # Route 10% traffic to new API
   kubectl apply -f k8s/identity-api-canary.yaml
   # Monitor for 24 hours
   # Increase to 50%, then 100%
   ```

2. Fallback plan: Keep old system parallel for 3 months
   - Old workflow remains functional
   - Gradual migration of data providers

3. Monitoring and alerting (24/7)
   - PagerDuty integration for critical alerts
   - Slack notifications for warnings

4. Post-deployment review (2 weeks after)
   - Collect feedback from data providers
   - Review metrics (latency, error rate, throughput)
   - Document lessons learned

**Success Criteria:**
- ✅ Production deployment successful
- ✅ Zero downtime during migration
- ✅ Fallback plan tested and documented
- ✅ Post-deployment review complete

---

## SQL Generation Examples

### 1. INSERT with UUID (New Entity)

**Context:** Shape Shifter generates SQL DML for new site entity.

```sql
-- Generated by Shape Shifter SEADSQLGenerator

-- External ID: a3e4f567-e89b-12d3-a456-426614174001 (UUID)
-- Allocated SEAD ID: 12345

INSERT INTO public.tbl_sites (
    site_id,                -- Allocated integer PK
    site_external_id,       -- External UUID
    site_external_id_type,  -- 'uuid'
    site_name,
    site_description,
    latitude_dd,
    longitude_dd,
    content_hash,           -- For future change detection
    date_updated
) VALUES (
    12345,                                      -- From allocation API
    'a3e4f567-e89b-12d3-a456-426614174001',   -- Generated by Shape Shifter
    'uuid',                                    -- Identifier type
    'Härjedalen Site A',
    'Archaeological site in northern Sweden',
    62.7345,
    14.2156,
    'abc123def456...',                         -- SHA-256 of entity data
    NOW()
)
ON CONFLICT (site_external_id) DO UPDATE SET
    site_name = EXCLUDED.site_name,
    site_description = EXCLUDED.site_description,
    latitude_dd = EXCLUDED.latitude_dd,
    longitude_dd = EXCLUDED.longitude_dd,
    content_hash = EXCLUDED.content_hash,
    date_updated = NOW();
```

### 2. INSERT with Natural Key (Legacy Provider)

**Context:** Legacy data provider without UUID capability uses natural keys.

```sql
-- External ID: LAB_SWE_123|SITE_HARJEDALEN_A|2024 (natural key)
-- Allocated SEAD ID: 12346

INSERT INTO public.tbl_sites (
    site_id,
    site_external_id,       -- Natural key (lab code + site name + year)
    site_external_id_type,  -- 'natural_key'
    site_name,
    content_hash,
    date_updated
) VALUES (
    12346,
    'LAB_SWE_123|SITE_HARJEDALEN_A|2024',  -- Composite business key
    'natural_key',
    'Härjedalen Site A',
    'def789ghi012...',
    NOW()
)
ON CONFLICT (site_external_id) DO UPDATE SET
    site_name = EXCLUDED.site_name,
    content_hash = EXCLUDED.content_hash,
    date_updated = NOW();
```

### 3. INSERT with FK Resolution (Topological Order)

**Context:** Child entity references parent via external_id, resolved to integer FK.

```sql
-- Parent must be inserted first (topological sorting ensures this)

-- Parent: tbl_sites
INSERT INTO public.tbl_sites (
    site_id, 
    site_external_id, 
    site_external_id_type,
    site_name,
    content_hash,
    date_updated
)
VALUES (
    12345, 
    'a3e4f567-e89b-12d3-a456-426614174001', 
    'uuid',
    'Härjedalen Site A',
    'abc123...',
    NOW()
);

-- Child: tbl_physical_samples (references site_id)
-- ForeignKeyResolver mapped:
--   sample.site_external_id → site.site_external_id → site.site_id (12345)

INSERT INTO public.tbl_physical_samples (
    physical_sample_id,              -- Allocated: 67890
    physical_sample_external_id,     -- External UUID for sample
    physical_sample_external_id_type,
    site_id,                         -- FK to tbl_sites.site_id (integer)
    sample_name,
    content_hash,
    date_updated
) VALUES (
    67890,
    'c5g6h789-e89b-12d3-a456-426614174003',  -- Sample's UUID
    'uuid',
    12345,                                    -- Resolved from site_external_id
    'Sample HS-A-001',
    'ghi345jkl678...',
    NOW()
)
ON CONFLICT (physical_sample_external_id) DO UPDATE SET
    sample_name = EXCLUDED.sample_name,
    site_id = EXCLUDED.site_id,
    content_hash = EXCLUDED.content_hash,
    date_updated = NOW();
```

### 4. UPDATE Detection (Phase 2: Change Detection)

**Context:** Re-submitting same external_id with different content_hash triggers UPDATE.

```sql
-- Pseudo-code workflow (Phase 2 implementation)

-- 1. Check if external_id exists and compare content_hash
SELECT sead_utility.detect_change(
    'tbl_sites',
    'a3e4f567-e89b-12d3-a456-426614174001',
    'new_hash_xyz...'
);
-- Returns: 'update' (hash changed)

-- 2. Generate UPDATE instead of INSERT
UPDATE public.tbl_sites
SET site_name = 'Härjedalen Site A (revised)',
    site_description = 'Updated description',
    content_hash = 'new_hash_xyz...',
    date_updated = NOW()
WHERE site_external_id = 'a3e4f567-e89b-12d3-a456-426614174001';
```

---

## Deployment Checklist

### Pre-Deployment

- [ ] Database backup created (staging + production)
- [ ] Rollback scripts tested
- [ ] Load tests passed (10,000 req/s sustained)
- [ ] API documentation published (Swagger UI)
- [ ] Monitoring dashboards configured
- [ ] PagerDuty integration active
- [ ] Team trained on new workflow

### Deployment

- [ ] Schema deployed to staging
- [ ] Functions deployed to staging
- [ ] API deployed to staging
- [ ] Integration tests passed (staging)
- [ ] Pilot tables tested (staging)
- [ ] Schema deployed to production
- [ ] Functions deployed to production
- [ ] API deployed to production (canary)
- [ ] Traffic routed incrementally (10% → 50% → 100%)
- [ ] Production integration tests passed

### Post-Deployment

- [ ] Monitor metrics for 24 hours
- [ ] Review error logs
- [ ] Collect feedback from data providers
- [ ] Document issues and resolutions
- [ ] Update runbooks
- [ ] Schedule post-mortem meeting

---

## Troubleshooting Guide

### Issue: ID Allocation Race Condition

**Symptom:** Two concurrent requests allocate same integer ID.

**Diagnosis:**
```sql
-- Check for duplicate allocated IDs
SELECT table_name, column_name, alloc_integer_id, COUNT(*)
FROM sead_utility.identity_allocations
GROUP BY table_name, column_name, alloc_integer_id
HAVING COUNT(*) > 1;
```

**Resolution:**
- Unique constraint `uq_allocated_id` should prevent this
- If occurs, investigate transaction isolation level
- Ensure `SERIALIZABLE` or `REPEATABLE READ` isolation

### Issue: Orphaned Allocations

**Symptom:** Allocations in 'allocated' status never committed.

**Diagnosis:**
```sql
-- Find old allocations never committed
SELECT submission_uuid, submission_name, COUNT(*), MAX(created_at)
FROM sead_utility.identity_allocations
WHERE status = 'allocated'
  AND created_at < NOW() - INTERVAL '7 days'
GROUP BY submission_uuid, submission_name;
```

**Resolution:**
```sql
-- Cleanup old orphaned allocations
SELECT sead_utility.rollback_submission(
    '<submission_uuid>'::UUID,
    TRUE  -- Hard delete to allow ID reuse
);
```

### Issue: API Latency Spike

**Symptom:** P95 latency > 500ms (target: < 100ms).

**Diagnosis:**
```sql
-- Check database connection pool
SELECT COUNT(*), state
FROM pg_stat_activity
WHERE application_name = 'sead_identity_api'
GROUP BY state;

-- Check slow queries
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
WHERE query LIKE '%identity_allocations%'
ORDER BY mean_exec_time DESC
LIMIT 10;
```

**Resolution:**
- Scale API horizontally (add more pods)
- Increase database connection pool size
- Add read replicas for resolution queries
- Enable query result caching (Redis)

---

**End of Implementation Specification**

**Related Documents:**
- [SEAD_IDENTITY_SYSTEM.md](./SEAD_IDENTITY_SYSTEM.md) - Design and architecture
- [SEAD_IDENTITY_NFR.md](./SEAD_IDENTITY_NFR.md) - Performance, security, testing
- [SEAD_INGESTER_DESIGN.md](./SEAD_INGESTER_DESIGN.md) - Shape Shifter integration
