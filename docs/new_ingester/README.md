# SEAD Ingestion And SIMS Proposal Docs

This folder contains two related but separate feature proposals:

1. the **Shape Shifter SEAD ingester**, which lives in this application and generates SQL DML
2. **SIMS** (SEAD Identity Management System), which is an external SEAD-side system consumed by the ingester via API

The goal of this folder is to keep those proposals linked, but not mixed.

## Structure

### Ingester proposal

- [SEAD_INGESTER_DESIGN.md](./SEAD_INGESTER_DESIGN.md)
   Shape Shifter component design for generating Sqitch-ready SQL DML from normalized DataFrames.

- [NEW_INGESTER.md](./NEW_INGESTER.md)
   Original notes and problem statement that led to the structured design.

### SIMS proposal

- [sims/README.md](./sims/README.md)
   Navigation for the external SIMS proposal.

- [sims/SEAD_IDENTITY_SYSTEM.md](./sims/SEAD_IDENTITY_SYSTEM.md)
   SIMS design and requirements.

- [sims/SEAD_IDENTITY_IMPLEMENTATION.md](./sims/SEAD_IDENTITY_IMPLEMENTATION.md)
   SIMS implementation details: schema, functions, and API shape.

- [sims/SEAD_IDENTITY_NFR.md](./sims/SEAD_IDENTITY_NFR.md)
   SIMS non-functional requirements, security, operations, and testing.

### Related material

- [../aggregate_model/README.md](../aggregate_model/README.md)
   Aggregate model documentation referenced by the SIMS design.

## How To Read These Docs

### If you are designing the ingester

1. Read [SEAD_INGESTER_DESIGN.md](./SEAD_INGESTER_DESIGN.md)
2. Use [sims/SEAD_IDENTITY_SYSTEM.md](./sims/SEAD_IDENTITY_SYSTEM.md) only as the external API/system dependency context
3. Use [sims/SEAD_IDENTITY_IMPLEMENTATION.md](./sims/SEAD_IDENTITY_IMPLEMENTATION.md) only when you need concrete SIMS API or persistence details

### If you are designing SIMS

1. Start with [sims/README.md](./sims/README.md)
2. Read [sims/SEAD_IDENTITY_SYSTEM.md](./sims/SEAD_IDENTITY_SYSTEM.md)
3. Continue with [sims/SEAD_IDENTITY_IMPLEMENTATION.md](./sims/SEAD_IDENTITY_IMPLEMENTATION.md)
4. Use [sims/SEAD_IDENTITY_NFR.md](./sims/SEAD_IDENTITY_NFR.md) for operational and security concerns

## Proposal Boundary

### In scope for the ingester docs

- DataFrame to SQL transformation
- reconciliation and mapping use inside Shape Shifter
- SIMS API consumption from the ingester
- foreign key resolution using SIMS-allocated SEAD IDs
- Sqitch-ready output and rollback handling in the ingester

### In scope for the SIMS docs

- external identity allocation model
- aggregate-root identity strategy
- external identifier formats: UUID or natural/business key
- API design, persistence model, and change detection foundation
- SIMS operations, security, performance, and audit

### Out of scope for the ingester docs

- SIMS internal database schema
- SIMS deployment model
- SIMS security and NFR details
- SIMS internal implementation choices unless required by the API contract

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
