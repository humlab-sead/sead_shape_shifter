# Aggregate Model for Identity Systems

This directory contains documentation for the **Generic Aggregate Model** - a metadata-driven system for tracking entity hierarchies and dependencies in identity allocation systems.

---

## 📁 Documents

### 1. **[AGGREGATE_MODEL_DESIGN.md](./AGGREGATE_MODEL_DESIGN.md)** - Generic Design ⭐

**Scope:** Domain-agnostic model for any identity system  
**Purpose:** Define database schema for tracking aggregates, dependencies, and relationships  
**Content:**
- Entity types registry, aggregate definitions, dependency tracking
- PostgreSQL tables, views, and functions
- Validation logic and topological sorting
- Generic migration strategy

**Use this for:** Understanding the model, implementing in any domain (finance, healthcare, e-commerce)

---

### 2. **[SEAD_AGGREGATE_MODEL.md](./SEAD_AGGREGATE_MODEL.md)** - SEAD Implementation 🔧

**Scope:** SEAD-specific implementation and usage  
**Purpose:** Apply aggregate model to SEAD database entities  
**Content:**
- SEAD entity analysis (which tables are aggregates)
- Data population scripts (INSERT statements for tbl_sites, tbl_locations, etc.)
- SEAD-specific validation examples
- Natural key patterns for SEAD entities
- Deployment plan for SEAD database

**Use this for:** Deploying aggregate model to SEAD staging/production

---

## 🎯 Quick Start

### For Implementation

**Step 1:** Read [AGGREGATE_MODEL_DESIGN.md](./AGGREGATE_MODEL_DESIGN.md)
- Understand the generic model structure
- Review tables: `entity_types`, `aggregate_definitions`, `entity_dependencies`
- Study validation functions and views

**Step 2:** Read [SEAD_AGGREGATE_MODEL.md](./SEAD_AGGREGATE_MODEL.md)
- See how model applies to SEAD entities
- Review entity classifications (aggregates vs dependents)
- Get data population scripts

**Step 3:** Deploy to SEAD
- Run generic DDL from AGGREGATE_MODEL_DESIGN.md
- Run SEAD data population from SEAD_AGGREGATE_MODEL.md
- Test with validation functions

---

## 🏗️ Architecture Overview

### Generic Model (Domain-Agnostic)

```
┌──────────────────────────────────────┐
│ entity_types                          │  EntityTypeRegistry
│ • entity_type_key (unique string)    │  - Any domain
│ • table_name, pk_column_name         │  - Metadata storage
│ • is_aggregate (boolean)             │  - Version tracking
└──────────────────────────────────────┘
              ↓
┌──────────────────────────────────────┐
│ aggregate_definitions                 │  AggregateMetadata
│ • aggregate_priority (order)          │  - Allocation rules
│ • supports_natural_keys (bool)        │  - Batch config
└──────────────────────────────────────┘
              ↓
┌──────────────────────────────────────┐
│ entity_dependencies                   │  DependencyGraph
│ • parent_entity_type_id (FK)          │  - FK relationships
│ • child_entity_type_id (FK)           │  - Cascade rules
│ • fk_column_name                      │  - Topological sort
└──────────────────────────────────────┘
```

### SEAD Implementation

```
SEAD Entities → Aggregate Model Metadata
───────────────────────────────────────
tbl_locations      → entity_type_key='location', is_aggregate=TRUE, priority=10
tbl_sites          → entity_type_key='site', is_aggregate=TRUE, priority=20
tbl_sample_groups  → entity_type_key='sample_group', is_aggregate=TRUE, priority=30
tbl_features       → entity_type_key='feature', is_aggregate=FALSE (dependent)

Dependencies:
site → location (FK: location_id)
sample_group → site (FK: site_id)
feature → site (FK: site_id)
```

---

## 🔑 Key Concepts

### Aggregate Root

**Definition:** An entity that:
- Has independent meaning (can exist without parent)
- Is submitted as primary data entry point
- Has child entities depending on it
- Forms a consistency boundary

**Examples:**
- **Generic:** Order, Patient, Account, Location
- **SEAD:** Site, Location, Sample Group, Physical Sample

### Dependency

**Definition:** A parent-child relationship where:
- Child references parent via foreign key
- Child cannot exist without parent (if FK required)
- Determines allocation order (parent before child)

**Examples:**
- **Generic:** Order → OrderLines, Patient → Encounters
- **SEAD:** Site → Sample Groups, Location → Sites

### Topological Depth

**Definition:** Number of dependency hops from root entities
- Depth 0: No parents (root aggregates like Location)
- Depth 1: Direct children of depth 0 (Site depends on Location)
- Depth 2: Children of depth 1 (Sample Group depends on Site)

**Use:** Determines allocation order automatically

---

## 📊 Benefits

### 1. Self-Documenting System
Query `v_aggregate_hierarchy` to see all entity relationships - no separate docs needed

### 2. Early Validation
API rejects submissions with missing parent entities before allocation starts

### 3. Optimized Batching
Automatically allocate aggregates + dependents in single transaction

### 4. Future-Proof
Supports schema evolution, change detection, soft deletes without model changes

### 5. Domain Agnostic
Same model works for SEAD, finance, healthcare, e-commerce

---

## 🧪 Testing Strategy

### Unit Tests
- `calculate_topological_depth()` correctly assigns depths
- `validate_entity_submission()` detects missing parents
- `get_allocation_order()` returns correct sequence

### Integration Tests
- Register SEAD entities and calculate depths
- Validate complex SEAD submissions
- Query hierarchy views with SEAD data

### Performance Tests
- Benchmark validation with 100+ entity types
- Test topological sorting with deep hierarchies (10+ levels)
- Measure query performance on dependency graph views

---

## 📚 Related Documentation

### Identity System Docs
- [../new_ingester/SEAD_IDENTITY_SYSTEM.md](../new_ingester/SEAD_IDENTITY_SYSTEM.md) - Core identity design
- [../new_ingester/SEAD_IDENTITY_IMPLEMENTATION.md](../new_ingester/SEAD_IDENTITY_IMPLEMENTATION.md) - Identity DB schema
- [../new_ingester/SEAD_IDENTITY_NFR.md](../new_ingester/SEAD_IDENTITY_NFR.md) - Performance/security

### Ingester Docs
- [../new_ingester/SEAD_INGESTER_DESIGN.md](../new_ingester/SEAD_INGESTER_DESIGN.md) - Shape Shifter integration

---

## 🚀 Deployment Checklist

### Phase 1: Generic Model (Week 1)
- [ ] Deploy tables: `entity_types`, `aggregate_definitions`, `entity_dependencies`
- [ ] Deploy views: `v_aggregate_hierarchy`, `v_entity_dependency_graph`, `v_aggregate_allocation_stats`
- [ ] Deploy functions: `calculate_topological_depth()`, `validate_entity_submission()`, `get_allocation_order()`
- [ ] Run unit tests

### Phase 2: SEAD Data (Week 2)
- [ ] Register SEAD entity types (5 aggregates + dependents)
- [ ] Define aggregate priorities (location=10, site=20, etc.)
- [ ] Model FK dependencies
- [ ] Calculate topological depths
- [ ] Validate with query tests

### Phase 3: API Integration (Week 3)
- [ ] Add validation endpoints to Identity API
- [ ] Add allocation order endpoints
- [ ] Update ingester to use validation
- [ ] Integration tests

### Phase 4: Production (Week 4)
- [ ] Deploy to staging
- [ ] Run pilot submissions
- [ ] Performance tuning
- [ ] Deploy to production

---

## 💡 Examples

### Query: Get All Aggregates
```sql
SELECT entity_type_key, aggregate_priority, depth_level
FROM sead_utility.entity_types
WHERE is_aggregate = TRUE
ORDER BY aggregate_priority;
```

### Query: Validate Submission
```sql
SELECT * FROM sead_utility.validate_entity_submission(
    submission_uuid,
    ARRAY['site', 'sample_group']  -- Will detect if 'location' missing
);
```

### Query: Get Allocation Order
```sql
SELECT * FROM sead_utility.get_allocation_order(
    ARRAY['analysis_entity', 'site', 'location']
);
-- Returns: location (depth 0), site (depth 1), analysis_entity (depth 4)
```

---

## 🤝 Contributing

When adding new entity types to SEAD:
1. Register in `entity_types` table
2. If aggregate: Add to `aggregate_definitions` with priority
3. Model dependencies in `entity_dependencies`
4. Recalculate depths: `SELECT * FROM calculate_topological_depth()`
5. Test validation with sample submissions

---

## 📞 Support

For questions about:
- **Generic model design** → See AGGREGATE_MODEL_DESIGN.md
- **SEAD-specific implementation** → See SEAD_AGGREGATE_MODEL.md
- **Identity system integration** → See ../new_ingester/README.md
