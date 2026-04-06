# SEAD Change Request Ingester

## Overview

This folder contains the proposal for replacing the current SEAD Clearinghouse ingester (`ingesters/sead/`) with a new ingester that generates Sqitch-ready SQL DML change requests directly from normalized DataFrames.

## Documents

- [SEAD_INGESTER_DESIGN.md](./SEAD_INGESTER_DESIGN.md) — Proposal: new ingester design and architecture
- [CHANGE_REQUEST_INGESTER.md](./CHANGE_REQUEST_INGESTER.md) — Original design notes (historical)

## Context

### What exists today

| Component | Status | Location |
|-----------|--------|----------|
| **Current SEAD ingester** | Production | `ingesters/sead/` — Clearinghouse CSV-based ingestion into staging tables |
| **SIMS** | Fully implemented | `sead_authority_service/src/identity/` — Identity resolution, UUID allocation, binding lifecycle |
| **SimsClient** | Fully implemented | `backend/app/clients/sims_client.py` — Async HTTP client wrapping SIMS `/identity` endpoints |
| **Target model conformance** | Implemented | `sead_standard_model.yml` + six registered conformance validators |
| **Ingester framework** | Implemented | `backend/app/ingesters/` — Protocol, registry, dynamic discovery |

### What this proposal adds

A new ingester registered under the same framework that:

1. Consumes normalized DataFrames (output of Shape Shifter core pipeline)
2. Resolves **all** entity identities via SIMS — reconciliation for existing entities, allocation for new ones
3. Resolves foreign keys from local `system_id` to SIMS-allocated SEAD integer IDs
4. Generates topologically-sorted SQL INSERT statements
5. Outputs a Sqitch-ready change request

### Key principle

**A change request must not be emitted until every entity identity is resolved.** This means every row in every entity table must have either a reconciled match to an existing SEAD entity or an allocated new SEAD identity, confirmed through a SIMS Binding Set. No unresolved `system_id` values may appear in the output SQL.

## Boundary

| Concern | Owner |
|---------|-------|
| Identity resolution, allocation, policy, binding lifecycle | SIMS (sead_authority_service) |
| SIMS API consumption, SQL generation, FK resolution, Sqitch output | This ingester (Shape Shifter) |
| Target model metadata (entity roles, identity columns, FKs) | `sead_standard_model.yml` (Shape Shifter) |
| Core ETL pipeline (extract, filter, link, unnest, translate) | Shape Shifter core (unchanged) |

## Related documentation

- SIMS design: `sead_authority_service/docs/SIMS/`
- SIMS operations: `sead_authority_service/docs/SIMS/OPERATIONS.md`
- Current ingester architecture: `ingesters/sead/ARCHITECTURE.md`
- Ingester framework: `ingesters/README.md`
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
