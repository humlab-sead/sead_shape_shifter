# Shape Shifter Proposal Index

This index covers proposals and initiative records that need attention or provide current project context. It lists decision documents, not their supporting task plans, diagrams, or handoffs. Those remain linked from their parent documents.

## Open Proposals

| Proposal | Status | Decision or scope |
|---|---|---|
| [Branch-Scoped Consumers For Mixed-Branch Parents](BRANCH_SCOPED_CONSUMERS_FOR_MIXED_BRANCH_PARENTS.md) | Proposed follow-up | Let downstream entities select which branch of a mixed parent they consume. |
| [BugsCEP Importer Migration Runtime Decision Spike](BUGSCEP_IMPORTER_MIGRATION_IMPLEMENTATION_DECISION/BUGSCEP_IMPORTER_MIGRATION_IMPLEMENTATION_DECISION.md) | Proposed change request | Test candidate runtime paths against the completed policy contract before choosing one. |
| [Define And Verify The SEAD Target Model Coverage Boundary](SEAD_TARGET_MODEL_COVERAGE_BOUNDARY.md) | Proposed change request | Pin the target-model coverage boundary, record one disposition per in-scope table, and verify it with a generated report and a lint hook. |
| [Ingester Authorization](INGESTER_AUTHORIZATION_TASKS/INGESTER_AUTHORIZATION_TASKS.md) | Proposed change | Authorize projects, sources, and destinations used by ingester operations. |
| [Secure Ingester Filesystem And Destination Access](INGESTER_FILESYSTEM_BOUNDARIES/INGESTER_FILESYSTEM_BOUNDARIES.md) | Proposed change | Restrict ingester file access and database destinations to approved resources. |
| [Ingester Idempotency And Re-submission](INGESTER_IDEMPOTENCY_AND_RESUBMISSION/INGESTER_IDEMPOTENCY_AND_RESUBMISSION.md) | Proposed; contract decisions pending | Define deterministic reruns, partial overlap, and recovery from interrupted requests. |
| [Release Cycle Evidence And Locking](RELEASE_CYCLE_EVIDENCE_AND_LOCKING/README.md) | Proposed process change | Define release identity, verification evidence, and comparisons between runs. |
| [RuleSync For Unified Agent Instructions](RULESYNC_AGENT_INSTRUCTIONS_UNIFICATION.md) | Proposed change | Generate shared agent instructions from one source and detect drift. |
| [Security Hardening Follow-up](SECURITY_HARDENING_FOLLOWUP/SECURITY_HARDENING_FOLLOWUP.md) | Proposed change request | Remediate unresolved application, authorization, deployment, and verification issues. |
| [AI Project Advisor](SHAPESHIFTER_PROJECT_AI_ADVISOR/SHAPESHIFTER_PROJECT_AI_ADVISOR.md) | Feature proposal | Provide project-scoped advice grounded in project state and SEAD knowledge. |
| [Shared Data Review And Operator Contract](CHANGE_REQUEST_INGESTER/SHARED_DATA_REVIEW_AND_OPERATOR_CONTRACT/SHARED_DATA_REVIEW_AND_OPERATOR_CONTRACT.md) | Draft | Define review and operator outcomes for shared data in change requests. |

## Current Initiatives

| Initiative | Status | Reference |
|---|---|---|
| BugsCEP pilot | Pilot draft implemented and validated on the current branch; importer migration continues. | [Pilot status and next work](BUGSCEP_PILOT_PROJECT.md) |
| SEAD Change Request Ingester | Delivery 1 is closed; candidate next-delivery capabilities remain undecided. | [Initiative overview and current documents](CHANGE_REQUEST_INGESTER/README.md) |
| Submission metadata | Repository implementation complete; upstream PostgreSQL validation remains pending. | [Submission metadata proposal](CHANGE_REQUEST_INGESTER/REFACTOR_SEAD_SUBMISSION_METADATA.md) |

## Future Proposals

These proposals are deferred or not yet approved. See each document for its detailed status and scope.

| Proposal | Topic |
|---|---|
| [Advanced FK Validation Modes](future/ADVANCED_FK_VALIDATION_MODES.md) | Direct, transitive, and path-based foreign-key validation. |
| [App-Managed Team Membership](future/APP_MANAGED_TEAM_MEMBERSHIP.md) | Manage team membership in the authorization database. |
| [Authorization Schema Migration Registry](future/AUTHORIZATION_SCHEMA_MIGRATION_REGISTRY.md) | Version and register authorization database migrations. |
| [Fixed-Entity Type Convention Enhancements](future/FIXED_ENTITY_TYPE_CONVENTION_ENHANCEMENTS.md) | Possible extensions to fixed-entity typing conventions. |
| [FK Null-Key Policy Model](future/FK_NULL_KEY_POLICY_MODEL.md) | Decide how missing foreign-key join values should be handled. |
| [Log Injection Sanitization](future/LOG_INJECTION_SANITIZATION.md) | Prevent user-supplied newlines from forging application log records. |
| [Native Application Authentication](future/NATIVE_APPLICATION_AUTHENTICATION.md) | Add application-managed authentication. |
| [Production Flip To The Authorized Server](future/PRODUCTION_FLIP_TO_AUTHORIZED_SERVER.md) | Move production traffic to the authorization-enabled server. |
| [Query Filter Engine Selection](future/QUERY_FILTER_ENGINE_SELECTION.md) | Make query-filter engine selection explicit. |
| [Server-Owned Resource Identifiers](future/SERVER_OWNED_RESOURCE_IDENTIFIERS.md) | Resolve generated resources through server-owned records rather than client paths. |
| [Target Model Ecosystem Enhancements](future/TARGET_MODEL_ECOSYSTEM_ENHANCEMENTS.md) | Consider future target-model tooling and distribution improvements. |
| [Unified File-Backed Entity Type](future/UNIFIED_FILE_BACKED_ENTITY_TYPE.md) | Replace separate file entity types with a unified type and format option. |
| [Reconciliation Future Improvements](RECONCILIATION_FUTURE_IMPROVEMENTS.md) | Placeholder for deferred reconciliation workflow improvements; scope is not yet defined. |

## On Hold

| Record | Status | Topic |
|---|---|---|
| [Raw Source Data Explorer](onhold/RAW_SOURCE_DATA_EXPLORER_PROPOSAL.md) | On hold; proposed product and technical direction | Investigate raw source data before mapping and transformation. |
| [Auto-Fix](onhold/AUTO_FIX.md) | Provisional feature; UI hidden | The backend retains a limited set of confirmation-based validation fixes. |

Other paused implementation and migration plans are available in [onhold/](onhold/). Completed or decided proposal records are available in [done/](done/).