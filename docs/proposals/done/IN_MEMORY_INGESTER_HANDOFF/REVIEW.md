# Proposal Review: Hand Normalized Tables To The Ingester In Memory

## Review Basis

| Item | Value |
|---|---|
| Reviewed document | [IN_MEMORY_INGESTER_HANDOFF.md](./IN_MEMORY_INGESTER_HANDOFF.md) |
| Related documents | [CHANGE_REQUEST_TARGET_BUNDLE_ACCESS](../../done/CHANGE_REQUEST_TARGET_BUNDLE_ACCESS/CHANGE_REQUEST_TARGET_BUNDLE_ACCESS.md), its [phase plan](../../done/CHANGE_REQUEST_TARGET_BUNDLE_ACCESS/CHANGE_REQUEST_TARGET_BUNDLE_ACCESS_PHASE_PLAN.md), [Phase 1 task plan](../../done/CHANGE_REQUEST_TARGET_BUNDLE_ACCESS/CHANGE_REQUEST_TARGET_BUNDLE_ACCESS_PHASE_1_TASK_PLAN.md), and [review](../../done/CHANGE_REQUEST_TARGET_BUNDLE_ACCESS/REVIEW.md) |
| Review date | 2026-10-19 |
| Revision reviewed | Branch `dev` at `50a7e5bc`, including the current uncommitted proposal and companion-plan revisions |
| Method | Read the proposals, prior reviews, cited Ingester Authorization proposal, and relevant Core, backend, ingester, and client code. No tests or live services were run. |

This review replaces the earlier review in this file. It is advice, not design approval. The proposal and companion documents were not changed.

## Overall Assessment

The shared no-write normalization step, separate table-input capability, and adapter are a sound way to remove Excel's lossy round trip while preserving `workflow()` and file-only ingesters. The proposal calls out intentional data differences and provides useful validation expectations. The companion proposal now limits its permission exception to bundle creation from an authorized saved project.

The main concern is the contract between the two proposals. The handoff delivers only an internal helper; the companion expects an operation a caller can invoke without the ingester permission. Neither defines a safe request path to that helper. The helper also needs a precise service-level authorization and trusted-config contract before the permission exception is enabled.

## Earlier Findings Reassessed

| Earlier finding | Current assessment |
|---|---|
| `C1` permission conflict | Resolved: companion `P-AC-1` exempts only the composed operation with no caller-supplied path. |
| `H1` no helper consumer | Open and now affects companion delivery; see `R1`. |
| `H2` ingester configuration path | Open; see `R2`. |
| `H3` service authorization mechanism | Open; see `R3`. |
| `M1` review-ID reference | Resolved: containment now points to the Ingester Authorization proposal. |
| `M2`, `M3`, `M4`, `L1` | Open; see `R7`, `R6`, and `R5`. |
| `M5`, `L2` | Minor planning refinements. The combined `P-AC-8` can be tested in parts, and the timezone question is due before table support is complete. |

## Findings

### High

#### R1 — The companion has no safe request path to the composed helper

**Location:** Handoff Proposed Design section 4, Non-Goals, `P-AC-8`; companion `P-AC-1` and Phase 1 task `T1.1`.

**Issue and impact:** The handoff excludes an endpoint and changes to `IngestRequest`. Today `IngestRequest.source` is required; `/ingesters/{key}/ingest` passes it to `IngesterService.ingest()`, which calls the file-oriented `ingester.ingest(request.source)`. The operator form also sends `source`. Companion `T1.1` targets the shared route's permission dependency but defines no path from that route to the new helper. Exempting the existing `sead_change_request` key would also exempt caller-supplied paths, contrary to both proposals. Leaving the route unchanged cannot satisfy companion `P-AC-1`.

**Recommendation:** Assign the project-based request entry point to one proposal. Define how it selects the helper without accepting a caller path, through a separate route or an explicit, mutually exclusive request mode. Its permission check must distinguish composed and file inputs. State that the handoff helper alone is infrastructure, then align companion `T1.1` and the client work.

**Evidence:** `backend/app/models/ingester.py:108`; `backend/app/api/v1/endpoints/ingesters.py:67-93`; `backend/app/services/ingester_service.py:116-172`; `frontend/src/components/ingester/IngesterForm.vue:915-958`.

**Confidence:** High.

#### R2 — Reusing the current config path does not establish trusted bundle inputs

**Location:** Handoff Proposed Design section 4 step 3, `P-AC-8`; companion Proposed Design and `P-AC-2`/`P-AC-3`.

**Issue and impact:** `IngesterService` copies unrestricted caller `request.config`. The ingester reads `target_model` from it, and `_create_config()` builds the database checker from `config["database"]`. The request also exposes `output_folder`; the artifact writer writes under whichever `IngesterConfig.output_folder` the backend supplies and removes an existing bundle directory. Reusing this path without a server-owned input rule can allow a project executor to choose a target model or database. Output safety remains dependent on the companion's later managed-root change. The handoff is that proposal's blocking dependency but does not distinguish trusted inputs from caller options.

**Recommendation:** Define which inputs the helper accepts. Derive the target model, database connection, trusted project context, and output location from server settings or the authorized project; accept only named submission options from a caller. Reuse runtime injection after that selection. Do not enable a project-only-permission entry point until the companion's managed output and database rules apply to it.

**Evidence:** `backend/app/models/ingester.py:108-123`; `backend/app/services/ingester_service.py:135-179,199-246`; `backend/app/services/ingester_runtime.py:49-67`; `ingesters/sead_change_request/input_resolution.py:187-200`; `ingesters/sead_change_request/artifact_writer.py:18-24`.

**Confidence:** High.

#### R3 — The internal helper's authorization check has no service contract

**Location:** Handoff Proposed Design section 4 step 1, `P-AC-8`, Planning Handoff.

**Issue and impact:** Current application and project gates are FastAPI dependencies. The project dependency reads `project_name` from the HTTP body; neither gate protects a direct helper call. The proposal says the helper requires project `execute` and inherits the companion permission decision, but gives no authorized input or check before normalization, database access, and artifact writing. `ExecuteService` already accepts an `AuthorizedResource` and verifies action, resource type, and active state.

**Recommendation:** Specify the helper's authorized-resource input and checks, including its project locator. State where `application:run_ingesters` is required for file input and where it is intentionally absent for composed bundle creation. Keep route dependency wiring separate. Test that denied direct calls perform no normalization, database access, or file writes.

**Evidence:** `backend/app/authorization/dependencies.py:158-208`; `backend/app/services/execute_service.py:57-91`; `backend/app/services/ingester_service.py:57-172`.

**Confidence:** High.

### Medium

#### R4 — The transitional Excel policy conflicts with the cited authorization proposal

**Location:** Handoff Summary, Non-Goals, `P-AC-6`, Planning Handoff; ingester authorization is now covered by the [Security Hardening Follow-up](../../SECURITY_HARDENING_FOLLOWUP/SECURITY_HARDENING_FOLLOWUP.md).

**Issue and impact:** The handoff and bundle-access proposals keep the caller-path route available behind `application:run_ingesters` until containment ships. Ingester Authorization says incomplete path-based operations must remain unavailable through routes and services until source and destination checks exist. Current code allows the path read. The documents give opposite delivery instructions for the interim period.

**Recommendation:** Decide the interim policy and update or expressly supersede the conflicting Ingester Authorization wording. Make the chosen gate and route availability rule explicit in `P-AC-6`.

**Confidence:** High.

#### R5 — Project-specification validation is absent from the composed contract

**Location:** Handoff Proposed Design section 4 step 2, Testing And Validation, `P-AC-8`.

**Issue and impact:** `ExecuteService.execute_workflow()` optionally runs `CompositeProjectSpecification` before normalization when `run_validation` is true. The proposed helper goes directly from mapping to normalization. Ingester validation covers change-request data, not necessarily project configuration. The difference has no stated choice or test.

**Recommendation:** State whether project-specification validation runs, whether it is optional, and what failure result it returns. Test that decision.

**Evidence:** `backend/app/services/execute_service.py:86-100`; `backend/app/models/execute.py:15-23`.

**Confidence:** High.

#### R6 — The parity criterion omits an exception and leaves safe names undefined

**Location:** Handoff Proposed Design `3, Testing And Validation, `P-AC-4`.

**Issue and impact:** The adapter deliberately keeps `data_table_index` while the Excel reader skips it; that name otherwise qualifies as a safe Excel sheet name. `P-AC-4` still promises equivalent decisions for Excel-representable data and safe names. It also does not define safe names: `xlsx` sends entity names directly to openpyxl, while the separate `openpyxl` dispatcher cleans and truncates them.

**Recommendation:** Exclude `data_table_index` from parity, define safe sheet names for the dispatcher used by the comparison, and state that cleaned or truncated names are intentional differences.

**Evidence:** `ingesters/sead_change_request/input_resolution.py:143-167`; `src/dispatch.py:69-80,244-255`.

**Confidence:** High.

### Low

#### R7 — The opening diagram presents a planned operation as current

**Location:** Handoff lines 3-6.

**Issue and impact:** The `backend helper → normalize → tables → ingester` path does not exist yet. Its unlabeled placement obscures the delivery gap in `R1`.

**Recommendation:** Label the file path as current and the table path as proposed.

**Confidence:** High.

## Planning Readiness

**Revision required.** The in-memory design is viable, but `R1`–`R3` must be settled across both proposals before it can support the companion permission exception. Resolve the interim file-path policy (`R4`) and make the validation and parity criteria precise (`R5`–`R6`) before approving a phase handoff. `R7` is a small clarity edit. No runtime behavior was verified.
