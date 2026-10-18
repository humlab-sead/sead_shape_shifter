# Move Existing Projects To Provider-Schema Scopes

## Status

- Proposed cutover, separated from the implementation phases.
- Scope: the operational and data-owner decisions plus per-project deployment data that switch existing projects from `sead-change-request:{project}` scopes to provider-schema scopes. No application code.
- Goal: enable projects one at a time, with a recorded decision about existing identities, without holding up or blocking the remaining development work.

Related: [Bind Each Project To One Curated Provider Scope](../../done/PROJECT_DATA_PROVIDER_SCOPE/PROJECT_DATA_PROVIDER_SCOPE.md), [Phase plan](../../done/PROJECT_DATA_PROVIDER_SCOPE/PROJECT_DATA_PROVIDER_SCOPE_PHASE_PLAN.md) (Phase 4 completed the remaining development work).

## Summary

The codes for provider-schema scopes are in place. Phases 1–3 shipped the registry, project binding, save rejection, trusted-project ingestion, the fixed provider row, declared business keys, and scope/run reporting.

What remains before a project can switch is not code. It is four operational items: an inventory of existing project-scoped SIMS identities, a decision to migrate or abandon them, approved provider-schema assignments per project, and one operator-verified SEAD provider ID per project, plus a per-schema key review. These belong in a cutover process, not in a development phase.

Recommendation: run the cutover as a separate, per-project operational change. Abandon existing `sead-change-request:*` identities by default, migrate only a scope whose inventory shows bindings that must survive, and enable one project at a time with a recorded scope/run verification.

## Problem

Phase 4 currently mixes two different kinds of work. Its acceptance criteria are cutover outcomes: assign pairs to existing projects, decide the treatment of old identities, and verify parity after the switch. The blockers found while completing Phase 3 are decisions and deployment data, not missing code:

1. No project has an approved provider-schema assignment.
2. The treatment of existing `sead-change-request:*` identities is undecided.
3. The per-schema key review (`V-1`) has not been performed.
4. No project has the fixed `data_provider` row that ingestion now requires.

Keeping these in Phase 4 has two costs. A small development gap with no dependency on those decisions is blocked behind them. And a phase that contains both code and an irreversible identity switch invites an accidental cutover when the phase is marked done.

## Current Behavior

Verified on branch `project-data-provider-scope`, 2026-10-18:

- The provider registry declares one provider, `mal`, with two schemas: `archeobotany/arbodat-pilot` and `radiocarbon/strucke-pilot`. BugsCEP is absent by design.
- The four project files under `data/projects` (`arbodat-rebecka`, `arbodat`, `bugs`, `strucke_v5`) declare no populated `provider_schema` and contain no fixed `data_provider` entity. `arbodat-rebecka` carries an empty `data_provider_code:` key. A fifth entry, `workshop-2026-final`, is a symlink to container data outside the repository.
- `data/` is git-ignored (`.gitignore` line 133). The live project files are deployment data, not repository-reviewed files. The tracked project files under `tests/test_data/projects` are test fixtures.
- SIMS exposes `GET /identity/scopes` for a scope listing.
- The staging database was unreachable from this environment (`psql … sead_staging` refused the connection), so the number of existing `sead-change-request:*` scopes and their bindings is unverified. See [Open Questions](#open-questions).

Phase 3 behavior to rely on: an unregistered or missing saved pair fails closed before any SIMS request, target-database access, or bundle write, and there is no project-name scope fallback.

## Scope

- Read-only inventory of existing `sead-change-request:*` scopes and their bindings.
- One recorded migrate-or-abandon decision per existing scope.
- One approved registered provider-schema pair per project, applied to deployment project data.
- The `V-1` key review for each pilot schema before that schema's first live run.
- One fixed `data_provider` row per project, with an operator-verified SEAD `data_provider_id` that matches the saved provider code.
- Per-project enablement order, verification, and a way to stop a project.

## Non-Goals

- No application, test, or frontend changes. Development work stays in Phase 4.
- No new registry entries, and no enabling BugsCEP.
- No scope merge or rename in SIMS. SIMS has no merge operation.
- No automated production deployment.
- No change to the scope string format or to the fixed provider row contract.
- No assignment of provider-schema pairs derived from project names.

## Proposed Design

### 1. Record the identity inventory first

List every scope whose name starts with `sead-change-request:` using `GET /identity/scopes`, and count its bindings. Where the listing is insufficient, use read-only SQL against `sead_identity.source_scopes` and the binding tables. Record the result per scope. No project switches before this record exists.

### 2. Decide per scope: migrate or abandon

Recommendation: abandon, unless the inventory shows bindings that must survive the switch.

Abandoning means the project starts fresh under its provider-schema scope: the first delivery after cutover allocates new identities for records the old scope already held. That is acceptable only when the old scope holds no production history or when re-delivery is planned.

Migration is required when old bindings must be preserved. It is a separate, reviewed operation that creates the corresponding identities under the new scope name, and it must be completed and verified before the project is enabled. It is never implied by assigning a pair.

### 3. Assign one approved pair per project

Each enabled project receives exactly one registered pair. The pair is written to deployment project metadata (`data_provider_code`, `provider_schema`). Because deployment project files are outside repository review, the assignment is applied while ingestion for that project is stopped, and the operator records which project was changed and when.

Candidate mappings must be confirmed, not assumed: `arbodat-rebecka` and `strucke_v5` share `sead_standard_model.yml`, and the schema codes suggest `arbodat-pilot` for `arbodat`-derived data and `strucke-pilot` for `strucke_v5`. Treat this as a proposal to the data owner, not a decision.

### 4. Complete the per-schema key review

For each pilot schema, before its first live run, review the resolved `EntityConfig.keys` and the transformed delivery: confirm that each ordered key identifies the intended tracked entity, and that a repeated key across deliveries means the same source entity. A schema whose keys are project-local or ambiguous stays disabled. The review is an entry check, not a new configuration format.

### 5. Enter and verify the fixed provider row

Each project needs one `type: fixed` `data_provider` entity with `public_id: data_provider_id`, `keys: [data_provider_code]`, and exactly one row. The operator enters the SEAD `data_provider_id` and confirms it belongs to the project's provider code. Project validation checks the shape without a database call; ingestion then confirms the ID and code against `tbl_data_providers` before any SIMS work.

### 6. Enable one project at a time

Order the projects so a smaller or lower-risk delivery runs first. For each project: assign the pair, add the fixed row, run validation, then run one delivery and record the effective `scope_name` and `run_id` from the response and from `manifest.json`. Confirm one provider row and one submission row in the bundle.

To stop a project, remove or invalidate its saved pair. Ingestion then fails closed with no side effects. Do not rename a scope or a schema code to withdraw a project: scope strings are immutable once used.

## Alternatives Considered

- **Keep the cutover inside Phase 4.** Rejected. It couples irreversible identity decisions to a small development fix with no dependency on them, and makes "Phase 4 complete" ambiguous.
- **Switch every project at once.** Rejected. It removes per-project verification and multiplies the blast radius of a wrong provider ID or key contract.
- **Migrate every old scope.** Rejected as a default. Migration is additional reviewed work with no benefit where no bindings must survive.
- **Derive assignments from project names or folder names.** Rejected. The scope must come from an approved pair, and a name-shaped rule is what this change removes.
- **Wait for the registry to grow first.** Rejected. The two pilot schemas are enough to prove the path; more schemas are a later registry decision.

## Risks And Tradeoffs

- **Irreversible scope names.** Once a delivery lands under a provider-schema scope, changing the pair or schema code re-identifies records. Assignment is a one-way decision per project.
- **Orphaned identities.** Abandoning old scopes leaves their bindings unreachable. That is a real loss of history, so the abandon decision needs an explicit record per scope.
- **Wrong manual provider ID.** Caught before SIMS by the ID/code check, but only when a target connection is configured. A missing connection blocks the run rather than guessing.
- **Shared-pair key collisions.** Projects on one pair share an identity namespace. The key review is the only control for cross-delivery meaning, and it is human judgement.
- **Deployment-data edits bypass application checks.** The save-path rejections do not apply to direct file edits, and `data/` is not tracked. A mistake is only caught at validation or ingestion.
- **Sequencing.** Enabling a project before its schema review or migration completes creates identities that must then be abandoned.
- **BugsCEP.** It stays outside the registry and outside this cutover. Enabling it needs a registry decision first.

## Testing And Validation

Per project, recorded in the cutover record:

- Scope inventory for the affected old scopes, with binding counts.
- A recorded migrate-or-abandon decision, and migration evidence where migration was chosen.
- Project validation passes with the assigned pair and fixed row, without a database call.
- The `V-1` review result for the project's schema.
- One live delivery whose response and `manifest.json` report the same `scope_name` and `run_id`, with one provider row and one submission row.
- A stopped project fails closed: no SIMS request, no target-database access, no bundle write.

## Acceptance Criteria

- `P-AC-1` Every existing `sead-change-request:*` scope and its binding count is recorded before any project is switched.
- `P-AC-2` Every such scope has a recorded migrate-or-abandon decision, and no migration is assumed from an assignment.
- `P-AC-3` Every enabled project has exactly one registered pair from the approved registry and one fixed provider row whose ID and code identify the same existing SEAD row. BugsCEP is not enabled.
- `P-AC-4` Every enabled project's schema has a recorded `V-1` key review before its first live delivery.
- `P-AC-5` Enablement is per project, and each enabled project has a recorded delivery where response, manifest, and SIMS request agree on `scope_name` and `run_id`, with one provider row and one submission row.
- `P-AC-6` A project without a valid saved pair fails closed on validation and ingestion, with no SIMS request, target-database access, or bundle write.
- `P-AC-7` Completing the cutover requires no application code change; any need discovered during cutover is reported as Phase 4 development work instead of being fixed inside the cutover.

## Planning Handoff

Confirmed decisions and constraints:

- Phases 1–3 provide the code. The cutover is operational and per project.
- Scope strings remain `provider://<provider-code>/<provider-schema>` and are immutable once used.
- There is no project-name scope fallback after cutover, and no automatic migration.
- The target `data_provider` row stays lookup-only; the bundle keeps one provider row and one submission row.
- BugsCEP stays outside the registry and outside this cutover.
- Remaining development work, including the project-independent ingestion entry point, is planned in Phase 4 and is not a prerequisite for this cutover.

Expected validation outcomes: `P-AC-1` through `P-AC-7` are satisfied by the recorded per-project checks above, not by an automated suite.

Open questions and when they must be resolved:

- How many existing `sead-change-request:*` scopes hold bindings? Resolve during inventory, before the first assignment.
- Which project receives which pair? Resolve by data-owner approval, before the first assignment.
- Which scopes are migrated? Resolve per scope after inventory, before that project's enablement.

## Open Questions

- **Assignment map:** which of `arbodat-rebecka`, `arbodat`, and `strucke_v5` map to `provider://mal/archeobotany/arbodat-pilot` and which to `provider://mal/radiocarbon/strucke-pilot`? Candidates above are unconfirmed.
- **Owner:** `TBD`. The inventory and identity decision need a named decision owner.
- **Environment order:** `TBD`. Confirm whether any project is enabled on staging only, or whether the first switch happens elsewhere.

## Final Recommendation

Treat the scope switch as its own operational proposal with its own acceptance criteria, and keep Phase 4 as the remaining development work. Inventory the old scopes, decide migrate or abandon per scope with abandon as the default, assign one approved pair per project, complete the schema key review, enter and verify each fixed provider row, then enable one project at a time and record the scope/run parity for the first delivery.
