# Shape Shifter Proposal Index

This index covers proposals and initiative records that need attention or provide current project context. It lists decision documents, not their supporting task plans, diagrams, or handoffs. Those remain linked from their parent documents.

## Open Proposals

| Proposal | Status | Decision or scope |
|---|---|---|
| [Linked Art Export from Shape Shifter](LINKED_ART_EXPORT/LINKED_ART_EXPORT.md) | Proposed change request — draft for review | Evaluate SEAD-to-Linked Art output through relational transformations and a registered output dispatcher before deciding on production support. |
| [Branch-Scoped Consumers For Mixed-Branch Parents](BRANCH_SCOPED_CONSUMERS_FOR_MIXED_BRANCH_PARENTS.md) | Proposed follow-up | Let downstream entities select which branch of a mixed parent they consume. |
| [Output Dataset Expectations](OUTPUT_DATASET_EXPECTATIONS/OUTPUT_DATASET_EXPECTATIONS.md) | Proposed change request | Check row counts, distinct business keys, and expected group counts on complete transformed output. |
| [Report Target Model Coverage Against SEAD](SEAD_TARGET_MODEL_COVERAGE_BOUNDARY.md) | Proposed change request | Let each target model declare its SEAD coverage source and measure coverage with a CLI against the pinned snapshot or live SEAD; no separate manifest. |
| [Publish Container Images From CI To GHCR And Deploy By Pull](GHCR_IMAGE_RELEASE.md) | Proposed change request | Build images in GitHub Actions, publish to GHCR, and deploy by digest-pinned pull instead of host-side builds and release archives. |
| [Move Existing Projects To Provider-Schema Scopes](CHANGE_REQUEST_INGESTER/CUTOVER_AND_DEPLOYMENT/PROJECT_PROVIDER_SCOPE_CUTOVER.md) | Proposed cutover | Inventory old project scopes, decide migrate or abandon, assign one approved pair per project, and enable projects one at a time as operational work. |
| [Project Folder Navigation With Breadcrumbs](FOLDER_NAVIGATION_WITH_BREADCRUMBS.md) | Proposed feature | Browse projects by their existing folder structure client-side, with breadcrumbs and URL-persisted folder state. |
| [Improve `@value` Guidance and Preview in Column Pickers](VALUE_REFERENCE_COLUMN_UX_ENHANCEMENT/VALUE_REFERENCE_COLUMN_UX_ENHANCEMENT.md) | Proposed feature | Add best-effort reference suggestions and column previews from cached entity data without backend resolution or validation changes. |
| [Make `@value` References Usable in Column Pickers](VALUE_REFERENCE_COLUMN_PICKERS/VALUE_REFERENCE_COLUMN_PICKERS.md) | Proposed feature | Add guided reference entry, resolved-column previews, and explicit replacement without restoring long dropdown lists. |
| [Security Hardening Follow-up](SECURITY_HARDENING_FOLLOWUP/SECURITY_HARDENING_FOLLOWUP.md) | Proposed change request | Remediate unresolved application, authorization, deployment, and verification issues, including safeguards for future generic ingester routes. |
| [Scaffold Project Entities From an Associated Target Model](TARGET_MODEL_GUIDED_ENTITY_CREATION/TARGET_MODEL_GUIDED_ENTITY_CREATION.md) | Proposed feature | Add a target-model picker that prefills missing project entity drafts without guessing source settings. |
| [AI Project Advisor](SHAPESHIFTER_PROJECT_AI_ADVISOR/SHAPESHIFTER_PROJECT_AI_ADVISOR.md) | Feature proposal | Provide project-scoped advice grounded in project state, SEAD knowledge, and source-level investigation. |

## Current Initiatives

| Initiative | Status | Reference |
|---|---|---|
| SEAD Change Request Ingester | MVP Delivery is closed; post-MVP proposals remain deferred. | [Initiative overview](CHANGE_REQUEST_INGESTER/README.md); [post-MVP proposal portfolio](CHANGE_REQUEST_INGESTER_POST_MVP/README.md) |
| Submission metadata | Complete; both package strategies passed disposable PostgreSQL validation. Upstream deployment and compatibility remain release dependencies. | [Completed submission metadata work](CHANGE_REQUEST_INGESTER/done/REFACTOR_SEAD_SUBMISSION_METADATA/REFACTOR_SEAD_SUBMISSION_METADATA.md) |

## Future Proposals

These proposals are deferred or not yet approved. See each document for its detailed status and scope.

| Proposal | Topic |
|---|---|
| BugsCEP pilot | Pilot draft implemented and validated on the current branch; importer migration continues. | [Pilot status and next work](future/BUGSCEP_PILOT_PROJECT.md) |
| [SEAD Change Request Ingester Post-MVP](CHANGE_REQUEST_INGESTER_POST_MVP/README.md) | Deferred capability proposals for the change request ingester; no combined delivery is accepted. |
| [Advanced FK Validation Modes](future/ADVANCED_FK_VALIDATION_MODES.md) | Direct, transitive, and path-based foreign-key validation. |
| [App-Managed Team Membership](future/APP_MANAGED_TEAM_MEMBERSHIP.md) | Manage team membership in the authorization database. |
| [Authorization Schema Migration Registry](future/AUTHORIZATION_SCHEMA_MIGRATION_REGISTRY.md) | Version and register authorization database migrations. |
| [BugsCEP Importer Migration Runtime Decision Spike](future/BUGSCEP_IMPORTER_MIGRATION_IMPLEMENTATION_DECISION/BUGSCEP_IMPORTER_MIGRATION_IMPLEMENTATION_DECISION.md) | Test candidate runtime paths against the completed policy contract before choosing one. |
| [Create Entity From Query Tester](future/CREATE_ENTITY_FROM_QUERY_TESTER.md) | Add a Create Entity action in Query Tester with create-mode prefill and an authorization-aware project selector. |
| [Fixed-Entity Type Convention Enhancements](future/FIXED_ENTITY_TYPE_CONVENTION_ENHANCEMENTS.md) | Possible extensions to fixed-entity typing conventions. |
| [FK Null-Key Policy Model](future/FK_NULL_KEY_POLICY_MODEL.md) | Decide how missing foreign-key join values should be handled. |
| [Log Injection Sanitization](future/LOG_INJECTION_SANITIZATION.md) | Prevent user-supplied newlines from forging application log records. |
| [Native Application Authentication](future/NATIVE_APPLICATION_AUTHENTICATION.md) | Add application-managed authentication. |
| [Production Flip To The Authorized Server](future/PRODUCTION_FLIP_TO_AUTHORIZED_SERVER.md) | Move production traffic to the authorization-enabled server. |
| [Query Filter Engine Selection](future/QUERY_FILTER_ENGINE_SELECTION.md) | Make query-filter engine selection explicit. |
| [Release Cycle Evidence And Locking](future/RELEASE_CYCLE_EVIDENCE_AND_LOCKING/README.md) | Define release identity, verification evidence, and comparisons between runs. |
| [RuleSync For Unified Agent Instructions](future/RULESYNC_AGENT_INSTRUCTIONS_UNIFICATION.md) | Generate shared agent instructions from one source and detect drift. |
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
