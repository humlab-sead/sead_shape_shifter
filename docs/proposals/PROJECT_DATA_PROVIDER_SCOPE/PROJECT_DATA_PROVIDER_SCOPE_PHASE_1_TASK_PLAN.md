# Project Data Provider Scope — Phase 1 Task Plan

## Phase Summary

**Phase:** 1, Curated Provider Registry. **Goal:** provide one reviewed `mal` provider record with two fixed pilot schema scopes and a local read interface for later phases.

**Readiness: Validated.** The phase plan marks Phase 1 ready for a task plan. The initial provider code `mal`, display name `MAL`, and two provider-schema codes are approved. The targets and validation methods below are verified against the repository. BugsCEP is excluded from the initial registry.

Sources: [proposal](./PROJECT_DATA_PROVIDER_SCOPE.md) (`P-AC-1`) and [phase plan](./PROJECT_DATA_PROVIDER_SCOPE_PHASE_PLAN.md) (Phase 1, `VM-1`). The fixed decisions are one scope per provider-schema pair, `scope_name: provider://<provider-code>/<provider-schema>`, code-reviewed files, a read-only interface, no live SIMS check, and no environment-specific target provider ID in the registry.

Acceptance criteria:

1. [ ] `PH1-AC-1` (from `P-AC-1`): provider `mal` has distinct `provider://mal/archeobotany/arbodat-pilot` and `provider://mal/radiocarbon/strucke-pilot` scopes; duplicate provider codes, duplicate schema codes within a provider, duplicate scopes, and mismatched names are rejected. BugsCEP is absent.
2. [ ] `PH1-AC-2` (from `P-AC-1`): a provider-schema pair or scope already bound to a project cannot be reassigned to a different provider or key contract.

**Implementation handoff:** if verified repository state differs from the findings below, stop and report the difference before changing the design or expanding scope.

## Repository Findings

**Repository basis:** branch `dev`, commit `254b44f9`, revised 2026-10-18. Uncommitted proposal-tree changes and the user's approved `mal` pilot identities were considered. The working tree also contains unrelated uncommitted proposal changes. No provider registry implementation exists yet. Existing source files outside these planning documents were inspected read-only.

| Evidence | Finding | Planning implication |
| --- | --- | --- |
| `backend/app/core/config.py::Settings.resolve_paths` | Shared paths are relative to `APPLICATION_ROOT`, are created during settings validation, and exclude the authorization database. | Add `GLOBAL_DATA_PROVIDER_DIR` beside the existing shared paths; resolve and protect it the same way. The proposed default is `shared/data-providers`. |
| `backend/app/services/data_source_service.py::DataSourceService` | Global data sources use one YAML file per item, but invalid files are skipped. | Use one file per provider with nested schema entries, but reject the entire provider registry on any invalid file, duplicate identity, or mismatched scope. |
| `backend/app/api/dependencies.py::get_data_source_service`, `backend/app/api/v1/api.py::api_router` | Services are injected and routers are registered explicitly. | Add a provider service dependency and one registered read endpoint. |
| `backend/app/api/v1/endpoints/data_sources.py::list_data_sources`, `backend/tests/authorization/test_route_authentication.py::AUTHENTICATED_ONLY_API_PATHS`, `docs/AUTHORIZATION_ROUTE_INVENTORY.md` | Global list routes require an authenticated principal; new routes must be classified and listed in the maintained route inventory. | Make `GET /api/v1/data-providers` authenticated and update both route checks and inventory. Do not add a write route or provider resource type. |
| Sibling `sead_authority_service/src/identity/models.py::SourceScope` and `schema/sql/identity/001_source_scopes.sql` | SIMS stores `scope_name` as a unique string/text value and accepts URI-style names; no path-segment validator was found. | The proposed slash-containing schema code fits the current scope-name contract. Treat the full string as one scope, not a SIMS parent-child hierarchy. |
| `.gitignore`, `deployment/container/podman-compose.yml`, `deployment/container/DEPLOYMENT.md` | `data/` is ignored; `/app/shared` is a writable bind mount; the reviewed `deployment/container/` tree is synced to the host. | Keep reviewed YAML under `deployment/container/resources/data-providers/` and bind that directory read-only at `/app/shared/data-providers`. Do not place reviewed files inside ignored runtime `data/` or only in the image, which the `/app/shared` mount would hide. |
| `deployment/container/resources/backend.env.example`, `.env.example`, `docs/OPERATIONS.md` | Shared paths are documented in runtime examples and operations guidance. | Document the provider path and the local-development override to the reviewed directory. |
| `backend/tests/conftest.py::authorized_client`, `backend/tests/test_config.py`, `backend/tests/test_authorization_config.py`, `backend/tests/test_data_source_api.py` | Temporary-directory settings and authenticated API fixtures already exist. | Reuse these patterns for provider tests; keep tests independent of actual provider values. |
| `data/projects/arbodat/shapeshifter.yml`, `data/projects/arbodat-rebecka/shapeshifter.yml`, `data/projects/strucke_v5/shapeshifter.yml`, `data/projects/bugs/shapeshifter.yml` | These local pilot project files have no populated provider-schema pair; only `arbodat-rebecka` contains a blank provider code. | Use the user's approved `mal` identities for the registry. Project-file assignments and BugsCEP remain outside Phase 1. |

The proposed tracked-directory mount is the concrete delivery method for the proposal's shared runtime registry. The default service path remains `shared/data-providers` relative to `APPLICATION_ROOT`; local development can set `SHAPE_SHIFTER_GLOBAL_DATA_PROVIDER_DIR` to the absolute reviewed directory. This uses the existing deployment sync and avoids a second registry copy.

## Scope

**In scope:** backend settings and a strict read-only provider registry service; Pydantic provider and schema models; an authenticated provider-list endpoint; the reviewed `mal.yml` file with two scopes; a read-only deployment mount; settings, API, service, route-inventory, deployment, and documentation checks.

**Out of scope:** project metadata requirements, project save guards, UI selection, SIMS calls, SEAD provider lookup, ingester changes, key-contract decisions, BugsCEP registration, and existing-project assignments. Those belong to later phases or separate decisions. No registry record contains `scope_uuid` or `data_provider_id`.

## Work Breakdown

### Area 1: Configure and deliver the reviewed registry

**Objective:** one configured runtime directory reads the reviewed YAML files in development and the container.

**Affected code:** `backend/app/core/config.py::Settings`, `.env.example`, `deployment/container/resources/backend.env.example`, `deployment/container/podman-compose.yml`, `deployment/container/DEPLOYMENT.md`, `docs/OPERATIONS.md`, `backend/tests/test_config.py`, and `backend/tests/test_authorization_config.py`; `deployment/container/resources/data-providers/README.md` (**NEW**).

**Dependencies:** none.

* [ ] `T1.1` **Configure the provider directory.**
  * **Target:** `backend/app/core/config.py::Settings` and `Settings.resolve_paths`; `.env.example`; `deployment/container/resources/backend.env.example`; `docs/OPERATIONS.md`; `backend/tests/test_config.py`; `backend/tests/test_authorization_config.py`.
  * **Current → required:** no provider path exists → `GLOBAL_DATA_PROVIDER_DIR` defaults to `shared/data-providers`, resolves under `APPLICATION_ROOT`, is created, and cannot contain `AUTHORIZATION_DATABASE_PATH`.
  * **Implementation:** add the setting and resolved-path accessor for dependency injection; include it in directory creation and authorization database containment checks; document the environment variable and local absolute-path override. Do not add it to directive expansion unless a later phase uses it there.
  * **Constraints:** preserve existing shared paths and their defaults. Never resolve provider data through the target database or SIMS.
  * **Validation:** `V-1` covers default and explicit paths, directory creation, and rejected authorization database placement.
* [ ] `T1.2` **Deliver reviewed files to the container as read-only data.**
  * **Target:** `deployment/container/resources/data-providers/README.md` (**NEW**); `deployment/container/podman-compose.yml`; `deployment/container/DEPLOYMENT.md`.
  * **Current → required:** `data/` is ignored and `/app/shared` is writable → reviewed files ship in the tracked deployment tree and are mounted read-only at `/app/shared/data-providers` inside the existing `/app/shared` mount.
  * **Implementation:** create the tracked directory with a README stating the provider fields, nested schema fields, exact scope formula, review requirement, and no runtime edits. Add the nested read-only bind mount from `./resources/data-providers` in the compose file; document refresh via the existing `sync-to-deploy` workflow and how to verify the effective mount.
  * **Constraints:** do not overwrite runtime shared data or add a second writable source of provider records. Keep deployment source paths relative to the compose file's directory.
  * **Validation:** `V-4` checks compose resolution, mount mode, and a local settings override. `V-5` checks that the tracked files exist in the deployment tree.

**Completion evidence:** settings resolve the provider path and a deployed container reads the reviewed directory at the default location with no write permission from the application.

### Area 2: Enforce provider-schema identity rules in one read service

**Objective:** callers receive a complete, deterministic registry or an explicit error.

**Affected code:** `backend/app/models/data_provider.py` (**NEW**), `backend/app/services/data_provider_service.py` (**NEW**), `backend/app/services/__init__.py`, `backend/tests/services/test_data_provider_service.py` (**NEW**).

**Dependencies:** Area 1's path contract.

* [ ] `T1.3` **Load and validate all provider files.**
  * **Target:** `backend/app/models/data_provider.py` (**NEW**); `backend/app/services/data_provider_service.py` (**NEW**); `backend/app/services/__init__.py`; `backend/tests/services/test_data_provider_service.py` (**NEW**).
  * **Current → required:** no provider reader exists → a service loads one `*.yml` file per provider, returns a sorted provider list and lookup by provider-schema pair, and rejects invalid registry content before returning any entry.
  * **Implementation:** define required provider `code` and `name` plus one or more `schemas` entries with required `provider_schema` and `scope_name`. Reject blank values and extra fields including target IDs. Require `scope_name == f"provider://{code}/{provider_schema}"`; treat a slash inside `provider_schema` as part of that identifier. Reject duplicate provider codes across files, duplicate schema codes within a provider, and duplicate scope names globally. Expose `DataProviderService.list_providers()` and `get_scope(code, provider_schema)`; both validate the complete directory. Read YAML without directive or environment substitution. Distinguish an empty existing directory (empty list) from a missing/unreadable configured directory (error). Report file and reason to operators without exposing filesystem details in the public API. Never add create, update, or delete methods.
  * **Constraints:** use absolute backend imports; load the whole registry for list and lookup so a malformed file cannot disappear silently. Display-name corrections may change `name`; established provider codes, schema codes, and scopes may not change after use.
  * **Validation:** `V-2` covers one provider with two valid synthetic schemas, two providers with independent schemas, sorted listing, pair lookup, empty registry, duplicate provider code, duplicate schema code, duplicate scope, mismatched scope, blank or extra fields, malformed YAML, and missing directory. Assert each invalid case returns no partial result.

**Completion evidence:** one provider can return two distinct exact scope names, pair lookup selects the intended one, and every invalid entry fails the complete read.

### Area 3: Expose an authenticated provider list

**Objective:** later project-selection work can read providers and their schema scopes without a database or SIMS request.

**Affected code:** `backend/app/api/dependencies.py`, `backend/app/api/v1/endpoints/data_providers.py` (**NEW**), `backend/app/api/v1/api.py`, `backend/tests/api/test_data_provider_api.py` (**NEW**), `backend/tests/authorization/test_route_authentication.py`, and `docs/AUTHORIZATION_ROUTE_INVENTORY.md`.

**Dependencies:** Area 2's service contract.

* [ ] `T1.4` **Register a read-only list endpoint.**
  * **Target:** `backend/app/api/dependencies.py::get_data_provider_service` (**NEW** symbol); `backend/app/api/v1/endpoints/data_providers.py` (**NEW**); `backend/app/api/v1/api.py::api_router`; `backend/tests/api/test_data_provider_api.py` (**NEW**); `backend/tests/authorization/test_route_authentication.py::AUTHENTICATED_ONLY_API_PATHS`; `docs/AUTHORIZATION_ROUTE_INVENTORY.md`.
  * **Current → required:** no provider API route exists → `GET /api/v1/data-providers` returns `code`, `name`, and nested `{provider_schema, scope_name}` entries from the validated registry to an authenticated principal.
  * **Implementation:** inject the service using the configured directory; require `get_principal()`; return a typed list sorted by provider code and schema code. Translate registry failure into a safe server error and log the cause. Register the router, add `/data-providers` to the authenticated-only classification, add its inventory row, and update the inventory route count from the assembled route table.
  * **Constraints:** no POST, PUT, PATCH, or DELETE; no resource-specific authorization record; no SIMS or target-database call. Keep errors free of host paths or YAML content.
  * **Validation:** `V-3` uses `backend/tests/conftest.py::authorized_client` to test authenticated success, empty list, invalid-registry failure without partial data or path disclosure, and unauthenticated `401`; `V-6` checks route classification and inventory parity.

**Completion evidence:** an authenticated request returns the full validated list, anonymous requests fail, and the route inventory remains complete.

### Area 4: Add approved records and preserve used identities

**Objective:** the approved `mal` provider has two reviewed schema scopes, and revisions do not change established pair-to-scope assignments.

**Affected data:** `deployment/container/resources/data-providers/mal.yml` (**NEW**); `deployment/container/resources/data-providers/README.md` (**NEW**, from Area 1).

**Dependencies:** Area 1 delivery path and Area 2 validation contract. The provider and schema values are approved.

* [ ] `T1.5` **Add the approved `mal` entry and review identity changes.**
  * **Target:** `deployment/container/resources/data-providers/mal.yml` (**NEW**).
  * **Current → required:** no approved records are checked in → one provider file contains `code: mal`, `name: MAL`, and exactly two schema entries: `archeobotany/arbodat-pilot` → `provider://mal/archeobotany/arbodat-pilot` and `radiocarbon/strucke-pilot` → `provider://mal/radiocarbon/strucke-pilot`.
  * **Implementation:** add those values and run the strict loader against the reviewed directory. For later registry revisions, compare the previous reviewed revision and the project binding inventory; reject removal, code or schema reuse, changed scope, or a display-name edit that actually reassigns `mal` to another provider. A genuine display-name correction is allowed only when review confirms the provider identity is unchanged.
  * **Constraints:** do not add BugsCEP or infer more schemas from pilot project names. Do not store SEAD IDs or SIMS scope UUIDs. A string match alone cannot distinguish a display-name correction from reassignment.
  * **Validation:** `V-5` verifies the exact record and parser acceptance; `V-7` records the prior-registry and bound-project comparison, including a proposed reassignment that must be rejected. Together these meet `VM-1`.

**Completion evidence:** the registry contains only the approved `mal` record and its two scopes, and a recorded review confirms established pair/scope identities were preserved.

## Acceptance-Criteria Coverage

| Criterion | Task IDs | Validation IDs | Expected evidence |
| --- | --- | --- | --- |
| `PH1-AC-1` from `P-AC-1` | `T1.1`, `T1.3`, `T1.4`, `T1.5` | `V-1`, `V-2`, `V-3`, `V-5` | The single `mal` record has two exact, distinct scopes; BugsCEP is absent; invalid registry content cannot produce a partial API list. |
| `PH1-AC-2` from `P-AC-1` | `T1.2`, `T1.3`, `T1.5` | `V-2`, `V-4`, `V-7` | No API mutation path; runtime mount is read-only; a reviewed comparison rejects changed or reassigned used pairs and scopes. |

## Validation And Testing

`VM-1` is met only after both automated registry checks and the identity review pass. Use synthetic codes and schemas for negative tests; separately check the approved `mal` file.

| ID | Check and target | Command or method | Covers | Expected result | Baseline |
| --- | --- | --- | --- | --- | --- |
| `V-1` | Settings path and authorization database checks in `backend/tests/test_config.py` and `backend/tests/test_authorization_config.py` | `rtk uv run pytest backend/tests/test_config.py backend/tests/test_authorization_config.py -q` | `T1.1` | New default and override tests pass; authorization DB under provider directory raises `ValueError`. | Pass: existing tests passed before the change; new cases do not exist yet. |
| `V-2` | Strict reader cases in `backend/tests/services/test_data_provider_service.py` (**NEW**) | `rtk uv run pytest backend/tests/services/test_data_provider_service.py -q` | `PH1-AC-1`, `T1.3` | One provider with two slash-containing schema codes returns two distinct scopes; pair lookup selects each. Duplicate provider, schema, and scope values, mismatch, blank or extra fields, malformed YAML, and missing directory fail without a partial result. An empty existing directory returns an empty list. | Not run: test file does not exist yet. |
| `V-3` | Authenticated list and safe failure in `backend/tests/api/test_data_provider_api.py` (**NEW**) | `rtk uv run pytest backend/tests/api/test_data_provider_api.py -q` | `T1.4`, `PH1-AC-1` | Authenticated `200` returns providers and their nested schema scopes in order; invalid registry returns safe `500`; anonymous request returns `401`. | Not run: test file does not exist yet. |
| `V-4` | Deployment read-only mount and local override | `rtk make -C deployment/container config`; on a test deployment, `podman inspect shape-shifter --format '{{json .Mounts}}'` and read the provider list using the configured path | `T1.1`, `T1.2`, `PH1-AC-2` | Compose resolves the source directory; `/app/shared/data-providers` is a read-only nested mount; local absolute override reads the same reviewed files. | Not run: compose change and test deployment do not exist yet. |
| `V-5` | Reviewed registry contents | `git ls-files --cached --others --exclude-standard deployment/container/resources/data-providers`; `rtk uv run python -c "from pathlib import Path; from backend.app.services.data_provider_service import DataProviderService; print([p.model_dump() for p in DataProviderService(Path('deployment/container/resources/data-providers')).list_providers()])"` | `T1.2`, `T1.5`, `PH1-AC-1` | Only `mal.yml` supplies provider records; it contains display name `MAL` and exactly the two approved schema/scope pairs. No BugsCEP entry appears. | Not run: reviewed directory and service do not exist yet. |
| `V-6` | Route classification and existing backend regression | `rtk uv run pytest backend/tests/authorization/test_route_authentication.py backend/tests/test_data_source_api.py backend/tests/services/test_data_source_service.py -q` | `T1.4` and preserved routes | New path has one inventory row, authentication classification passes, and existing data-source tests remain green. | Pass: existing route and data-source tests passed before the change. |
| `V-7` | Historical identity review | For the first file, inspect `git diff --no-index /dev/null deployment/container/resources/data-providers/mal.yml` (exit 1 means the new file differs); for later revisions, use `git diff origin/dev...HEAD -- deployment/container/resources/data-providers`. Inspect local bindings with `rg -n 'data_provider_code:|provider_schema:' data/projects -g 'shapeshifter.yml'` and repeat against each affected deployment's project directory; record reviewer decision. | `PH1-AC-2`, `T1.5` | Previously used provider-schema pairs and scopes remain assigned to the same provider and key contract; a deletion, reuse, or reassignment is rejected. | Not run: first registry revision has no earlier approved record; no provider-schema bindings exist in the checked local pilot files. |

The two focused baseline runs were `rtk uv run pytest backend/tests/test_config.py backend/tests/authorization/test_route_authentication.py -q` and `rtk uv run pytest backend/tests/services/test_data_source_service.py backend/tests/test_data_source_api.py -q`; both exited successfully on this repository basis. Run `rtk make lint` after implementation, following the repository workflow; its baseline was not run for this planning-only change.

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
| --- | --- | --- | --- |
| Provider path and tests | `backend/app/core/config.py::Settings`; `backend/tests/test_config.py`; `backend/tests/test_authorization_config.py` | `T1.1` | `V-1` passes. |
| Settings and operations documentation | `.env.example`; `deployment/container/resources/backend.env.example`; `docs/OPERATIONS.md` | `T1.1` | Provider path and local override documented. |
| Tracked registry instructions and container mount | `deployment/container/resources/data-providers/README.md` (**NEW**); `deployment/container/podman-compose.yml`; `deployment/container/DEPLOYMENT.md` | `T1.2` | `V-4` and `V-5` pass. |
| Registry model, service, and tests | `backend/app/models/data_provider.py` (**NEW**); `backend/app/services/data_provider_service.py` (**NEW**); `backend/app/services/__init__.py`; `backend/tests/services/test_data_provider_service.py` (**NEW**) | `T1.3` | `V-2` passes. |
| Authenticated read API and route inventory | `backend/app/api/dependencies.py`; `backend/app/api/v1/endpoints/data_providers.py` (**NEW**); `backend/app/api/v1/api.py`; `backend/tests/api/test_data_provider_api.py` (**NEW**); `backend/tests/authorization/test_route_authentication.py`; `docs/AUTHORIZATION_ROUTE_INVENTORY.md` | `T1.4` | `V-3` and `V-6` pass. |
| Approved provider file | `deployment/container/resources/data-providers/mal.yml` (**NEW**) | `T1.5` | `V-5` and `V-7` pass. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
| --- | --- | --- | --- |
| Area 1: Configure and deliver registry | Not started | None | Proposed tracked source and read-only mount are based on verified deployment layout. |
| Area 2: Enforce identity rules | Not started | Area 1 path contract | Synthetic data can be used for tests. |
| Area 3: Expose provider list | Not started | Area 2 | Route inventory and authentication tests must be updated together. |
| Area 4: Add approved record | Not started | Areas 1 and 2 | `mal.yml`, `MAL`, and both schema/scope pairs are approved. |

## Definition Of Done

* [ ] `mal.yml` contains display name `MAL` and exactly the two approved schema/scope pairs; BugsCEP is absent.
* [ ] `PH1-AC-1` and `PH1-AC-2` have task and validation results, including the manual identity review required by `VM-1`.
* [ ] All work areas and deliverables are complete; the read API returns the complete validated registry and has no mutation route.
* [ ] `V-1` through `V-7` pass or have a recorded, justified environment-specific result; focused regressions and `rtk make lint` pass.
* [ ] The tracked registry reaches the container as a read-only mount, and operations documentation matches the effective paths.
* [ ] No SIMS request, target-database request, project binding, or ingestion behavior is added in Phase 1.
* [ ] Deviations and follow-up work are recorded, and no unresolved question changes implementation or validation.

## Risks And Open Questions

1. **Used-identity review:** the registry format can prove that scopes match pairs, but it cannot infer whether a changed display name or schema meaning reassigns a used identity. Review the previous registry revision and affected project bindings for every change. Later project-save enforcement does not replace this registry review.
2. **Deployment verification:** the nested read-only mount is supported by the existing compose layout in principle, but its effective mode must be verified on the deployment host before enabling provider selection. The current plan does not claim a deployed mount has been tested.
