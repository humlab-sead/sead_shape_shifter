# Review: Change Request Target Bundle Access

## Review Basis

- Reviewed: [proposal](./CHANGE_REQUEST_TARGET_BUNDLE_ACCESS.md), revised on 2026-10-19, against repository commit `ed8a8e4d` on `in-memory-ingester-handoff`.
- Related: completed [in-memory handoff phase plan](../done/IN_MEMORY_INGESTER_HANDOFF/IN_MEMORY_INGESTER_HANDOFF_PHASE_PLAN.md), this topic's [phase plan](./CHANGE_REQUEST_TARGET_BUNDLE_ACCESS_PHASE_PLAN.md) and [Phase 1 task plan](./CHANGE_REQUEST_TARGET_BUNDLE_ACCESS_PHASE_1_TASK_PLAN.md).
- Method: compared the decisions with the project-only routes, direct helper, request models, bundle writer, identity adapter, and client. No tests or deployment checks were run for this review.

## Overall Assessment

The completed handoff makes the narrow permission exception feasible: Change Request validation and ingestion now have dedicated project-only routes, strict requests without source or output paths, an authorized-project helper, and table input. The proposal has been updated to use those shipped contracts. It now covers both routes and direct helper calls, preserves `project:execute`, and keeps Change Request file input retired. It also states the managed-output and read-only database safeguards that must precede the permission change.

The proposal is ready for a refreshed phase plan. Its existing phase plan and task plan still describe the pre-handoff implementation and would direct work to the wrong routes and service. The output reservation and SIMS ordering are design requirements in the revised proposal, but their runtime behavior remains unverified.

## Findings

### High — The execution plans are stale after the handoff

**Location:** [phase plan](./CHANGE_REQUEST_TARGET_BUNDLE_ACCESS_PHASE_PLAN.md) Summary, Current Position, Depends On, `PH1-AC-1`–`PH1-AC-4`; [task plan](./CHANGE_REQUEST_TARGET_BUNDLE_ACCESS_PHASE_1_TASK_PLAN.md) Readiness, Repository Findings, `T1.1`–`T1.4`, and validation table.

Both documents still say the handoff is unimplemented. `T1.1` targets the shared `ingest_data` route and keeps Change Request validation gated, while the shipped [project-only routes](../../../backend/app/api/v1/endpoints/ingesters.py) and [helper](../../../backend/app/services/project_ingester_service.py) each have an application-action check. `T1.2` calls for adding `INGEST_OUTPUT_DIR` through `IngesterService`, though the [setting](../../../backend/app/core/config.py) and its use in `ProjectIngesterService` already exist. Following these tasks could leave the intended workflow gated or change authorization on the shared file route. Refresh both plans from the revised `P-AC-*` criteria before implementation, including the safe run-ID folder token, early output reservation, actual output-path propagation, and validation's sequence rule. **Confidence: High.**

### Low — Related status and authorization documentation still describe earlier behavior

**Location:** [in-memory handoff proposal](../done/IN_MEMORY_INGESTER_HANDOFF/IN_MEMORY_INGESTER_HANDOFF.md) Status; [authorization route inventory](../../AUTHORIZATION_ROUTE_INVENTORY.md) ingester routes.

The handoff proposal still says "Proposed feature" although its [phase plan](../done/IN_MEMORY_INGESTER_HANDOFF/IN_MEMORY_INGESTER_HANDOFF_PHASE_PLAN.md) records Phases 1–5 complete. The route inventory omits the project-only routes and says the shared routes accept no project locator, although their models include `project_name`. Update these references when the plans are refreshed so maintainers do not infer the wrong current permission path. **Confidence: High.**

## Proposal Updates Applied

- Recorded the handoff as complete and corrected the current route, helper, file-input, output-setting, and output-response descriptions.
- Scoped the exception to both project-only routes and direct helper calls, with their project authorization intact; removed the obsolete Change Request caller-path case.
- Defined the output folder as a UTC timestamp plus a SHA-256 digest of the effective run ID. The raw caller-provided ID remains in SIMS, the response, and the manifest, but cannot become a path component. A collision must be detected before SIMS calls for that request, and the actual written path must reach `IngestResponse.output_path`.
- Applied the no-write/no-`nextval` target-database rule to both validation and ingestion, and made `P-AC-5` explicit about the provider-schema SIMS scope and declared business keys.

## Planning Readiness

**Ready.** No unresolved decision in the revised proposal blocks phase planning or human design approval. The existing phase plan and task plan require the High finding above to be addressed before implementation. This review is advice, not approval.
