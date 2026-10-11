# Container Setup Simplification — Phase 1 Task Plan

## Phase Summary

**Phase:** Phase 1 — Separate Runtime Checks And Preserve Application Coverage  
**Goal:** Keep ecosystem runtime verification outside Shape Shifter while preserving its application authorization tests.  
**Readiness:** Validated  
**Dependencies:** The proposal decisions and the existing [operations verification handoff](./OPERATIONS_VERIFICATION_HANDOFF.md). No operations owner, repository, or tooling decision is required.

**Sources**

- [Container Setup Simplification proposal](./CONTAINER_SETUP_SIMPLIFICATION.md)
- [Container Setup Simplification phase plan](./CONTAINER_SETUP_SIMPLIFICATION_PHASE_PLAN.md)

**Acceptance Criteria**

- `PH1-AC-1` (from `P-AC-3`): The handoff defines the required runtime outcomes, and this work adds no replacement operations tooling.
- `PH1-AC-2` (from `P-AC-4`): Shape Shifter automated tests continue to cover its authentication and authorization behavior.
- `PH1-AC-3` (from `P-AC-5`): No dispatch-only `post-install.sh` is added; the handoff states that routine checks should not change system state and state-changing actions must be explicit.

## Repository Findings

**Repository basis:** Branch `container-setup-simplifications`, commit `a0c46fed`, planning date 2026-10-11. The worktree already contains changes to the proposal and untracked phase-plan and handoff documents; these were considered and are outside this task plan. Paths were repointed to the current `deployment/` tree layout; at Phase 1 time the trees sat at the repository root (`container/`, `container-host/`).

| Evidence | Finding | Planning implication |
| --- | --- | --- |
| `deployment/container/scripts/verify/README.md` | Lists operational host checks, application probes, orchestration, fixtures, and the release checker as retained. | Replace the operational inventory and run instructions; keep the release checker documented. |
| `deployment/container/scripts/verify/run_deployment_verification.sh`, `complete_test_deployment_verification.sh` | Orchestrate host and runtime checks; the first also provisions a disposable project and can run authenticated and rollback checks. | Remove both orchestrators with their operational dependencies; do not port them into another Shape Shifter entry point. |
| `deployment/container/scripts/verify/verify_container_release.sh`, `.github/workflows/container-release.yml`, `deployment/container/scripts/deploy/manage_container_release.sh` | The release checker validates source/archive policy and is called by the workflow and host manager. | Keep the release checker and its active callers unchanged in this phase; trusted validation changes belong to Phase 2. |
| `deployment/container/tests/test_verify_inventory.sh` | Requires every tracked verification script to have a disposition and asserts that rollback and orchestrator safeguards remain. | Update the test to describe and assert the reduced verification directory rather than deleted scripts. |
| `docs/OPERATIONS.md` | Instructs operators to run `verify_firewall.sh` and `verify_container_config.sh` after deployments. | Remove instructions that rely on scripts being retired and point to the handoff as requirements, not as an operations procedure. |
| `backend/tests/authorization/` | Contains application tests for route authentication, project and cross-resource access, authorization policy, mutations, and service access. | Keep these tests and the application authorization implementation out of scope for removal. |

### Baseline Results

- `bash deployment/container/tests/test_verify_inventory.sh` — **Pass**.
- `uv run pytest backend/tests/authorization -q` — **Fail** on the pre-existing `test_route_inventory_matches_assembled_api_routes`: `POST /api/v1/projects/{project_name}/entities/{entity_name}/column-availability` is missing from the route inventory.
- `uv run pytest backend/tests/authorization -q -k 'not test_route_inventory_matches_assembled_api_routes'` — **Pass**. This isolates the existing route-inventory failure from authorization behavior regression checks.

Do not fix the unrelated route-inventory failure as part of this phase.

## Scope

**In scope**

- Remove deployed host/runtime verification scripts and their fixtures from Shape Shifter.
- Retain `deployment/container/scripts/verify/verify_container_release.sh` and its existing workflow and host-manager callers.
- Update the verification README, active operations documentation, and inventory regression test.
- Preserve application authorization tests without replacing them with deployed probes.

**Out of scope**

- Implementing or selecting SEAD operations tools, scripts, procedures, schedules, or storage.
- Changing Shape Shifter authorization policy or application behavior.
- Moving or changing release-policy validation and the host release manager; those are Phase 2.
- Changing deployment commands, container configuration helpers, or host provisioning.

## Work Breakdown

### Area 1: Remove Host And Runtime Verification

**Objective:** Remove the operational check implementations and test fixtures from the Shape Shifter source tree without removing release validation or application tests.

**Affected code:** Existing paths listed below.

**Dependencies:** None.

**Tasks**

- [x] `T1.1` **Change:** Delete host-wide and deployed-runtime verification scripts and their disposable-check inputs.
  - **Target:** `deployment/container/scripts/verify/complete_test_deployment_verification.sh`; `deployment/container/scripts/verify/deployment-verification.options.yml.example`; `deployment/container/scripts/verify/disposable-project/shapeshifter.yml`; `deployment/container/scripts/verify/rollback_exercise.sh`; `deployment/container/scripts/verify/run_deployment_verification.sh`; `deployment/container/scripts/verify/setup.sh`; `deployment/container/scripts/verify/teardown.sh`; `deployment/container/scripts/verify/verify_authenticated_access.sh`; `deployment/container/scripts/verify/verify_container_config.sh`; `deployment/container/scripts/verify/verify_credential_rotation.sh`; `deployment/container/scripts/verify/verify_endpoint_containment.sh`; `deployment/container/scripts/verify/verify_firewall.sh`; `deployment/container/scripts/verify/verify_logs.sh`; `deployment/container/scripts/verify/verify_postgres_grants.sh`; `deployment/container/scripts/verify/verify_readonly_role.sql`.
  - **Current → required:** These files implement or support checks for host exposure, deployed configuration and identity, credentials, logs, database grants, rollback, and disposable deployment probes. Remove them from Shape Shifter rather than replacing them with operations scripts or a wrapper.
  - **Implementation:** Delete only the listed operational files. Keep `deployment/container/scripts/verify/verify_container_release.sh`, application authorization code, and all files under `backend/tests/authorization/`. Do not change release-workflow or release-manager behavior in this phase.
  - **Constraints:** Operations implementation is outside scope. The release checker is not an ecosystem runtime check and remains until Phase 2.
  - **Validation:** `V-1`, `V-2`, `V-3`, `V-4`.
- [x] `T1.2` **Change:** Update active documentation to remove instructions that depend on retired operational scripts.
  - **Target:** `deployment/container/scripts/verify/README.md`; `docs/OPERATIONS.md`.
  - **Current → required:** The verification README presents the operations checks as active Shape Shifter checks, and the operations guide tells operators to run the firewall and container-configuration scripts. Document only the retained release checker in the verification README. Remove the retired commands and explain that the handoff states tool-agnostic requirements; it is not an implemented operations procedure.
  - **Implementation:** Remove the operational inventory, usage examples, and claims that Shape Shifter supplies the operations checks. Keep accurate release-check information and its existing callers. Link to `OPERATIONS_VERIFICATION_HANDOFF.md` for requirements without assigning an operations repository or tool.
  - **Constraints:** Preserve useful deployment guidance unrelated to the retired scripts. Do not imply that the handoff implements the checks.
  - **Validation:** `V-1`, `V-2`.
- [x] `T1.3` **Change:** Revise the verification inventory regression test for the reduced directory.
  - **Target:** `deployment/container/tests/test_verify_inventory.sh`.
  - **Current → required:** The test requires dispositions for all prior scripts and checks safeguards implemented by the deleted rollback and orchestrator scripts. It must instead confirm that the release checker remains documented, operational check files are absent, and no test depends on deleted state-changing or interactive checkers.
  - **Implementation:** Update the inventory assertions to cover the retained release checker and the approved contents of `deployment/container/scripts/verify/`. Ensure the check distinguishes files present in the worktree from deleted paths still listed in the Git index. Remove assertions that read `rollback_exercise.sh` or either deleted orchestrator.
  - **Constraints:** Keep the test read-only. Do not weaken the check that the release checker is documented.
  - **Validation:** `V-1`, `V-2`, `V-5`.

**Completion evidence:** Only the release checker and its current supporting documentation remain in `deployment/container/scripts/verify/`; active documentation and the inventory test no longer depend on the retired operational scripts.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected evidence |
| --- | --- | --- | --- |
| `PH1-AC-1` (from `P-AC-3`) | `T1.1`, `T1.2`, `T1.3` | `V-1`, `V-2` | The handoff remains the tool-agnostic requirements document, operational implementations are absent from Shape Shifter, and no replacement operations tooling is added. |
| `PH1-AC-2` (from `P-AC-4`) | `T1.1` | `V-3`, `V-4` | Application authorization tests remain in place and pass apart from the documented pre-existing route-inventory failure. |
| `PH1-AC-3` (from `P-AC-5`) | `T1.2`, `T1.3` | `V-2`, `V-5` | No dispatch-only `post-install.sh` is added; the handoff retains its safe-default and explicit-state-change requirements. |

## Execution Record

**Completed 2026-10-11**

- `T1.1`: Deleted all 15 listed operational scripts and fixtures. `verify_container_release.sh` remains, and its calls from `container-release.yml` and `manage_container_release.sh` remain intact.
- `T1.2`: Updated the verification README to cover release validation only and replaced the two retired-script procedures in `docs/OPERATIONS.md` with the handoff ownership note.
- `T1.3`: Updated the inventory test to require only the README and release checker in the verification directory, without relying on Git index entries for deleted files.

| Criterion | Status and evidence |
| --- | --- |
| `PH1-AC-1` | Supported: the handoff still contains `OPS-REQ-1` through `OPS-REQ-14`; the operational implementations are absent, with no replacement tooling added (`V-1`, `V-2`). |
| `PH1-AC-2` | Supported: the authorization suite passes excluding the pre-existing route-inventory failure; the full run has no additional failures (`V-3`, `V-4`). |
| `PH1-AC-3` | Supported: active operator docs point to the handoff as requirements only, the handoff retains its safe-default requirement, and no `post-install.sh` exists under `deployment/container/` (`V-2`, `V-5`). |

## Validation And Testing

| ID | Check and target | Command or method | Covers | Expected result | Baseline |
| --- | --- | --- | --- | --- | --- |
| `V-1` | Verification directory regression | `bash deployment/container/tests/test_verify_inventory.sh` | `PH1-AC-1`, `PH1-AC-3` | Pass; the release checker is documented, retired operational files are absent, and no removed script is executed or required by the test. | **Pass** before and after changes (2026-10-11). |
| `V-2` | Handoff and active-reference review | Confirm `OPS-REQ-1` through `OPS-REQ-14` remain in `docs/proposals/CONTAINER_SETUP_SIMPLIFICATION/OPERATIONS_VERIFICATION_HANDOFF.md`; search active `deployment/container/` and `docs/OPERATIONS.md` content for retired script names. Ignore historical proposal/archive content and the test's explicit absence assertions. | `PH1-AC-1`, `PH1-AC-3` | All required outcomes remain; no active operator instruction points to a retired checker, and no replacement tool or `post-install.sh` is added. | **Pass** after changes (2026-10-11). |
| `V-3` | Application authorization regression excluding known baseline failure | `uv run pytest backend/tests/authorization -q -k 'not test_route_inventory_matches_assembled_api_routes'` | `PH1-AC-2` | Pass; the existing authorization tests continue to cover route authentication, project/resource isolation, policy, mutation, and service access. | **Pass** before and after changes (2026-10-11). |
| `V-4` | Full authorization-suite comparison | `uv run pytest backend/tests/authorization -q` | `PH1-AC-2` | No new failures. The only permitted baseline failure is `test_route_inventory_matches_assembled_api_routes` with the documented missing `column-availability` route. | **Fail** before and after changes (2026-10-11) with the same one known failure. |
| `V-5` | Syntax check for the changed inventory test | `bash -n deployment/container/tests/test_verify_inventory.sh` | `PH1-AC-1`, `PH1-AC-3` | Exit status 0. | **Pass** after changes (2026-10-11). |

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
| --- | --- | --- | --- |
| Deleted operational scripts and fixtures | The 15 paths listed in `T1.1` | `T1.1` | The files are absent from the Shape Shifter source tree; `verify_container_release.sh` remains. |
| Updated verification documentation | `deployment/container/scripts/verify/README.md` | `T1.2` | Documents only release validation still provided in this directory. |
| Updated operator documentation | `docs/OPERATIONS.md` | `T1.2` | No commands point to retired scripts; the handoff is described as requirements, not a runbook. |
| Updated inventory regression test | `deployment/container/tests/test_verify_inventory.sh` | `T1.3` | `V-1` and `V-5` pass and no longer inspect deleted scripts. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1: Remove host and runtime verification | Done | None | 15 operational files removed; release validation and backend authorization tests remain. |

## Definition Of Done

- [x] All `T1.*` tasks are complete.
- [x] `PH1-AC-1`, `PH1-AC-2`, and `PH1-AC-3` have implementation and validation evidence.
- [x] The release checker remains in place with its current callers.
- [x] Application authorization tests are not removed or replaced by deployment probes.
- [x] Active documentation and the inventory test no longer depend on retired scripts.
- [x] `V-1`, `V-2`, `V-3`, and `V-5` pass; `V-4` has no failure beyond its documented baseline.
- [x] No operations tooling or dispatch-only `post-install.sh` was added.
- [x] Any source mismatch or additional authorization-test failure is reported without broadening the phase.

## Risks And Open Questions

- The authorization suite has one known route-inventory failure unrelated to this phase. Keep it visible in validation results and do not fix it here.
- If implementation discovers an active caller outside the inspected release checker, verification README, inventory test, and operations guide, stop and report the evidence before expanding the removal scope.
