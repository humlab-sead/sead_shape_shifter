# Authorization Route Inventory

## Purpose

This inventory records the authorization requirement declared by every registered API route and the direct application routes mounted outside `api_router`. It is derived from the assembled FastAPI route table, `backend/app/api/v1/api.py`, and `backend/app/main.py` on the current branch. Update this document when adding, removing, or changing a route, mount, or authorization dependency.

The current API-only runtime exposes 136 HTTP route entries under `/api/v1`, including the generated OpenAPI, Swagger UI, and ReDoc routes. It also exposes the Swagger OAuth redirect helper at `/docs/oauth2-redirect` and the repository documentation mount at `/docs/*`. The `/assets/*`, frontend SPA catch-all, and API-only `/` route are conditional on the frontend build state described below.

`UNDECLARED` means the route has no `authorization_requirement` metadata. It does not mean the route is anonymously accessible: trusted-proxy middleware requires authentication for all paths except `/api/v1/health` when enabled. An undeclared route still needs classification before authorization cutover; no row currently reads `UNDECLARED`.

## Requirement Terms

| Requirement                         | Meaning                                                    |
|-------------------------------------|------------------------------------------------------------|
| `project:read`                      | Read the project or its child resource                     |
| `project:edit`                      | Edit the project or its child resource                     |
| `project:execute`                   | Execute a project operation                                |
| `project:delete`                    | Delete the project                                         |
| `shared_data_source:read`           | Read the named shared data source or its child resource    |
| `application:create_project`        | Create a project                                           |
| `application:manage_shared_sources` | Manage shared data sources or schema cache                 |
| `application:read_logs`             | Defined application action for application logs; no route requires it |
| `application:run_ingesters`         | Run a data ingester, either validation or ingestion; held through the `operator` application role |
| `authenticated`                     | Any authenticated principal may call; no additional resource or application requirement is declared on the route. Trusted-proxy authentication still applies and any response-scoping behavior is described in the route notes |
| `enforcement pending`               | Added after a requirement to show that the row records the intended requirement while the route still declares no `authorization_requirement` metadata |
| `UNDECLARED`                        | No route authorization metadata; classification is pending |

## Public And Static Paths

| Method       | Path                    | Requirement     | Notes                                                                                                  |
|--------------|-------------------------|-----------------|--------------------------------------------------------------------------------------------------------|
| `GET`        | `/api/v1/health`        | Public          | Explicit trusted-proxy middleware exception for container health checks                                |
| `GET, HEAD`  | `/api/v1/openapi.json`  | `authenticated` | FastAPI-generated OpenAPI schema; configured application path, not an unprefixed `/openapi.json` route |
| `GET, HEAD`  | `/api/v1/docs`          | `authenticated` | FastAPI-generated Swagger UI; direct application route outside `api_router`                            |
| `GET, HEAD`  | `/docs/oauth2-redirect` | `authenticated` | FastAPI-generated Swagger OAuth redirect helper; direct application route outside `api_router`         |
| `GET, HEAD`  | `/api/v1/redoc`         | `authenticated` | FastAPI-generated ReDoc UI; direct application route outside `api_router`                              |
| Static mount | `/docs/*`               | `authenticated` | Repository documentation static mount published to authenticated principals                                         |
| Static mount | `/assets/*`             | `authenticated` | Present only when the production frontend build exists                        |
| `GET`        | `/{full_path:path}`     | `authenticated` | Frontend SPA catch-all when the production frontend build exists                                       |
| `GET`        | `/`                     | `authenticated` | API-only root route when no frontend build exists                                                      |

Every row above except the health check requires an authenticated principal through the trusted-proxy middleware. None of them carries `authorization_requirement` metadata, so the middleware `public_paths` set is the only control that keeps them non-public; adding a path to that set would expose it with no policy check. The `/docs/*` mount publishes the repository documentation tree, including `docs/proposals/`, to any authenticated principal. The container image builds the frontend, so a deployment serves `/assets/*` and the SPA catch-all instead of the API-only root. The health check stays public because the container, compose, and host probes call it without credentials.

## API Routes

### Help And Sessions

| Method   | Path                                     | Requirement    |
|----------|------------------------------------------|----------------|
| `GET`    | `/api/v1/help-docs/{doc_path:path}`      | `authenticated` |
| `POST`   | `/api/v1/sessions`                       | `project:edit` |
| `GET`    | `/api/v1/sessions/current`               | `project:edit` |
| `DELETE` | `/api/v1/sessions/current`               | `project:edit` |
| `GET`    | `/api/v1/sessions/{project_name}/active` | `project:read` |

`GET /api/v1/help-docs/{doc_path:path}` serves markdown from the repository `docs/` directory, the same tree the `/docs/*` mount publishes. It rejects absolute paths and `..` segments and requires the resolved file to stay under `docs/`, so it requires an authenticated principal and no project role.

`POST /api/v1/sessions` declares `project:edit` through `require_project(Action.EDIT, body_locator=True)`, which reads `project_name` from the request body because the route has no project path or query parameter.

### Projects

| Method   | Path                                                 | Requirement                                  |
|----------|------------------------------------------------------|----------------------------------------------|
| `GET`    | `/api/v1/projects`                                   | `authenticated`                              |
| `GET`    | `/api/v1/projects/{name}`                            | `project:read`                               |
| `POST`   | `/api/v1/projects/{name}/refresh`                    | `project:edit`                               |
| `POST`   | `/api/v1/projects`                                   | `application:create_project`                 |
| `PUT`    | `/api/v1/projects/{name}`                            | `project:edit`                               |
| `PATCH`  | `/api/v1/projects/{name}/metadata`                   | `project:edit`                               |
| `DELETE` | `/api/v1/projects/{name}`                            | `project:delete`                             |
| `POST`   | `/api/v1/projects/{name}/copy`                       | `project:read`; `application:create_project` |
| `POST`   | `/api/v1/projects/{name}/validate`                   | `project:read`                               |
| `GET`    | `/api/v1/projects/{name}/backups`                    | `project:read`                               |
| `POST`   | `/api/v1/projects/{name}/restore`                    | `project:edit`                               |
| `GET`    | `/api/v1/projects/active/name`                       | `project:read`                               |
| `POST`   | `/api/v1/projects/{name}/activate`                   | `project:read`                               |
| `GET`    | `/api/v1/projects/{name}/data-sources`               | `project:read`                               |
| `POST`   | `/api/v1/projects/{name}/data-sources`               | `project:edit`; `shared_data_source:read`    |
| `DELETE` | `/api/v1/projects/{name}/data-sources/{source_name}` | `project:edit`                               |
| `GET`    | `/api/v1/projects/{name}/raw-yaml`                   | `project:read`                               |
| `PUT`    | `/api/v1/projects/{name}/raw-yaml`                   | `project:edit`                               |
| `GET`    | `/api/v1/projects/{name}/target-model-yaml`          | `project:read`                               |
| `PUT`    | `/api/v1/projects/{name}/target-model-yaml`          | `project:edit`                               |
| `GET`    | `/api/v1/projects/{name}/target-model-docs`          | `project:read`                               |
| `GET`    | `/api/v1/projects/{name}/layout`                     | `project:read`                               |
| `PUT`    | `/api/v1/projects/{name}/layout`                     | `project:edit`                               |
| `DELETE` | `/api/v1/projects/{name}/layout`                     | `project:edit`                               |
| `POST`   | `/api/v1/projects/{name}/files`                      | `project:edit`                               |
| `GET`    | `/api/v1/projects/{name}/files`                      | `project:read`                               |

`GET /api/v1/projects` returns metadata only for projects the principal can read: `ProjectService.list_authorized_projects` requires an `active` resource record and `project:read` for each entry, so the route narrows its response instead of denying the request. Projects without an authorization record are omitted. The route declares no `authorization_requirement` metadata because the check applies to each listed entry rather than to one request; the authenticated-only classification in the automated check records that distinction.

`GET /api/v1/projects/active/name` declares `project:read` on the deployment's active project through `require_active_project(Action.READ)`, which reads the locator from application state because the route carries no project path or query parameter. A request with no active project returns `{"name": null}`; a request for an active project the principal cannot read returns the concealed `404 {"detail": "Resource not found"}`. `POST /api/v1/projects/{name}/activate` requires `project:read` on the named project, so the active project is always readable by the principal that activated it.

### Entities, Directives, And Validation

| Method   | Path                                                             | Requirement    |
|----------|------------------------------------------------------------------|----------------|
| `GET`    | `/api/v1/projects/{project_name}/entities`                       | `project:read` |
| `GET`    | `/api/v1/projects/{project_name}/entities/{entity_name}`         | `project:read` |
| `POST`   | `/api/v1/projects/{project_name}/entities`                       | `project:edit` |
| `PUT`    | `/api/v1/projects/{project_name}/entities/{entity_name}`         | `project:edit` |
| `DELETE` | `/api/v1/projects/{project_name}/entities/{entity_name}`         | `project:edit` |
| `POST`   | `/api/v1/projects/{project_name}/entities/generate-from-table`   | `project:edit` |
| `GET`    | `/api/v1/projects/{project_name}/entities/{entity_name}/values`  | `project:read` |
| `PUT`    | `/api/v1/projects/{project_name}/entities/{entity_name}/values`  | `project:edit` |
| `GET`    | `/api/v1/projects/{project_name}/entities/{entity_name}/columns` | `project:read` |
| `POST`   | `/api/v1/projects/{project_name}/validate-directive`             | `project:read` |
| `GET`    | `/api/v1/projects/{project_name}/valid-directives`               | `project:read` |
| `POST`   | `/api/v1/projects/{name}/validate/data`                          | `project:read` |
| `POST`   | `/api/v1/projects/{name}/entities/{entity_name}/validate`        | `project:read` |
| `POST`   | `/api/v1/projects/{name}/validate/target-model`                  | `project:read` |
| `GET`    | `/api/v1/projects/{name}/dependencies`                           | `project:read` |
| `POST`   | `/api/v1/projects/{name}/dependencies/check`                     | `project:read` |
| `POST`   | `/api/v1/projects/{name}/fixes/preview`                          | `project:read` |
| `POST`   | `/api/v1/projects/{name}/fixes/apply`                            | `project:edit` |

### Tasks

| Method   | Path                                                   | Requirement    |
|----------|--------------------------------------------------------|----------------|
| `GET`    | `/api/v1/projects/{name}/tasks`                        | `project:read` |
| `POST`   | `/api/v1/projects/{name}/tasks/initialize`             | `project:edit` |
| `POST`   | `/api/v1/projects/{name}/tasks/{entity_name}/complete` | `project:edit` |
| `POST`   | `/api/v1/projects/{name}/tasks/{entity_name}/ignore`   | `project:edit` |
| `DELETE` | `/api/v1/projects/{name}/tasks/{entity_name}`          | `project:edit` |
| `POST`   | `/api/v1/projects/{name}/tasks/{entity_name}/todo`     | `project:edit` |
| `POST`   | `/api/v1/projects/{name}/tasks/{entity_name}/ongoing`  | `project:edit` |
| `POST`   | `/api/v1/projects/{name}/tasks/{entity_name}/flag`     | `project:edit` |
| `GET`    | `/api/v1/projects/{name}/tasks/{entity_name}/note`     | `project:read` |
| `PUT`    | `/api/v1/projects/{name}/tasks/{entity_name}/note`     | `project:edit` |
| `DELETE` | `/api/v1/projects/{name}/tasks/{entity_name}/note`     | `project:edit` |
| `POST`   | `/api/v1/projects/{name}/tasks/migrate-to-sidecar`     | `project:edit` |
| `GET`    | `/api/v1/projects/{name}/tasks/sidecar/status`         | `project:read` |

### Shared Data Sources, Schema, And Queries

| Method   | Path                                                            | Requirement                         | Notes                                                                                                               |
|----------|-----------------------------------------------------------------|-------------------------------------|---------------------------------------------------------------------------------------------------------------------|
| `GET`    | `/api/v1/data-sources/drivers`                                  | `authenticated`                     | Non-sensitive driver metadata                                                                                       |
| `GET`    | `/api/v1/data-sources/entity-types`                             | `authenticated`                     | Non-sensitive entity-type metadata                                                                                  |
| `GET`    | `/api/v1/data-sources`                                          | `authenticated`                     | Returns only shared data sources the principal can read (`shared_data_source:read`)                                 |
| `GET`    | `/api/v1/data-sources/files`                                    | `authenticated`                     | Global shared-data files returned only to operators (`application:manage_shared_sources`); project-local files returned only with `project:read` for the named project |
| `GET`    | `/api/v1/data-sources/excel/metadata`                           | `authenticated`                     | Global reads require `application:manage_shared_sources`; project-local reads require `project:read`; `location=local` requires `project_name` |
| `POST`   | `/api/v1/data-sources/files`                                    | `application:manage_shared_sources` |                                                                                                                     |
| `GET`    | `/api/v1/data-sources/{filename}`                               | `shared_data_source:read`           |                                                                                                                     |
| `POST`   | `/api/v1/data-sources`                                          | `application:manage_shared_sources` |                                                                                                                     |
| `PUT`    | `/api/v1/data-sources/{filename}`                               | `application:manage_shared_sources` |                                                                                                                     |
| `DELETE` | `/api/v1/data-sources/{filename}`                               | `application:manage_shared_sources` |                                                                                                                     |
| `POST`   | `/api/v1/data-sources/{filename}/test`                          | `shared_data_source:read`           |                                                                                                                     |
| `GET`    | `/api/v1/data-sources/{name}/status`                            | `shared_data_source:read`           |                                                                                                                     |
| `GET`    | `/api/v1/data-sources/{name}/tables`                            | `shared_data_source:read`           |                                                                                                                     |
| `POST`   | `/api/v1/data-sources/tables`                                   | `authenticated`                     | Client-supplied config introspection; follow-up to resolve config server-side from a registered source               |
| `GET`    | `/api/v1/data-sources/{name}/tables/{table_name}/schema`        | `shared_data_source:read`           |                                                                                                                     |
| `POST`   | `/api/v1/data-sources/tables/schema`                            | `authenticated`                     | Client-supplied config introspection; follow-up to resolve config server-side from a registered source               |
| `GET`    | `/api/v1/data-sources/{name}/tables/{table_name}/preview`       | `shared_data_source:read`           |                                                                                                                     |
| `GET`    | `/api/v1/data-sources/{name}/tables/{table_name}/type-mappings` | `shared_data_source:read`           |                                                                                                                     |
| `POST`   | `/api/v1/data-sources/{name}/tables/{table_name}/import`        | `shared_data_source:read`           |                                                                                                                     |
| `POST`   | `/api/v1/data-sources/{name}/cache/invalidate`                  | `application:manage_shared_sources` |                                                                                                                     |
| `POST`   | `/api/v1/data-sources/{data_source_name}/query/execute`         | `shared_data_source:read`           |                                                                                                                     |
| `POST`   | `/api/v1/data-sources/{data_source_name}/query/validate`        | `shared_data_source:read`           |                                                                                                                     |
| `POST`   | `/api/v1/data-sources/{data_source_name}/query/columns`         | `shared_data_source:read`           |                                                                                                                     |

### Suggestions, Preview, And Reconciliation

| Method   | Path                                                                                                         | Requirement    |
|----------|--------------------------------------------------------------------------------------------------------------|----------------|
| `POST`   | `/api/v1/suggestions/analyze`                                                                                | `authenticated` |
| `POST`   | `/api/v1/suggestions/entity`                                                                                 | `authenticated` |
| `POST`   | `/api/v1/projects/{project_name}/entities/{entity_name}/preview`                                             | `project:read` |
| `POST`   | `/api/v1/projects/{project_name}/entities/{entity_name}/sample`                                              | `project:read` |
| `DELETE` | `/api/v1/projects/{project_name}/preview-cache`                                                              | `project:edit` |
| `POST`   | `/api/v1/projects/{project_name}/entities/{entity_name}/foreign-keys/{fk_index}/test`                        | `project:read` |
| `GET`    | `/api/v1/reconciliation/health`                                                                              | `authenticated` |
| `GET`    | `/api/v1/reconciliation/manifest`                                                                            | `authenticated` |
| `GET`    | `/api/v1/projects/{project_name}/reconciliation`                                                             | `project:read` |
| `PUT`    | `/api/v1/projects/{project_name}/reconciliation`                                                             | `project:edit` |
| `PUT`    | `/api/v1/projects/{project_name}/reconciliation/raw`                                                         | `project:edit` |
| `GET`    | `/api/v1/projects/{project_name}/reconciliation/{entity_name}/{target_field}/preview`                        | `project:read` |
| `POST`   | `/api/v1/projects/{project_name}/reconciliation/{entity_name}/{target_field}/auto-reconcile`                 | `project:edit` |
| `GET`    | `/api/v1/operations/{operation_id}/progress`                                                                 | `project:read` |
| `GET`    | `/api/v1/operations/{operation_id}/stream`                                                                   | `project:read` |
| `POST`   | `/api/v1/operations/{operation_id}/cancel`                                                                   | `project:edit` |
| `POST`   | `/api/v1/projects/{project_name}/reconciliation/{entity_name}/{target_field}/auto-reconcile-sync`            | `project:edit` |
| `GET`    | `/api/v1/projects/{project_name}/reconciliation/{entity_name}/{target_field}/suggest`                        | `project:read` |
| `POST`   | `/api/v1/projects/{project_name}/reconciliation/{entity_name}/{target_field}/mapping`                        | `project:edit` |
| `DELETE` | `/api/v1/projects/{project_name}/reconciliation/{entity_name}/{target_field}/mapping`                        | `project:edit` |
| `POST`   | `/api/v1/projects/{project_name}/reconciliation/{entity_name}/{target_field}/export-to-mapping`              | `project:edit` |
| `POST`   | `/api/v1/projects/{project_name}/reconciliation/{entity_name}/{target_field}/mark-unmatched`                 | `project:edit` |
| `GET`    | `/api/v1/projects/{project_name}/reconciliation/mapping-registry`                                            | `project:read` |
| `POST`   | `/api/v1/projects/{project_name}/reconciliation/mapping-registry`                                            | `project:edit` |
| `PUT`    | `/api/v1/projects/{project_name}/reconciliation/mapping-registry/{entity_name}/{target_field}`               | `project:edit` |
| `DELETE` | `/api/v1/projects/{project_name}/reconciliation/mapping-registry/{entity_name}/{target_field}`               | `project:edit` |
| `GET`    | `/api/v1/projects/{project_name}/reconciliation/available-fields/{entity_name}`                              | `project:read` |
| `GET`    | `/api/v1/projects/{project_name}/reconciliation/mapping-registry/{entity_name}/{target_field}/mapping-count` | `project:read` |

`POST /api/v1/suggestions/analyze` and `POST /api/v1/suggestions/entity` analyze client-supplied entity configuration and an optional `data_source_name`, so they carry no stored resource; a follow-up should resolve the source server-side and require shared-source read, as with `POST /api/v1/data-sources/tables`. `GET /api/v1/reconciliation/health` and `GET /api/v1/reconciliation/manifest` report reconciliation service status and its manifest and expose no project or shared-source data; the health response includes the configured service URL.

### Mapping, Execution, And Materialization

| Method   | Path                                                                      | Requirement       |
|----------|---------------------------------------------------------------------------|-------------------|
| `GET`    | `/api/v1/projects/{project_name}/mapping/{entity_name}`                   | `project:read`    |
| `GET`    | `/api/v1/projects/{project_name}/mapping/{entity_name}/{local_key_value}` | `project:read`    |
| `PUT`    | `/api/v1/projects/{project_name}/mapping/{entity_name}/{local_key_value}` | `project:edit`    |
| `DELETE` | `/api/v1/projects/{project_name}/mapping/{entity_name}/{local_key_value}` | `project:edit`    |
| `GET`    | `/api/v1/dispatchers`                                                     | `authenticated`   |
| `POST`   | `/api/v1/projects/{name}/execute`                                         | `project:execute` |
| `GET`    | `/api/v1/projects/{name}/execute/download`                                | `project:read`    |
| `GET`    | `/api/v1/projects/{project_name}/entities/{entity_name}/can-materialize`  | `project:read`    |
| `POST`   | `/api/v1/projects/{project_name}/entities/{entity_name}/materialize`      | `project:edit`    |
| `POST`   | `/api/v1/projects/{project_name}/entities/{entity_name}/unmaterialize`    | `project:edit`    |
| `PATCH`  | `/api/v1/projects/{project_name}/mapping/from-materialized/{entity_name}` | `project:edit`    |

`GET /api/v1/dispatchers` returns only registered output-dispatcher metadata (key, target type, description, and file extension) and exposes no project data, so it requires an authenticated principal and no project role. The route that consumes those dispatchers, `POST /api/v1/projects/{name}/execute`, requires `project:execute`.

### Ingester, Filters, Logs, And Release Notes

| Method | Path                                  | Requirement                              |
|--------|---------------------------------------|------------------------------------------|
| `GET`  | `/api/v1/ingesters`                   | `authenticated`                          |
| `POST` | `/api/v1/ingesters/{key}/validate`    | `application:run_ingesters`; enforcement pending |
| `POST` | `/api/v1/ingesters/{key}/ingest`      | `application:run_ingesters`; enforcement pending |
| `GET`  | `/api/v1/filters/types`               | `authenticated`                          |
| `GET`  | `/api/v1/logs/{log_type}`             | `authenticated`                          |
| `GET`  | `/api/v1/logs/{log_type}/download`    | `authenticated`                          |
| `GET`  | `/api/v1/whats-new`                   | `authenticated`                          |
| `GET`  | `/api/v1/whats-new/{version}/content` | `authenticated`                          |

Application and error logs are global: no project-scoped log file exists, so any authenticated principal may read or download them. The `application:read_logs` action remains defined but is not required by any route.

`GET /api/v1/whats-new` and `GET /api/v1/whats-new/{version}/content` return release-note metadata and markdown published in `docs/whats-new/`, so they require an authenticated principal and no project role.

`GET /api/v1/ingesters` returns registered ingester metadata (key, name, description, version, and supported formats) and `GET /api/v1/filters/types` returns filter configuration schemas, so both require an authenticated principal and no project role.

`POST /api/v1/ingesters/{key}/validate` and `POST /api/v1/ingesters/{key}/ingest` record `application:run_ingesters`, which the `operator` application role holds. Neither route declares that metadata yet. The two routes accept no project locator: `IngestRequest` carries a server file path in `source`, an `output_folder`, and the `do_register` and `explode` flags, so a run is not addressed to a project and cannot be authorized by `project:execute` alone. Enforcement, which must cover the source, the destination, and the database registration the operations reach, is owned by [INGESTER_AUTHORIZATION_TASKS.md](proposals/CHANGE_REQUEST_INGESTER/INGESTER_AUTHORIZATION_TASKS.md); the source and destination containment checks are owned by [INGESTER_FILESYSTEM_BOUNDARIES.md](proposals/CHANGE_REQUEST_INGESTER/INGESTER_FILESYSTEM_BOUNDARIES.md).

Principals who run and review projects are expected to run these ingesters for that work. Granting `operator` meets that expectation today. If a run must instead be limited to one project, the route needs a project locator plus `project:execute` alongside the containment checks.

## Lifecycle And Background Coverage

Routes are not the only entry points that reach protected work. The table below records the resource lifecycle calls and the background tasks, with the authorization that guards each one. Authorization checks reject any resource whose lifecycle state is not `active`, so a resource in `deleting` or `deleted` fails every check until it returns to `active`.

| Entry point | Authorization | Lifecycle or operation call | Evidence |
|-------------|---------------|-----------------------------|----------|
| `POST /api/v1/projects` | `application:create_project` through `require_application_action` | `ProjectService.assign_project_owner` calls `AuthorizationService.register_project`, which creates the project resource and grants the creating principal the `owner` role | `backend/app/api/v1/endpoints/projects.py::create_project`, `backend/app/services/project_service.py::assign_project_owner` |
| `POST /api/v1/projects/{name}/copy` | `project:read` on the source project plus `application:create_project` | `assign_project_owner` calls `register_project` for the copied project | `backend/app/api/v1/endpoints/projects.py::copy_project` |
| `DELETE /api/v1/projects/{name}` | `project:delete` through `require_project` | `transition_resource` moves the resource to `deleting`, returns it to `active` when the delete fails, and moves it to `deleted` when the delete succeeds | `backend/app/api/v1/endpoints/projects.py::delete_project` |
| `POST /api/v1/data-sources` | `application:manage_shared_sources` through `require_application_action` | `AuthorizationService.register_shared_data_source` creates the shared-source resource and grants the creating principal the `reader` role; the created file is deleted again when registration fails | `backend/app/api/v1/endpoints/data_sources.py::create_data_source` |
| `DELETE /api/v1/data-sources/{filename}` | `application:manage_shared_sources` through `require_application_action` | `transition_resource` moves the resource through `deleting` to `deleted`, and back to `active` when the delete fails | `backend/app/api/v1/endpoints/data_sources.py::delete_data_source` |
| Auto-reconcile background task | `project:edit` on the route that starts it; `require_operation(Action.READ)` for progress and stream, `require_operation(Action.EDIT)` for cancel | `operation_manager.create_operation` records `owner_principal_id` and `project_resource_id`, and `asyncio.create_task` runs the reconciliation under that operation identifier | `backend/app/api/v1/endpoints/reconciliation.py::auto_reconcile_entity`, `backend/app/core/operation_manager.py::create_operation` |
| Session cleanup task | None: the task runs outside a request and holds no principal | Releases sessions left inactive for 30 minutes; sessions and the project names they reference are application state, not authorization resources | `backend/app/core/state_manager.py::_cleanup_stale_sessions` |

**Project rename:** no project rename entry point exists. `ProjectService.update_metadata` ignores its `new_name` argument because the project file name is the authoritative source for the project name, so no rename path needs a lifecycle check. The two `update_metadata` docstrings and the `MetadataUpdateRequest.name` description state this instead of pointing at a `rename_project()` method that does not exist.

**Background entry-point search:** searching `backend/app/` for `asyncio.create_task`, `BackgroundTasks`, `run_in_executor`, and `operation_manager.create_operation` returns two background task starts and one operation creator: the auto-reconcile task and the session cleanup task recorded above, with `reconciliation.py::auto_reconcile_entity` as the only `create_operation` caller. No `BackgroundTasks`, `run_in_executor`, or other task start exists in the backend, so no further background entry point reaches protected work.

## Classification Review

Reviewed by Roger Mähler on 2026-09-17. Every route row and every lifecycle or background entry was checked against the implemented policy in [AUTHORIZATION.md](AUTHORIZATION.md), the role and action maps in `backend/app/authorization/policy.py`, the resource types and actions in `backend/app/authorization/models.py`, and the assembled route set read by `backend/tests/authorization/test_route_authentication.py`.

- The inventory holds 141 route rows and no row reads `UNDECLARED`.
- Resource requirements use only defined resource type and action pairs: `project:read` (43 rows), `project:edit` (48), `project:execute` (1), `project:delete` (1), `shared_data_source:read` (12).
- Application requirements use only defined actions, each granted by an application role the policy defines: `create_project` through `project_creator`, and `manage_shared_sources` and `run_ingesters` through `operator`. No route requires `read_logs`.
- The assembled application exposes no unclassified `/api/v1` route, and every documented non-API row is either served by the application or depends on the frontend build.

Corrections to this review use the same requirement terms and note style. A row that needs a policy decision is reported instead of guessed.

## Maintenance

Before merging a route change:

1. Update the route's row with its declared resource type and action, or `UNDECLARED` while classification is pending.
2. Confirm that the route's FastAPI dependency exposes matching `authorization_requirement` metadata.
3. Update [AUTHORIZATION.md](AUTHORIZATION.md) if the policy, principal contract, or denial behavior changes.
4. Add regression coverage for the route requirement.

The completeness check lives in `backend/tests/authorization/test_route_authentication.py`: `test_api_routes_are_classified` requires declared metadata or a documented classification for every assembled API route, `test_route_inventory_matches_assembled_api_routes` keeps the API rows and the registered routes equal, and `test_route_inventory_matches_direct_and_mounted_routes` covers the rows outside the API prefix.
