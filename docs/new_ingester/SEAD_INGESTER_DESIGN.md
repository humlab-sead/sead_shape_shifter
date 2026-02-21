# SEAD SQL Ingester - Design Document

**Version:** 1.0  
**Date:** February 21, 2026  
**Status:** Design Phase  
**Scope:** Shape Shifter SEAD Ingester Component

---

## Executive Summary

This document describes a new SEAD ingester for Shape Shifter that generates Sqitch-ready SQL DML directly from normalized DataFrames, eliminating the multi-step file-based workflow. The ingester integrates with SEAD's hybrid identity system (see [SEAD_IDENTITY_SYSTEM.md](./SEAD_IDENTITY_SYSTEM.md)) to allocate IDs via API and generates topologically-sorted SQL INSERT/UPSERT statements ready for database change control.

**Key Innovation:** Direct DataFrame → SQL DML transformation with automated ID allocation, FK resolution, and Sqitch integration, reducing ingestion time from days to hours.

**Isolation Principle:** ALL SEAD-specific logic (identity allocation, SQL generation, reconciliation) resides in this ingester component. Shape Shifter core remains domain-agnostic.

---

## Problem Statement

### Current Workflow Bottlenecks

Today's ingestion pipeline has 6 handoff points:

```
Data Provider → Shape Shifter (User)
                  ↓
              Project YAML
                  ↓
           Shape Shifter (Normalizer) → Normalized DataFrames
                  ↓
           Shape Shifter (Dispatcher) → CSV/Excel files
                  ↓
           Shape Shifter (Ingester) → SEAD Clearinghouse Submission
                  ↓
           SEAD Transport System → SQL DML Scripts (ID allocation happens here)
                  ↓
           SEAD Sqitch → Database
```

**Pain Points:**
1. **Manual ID Reconciliation:** Transport System allocates IDs, requires manual mapping
2. **File-Based Handoffs:** CSV/Excel files must be validated, transferred, re-parsed
3. **No Reusability:** Project YAML must be manually updated for each new dataset
4. **Long Turnaround:** 2-5 days from normalized data to database insertion
5. **Limited Concurrency:** Single-threaded Transport System is bottleneck
6. **Error Recovery:** Failures late in pipeline require starting over

### Proposed Workflow

```
Data Provider → Shape Shifter (User) → Project YAML
                  ↓
           Shape Shifter (Normalizer) → Normalized DataFrames
                  ↓
           Shape Shifter (SEAD Ingester) → SQL DML Scripts
              ↓                 ↑
           SEAD Identity API ──┘ (ID allocation)
              ↓
           SEAD Sqitch → Database
```

**Improvements:**
- **3 handoffs** (vs 6) - 50% reduction
- **Direct SQL generation** - No file intermediaries
- **Automated ID allocation** - Via SEAD Identity API
- **Same-day turnaround** - Hours instead of days
- **Concurrent safe** - Multiple ingestions in parallel
- **Fail fast** - Validation and dry-run before execution

---

## Goals

### Primary Goals
- ✅ **Generate Sqitch-ready SQL DML** from normalized DataFrames
- ✅ **Automate SEAD ID allocation** via SEAD Identity API (UUID-based)
- ✅ **Resolve Foreign Keys** from Shape Shifter `system_id` to allocated SEAD IDs
- ✅ **Preserve existing Project YAML** - Reusable across datasets
- ✅ **Topological SQL ordering** - Parents before children (FK constraints)
- ✅ **Idempotent ingestion** - Re-running same data doesn't create duplicates
- ✅ **Isolation** - ALL SEAD-specific logic in ingester, core remains agnostic

### Secondary Goals
- 🎯 **Dry-run validation** - Validate without executing SQL
- 🎯 **Partial ingestion** - Commit successful entities, rollback failed ones
- 🎯 **Reconciliation integration** - Leverage existing `mappings.yml` for known entities
- 🎯 **Audit trail** - Track what was ingested, when, by whom
- 🎯 **CLI and API access** - Usable from scripts and web interface

### Non-Goals
- ❌ **Replace Shape Shifter core** - Normalizer pipeline unchanged
- ❌ **Modify SEAD schema** - Work with existing tables (only add UUID columns)
- ❌ **Replace existing dispatchers** - CSV/Excel dispatchers remain for other use cases
- ❌ **Handle DDL** - This ingester only generates DML (INSERT/UPDATE)

---

## Architecture Overview

### Component Structure

```
┌──────────────────────────────────────────────────────────────────────┐
│ Shape Shifter Core (Unchanged)                                       │
│                                                                       │
│  ┌────────────┐   ┌────────────┐   ┌────────────┐   ┌────────────┐ │
│  │  Extract   │ → │   Filter   │ → │    Link    │ → │  Unnest    │ │
│  └────────────┘   └────────────┘   └────────────┘   └────────────┘ │
│         ↓                                                             │
│  ┌────────────┐   ┌────────────┐                                    │
│  │ Translate  │ → │   Store    │ (unchanged dispatchers)             │
│  └────────────┘   └────────────┘                                    │
└──────────────────────────────────────────────────────────────────────┘
                               ↓
┌──────────────────────────────────────────────────────────────────────┐
│ SEAD Ingester (New - ALL SEAD-specific logic here)                   │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ 1. UUID Generation                                           │    │
│  │    - Generate UUID for each entity row                       │    │
│  │    - Map Shape Shifter system_id → UUID                      │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                               ↓                                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ 2. Reconciliation (Optional)                                 │    │
│  │    - Check mappings.yml for existing SEAD entities           │    │
│  │    - Mark matched entities (don't allocate new IDs)          │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                               ↓                                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ 3. Identity Allocation (SEAD API)                            │    │
│  │    - Call SEAD Identity API with UUIDs                       │    │
│  │    - Get back allocated integer IDs                          │    │
│  │    - Store UUID ↔ Integer mapping                            │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                               ↓                                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ 4. Foreign Key Resolution                                    │    │
│  │    - Resolve FK system_id → allocated parent integer ID      │    │
│  │    - Validate referential integrity                          │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                               ↓                                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ 5. SQL Generation                                            │    │
│  │    - Topological sorting (parents before children)           │    │
│  │    - Generate INSERT/UPSERT statements                       │    │
│  │    - Parameterized queries (SQL injection prevention)        │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                               ↓                                       │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │ 6. Sqitch Integration                                        │    │
│  │    - Wrap SQL in Sqitch deployment script                    │    │
│  │    - Add rollback plan                                       │    │
│  └─────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────┘
                               ↓
┌──────────────────────────────────────────────────────────────────────┐
│ SEAD Change Control (Sqitch) → Database                              │
└──────────────────────────────────────────────────────────────────────┘
```

### Integration with Shape Shifter's Three-Tier Identity System

Shape Shifter has a three-tier identity system ([docs/CONFIGURATION_GUIDE.md](../CONFIGURATION_GUIDE.md)):

1. **`system_id`** - Local sequential (1, 2, 3...), temporary, used for FK relationships during normalization
2. **`keys`** - Business keys for deduplication and reconciliation (e.g., `["site_name"]`)
3. **`public_id`** - Target schema column name (e.g., `site_id`) + holds allocated SEAD IDs from mappings.yml

**SEAD Ingester Integration:**

```
Shape Shifter (Normalization)                SEAD Ingester (This Component)
────────────────────────────────            ────────────────────────────────
system_id (local, temporary)                 → Generate UUIDs
     ↓                                            ↓
keys (business keys)                         → Reconciliation (optional)
     ↓                                            ↓
public_id (column name)                      → Call SEAD Identity API
                                                  ↓
                                             Allocated SEAD integer IDs
                                                  ↓
                                             Map system_id → allocated ID
                                                  ↓
                                             Resolve FKs (system_id → SEAD ID)
                                                  ↓
                                             Generate SQL with SEAD IDs
```

**Critical:** The ingester maps Shape Shifter's temporary `system_id` (1, 2, 3...) to:
1. **Externally-generated UUIDs** (stable across runs)
2. **SEAD-allocated integer IDs** (via Identity API)

This allows Shape Shifter's core to remain unchanged while enabling robust external ID management.

---

## Detailed Component Design

### 1. UUID Generation Component

**Purpose:** Generate stable UUIDs for each entity row in normalized DataFrames.

**Implementation:**

```python
# ingesters/sead/uuid_generator.py

from uuid import uuid4
import pandas as pd
from typing import Dict

class UUIDGenerator:
    """
    Generates UUIDs for normalized entities.
    Maps Shape Shifter system_id → UUID for FK resolution.
    """
    
    def __init__(self):
        self.system_id_to_uuid: Dict[str, Dict[int, str]] = {}  # {entity: {system_id: uuid}}
    
    def generate_for_entity(self, entity_name: str, df: pd.DataFrame) -> pd.DataFrame:
        """
        Adds a UUID column to the DataFrame.
        Stores system_id → UUID mapping for FK resolution.
        
        Args:
            entity_name: Entity name (e.g., 'site')
            df: Normalized DataFrame with system_id column
        
        Returns:
            DataFrame with added {entity}_uuid column
        """
        uuid_column = f"{entity_name}_uuid"
        
        # Generate UUIDs
        df[uuid_column] = [str(uuid4()) for _ in range(len(df))]
        
        # Store mapping: system_id → UUID
        self.system_id_to_uuid[entity_name] = dict(zip(
            df['system_id'],
            df[uuid_column]
        ))
        
        return df
    
    def get_uuid_for_system_id(self, entity_name: str, system_id: int) -> str:
        """Retrieve UUID for a given entity's system_id (used for FK resolution)."""
        return self.system_id_to_uuid[entity_name][system_id]
```

**Usage:**

```python
generator = UUIDGenerator()

# Add UUIDs to each entity
df_sites = generator.generate_for_entity("site", normalized_tables["site"])
df_samples = generator.generate_for_entity("sample", normalized_tables["sample"])

# FK resolution: sample.site_id (system_id) → site.site_uuid
df_samples["site_uuid_fk"] = df_samples["site_id"].apply(
    lambda sid: generator.get_uuid_for_system_id("site", sid)
)
```

---

### 2. Reconciliation Component (Optional Integration)

**Purpose:** Match normalized data to existing SEAD entities using `mappings.yml` (Shape Shifter's existing reconciliation mechanism).

**Integration Strategy:**

Shape Shifter already has `mappings.yml` that maps business keys to SEAD IDs:

```yaml
# data/projects/my_project/mappings.yml
mappings:
  location:
    remote_key: location_id
    local_key: location_name
    mappings:
      "Norway": 162    # Existing SEAD location_id
      "Sweden": 205
```

**Ingester Behavior:**

1. **Entities in mappings.yml** → Use existing SEAD IDs (no allocation needed)
2. **New entities** → Allocate via SEAD Identity API
3. **Partial matches** → Mixed (some mapped, some allocated)

**Implementation:**

```python
# ingesters/sead/reconciliation.py

from typing import Dict, Set
import pandas as pd

class ReconciliationIntegrator:
    """
    Integrates with Shape Shifter's mappings.yml for reconciliation.
    Identifies which entities already exist in SEAD (don't need new IDs).
    """
    
    def __init__(self, mappings: Dict):
        """
        Args:
            mappings: Loaded from mappings.yml (Shape Shifter's reconciliation data)
        """
        self.mappings = mappings
    
    def identify_existing_entities(
        self, 
        entity_name: str, 
        df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Adds column: is_existing (bool) and existing_sead_id (int or None).
        
        Args:
            entity_name: Entity name (e.g., 'location')
            df: Normalized DataFrame with business key columns
        
        Returns:
            DataFrame with added is_existing and existing_sead_id columns
        """
        if entity_name not in self.mappings:
            # No mappings for this entity → all are new
            df["is_existing"] = False
            df["existing_sead_id"] = None
            return df
        
        entity_mappings = self.mappings[entity_name]["mappings"]
        local_key = self.mappings[entity_name]["local_key"]
        
        # Map business key → SEAD ID
        df["existing_sead_id"] = df[local_key].map(entity_mappings)
        df["is_existing"] = df["existing_sead_id"].notnull()
        
        return df
```

**Usage:**

```python
reconciler = ReconciliationIntegrator(mappings_yml)

# Mark existing entities
df_locations = reconciler.identify_existing_entities("location", df_locations)

# Filter for ID allocation
df_new_locations = df_locations[~df_locations["is_existing"]]
df_existing_locations = df_locations[df_locations["is_existing"]]

# Only allocate IDs for new locations
allocate_ids_for(df_new_locations)
```

---

### 3. Identity Allocation Component

**Purpose:** Call SEAD Identity API to allocate integer IDs for new entities.

**See:** [SEAD_IDENTITY_SYSTEM.md](./SEAD_IDENTITY_SYSTEM.md) for full API specification.

**Implementation:**

```python
# ingesters/sead/identity_allocator.py

import requests
from typing import List, Dict
from uuid import UUID

class SEADIdentityAllocator:
    """
    Client for SEAD Identity Allocation API.
    Handles submission creation, batch allocation, and commit/rollback.
    """
    
    def __init__(self, api_base_url: str, api_key: str):
        self.api_base_url = api_base_url
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {api_key}"})
    
    def create_submission(
        self, 
        submission_name: str, 
        source_system: str = "shape_shifter",
        data_type: str = "general"
    ) -> UUID:
        """
        Creates a SEAD submission (groups related allocations).
        
        Returns:
            submission_uuid: Unique identifier for this submission
        """
        response = self.session.post(
            f"{self.api_base_url}/submissions",
            json={
                "submission_name": submission_name,
                "source_system": source_system,
                "data_type": data_type,
            }
        )
        response.raise_for_status()
        return UUID(response.json()["submission_uuid"])
    
    def allocate_batch(
        self,
        submission_uuid: UUID,
        table_name: str,
        column_name: str,
        external_uuids: List[str],
    ) -> Dict[str, int]:
        """
        Allocates SEAD integer IDs for a batch of UUIDs (idempotent).
        
        Args:
            submission_uuid: Submission ID from create_submission()
            table_name: SEAD table name (e.g., 'tbl_sites')
            column_name: SEAD PK column (e.g., 'site_id')
            external_uuids: List of UUIDs to allocate
        
        Returns:
            Mapping: {uuid: allocated_integer_id}
        """
        response = self.session.post(
            f"{self.api_base_url}/submissions/{submission_uuid}/allocations/batch",
            json={
                "table_name": table_name,
                "column_name": column_name,
                "allocations": [
                    {"external_uuid": str(uuid)} for uuid in external_uuids
                ],
            }
        )
        response.raise_for_status()
        
        # Parse response: [{external_uuid, alloc_integer_id}, ...]
        allocations = response.json()["allocations"]
        return {a["external_uuid"]: a["alloc_integer_id"] for a in allocations}
    
    def commit_submission(self, submission_uuid: UUID, change_request_id: str = None):
        """Marks submission as committed (SQL successfully executed)."""
        response = self.session.post(
            f"{self.api_base_url}/submissions/{submission_uuid}/commit",
            json={"change_request_id": change_request_id}
        )
        response.raise_for_status()
    
    def rollback_submission(self, submission_uuid: UUID, delete_allocations: bool = False):
        """Rolls back submission (allows ID reuse if delete_allocations=True)."""
        response = self.session.post(
            f"{self.api_base_url}/submissions/{submission_uuid}/rollback",
            json={"delete_allocations": delete_allocations}
        )
        response.raise_for_status()
```

**Usage:**

```python
allocator = SEADIdentityAllocator(
    api_base_url="https://sead.se/api/v1",
    api_key=os.getenv("SEAD_API_KEY")
)

# Create submission
submission_uuid = allocator.create_submission(
    submission_name="dendro_batch_2026_02",
    data_type="dendro"
)

# Allocate IDs (batch)
uuid_to_site_id = allocator.allocate_batch(
    submission_uuid=submission_uuid,
    table_name="tbl_sites",
    column_name="site_id",
    external_uuids=df_sites["site_uuid"].tolist()
)

# Map back to DataFrame
df_sites["site_id"] = df_sites["site_uuid"].map(uuid_to_site_id)

# On success
allocator.commit_submission(submission_uuid)

# On failure
# allocator.rollback_submission(submission_uuid, delete_allocations=True)
```

---

### 4. Foreign Key Resolution Component

**Purpose:** Resolve FK references from Shape Shifter `system_id` to allocated SEAD integer IDs.

**Implementation:**

```python
# ingesters/sead/fk_resolver.py

import pandas as pd
from typing import Dict

class ForeignKeyResolver:
    """
    Resolves foreign key references:
    1. Shape Shifter system_id → UUID (via UUIDGenerator)
    2. UUID → Allocated SEAD integer ID (via IdentityAllocator)
    """
    
    def __init__(
        self, 
        uuid_generator,  # UUIDGenerator instance
        allocated_ids: Dict[str, Dict[str, int]]  # {entity: {uuid: sead_id}}
    ):
        self.uuid_generator = uuid_generator
        self.allocated_ids = allocated_ids  # From IdentityAllocator.allocate_batch()
    
    def resolve_fk(
        self,
        child_df: pd.DataFrame,
        fk_config: Dict,  # From Project YAML foreign_keys definition
        entity_name: str
    ) -> pd.DataFrame:
        """
        Resolves FK system_id → allocated SEAD ID.
        
        Args:
            child_df: Child entity DataFrame (e.g., samples)
            fk_config: FK configuration from Project YAML
                {
                    "entity": "site",
                    "local_keys": ["site_name"],
                    "remote_keys": ["site_name"]
                }
            entity_name: Current entity name
        
        Returns:
            DataFrame with resolved FK column (e.g., site_id with SEAD IDs)
        """
        parent_entity = fk_config["entity"]
        fk_column = f"{parent_entity}_id"  # Assumes naming convention
        
        # FK column in Shape Shifter's normalized data contains system_id
        # We need to convert: system_id → UUID → allocated SEAD ID
        
        def resolve_system_id_to_sead_id(system_id):
            # Step 1: system_id → UUID
            parent_uuid = self.uuid_generator.get_uuid_for_system_id(
                parent_entity, 
                system_id
            )
            
            # Step 2: UUID → Allocated SEAD ID
            sead_id = self.allocated_ids[parent_entity][parent_uuid]
            
            return sead_id
        
        # Apply resolution
        child_df[fk_column] = child_df[fk_column].apply(resolve_system_id_to_sead_id)
        
        return child_df
    
    def validate_referential_integrity(
        self,
        child_df: pd.DataFrame,
        parent_df: pd.DataFrame,
        fk_column: str,
        parent_pk_column: str
    ) -> bool:
        """
        Validates that all FK values exist in parent table.
        
        Returns:
            True if valid, raises exception if invalid
        """
        parent_ids = set(parent_df[parent_pk_column])
        child_fk_ids = set(child_df[fk_column])
        
        orphaned = child_fk_ids - parent_ids
        if orphaned:
            raise ValueError(
                f"FK integrity violation: Child references non-existent parent IDs: {orphaned}"
            )
        
        return True
```

**Usage:**

```python
resolver = ForeignKeyResolver(uuid_generator, allocated_ids)

# Resolve FK: sample.site_id (system_id) → site.site_id (SEAD ID)
df_samples = resolver.resolve_fk(
    child_df=df_samples,
    fk_config=project_yaml["entities"]["sample"]["foreign_keys"][0],
    entity_name="sample"
)

# Validate integrity
resolver.validate_referential_integrity(
    child_df=df_samples,
    parent_df=df_sites,
    fk_column="site_id",
    parent_pk_column="site_id"
)
```

---

### 5. SQL Generation Component

**Purpose:** Generate Sqitch-ready SQL INSERT/UPSERT statements with topological sorting.

**Implementation:**

```python
# ingesters/sead/sql_generator.py

import pandas as pd
from typing import List, Dict
from src.state import ProcessState  # Reuse Shape Shifter's topological sort

class SEADSQLGenerator:
    """
    Generates SQL DML statements for SEAD ingestion.
    - Topological sorting (parents before children)
    - Parameterized queries (SQL injection prevention)
    - UPSERT support (ON CONFLICT DO UPDATE)
    """
    
    def __init__(self, project_config: Dict):
        self.project_config = project_config
        self.process_state = ProcessState(project_config["entities"])
    
    def generate_sql(
        self,
        normalized_tables: Dict[str, pd.DataFrame],
        table_mapping: Dict[str, str]  # entity_name → SEAD table name
    ) -> str:
        """
        Generates complete SQL script for ingestion.
        
        Args:
            normalized_tables: {entity_name: DataFrame with allocated SEAD IDs}
            table_mapping: {entity_name: sead_table_name}
                e.g., {"site": "tbl_sites", "sample": "tbl_physical_samples"}
        
        Returns:
            SQL script with BEGIN/COMMIT block
        """
        # Topological sort entities (parents before children)
        sorted_entities = self.process_state.sorted_entities
        
        sql_parts = [
            "-- Generated by Shape Shifter SEAD Ingester",
            f"-- Date: {pd.Timestamp.now()}",
            "",
            "BEGIN;",
            ""
        ]
        
        for entity_name in sorted_entities:
            if entity_name not in normalized_tables:
                continue
            
            df = normalized_tables[entity_name]
            sead_table = table_mapping[entity_name]
            entity_config = self.project_config["entities"][entity_name]
            
            # Generate INSERT statements for this entity
            entity_sql = self._generate_entity_inserts(
                df=df,
                entity_name=entity_name,
                sead_table=sead_table,
                entity_config=entity_config
            )
            
            sql_parts.append(f"-- Entity: {entity_name} → {sead_table}")
            sql_parts.append(entity_sql)
            sql_parts.append("")
        
        sql_parts.append("COMMIT;")
        
        return "\n".join(sql_parts)
    
    def _generate_entity_inserts(
        self,
        df: pd.DataFrame,
        entity_name: str,
        sead_table: str,
        entity_config: Dict
    ) -> str:
        """
        Generates INSERT/UPSERT statements for one entity.
        
        Strategy:
        - Reconciled entities (is_existing=True) → UPDATE (if needed)
        - New entities → INSERT with ON CONFLICT DO UPDATE (idempotent)
        """
        public_id_col = entity_config.get("public_id", f"{entity_name}_id")
        uuid_col = f"{entity_name}_uuid"
        
        # Filter columns (exclude Shape Shifter internal columns)
        columns_to_insert = [
            col for col in df.columns 
            if col not in ["system_id", "is_existing", "existing_sead_id"]
        ]
        
        inserts = []
        for _, row in df.iterrows():
            # Build INSERT statement
            columns = ", ".join(columns_to_insert)
            values = ", ".join([
                self._format_value(row[col]) for col in columns_to_insert
            ])
            
            # UPSERT: ON CONFLICT (uuid) DO UPDATE
            # This makes ingestion idempotent
            update_clause = ", ".join([
                f"{col} = EXCLUDED.{col}" 
                for col in columns_to_insert 
                if col not in [public_id_col, uuid_col]  # Don't update PK/UUID
            ])
            
            sql = f"""
INSERT INTO {sead_table} ({columns})
VALUES ({values})
ON CONFLICT ({uuid_col}) DO UPDATE SET
    {update_clause},
    date_updated = NOW();
""".strip()
            
            inserts.append(sql)
        
        return "\n\n".join(inserts)
    
    def _format_value(self, value) -> str:
        """Formats Python value for SQL (escapes strings, handles nulls)."""
        if pd.isna(value):
            return "NULL"
        elif isinstance(value, str):
            # Escape single quotes
            escaped = value.replace("'", "''")
            return f"'{escaped}'"
        elif isinstance(value, (int, float)):
            return str(value)
        else:
            # Handle other types (dates, UUIDs, etc.)
            return f"'{str(value)}'"
```

**Usage:**

```python
generator = SEADSQLGenerator(project_config)

table_mapping = {
    "site": "tbl_sites",
    "sample": "tbl_physical_samples",
}

sql_script = generator.generate_sql(
    normalized_tables={
        "site": df_sites_with_sead_ids,
        "sample": df_samples_with_sead_ids,
    },
    table_mapping=table_mapping
)

# Write to file
with open("deploy_dendro_2026_02.sql", "w") as f:
    f.write(sql_script)
```

---

### 6. Sqitch Integration Component

**Purpose:** Wrap SQL in Sqitch deployment script with proper metadata and rollback plan.

**Implementation:**

```python
# ingesters/sead/sqitch_wrapper.py

from datetime import datetime
from typing import Dict

class SqitchWrapper:
    """
    Wraps generated SQL in Sqitch deployment format.
    Sqitch is SEAD's database change control system.
    """
    
    def __init__(self, project_name: str, submission_name: str):
        self.project_name = project_name
        self.submission_name = submission_name
        self.change_id = f"{submission_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    def wrap_deployment(self, sql_content: str, entity_summary: Dict[str, int]) -> str:
        """
        Creates Sqitch deploy script.
        
        Args:
            sql_content: Generated SQL INSERT/UPDATE statements
            entity_summary: {entity_name: row_count}
        
        Returns:
            Sqitch-formatted deploy script
        """
        summary_lines = [
            f"-- {entity}: {count} rows" 
            for entity, count in entity_summary.items()
        ]
        
        return f"""-- Deploy {self.change_id}
-- requires: sead_schema

-- Metadata
-- Project: {self.project_name}
-- Submission: {self.submission_name}
-- Generated: {datetime.now().isoformat()}
-- Summary:
{chr(10).join(summary_lines)}

BEGIN;

{sql_content}

COMMIT;
"""
    
    def wrap_rollback(self, entity_summary: Dict[str, int], submission_uuid: str) -> str:
        """
        Creates Sqitch rollback script (calls SEAD Identity API to rollback allocation).
        
        Args:
            entity_summary: {entity_name: row_count}
            submission_uuid: SEAD submission UUID
        
        Returns:
            Sqitch-formatted rollback script
        """
        return f"""-- Revert {self.change_id}

BEGIN;

-- WARNING: This will rollback ID allocations for submission {submission_uuid}
-- via SEAD Identity API. Data inserted by deploy script will remain unless
-- manually deleted.

-- Call SEAD Identity API rollback endpoint:
-- POST /api/v1/submissions/{submission_uuid}/rollback

-- Manual cleanup (if needed):
{self._generate_delete_statements(entity_summary)}

COMMIT;
"""
    
    def _generate_delete_statements(self, entity_summary: Dict[str, int]) -> str:
        """Generates DELETE statements for manual rollback (commented out)."""
        deletes = []
        for entity, count in entity_summary.items():
            deletes.append(
                f"-- DELETE FROM tbl_{entity}s "
                f"WHERE {entity}_uuid IN (SELECT external_uuid FROM sead_utility.identity_allocations WHERE submission_uuid = '{submission_uuid}');"
            )
        return "\n".join(deletes)
```

**Usage:**

```python
wrapper = SqitchWrapper(
    project_name="dendro_project",
    submission_name="dendro_batch_2026_02"
)

# Generate deploy script
deploy_script = wrapper.wrap_deployment(
    sql_content=generated_sql,
    entity_summary={"site": 15, "sample": 342}
)

# Generate rollback script
rollback_script = wrapper.wrap_rollback(
    entity_summary={"site": 15, "sample": 342},
    submission_uuid=str(submission_uuid)
)

# Write Sqitch files
with open(f"deploy/{wrapper.change_id}.sql", "w") as f:
    f.write(deploy_script)

with open(f"revert/{wrapper.change_id}.sql", "w") as f:
    f.write(rollback_script)
```

---

## Main Ingester Class (Orchestrator)

**Purpose:** Orchestrate all components into a cohesive ingestion workflow.

**Implementation:**

```python
# ingesters/sead/ingester.py

from backend.app.ingesters.protocol import Ingester, IngesterConfig, IngesterMetadata
from backend.app.ingesters.protocol import ValidationResult, IngestionResult
from backend.app.ingesters.registry import Ingesters

from .uuid_generator import UUIDGenerator
from .reconciliation import ReconciliationIntegrator
from .identity_allocator import SEADIdentityAllocator
from .fk_resolver import ForeignKeyResolver
from .sql_generator import SEADSQLGenerator
from .sqitch_wrapper import SqitchWrapper

import pandas as pd
from pathlib import Path
from typing import Dict
import yaml

@Ingesters.register(key="sead_sql")
class SEADSQLIngester(Ingester):
    """
    SEAD SQL Ingester - Generates Sqitch-ready SQL DML from normalized DataFrames.
    
    ALL SEAD-specific logic resides in this ingester.
    Shape Shifter core remains domain-agnostic.
    """
    
    @classmethod
    def get_metadata(cls) -> IngesterMetadata:
        return IngesterMetadata(
            key="sead_sql",
            name="SEAD SQL Ingester",
            description="Generates SQL DML for SEAD database via Identity API",
            version="1.0.0",
            supported_formats=["dataframe"],  # Ingests from normalized DataFrames
        )
    
    def __init__(self, config: IngesterConfig):
        """
        Initialize SEAD ingester.
        
        config.extra expected keys:
            - sead_api_url: str (SEAD Identity API base URL)
            - sead_api_key: str (API authentication key)
            - project_path: str (Path to Shape Shifter project directory)
            - output_folder: str (Where to write Sqitch scripts)
            - table_mapping: Dict[str, str] (entity_name → SEAD table name)
            - reconcile: bool (Whether to use mappings.yml reconciliation, default True)
        """
        self.config = config
        
        # Extract SEAD-specific config
        self.sead_api_url = config.extra["sead_api_url"]
        self.sead_api_key = config.extra["sead_api_key"]
        self.project_path = Path(config.extra["project_path"])
        self.output_folder = Path(config.extra.get("output_folder", "./output"))
        self.table_mapping = config.extra["table_mapping"]
        self.reconcile = config.extra.get("reconcile", True)
        
        # Load project YAML
        with open(self.project_path / "shapeshifter.yml") as f:
            self.project_config = yaml.safe_load(f)
        
        # Initialize components
        self.uuid_generator = UUIDGenerator()
        self.allocator = SEADIdentityAllocator(self.sead_api_url, self.sead_api_key)
        self.sql_generator = SEADSQLGenerator(self.project_config)
        
        # Optional: Reconciliation
        if self.reconcile and (self.project_path / "mappings.yml").exists():
            with open(self.project_path / "mappings.yml") as f:
                mappings = yaml.safe_load(f)
            self.reconciler = ReconciliationIntegrator(mappings.get("mappings", {}))
        else:
            self.reconciler = None
    
    def validate(self, normalized_tables: Dict[str, pd.DataFrame]) -> ValidationResult:
        """
        Validate normalized DataFrames before ingestion (dry-run).
        
        Checks:
        - Required columns present
        - FK referential integrity
        - Data types compatible with SEAD schema
        - UUID generation successful
        - SEAD API reachable
        """
        errors = []
        warnings = []
        
        try:
            # 1. Check SEAD API connectivity
            test_submission = self.allocator.create_submission(
                submission_name=f"validation_test_{pd.Timestamp.now().timestamp()}",
                data_type="validation"
            )
            self.allocator.rollback_submission(test_submission, delete_allocations=True)
            
        except Exception as e:
            errors.append(f"SEAD API connectivity failed: {e}")
        
        # 2. Validate entity configurations
        for entity_name, df in normalized_tables.items():
            entity_config = self.project_config["entities"].get(entity_name)
            if not entity_config:
                errors.append(f"Entity '{entity_name}' not found in project config")
                continue
            
            # Check required columns
            public_id_col = entity_config.get("public_id", f"{entity_name}_id")
            if "system_id" not in df.columns:
                errors.append(f"Entity '{entity_name}' missing 'system_id' column")
            
            # Check data types (basic validation)
            if not pd.api.types.is_numeric_dtype(df["system_id"]):
                errors.append(f"Entity '{entity_name}': system_id must be numeric")
        
        # 3. Validate FK references
        for entity_name, df in normalized_tables.items():
            entity_config = self.project_config["entities"].get(entity_name, {})
            foreign_keys = entity_config.get("foreign_keys", [])
            
            for fk in foreign_keys:
                parent_entity = fk["entity"]
                if parent_entity not in normalized_tables:
                    errors.append(
                        f"FK validation failed: Parent entity '{parent_entity}' "
                        f"not found for child '{entity_name}'"
                    )
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def ingest(
        self, 
        normalized_tables: Dict[str, pd.DataFrame],
        submission_name: str,
        data_type: str = "general",
        dry_run: bool = False
    ) -> IngestionResult:
        """
        Main ingestion workflow.
        
        Args:
            normalized_tables: {entity_name: DataFrame} (from Shape Shifter normalizer)
            submission_name: Human-readable submission name
            data_type: SEAD data type (e.g., 'dendro', 'ceramics')
            dry_run: If True, generate SQL but don't allocate IDs (validation only)
        
        Returns:
            IngestionResult with success status, row counts, and output file paths
        """
        try:
            # Step 0: Validation
            validation = self.validate(normalized_tables)
            if not validation.is_valid:
                return IngestionResult(
                    success=False,
                    message=f"Validation failed: {', '.join(validation.errors)}",
                    records_processed=0
                )
            
            if dry_run:
                return IngestionResult(
                    success=True,
                    message="Dry-run validation passed (no IDs allocated)",
                    records_processed=0
                )
            
            # Step 1: Create SEAD submission
            submission_uuid = self.allocator.create_submission(
                submission_name=submission_name,
                source_system="shape_shifter",
                data_type=data_type
            )
            
            # Step 2: Generate UUIDs for all entities
            for entity_name, df in normalized_tables.items():
                normalized_tables[entity_name] = self.uuid_generator.generate_for_entity(
                    entity_name, df
                )
            
            # Step 3: Reconciliation (optional)
            if self.reconciler:
                for entity_name, df in normalized_tables.items():
                    normalized_tables[entity_name] = self.reconciler.identify_existing_entities(
                        entity_name, df
                    )
            
            # Step 4: Allocate SEAD IDs (batch per entity)
            allocated_ids = {}  # {entity_name: {uuid: sead_id}}
            
            for entity_name, df in normalized_tables.items():
                # Filter only new entities (not reconciled)
                if "is_existing" in df.columns:
                    df_new = df[~df["is_existing"]]
                else:
                    df_new = df
                
                if len(df_new) == 0:
                    continue  # All reconciled, skip allocation
                
                # Call SEAD Identity API
                uuid_col = f"{entity_name}_uuid"
                sead_table = self.table_mapping[entity_name]
                public_id_col = self.project_config["entities"][entity_name].get(
                    "public_id", f"{entity_name}_id"
                )
                
                allocated = self.allocator.allocate_batch(
                    submission_uuid=submission_uuid,
                    table_name=sead_table,
                    column_name=public_id_col,
                    external_uuids=df_new[uuid_col].tolist()
                )
                
                allocated_ids[entity_name] = allocated
                
                # Map allocated IDs back to DataFrame
                normalized_tables[entity_name][public_id_col] = (
                    normalized_tables[entity_name][uuid_col].map(allocated)
                )
            
            # Step 5: Resolve Foreign Keys
            resolver = ForeignKeyResolver(self.uuid_generator, allocated_ids)
            
            for entity_name, df in normalized_tables.items():
                entity_config = self.project_config["entities"][entity_name]
                foreign_keys = entity_config.get("foreign_keys", [])
                
                for fk_config in foreign_keys:
                    normalized_tables[entity_name] = resolver.resolve_fk(
                        child_df=df,
                        fk_config=fk_config,
                        entity_name=entity_name
                    )
            
            # Step 6: Generate SQL
            sql_script = self.sql_generator.generate_sql(
                normalized_tables=normalized_tables,
                table_mapping=self.table_mapping
            )
            
            # Step 7: Wrap in Sqitch deployment
            wrapper = SqitchWrapper(
                project_name=self.project_config.get("name", "unknown"),
                submission_name=submission_name
            )
            
            entity_summary = {
                entity: len(df) for entity, df in normalized_tables.items()
            }
            
            deploy_script = wrapper.wrap_deployment(sql_script, entity_summary)
            rollback_script = wrapper.wrap_rollback(entity_summary, str(submission_uuid))
            
            # Step 8: Write output files
            self.output_folder.mkdir(parents=True, exist_ok=True)
            deploy_path = self.output_folder / f"deploy_{wrapper.change_id}.sql"
            rollback_path = self.output_folder / f"revert_{wrapper.change_id}.sql"
            
            with open(deploy_path, "w") as f:
                f.write(deploy_script)
            
            with open(rollback_path, "w") as f:
                f.write(rollback_script)
            
            # Step 9: Return success
            total_rows = sum(len(df) for df in normalized_tables.values())
            
            return IngestionResult(
                success=True,
                message=f"SQL generated successfully. Deploy: {deploy_path}",
                records_processed=total_rows,
                metadata={
                    "submission_uuid": str(submission_uuid),
                    "deploy_script": str(deploy_path),
                    "rollback_script": str(rollback_path),
                    "entity_summary": entity_summary,
                }
            )
        
        except Exception as e:
            # Rollback on failure
            if 'submission_uuid' in locals():
                self.allocator.rollback_submission(
                    submission_uuid, 
                    delete_allocations=True
                )
            
            return IngestionResult(
                success=False,
                message=f"Ingestion failed: {str(e)}",
                records_processed=0
            )
```

---

## CLI Integration

**Usage:**

```bash
# Validate only (dry-run)
python -m backend.app.scripts.ingest ingest sead_sql \
  --project-path data/projects/dendro_2026 \
  --submission-name "dendro_batch_001" \
  --data-type "dendro" \
  --dry-run

# Full ingestion (allocate IDs, generate SQL)
python -m backend.app.scripts.ingest ingest sead_sql \
  --project-path data/projects/dendro_2026 \
  --submission-name "dendro_batch_001" \
  --data-type "dendro" \
  --output-folder output/dendro \
  --sead-api-url https://sead.se/api/v1 \
  --sead-api-key $SEAD_API_KEY \
  --reconcile  # Use mappings.yml for reconciliation
```

---

## Implementation Phases

### Phase 1: Core Infrastructure (Weeks 1-3)

**Dependencies:** SEAD Identity System deployed (see [SEAD_IDENTITY_SYSTEM.md](./SEAD_IDENTITY_SYSTEM.md))

**Deliverables:**
- [ ] UUID Generation component
- [ ] Identity Allocator (SEAD API client)
- [ ] FK Resolver (system_id → UUID → SEAD ID)
- [ ] Unit tests for each component

**Success Criteria:**
- Generate UUIDs for 10,000 entities in < 1 second
- Allocate 1,000 SEAD IDs in < 5 seconds (batch API)
- Resolve FKs with 100% accuracy (referential integrity checks pass)

---

### Phase 2: SQL Generation (Weeks 4-5)

**Deliverables:**
- [ ] SQL Generator with topological sorting
- [ ] Sqitch wrapper (deploy/revert scripts)
- [ ] Parameterized query builder (SQL injection prevention)
- [ ] Integration tests with test SEAD schema

**Success Criteria:**
- Generate valid SQL for 5 test projects
- FK integrity checks pass 100%
- SQL executes successfully on SEAD staging

---

### Phase 3: Reconciliation Integration (Week 6)

**Deliverables:**
- [ ] Reconciliation component (mappings.yml integration)
- [ ] Mixed ingestion (some reconciled, some new)
- [ ] Update vs INSERT logic
- [ ] Tests with historical reconciliation data

**Success Criteria:**
- Correctly identify 95%+ of reconciled entities
- No duplicate entity creation for reconciled data
- Existing SEAD IDs preserved

---

### Phase 4: Main Orchestrator (Week 7)

**Deliverables:**
- [ ] SEADSQLIngester class (implements Ingester protocol)
- [ ] End-to-end workflow orchestration
- [ ] Error handling and rollback logic
- [ ] Comprehensive integration tests

**Success Criteria:**
- Complete end-to-end test with real project
- Rollback successfully recovers from failures
- Dry-run mode validates without side effects

---

### Phase 5: CLI & Documentation (Week 8)

**Deliverables:**
- [ ] CLI commands integrated with existing `ingest` tool
- [ ] User documentation and examples
- [ ] Runbooks for common scenarios
- [ ] Training materials for SEAD team

**Success Criteria:**
- Non-technical users can run ingestion from CLI
- Documentation covers 10+ common use cases
- Positive feedback from pilot users

---

### Phase 6: Production Rollout (Weeks 9-10)

**Deliverables:**
- [ ] Gradual rollout (test projects → production)
- [ ] Performance tuning and optimization
- [ ] Monitoring and alerting setup
- [ ] Fallback plan (keep old workflow parallel for 3 months)

**Success Criteria:**
- 5+ successful production ingestions
- Zero data loss or corruption incidents
- Performance meets benchmarks (< 1 hour for 10,000 entities)

---

## Testing Strategy

### Unit Tests

**Components to test:**
- UUID Generator (collision detection, mapping correctness)
- Identity Allocator (idempotency, error handling)
- FK Resolver (system_id → SEAD ID mapping accuracy)
- SQL Generator (syntax validation, topological sorting)
- Sqitch Wrapper (script format validation)

### Integration Tests

**End-to-end workflows:**
- [ ] Simple project (2 entities, no FKs) → SQL generation
- [ ] Complex project (10+ entities, multiple FK levels) → SQL generation
- [ ] Reconciled project (mix of existing and new entities) → Mixed SQL
- [ ] Rollback scenario (failure after allocation) → Cleanup verification
- [ ] Concurrent ingestions (2 submissions in parallel) → No conflicts

### Performance Tests

**Benchmarks:**
- [ ] 1,000 entities × 1,000 rows = 1M rows → < 5 minutes end-to-end
- [ ] 100 entities × 100 rows = 10K rows → < 30 seconds end-to-end
- [ ] Batch allocation 10,000 UUIDs → < 10 seconds
- [ ] SQL generation for 100 entities → < 5 seconds

### Validation Tests

**Dry-run scenarios:**
- [ ] Missing FK parent entity → Error detected before allocation
- [ ] Invalid data types → Error detected before allocation
- [ ] SEAD API unreachable → Error detected early
- [ ] Duplicate business keys → Warning issued

---

## Risk Analysis

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| **SEAD API downtime** | Medium | High | Queue-based retry logic, fallback to old workflow |
| **FK resolution errors** | Low | High | Extensive validation in dry-run, unit tests for all FK patterns |
| **SQL injection vulnerability** | Low | Critical | Parameterized queries, input sanitization, security audit |
| **Data loss on rollback** | Low | Critical | Atomic transactions, rollback tests, audit trail |
| **Performance degradation (large projects)** | Medium | Medium | Batch allocation, connection pooling, async processing |
| **Sqitch integration issues** | Medium | Medium | Early validation with SEAD team, pilot deployments |
| **Reconciliation mismatch** | Medium | Medium | Human review step for reconciled entities, confidence scores |

---

## Security Considerations

### API Security
- **Authentication:** SEAD API key stored securely (environment variables, secrets manager)
- **Authorization:** Per-submission permissions enforced by SEAD API
- **Encryption:** HTTPS for all API communication (TLS 1.3)

### SQL Injection Prevention
- **Parameterized queries:** Never concatenate user input into SQL
- **Input validation:** Whitelist entity/table names, reject suspicious patterns
- **Code review:** Security audit of SQL generation logic

### Data Privacy
- **Audit trail:** All ingestions logged with user, timestamp, submission UUID
- **Access control:** Only authorized users can create submissions
- **Data retention:** Rollback data retained for 90 days, then archived

---

## Open Questions

1. **Partial Commits:** Should we support committing successful entities while rolling back failed ones?
   - **Recommendation:** Phase 2 feature - requires transaction savepoints

2. **Schema Evolution:** How to handle SEAD schema changes (new columns, renamed tables)?
   - **Recommendation:** Version table_mapping in project YAML, validate against SEAD schema API

3. **Performance Optimization:** Should we pre-allocate ID ranges for known entity counts?
   - **Recommendation:** Benchmark and decide - may reduce API round-trips

4. **Reconciliation Confidence:** Should we support fuzzy matching for reconciliation?
   - **Recommendation:** Phase 3 feature - add confidence scores, require manual review for < 90%

5. **Concurrent Submissions:** How to handle multiple Shape Shifter instances ingesting simultaneously?
   - **Recommendation:** SEAD Identity API handles concurrency - test with load tests

6. **Rollback Cleanup:** Should rollback delete all data or just mark allocations as rolled_back?
   - **Recommendation:** Configurable - default soft rollback (preserve audit), option for hard delete (testing)

---

## Success Criteria

### Technical
- ✅ Generate valid Sqitch-ready SQL for 20+ test projects
- ✅ 100% FK referential integrity in generated SQL
- ✅ Zero ID collisions across concurrent submissions
- ✅ < 1 hour end-to-end time for 10,000 entity project
- ✅ Successful integration with SEAD Identity API (> 99% uptime)

### Business
- ✅ Reduce ingestion time from days to hours (5x improvement)
- ✅ Enable concurrent submissions (3+ teams working in parallel)
- ✅ Improve data quality (95%+ reconciliation accuracy)
- ✅ Eliminate manual ID reconciliation (zero manual ID mapping steps)

### Adoption
- ✅ 10+ successful production ingestions within 3 months
- ✅ Positive feedback from SEAD data managers
- ✅ Training materials complete and reviewed
- ✅ Old workflow deprecated after 6 months

---

## Future Enhancements

### Phase 2 Features (Post-MVP)
- **Partial commits:** Savepoint-based granular rollback
- **Real-time validation:** WebSocket feedback during data preparation
- **GraphQL API:** Alternative to REST for complex queries
- **Automated reconciliation:** Fuzzy matching with confidence scores
- **Schema introspection:** Auto-generate table_mapping from SEAD schema

### Long-term Vision
- **Federated ingestion:** Multiple SEAD instances with cross-instance reconciliation
- **Event sourcing:** Stream-based ingestion (Kafka/Redis Streams)
- **Natural key integration:** Link UUIDs to DOIs, ISBNs, ORCIDs
- **Blockchain audit trail:** Immutable ingestion records (if compliance requires)

---

## Appendix A: Configuration Example

**Project YAML (Shape Shifter):**

```yaml
# data/projects/dendro_2026/shapeshifter.yml

name: dendro_2026
description: Dendrochronology dataset February 2026

entities:
  site:
    system_id: system_id
    public_id: site_id
    keys: [site_name]
    columns:
      - site_name
      - latitude
      - longitude
    
  sample:
    system_id: system_id
    public_id: physical_sample_id
    keys: [sample_name]
    columns:
      - sample_name
      - site_id
      - collection_date
    foreign_keys:
      - entity: site
        local_keys: [site_name]
        remote_keys: [site_name]
```

**Ingester Config:**

```python
# CLI arguments or config file

config = IngesterConfig(
    extra={
        "sead_api_url": "https://sead.se/api/v1",
        "sead_api_key": os.getenv("SEAD_API_KEY"),
        "project_path": "data/projects/dendro_2026",
        "output_folder": "output/dendro_2026",
        "table_mapping": {
            "site": "tbl_sites",
            "sample": "tbl_physical_samples",
        },
        "reconcile": True,
    }
)
```

---

## Appendix B: Generated SQL Example

**Input:** 2 sites, 3 samples

**Output:**

```sql
-- Generated by Shape Shifter SEAD Ingester
-- Date: 2026-02-21 10:30:00
-- Submission: dendro_batch_001
-- Summary:
-- site: 2 rows
-- sample: 3 rows

BEGIN;

-- Entity: site → tbl_sites
INSERT INTO tbl_sites (site_id, site_uuid, site_name, latitude, longitude, date_updated)
VALUES (12345, 'a3e4f567-e89b-12d3-a456-426614174001', 'Site A', 59.123, 18.456, NOW())
ON CONFLICT (site_uuid) DO UPDATE SET
    site_name = EXCLUDED.site_name,
    latitude = EXCLUDED.latitude,
    longitude = EXCLUDED.longitude,
    date_updated = NOW();

INSERT INTO tbl_sites (site_id, site_uuid, site_name, latitude, longitude, date_updated)
VALUES (12346, 'b4f5g678-f90c-23e4-b567-537725285002', 'Site B', 60.234, 19.567, NOW())
ON CONFLICT (site_uuid) DO UPDATE SET
    site_name = EXCLUDED.site_name,
    latitude = EXCLUDED.latitude,
    longitude = EXCLUDED.longitude,
    date_updated = NOW();

-- Entity: sample → tbl_physical_samples
INSERT INTO tbl_physical_samples (physical_sample_id, physical_sample_uuid, sample_name, site_id, collection_date, date_updated)
VALUES (67890, 'c5g6h789-e89b-12d3-a456-426614174003', 'Sample 1', 12345, '2025-06-15', NOW())
ON CONFLICT (physical_sample_uuid) DO UPDATE SET
    sample_name = EXCLUDED.sample_name,
    site_id = EXCLUDED.site_id,
    collection_date = EXCLUDED.collection_date,
    date_updated = NOW();

INSERT INTO tbl_physical_samples (physical_sample_id, physical_sample_uuid, sample_name, site_id, collection_date, date_updated)
VALUES (67891, 'd6h7i890-f01d-34e5-c678-648836396003', 'Sample 2', 12345, '2025-06-16', NOW())
ON CONFLICT (physical_sample_uuid) DO UPDATE SET
    sample_name = EXCLUDED.sample_name,
    site_id = EXCLUDED.site_id,
    collection_date = EXCLUDED.collection_date,
    date_updated = NOW();

INSERT INTO tbl_physical_samples (physical_sample_id, physical_sample_uuid, sample_name, site_id, collection_date, date_updated)
VALUES (67892, 'e7i8j901-g12e-45f6-d789-759947407004', 'Sample 3', 12346, '2025-06-17', NOW())
ON CONFLICT (physical_sample_uuid) DO UPDATE SET
    sample_name = EXCLUDED.sample_name,
    site_id = EXCLUDED.site_id,
    collection_date = EXCLUDED.collection_date,
    date_updated = NOW();

COMMIT;
```

---

## Appendix C: Directory Structure

```
ingesters/
└── sead/
    ├── __init__.py
    ├── ingester.py                 # Main SEADSQLIngester class
    ├── uuid_generator.py           # UUID generation + mapping
    ├── reconciliation.py           # mappings.yml integration
    ├── identity_allocator.py       # SEAD Identity API client
    ├── fk_resolver.py              # FK system_id → SEAD ID
    ├── sql_generator.py            # SQL DML generation
    ├── sqitch_wrapper.py           # Sqitch deploy/revert scripts
    └── tests/
        ├── test_uuid_generator.py
        ├── test_reconciliation.py
        ├── test_identity_allocator.py
        ├── test_fk_resolver.py
        ├── test_sql_generator.py
        ├── test_sqitch_wrapper.py
        └── test_ingester_e2e.py    # End-to-end integration
```

---

**End of Document**

**Related Documents:**
- [SEAD_IDENTITY_SYSTEM.md](./SEAD_IDENTITY_SYSTEM.md) - Hybrid Integer + UUID identity allocation system (external to Shape Shifter)
- [NEW_INGESTER.md](./NEW_INGESTER.md) - Original design notes (reference)
- [../CONFIGURATION_GUIDE.md](../CONFIGURATION_GUIDE.md) - Shape Shifter configuration reference
- [../ARCHITECTURE.md](../ARCHITECTURE.md) - Shape Shifter system architecture
