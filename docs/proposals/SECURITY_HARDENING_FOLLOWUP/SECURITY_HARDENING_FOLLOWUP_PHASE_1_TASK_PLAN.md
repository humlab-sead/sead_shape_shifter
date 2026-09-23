# Security Hardening Follow-up — Phase 1 Task Plan

Repository-verified task plan for **Phase 1: Contain request-controlled file and environment disclosure**.

Source proposal: [SECURITY_HARDENING_FOLLOWUP.md](SECURITY_HARDENING_FOLLOWUP.md) · Source phase plan: [SECURITY_HARDENING_FOLLOWUP_PHASE_PLAN.md](SECURITY_HARDENING_FOLLOWUP_PHASE_PLAN.md) · Phase criteria: `PH1-AC-1` … `PH1-AC-5` (from `P-AC-1`, `P-AC-8`).

## Phase Summary

- **Phase title:** Contain request-controlled file and environment disclosure
- **Goal:** Close the CRITICAL request-path defects so untrusted route and project inputs can no longer read or write outside approved roots or expose environment values.
- **Readiness:** **Validated** — every edit site below is verified against `dev @ 5bb562a1`; no unresolved decision can change implementation.
- **Constraints (fixed by the proposal):** contain the *mapped* path at the service boundary; never ban `:` outright — `namespace:project` locators are a shipped convention; environment substitution resolves only at the mapper boundary; the `run_ingesters` gate and log-route role classification are out of scope here.
- **Dependencies:** none pending. This phase produces the disposable reproduction environment that later phases (2, 6, 7) reuse.

Acceptance criteria:

- [x] `PH1-AC-1` (from `P-AC-1`) The SPA route serves only files under the frontend dist directory; absolute-path and `..` arms are rejected.
- [ ] `PH1-AC-2` (from `P-AC-1`) `${VAR}` expansion in request-supplied and stored entity config reaches only approved variables; unapproved names neither expand nor return values in preview rows.
- [ ] `PH1-AC-3` (from `P-AC-1`) An entity type missing from the mapper factory fails as unsupported before any file read.
- [ ] `PH1-AC-4` (from `P-AC-1`) Project creation cannot write outside `PROJECTS_DIR` via traversal, an absolute name, or a colon locator aliasing another project's file, and `namespace:project` locators continue to work.
- [ ] `PH1-AC-5` (from `P-AC-8`) The ledger's root-only bootstrap tests run in the disposable environment with the host verified untouched.

## Repository Findings

**Repository basis:** branch `dev`, commit `5bb562a1`, planned 2026-09-23. Uncommitted changes are limited to `.vscode/settings.json` and the new `docs/proposals/SECURITY_HARDENING_FOLLOWUP/` folder; no implementation file is dirty. Ledger IDs refer to the untracked `secrets/FINDINGS.md`.

| Evidence | Finding | Planning implication |
|---|---|---|
| `backend/app/main.py::serve_spa` | Catch-all does `file_path = frontend_dist / full_path` then `FileResponse(file_path)` with no containment; absolute and `..` arms escape | Add containment before serving (S1) |
| `src/path_resolution.py::resolve_contained_path` | Framework-neutral helper already resolves symlinks and rejects escapes; `allow_absolute` defaults False | Reuse this helper; do not add a new one |
| `backend/app/services/project/project_utils.py::validate_project_name` | Rejects `..`, leading `/`, backslash, empty segments — but is a substring/prefix check, not a resolved-path check | Keep it; add resolved containment as the authoritative guard (B1c/B2) |
| `backend/app/services/project/project_operations.py::create_project` | Builds `self.projects_dir / ProjectNameMapper.to_path(name) / "shapeshifter.yml"` and only checks `file_path.exists()`; does **not** call `validate_project_name` or `resolve_contained_path` | Root cause of B1/B1b/B1c/B2 — contain the mapped path here |
| `backend/app/services/project/project_operations.py::copy_project` | Same uncontained `to_path` join for source and target dirs | Apply the same containment |
| `backend/app/api/v1/endpoints/projects.py::create_project` | Passes `request.name` straight to the service; `_project_directory` (contained) exists but is used only by other routes | Service-level fix covers create; keep endpoint unchanged |
| `backend/app/mappers/project_name_mapper.py::to_path` | Replaces `:`→`/`, so `up:../victim` → `up/../victim` aliases another tree | Containment must run on the mapped path, not the raw name |
| `backend/app/mappers/entity_config_mapper.py::EntityConfigMapperFactory.get_mapper` | Cache keys `{csv,xlsx,openpyxl,fixed}`; everything else returns no-op `DefaultEntityConfigMapper`, leaving `options.filename` raw | Reject unmapped types as unsupported (A2) |
| `src/loaders/file_loaders.py` / `excel_loaders.py` | `DataLoaders` registers `csv,tsv` and `xlsx,xls,openpyxl` — **broader** than the mapper cache, so `tsv`/`xls` bypass containment and hit `read_csv`/`read_excel` with a raw path | Confirms A2 is reachable, not theoretical |
| `src/utility.py::replace_env_vars` / `_resolve_env_var` | Expands any `${NAME}` against `os.environ` with no allowlist; `env_prefix` is a soft fallback, not a restriction | Add an allowlist gate at the boundary (A1/A1b) |
| `src/configuration/resolve.py::EnvironmentVariableResolver.resolve_directive` | The `${...}` resolver used during project resolution; calls `replace_env_vars` per match | Allowlist enforcement belongs here and/or in `replace_env_vars` |
| `backend/app/services/shapeshift_service.py::preview_entity` | `override_config` (request body) is resolved via `_resolve_entity_config` then `project.resolve(..., **settings.env_opts)`; resolved values return in `PreviewResult` | Both stored and request-supplied paths must respect the allowlist (A1, A1b) |
| `backend/tests/services/test_project_utils.py` | Covers `validate_project_name` traversal/absolute cases at the util level only | Extend with resolved-path and alias cases |
| `backend/tests/mappers/test_entity_config_mapper.py` | Covers mapper factory for known types | Add unsupported-type case |
| `.github/workflows/` | Only `release.yml`; no CI runs the ledger package | Phase 1 does not add CI (that is `PH7-AC-4`) |

## Scope

**In scope**

- SPA catch-all containment (S1).
- Environment-variable allowlist at the configuration-mapping boundary for request-supplied and stored config (A1, A1b).
- Reject entity types absent from the mapper factory as unsupported (A2).
- Resolved-path containment for project create/copy/delete against traversal, absolute names, and colon aliasing (B1, B1b, B1c, B2).
- A disposable reproduction environment for the ledger's root-only bootstrap tests (PH1-AC-5).

**Out of scope**

- Shared-source body authorization (D), restore cache invalidation (G), audit actors (30), masking (14a), SQL policy (13), build pinning (11), verification gates (25/31/34/35) — later phases.
- Reopening the fixed `run_ingesters` gate or changing log-route role requirements.
- Banning `:` in project names.

**Affected components:** `backend/app/main.py`, `backend/app/services/project/`, `backend/app/mappers/`, `src/utility.py`, `src/configuration/resolve.py`, and their backend/core tests.

## Work Breakdown

### Area 1: Contain the SPA catch-all

**Objective:** `GET /{full_path}` serves only files inside `frontend/dist`.

**Affected code:** `backend/app/main.py::serve_spa`; `src/path_resolution.py::resolve_contained_path` (reuse).

**Dependencies:** none.

**Tasks:**

* [x] `T1.1` **Change:** Reject any SPA path that resolves outside `frontend_dist`.
  * **Target:** `backend/app/main.py::serve_spa`.
  * **Current → required:** `frontend_dist / full_path` is served whenever `is_file()`, including absolute and `..` arms → resolve through `resolve_contained_path(full_path, frontend_dist)` and fall through to `index.html` on `ValueError`.
  * **Implementation:** Wrap the containment call in `try/except ValueError`; on escape, serve `frontend_dist / "index.html"` (client-routing behavior preserved); never return a path outside the dist root. Keep the `/assets` mount unchanged.
  * **Constraints:** Do not break legitimate SPA deep links (unknown non-file paths still return `index.html`).
  * **Validation:** `V-1`.

**Completion evidence:** A request with `..%2f` or an absolute path no longer returns file content outside `frontend/dist`; a normal deep link still returns `index.html`.

### Area 2: Restrict environment-variable expansion to an approved list

**Objective:** `${VAR}` expansion reaches only approved variables, for both request-supplied and stored config.

**Affected code:** `src/utility.py::replace_env_vars`, `_resolve_env_var`; `src/configuration/resolve.py::EnvironmentVariableResolver.resolve_directive`; `backend/app/services/shapeshift_service.py::preview_entity` (consumer).

**Dependencies:** none.

**Tasks:**

* [x] `T1.2` **Add an approved-variable gate to expansion.**
  * **Target:** `src/utility.py::replace_env_vars`.
  * **Current → required:** Any `${NAME}` resolves against `os.environ` → only names on an approved list expand; others resolve to empty (or stay literal) and never return a secret value.
  * **Implementation:** Introduce an `allowed_vars: frozenset[str] | None = None` parameter (None = current behavior, for trusted internal callers). When supplied, `_resolve_env_var` returns `""` for names not in the set. Populate the approved set from a single configuration source (the existing `Settings`/env-prefix area) listing the variables legitimate project YAML uses (e.g. `SHAPE_SHIFTER_*` data-dir/application-root names). Keep `env_prefix` behavior intact.
  * **Constraints:** Trusted internal callers that must expand arbitrary vars keep working by passing `allowed_vars=None`; the preview and stored-config resolution paths pass the approved set.
  * **Validation:** `V-2`.
* [x] `T1.3` **Thread the allowlist through the resolution boundary.**
  * **Target:** `src/configuration/resolve.py::EnvironmentVariableResolver.resolve_directive` and the `ResolutionContext` it reads.
  * **Current → required:** The `${...}` resolver expands every name → it expands only approved names when the context carries an allowlist.
  * **Implementation:** Carry the approved set on `ResolutionContext` and pass it to `replace_env_vars`. Ensure both the request-body `override_config` path and the stored-project `resolve()` path in `preview_entity` reach the resolver with the allowlist set.
  * **Done:** `ResolutionContext.allowed_vars` (and `for_loaded_source`), `resolve_directives(allowed_vars=...)`, and `EnvironmentVariableResolver` now pass the set to `replace_env_vars`. `ShapeShiftProject.resolve` reads `allowed_vars` from context. `Settings` gains `RESOLVER_ALLOWED_ENV_VARS` (CSV, defaulting to the names real project YAML uses: `APPLICATION_ROOT`, `GLOBAL_DATA_DIR`, `GLOBAL_DATA_SOURCE_DIR`, `SEAD_HOST/PORT/DBNAME/USER`, `BUGS_CEP_MDB_FILE`) surfaced as a `frozenset` via `env_opts["allowed_vars"]`, so both preview paths resolve with the allowlist. Core default stays `None` (unrestricted) for trusted internal callers.
  * **Constraints:** `${ENV_VAR}` directives remain supported for approved names; do not resolve env vars outside the mapper/resolver boundary.
  * **Validation:** `V-2`.

**Completion evidence:** A preview request or stored entity config using `${ANY_SECRET}` returns no environment value in `PreviewResult.rows`; approved variables still resolve.

### Area 3: Reject unmapped entity types as unsupported

**Objective:** An entity type without a containment mapper fails before any file read.

**Affected code:** `backend/app/mappers/entity_config_mapper.py::EntityConfigMapperFactory.get_mapper`; `backend/app/services/shapeshift_service.py::_resolve_entity_config`.

**Dependencies:** none.

**Tasks:**

* [x] `T1.4` **Fail closed on types absent from the mapper factory.**
  * **Target:** `EntityConfigMapperFactory.get_mapper`.
  * **Current → required:** Unknown types return the no-op `DefaultEntityConfigMapper`, so `tsv`/`xls`/other registered loaders receive a raw `options.filename` → types that name a file-based loader but have no containment mapper are rejected as unsupported before resolution.
  * **Implementation:** Distinguish legitimately no-op types (sql-family, entity, merged — no `options.filename`) from file-capable loader keys missing from the mapper cache (`tsv`, `xls`). Reject the latter (raise a `BadRequestError`/`ConfigurationError` at the mapper boundary) rather than passing them through. Keep the no-op default only for types that never carry a file path.
  * **Done:** `FILE_BASED_DRIVERS` is now the authoritative file-capable set (`csv, tsv, xlsx, xls, openpyxl`). `get_mapper` returns the cached mapper when present; if the type is file-capable but has no mapper (`tsv`, `xls`), it raises `BadRequestError` before any file read; otherwise it returns the no-op default. SQL-family (`sqlite`, `postgres`, `ucanaccess`, `duckdb`), `entity`, `merged`, and `fixed` are unchanged. `BadRequestError` maps to HTTP 400 via the error middleware.
  * **Constraints:** Do not break `sql`, `entity`, `merged`, or `fixed` flows; do not widen the mapper cache silently — the point is that a file path never reaches a loader uncontained.
  * **Validation:** `V-3`.

**Completion evidence:** A preview with `type: tsv` (or `xls`) and an out-of-root `options.filename` is rejected as unsupported; `type: csv` still resolves through the contained file mapper.

### Area 4: Contain project create/copy/delete paths

**Objective:** Project lifecycle cannot write outside `PROJECTS_DIR` or alias another project's file.

**Affected code:** `backend/app/services/project/project_operations.py::create_project`, `copy_project`, `delete_project`; `backend/app/services/project/project_utils.py::validate_project_name`; `src/path_resolution.py::resolve_contained_path` (reuse).

**Dependencies:** none.

**Tasks:**

* [ ] `T1.5` **Resolve and contain the project directory at the service boundary.**
  * **Target:** `ProjectOperations.create_project`, `copy_project`, `delete_project`.
  * **Current → required:** `self.projects_dir / ProjectNameMapper.to_path(name)` joined with only an `exists()` collision check → validate the name, then resolve the mapped path through `resolve_contained_path(to_path(name), projects_dir)` and reject on `ValueError`, for every path built from a caller-supplied name.
  * **Implementation:** Add a shared helper (on `ProjectUtils` or `ProjectOperations`) that runs `validate_project_name` then `resolve_contained_path` and returns the contained `shapeshifter.yml` path; use it in create/copy/delete and the collision check. The collision check must compare resolved paths, so `up:../victim` cannot pass while pointing at another project's file.
  * **Constraints:** Preserve `namespace:project` (e.g. `arbodat:arbodat-copy` → `arbodat/arbodat-copy`); reject absolute names and `..` at any segment; keep existing `ResourceConflictError`/`ResourceNotFoundError` semantics.
  * **Validation:** `V-4`.

**Completion evidence:** Creating `../../x`, `/etc/x`, or `up:../victim` fails and writes nothing outside `PROJECTS_DIR`; `arbodat:new-copy` still creates `PROJECTS_DIR/arbodat/new-copy/shapeshifter.yml`.

### Area 5: Disposable reproduction environment for root-only tests

**Objective:** The ledger's root-only bootstrap tests can run with the host provably untouched.

**Affected code:** `NEW` container/VM recipe under `docs/testing/` (or the existing testing-docs location); reference to the untracked `secrets/` package.

**Dependencies:** none (consumed by phases 2, 6, 7).

**Tasks:**

* [ ] `T1.6` **Document an isolated run recipe for the ledger package.**
  * **Target:** `NEW` `docs/testing/SECURITY_LEDGER_REPRODUCTION.md`.
  * **Current → required:** No maintained procedure exists; the ledger warns its harness rewrites positional args only and must not run on a workstation → a maintained recipe runs `RUN.sh` inside a disposable container/VM and asserts host paths are unchanged.
  * **Implementation:** Record the disposable-environment steps, the host-untouched assertion, and the explicit warning against workstation/root runs. Reference the ledger's own limits (section 6) without copying the package.
  * **Constraints:** Do not commit anything from `secrets/`; the recipe points at the local package path as `TBD` (operator-supplied).
  * **Validation:** `V-5`.

**Completion evidence:** A reviewer can run the package in a throwaway environment following the doc, and the doc states the host-untouched check.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected evidence |
|---|---|---|---|
| `PH1-AC-1` | `T1.1` | `V-1` | SPA absolute/`..` arms rejected; deep links still return `index.html` |
| `PH1-AC-2` | `T1.2`, `T1.3` | `V-2` | Unapproved `${VAR}` returns no value in preview; approved vars resolve |
| `PH1-AC-3` | `T1.4` | `V-3` | `tsv`/`xls` unmapped type rejected before file read |
| `PH1-AC-4` | `T1.5` | `V-4` | Traversal/absolute/colon-alias writes blocked; namespaced locators work |
| `PH1-AC-5` | `T1.6` | `V-5` | Reproduction doc runs package in disposable env, host untouched |

## Validation And Testing

New test files are marked `NEW`. Run focused backend tests with the repo venv; the exact pytest invocation follows the repository convention `uv run pytest <path> -v`.

| ID | Check and target | Command or method | Covers | Expected result | Baseline |
|---|---|---|---|---|---|
| `V-1` | `backend/tests/api/test_spa_catchall_containment.py` — `resolve_spa_file` with `..`, absolute, symlink-escape, deep link, and root against a fake dist | `uv run pytest backend/tests/api/test_spa_catchall_containment.py -v` | `PH1-AC-1` | Escape arms fall back to `index.html`; deep link and root return `index.html`; in-root file served | Pass (7 tests, 2026-09-23) |
| `V-2` | `NEW` `backend/tests/test_env_var_allowlist.py` — preview with `${SECRET}` in `override_config` and in stored YAML; approved var still resolves | `uv run pytest backend/tests/test_env_var_allowlist.py -v` | `PH1-AC-2` | No env value in `PreviewResult.rows`; approved var expands | Pass (6 tests, 2026-09-23) |
| `V-3` | `backend/tests/mappers/test_entity_config_mapper.py` (extend) — `get_mapper("tsv")`/`get_mapper("xls")` reject; `csv`/`sql`/`fixed` unchanged | `uv run pytest backend/tests/mappers/test_entity_config_mapper.py -v` | `PH1-AC-3` | File-capable unmapped types raise; others pass | Pass (31 tests, 2026-09-23) |
| `V-4` | `backend/tests/services/test_project_utils.py` + `backend/tests/services/project/` (extend) — create/copy/delete with `../../x`, `/abs`, `up:../victim`, `ns:child`; assert filesystem effect | `uv run pytest backend/tests/services/test_project_utils.py backend/tests/services/project -v` | `PH1-AC-4` | Out-of-root writes rejected, nothing written; namespaced create works | Pass (existing util cases green) |
| `V-5` | Manual: follow `docs/testing/SECURITY_LEDGER_REPRODUCTION.md` in a throwaway container; confirm host-untouched assertion | Manual method | `PH1-AC-5` | Package runs isolated; host paths unchanged | Not run: doc is new |
| `V-6` | Regression: full backend suite for touched areas | `uv run pytest backend/tests -v` | `PH1-AC-1`-`PH1-AC-4` | No new failures vs baseline | Fail (pre-existing): ledger records 25 failed / 4 errors on trunk, incl. 11 in `tests/process/test_subset_service.py` — not caused by Phase 1; confirm the delta is zero |
| `V-7` | Lint/format | `make lint` (Black + isort) | all | Clean | Not run |

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
|---|---|---|---|
| SPA containment | `backend/app/main.py::serve_spa`, `resolve_spa_file` | `T1.1` | `V-1` passes |
| Env allowlist in expansion | `src/utility.py::replace_env_vars`, `_resolve_env_var` | `T1.2` | `V-2` passes |
| Allowlist at resolver boundary | `src/configuration/resolve.py::EnvironmentVariableResolver`, `ResolutionContext` | `T1.3` | `V-2` passes |
| Unsupported-type rejection | `backend/app/mappers/entity_config_mapper.py::EntityConfigMapperFactory` | `T1.4` | `V-3` passes |
| Contained project paths | `backend/app/services/project/project_operations.py`, `project_utils.py` | `T1.5` | `V-4` passes |
| Reproduction recipe | `NEW` `docs/testing/SECURITY_LEDGER_REPRODUCTION.md` | `T1.6` | `V-5` passes |
| New regression tests | `backend/tests/api/test_spa_catchall_containment.py` (created); `backend/tests/test_env_var_allowlist.py` (created); extended `test_entity_config_mapper.py`, `test_project_utils.py` | `T1.1`-`T1.5` | `V-1` passes; `V-2` passes; `V-3`-`V-4` pending |

## Progress Tracker

| Area | Status | Dependencies | Notes |
|---|---|---|---|
| Area 1 — SPA containment | Done | None | `T1.1` implemented; `V-1` passes (7 tests) |
| Area 2 — Env allowlist | Done | None | `T1.2` (gate in `replace_env_vars`) and `T1.3` (allowlist threaded through `ResolutionContext`/`resolve_directives`/`Settings.env_opts`) done; `V-2` passes (6 tests) |
| Area 3 — Unmapped types | Done | None | `T1.4` done (`get_mapper` fails closed for `tsv`/`xls`); `V-3` passes (31 tests) |
| Area 4 — Project paths | Not started | None | `T1.5` |
| Area 5 — Repro environment | Not started | None | `T1.6` |

## Definition Of Done

- [ ] Every `PH1-AC-*` criterion has implementation (`T*`) and validation (`V*`) evidence.
- [ ] All five areas and deliverables are complete.
- [ ] `V-1`-`V-5` pass; `V-6` shows zero new failures against the recorded trunk baseline; `V-7` clean.
- [ ] `namespace:project` locators and legitimate `${ENV_VAR}` directives are regression-tested as preserved.
- [ ] No file path reaches a loader uncontained; no `${...}` outside the approved list returns a value.
- [ ] The reproduction doc exists and states the host-untouched check and the no-workstation warning.
- [ ] Deviations and follow-up work are recorded; no open question affects implementation.

## Risks And Open Questions

- **Approved-variable set membership (minor decision, not blocking):** the exact list of legitimate env vars must come from real project YAML, not invention. Resolution: derive it from `Settings`/`env_prefix` and the directives already used in `data/projects/**` during the task-plan execution; keep `allowed_vars=None` for trusted internal callers so nothing that legitimately expands today breaks. Verify against existing env-var tests (`backend/tests/test_env_var_resolution.py`, `test_env_var_preservation.py`).
- **Trunk baseline is already red:** the ledger records 25 failed / 4 errors on `dev` unrelated to Phase 1. Gate on "zero new failures vs baseline" (`V-6`), not "all green".
- **`tsv`/`xls` loader reachability:** confirmed via `DataLoaders` registration broader than the mapper cache; if a fix instead widens the mapper cache, it must add containment, not a no-op — verify the chosen approach still rejects the out-of-root filename in `V-3`.
