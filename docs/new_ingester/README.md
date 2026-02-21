# SEAD SQL Ingester - Design Documentation

This directory contains comprehensive design documentation for the new SEAD SQL ingester component.

---

## 📁 Document Structure

### Core Design Documents

1. **[SEAD_IDENTITY_SYSTEM.md](./SEAD_IDENTITY_SYSTEM.md)** ⭐ **Start Here - Design**
   - **Scope:** SEAD Database System (external to Shape Shifter)
   - **Purpose:** Hybrid identity allocation design (UUID OR natural keys + integer PKs)
   - **Key Innovation:** Flexible external identifiers enabling distributed, concurrent ingestion
   - **Content:** Architecture, workflows, API principles, change detection strategy, aggregate roots
   - **Status:** Design Phase - Foundation for the ingester
   - **Read this first** to understand the identity allocation architecture

2. **[SEAD_IDENTITY_IMPLEMENTATION.md](./SEAD_IDENTITY_IMPLEMENTATION.md)** 🔧 **Implementation Details**
   - **Scope:** Database schema, SQL functions, API specification
   - **Purpose:** Complete implementation reference for SEAD Identity System
   - **Content:** DDL (CREATE TABLE), PL/pgSQL functions, REST endpoints, migration phases
   - **Dependencies:** Requires PostgreSQL 12+, uuid-ossp extension
   - **Use this for:** Database deployment, API development, SQL generation

3. **[SEAD_IDENTITY_NFR.md](./SEAD_IDENTITY_NFR.md)** 📊 **Non-Functional Requirements**
   - **Scope:** Performance, security, reliability, testing
   - **Purpose:** Operational requirements and success criteria
   - **Content:** Latency targets (< 10ms P95), security (OAuth 2.0), monitoring (Prometheus), load tests
   - **Use this for:** DevOps setup, performance tuning, incident response

4. **[SEAD_INGESTER_DESIGN.md](./SEAD_INGESTER_DESIGN.md)** ⭐ **Main Ingester Design**
   - **Scope:** Shape Shifter SEAD Ingester Component
   - **Purpose:** Generate Sqitch-ready SQL DML from normalized DataFrames
   - **Key Innovation:** Direct DataFrame → SQL transformation with automated ID allocation
   - **Dependencies:** Requires SEAD Identity System API (documents #1-3)
   - **Isolation Principle:** ALL SEAD-specific logic resides in this ingester

5. **[NEW_INGESTER.md](./NEW_INGESTER.md)** 📝 **Original Notes**
   - **Scope:** Reference document (original design notes)
   - **Purpose:** Historical context and initial problem statement
   - **Status:** Superseded by documents #1-4 (kept for reference)

---

## 🎯 Quick Start

### For Implementers

**Recommended reading order:**

1. **Identity Design** ([SEAD_IDENTITY_SYSTEM.md](./SEAD_IDENTITY_SYSTEM.md))
   - Understand hybrid identity model (UUID/natural key + integer PK)
   - Review three-tier architecture and workflows
   - Study aggregate root strategy and change detection
   - **Time:** 30-45 minutes

2. **Implementation Details** ([SEAD_IDENTITY_IMPLEMENTATION.md](./SEAD_IDENTITY_IMPLEMENTATION.md))
   - Review database schema (DDL for identity_allocations, submissions)
   - Study PostgreSQL functions (allocate_identity, resolve_external_id, etc.)
   - Understand REST API specification (6 endpoints)
   - **Implementation:** Deploy SEAD Identity API first (Phase 1-2)

3. **Non-Functional Requirements** ([SEAD_IDENTITY_NFR.md](./SEAD_IDENTITY_NFR.md))
   - Review performance targets (< 10ms P95, 10k req/s throughput)
   - Study security requirements (OAuth 2.0, API keys, audit trail)
   - Understand monitoring and alerting setup (Prometheus, Grafana)
   - **Implementation:** Configure DevOps infrastructure (Phase 1)

4. **Ingester Design** ([SEAD_INGESTER_DESIGN.md](./SEAD_INGESTER_DESIGN.md))
   - Review component architecture (6 components)
   - Study integration with Shape Shifter's three-tier identity system
   - Understand SQL generation workflow (topological sorting)
   - **Implementation:** Build ingester components (Phase 3-6)

### For Reviewers

**Focus areas by document:**

- **SEAD_IDENTITY_SYSTEM.md** (Design)
  - Architecture: Three-tier model, aggregate roots, change detection strategy
  - Business logic: Idempotent allocation, flexible identifier types
  - Integration: API design principles, workflow diagrams

- **SEAD_IDENTITY_IMPLEMENTATION.md** (Technical)
  - Database schema: Table structures, constraints, indexes
  - SQL functions: PL/pgSQL implementations, error handling
  - API specification: REST endpoints, request/response formats
  - Migration strategy: 5-phase rollout plan

- **SEAD_IDENTITY_NFR.md** (Operational)
  - Performance: Latency targets, throughput benchmarks, scalability
  - Security: Authentication (OAuth 2.0, API keys), authorization, audit trail
  - Reliability: High availability, fault tolerance, disaster recovery
  - Testing: Unit, integration, load, chaos engineering strategies

- **SEAD_INGESTER_DESIGN.md** (Shape Shifter Component)
  - Component isolation: ALL SEAD logic in ingester (core remains agnostic)
  - Integration points: mappings.yml, ShapeShifter.table_store, Sqitch
  - SQL generation: Topological sorting, FK resolution, idempotent INSERT

---

## 🏗️ Architecture Overview

### Two-System Design

```
┌──────────────────────────────────────────────────────┐
│ SEAD Identity System (External to Shape Shifter)     │
│ • Hybrid Integer + UUID architecture                 │
│ • REST API for ID allocation                         │
│ • PostgreSQL functions and tables                    │
│ • Idempotent allocation (same UUID → same integer)   │
│ • See: SEAD_IDENTITY_SYSTEM.md                       │
└──────────────────────────────────────────────────────┘
                        ↕ API Calls
┌──────────────────────────────────────────────────────┐
│ Shape Shifter SEAD Ingester (This Component)         │
│ • UUID generation for entities                       │
│ • Identity allocation via SEAD API                   │
│ • FK resolution (system_id → SEAD ID)                │
│ • SQL DML generation (topologically sorted)          │
│ • Sqitch integration (deploy/rollback scripts)       │
│ • See: SEAD_INGESTER_DESIGN.md                       │
└──────────────────────────────────────────────────────┘
```

### Current vs. Proposed Workflow

**Before (6 handoffs, 2-5 days):**
```
Data → Shape Shifter (User) → YAML → Normalizer → DataFrames →
Dispatcher → CSV/Excel → Ingester → Clearinghouse → 
Transport System (ID allocation) → Sqitch → Database
```

**After (3 handoffs, same day):**
```
Data → Shape Shifter (User) → YAML → Normalizer → DataFrames →
SEAD Ingester (ID allocation via API) → Sqitch → Database
```

**Improvements:**
- 50% fewer handoffs
- 5x faster turnaround time
- Automated ID allocation
- Concurrent-safe submissions
- Idempotent (replayable) ingestion

---

## 🔑 Key Innovations

### 1. Hybrid Identity System (Integer + UUID)

**Problem:** External systems can't predict SEAD integer IDs, causing:
- Brittle FK resolution
- No idempotent ingestion
- Manual reconciliation required

**Solution:** Complementary UUIDs
- External systems generate UUIDs locally (stable across runs)
- SEAD allocates integers via API, maintains UUID ↔ Integer mapping
- FKs resolved via UUID references during ingestion
- Same UUID → Same integer (idempotent)

**Benefits:**
- Distributed ID generation (offline-capable)
- Concurrent submissions without conflicts
- Cross-system entity linking
- Audit trail for all allocations

### 2. Isolation Principle

**ALL SEAD-specific logic resides in the ingester component:**

✅ **In Ingester:**
- UUID generation
- SEAD API calls
- SEAD table mapping
- SQL dialect specifics
- Sqitch integration

❌ **Not in Shape Shifter Core:**
- Core remains domain-agnostic
- No SEAD dependencies in normalizer
- Reusable for other target systems

**Benefits:**
- Maintainability (isolated SEAD changes)
- Testability (mock SEAD API easily)
- Reusability (core works with any target)

### 3. Topological SQL Generation

**Reuses Shape Shifter's ProcessState:**
- Entities sorted by FK dependencies (parents before children)
- Validates referential integrity before SQL generation
- Generates transaction-safe SQL (BEGIN/COMMIT)

**Benefits:**
- FK constraints always satisfied
- Single transaction (atomic commit)
- Rollback on failure (clean recovery)

---

## 📊 Implementation Phases

### Phase 1: SEAD Identity System (External) - **Weeks 1-3**
**Owner:** SEAD Team

- [ ] Deploy `identity_allocations` table to SEAD staging
- [ ] Deploy PostgreSQL functions (allocate, resolve, commit, rollback)
- [ ] Implement REST API (FastAPI/Flask)
- [ ] Load testing (10,000 allocations/sec target)
- [ ] Deploy to SEAD production

**Deliverables:** SEAD Identity API live and tested

---

### Phase 2: Shape Shifter Ingester - **Weeks 4-8**
**Owner:** Shape Shifter Team

#### Week 4-5: Core Components
- [ ] UUID Generator
- [ ] Identity Allocator (API client)
- [ ] FK Resolver
- [ ] Unit tests

#### Week 6: SQL Generation
- [ ] SQL Generator (topological sorting)
- [ ] Sqitch Wrapper (deploy/revert scripts)
- [ ] Integration tests

#### Week 7: Reconciliation
- [ ] Reconciliation integrator (mappings.yml)
- [ ] Mixed ingestion (existing + new entities)
- [ ] Tests with historical data

#### Week 8: Orchestrator
- [ ] SEADSQLIngester main class
- [ ] End-to-end workflow
- [ ] Error handling and rollback
- [ ] CLI integration

**Deliverables:** Working ingester, ready for pilot projects

---

### Phase 3: Pilot & Rollout - **Weeks 9-10**
**Owner:** Both Teams

- [ ] Pilot with 3 test projects
- [ ] Performance tuning
- [ ] Documentation and training
- [ ] Production rollout (gradual)
- [ ] Monitor and iterate

**Success Criteria:** 5+ successful production ingestions, positive feedback

---

## 🧪 Testing Strategy

### Unit Tests
- UUID generation (collision detection, mapping)
- Identity allocation (idempotency, error handling)
- FK resolution (system_id → SEAD ID accuracy)
- SQL generation (syntax, topological sorting)

### Integration Tests
- End-to-end workflow (DataFrame → SQL)
- SEAD API connectivity
- Reconciliation with mappings.yml
- Rollback scenarios

### Performance Tests
- 10,000 entities → < 5 minutes end-to-end
- Batch allocation 10,000 UUIDs → < 10 seconds
- Concurrent submissions (100 parallel) → No conflicts

### Validation Tests (Dry-Run)
- Missing FK parent → Error before allocation
- Invalid data types → Error before allocation
- SEAD API unreachable → Error early
- Duplicate business keys → Warning issued

---

## 🔒 Security Considerations

### SEAD Identity API
- **Authentication:** OAuth 2.0 + API keys
- **Authorization:** Submission-level permissions
- **Encryption:** TLS 1.3 for all communication
- **Rate Limiting:** 1000 requests/min per client

### SQL Generation
- **Parameterized queries:** No string concatenation
- **Input validation:** Whitelist entity/table names
- **Code review:** Security audit required

### Data Privacy
- **Audit trail:** All operations logged
- **Access control:** Role-based permissions
- **Data retention:** 90 days for rollback data

---

## 📈 Success Metrics

### Technical
- ✅ 100% FK referential integrity
- ✅ Zero ID collisions
- ✅ < 1 hour for 10,000 entity project
- ✅ 99%+ API uptime

### Business
- ✅ 5x faster ingestion (days → hours)
- ✅ 3+ concurrent submissions
- ✅ 95%+ reconciliation accuracy
- ✅ Zero manual ID mapping steps

### Adoption
- ✅ 10+ production ingestions in 3 months
- ✅ Positive user feedback
- ✅ Old workflow deprecated after 6 months

---

## ⚠️ Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| **API downtime** | Queue-based retry, fallback workflow |
| **FK errors** | Extensive validation, dry-run mode |
| **SQL injection** | Parameterized queries, input sanitization |
| **Data loss** | Atomic transactions, rollback tests |
| **Performance** | Batch allocation, connection pooling |

See individual documents for detailed risk analysis.

---

## 🔮 Future Enhancements

### Post-MVP (Phase 2)
- Partial commits (savepoint-based rollback)
- Real-time validation (WebSocket feedback)
- Fuzzy reconciliation (confidence scores)
- Schema introspection (auto-generate table_mapping)

### Long-Term Vision
- Federated ingestion (multi-SEAD instances)
- Event sourcing (stream-based ingestion)
- Natural key integration (DOIs, ORCIDs)
- Blockchain audit trail (if compliance requires)

---

## 📞 Contacts & Resources

### Key Stakeholders
- **SEAD Team:** Identity System implementation, API deployment
- **Shape Shifter Team:** Ingester component, integration
- **Data Managers:** Testing, validation, reconciliation rules

### Related Documentation
- [Shape Shifter Architecture](../ARCHITECTURE.md)
- [Configuration Guide](../CONFIGURATION_GUIDE.md)
- [Developer Guide](../DEVELOPER_GUIDE.md)
- [Ingester System](../../backend/app/ingesters/README.md)

---

## ❓ FAQ

### Q: Why hybrid Integer + UUID instead of pure UUID PKs?

**A:** Performance and backward compatibility. Integer PKs are 4x smaller, faster for JOINs, and SEAD's existing ecosystem expects them. UUIDs are complementary identifiers for external systems.

### Q: Can we use this ingester for non-SEAD targets?

**A:** No, this ingester is SEAD-specific (by design). For other targets, create a new ingester following Shape Shifter's ingester protocol. The core normalizer remains reusable.

### Q: What happens if SEAD API is unreachable?

**A:** The ingester fails fast with clear error message. Optionally, implement queue-based retry logic or fallback to old file-based workflow.

### Q: How are duplicates prevented?

**A:** Idempotent allocation (same UUID → same integer) + SQL UPSERT (`ON CONFLICT DO UPDATE`). Re-running same data updates existing records instead of creating duplicates.

### Q: Can we preview SQL without allocating IDs?

**A:** Yes, use `--dry-run` mode. Validates data and generates SQL with placeholder IDs, but doesn't call SEAD API.

### Q: What's the rollback strategy?

**A:** Two-phase: Call SEAD API to rollback allocations (soft delete by default), optionally hard delete for testing. Generated SQL is never executed in rollback scenarios.

---

**Last Updated:** February 21, 2026  
**Status:** Design Phase  
**Next Review:** After Phase 1 (SEAD Identity API deployment)
