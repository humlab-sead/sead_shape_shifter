# Authorization Route Inventory

## Purpose

This inventory records the authorization requirement declared by every registered API route and the direct application routes mounted outside `api_router`. It is derived from the assembled FastAPI route table, `backend/app/api/v1/api.py`, and `backend/app/main.py` on the current branch. Update this document when adding, removing, or changing a route, mount, or authorization dependency.

The inventory groups the API routes by feature. It also lists the Swagger OAuth redirect helper at `/docs/oauth2-redirect`, the repository documentation mount at `/docs/*`, and frontend routes that depend on the production build. Resource lifecycle and background-task coverage is documented in [AUTHORIZATION.md](AUTHORIZATION.md#resource-lifecycle-and-background-operations).

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
| `application:run_ingesters`         | Run a data ingester, either validation or ingestion; held through the `operator` deployment role |
| `authenticated`                     | Any authenticated principal may call; no additional resource or application requirement is declared on the route. Trusted-proxy authentication still applies and any response-scoping behavior is described in the route notes |

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

Every row above except the health check requires an authenticated principal through the trusted-proxy middleware. The API health and generated API documentation routes also carry route metadata for the inventory check; that metadata does not enforce authentication or resource permissions. The middleware enforces identity for these paths, and adding a protected path to its `public_paths` set would bypass that check. The `/docs/*` mount publishes the repository documentation tree, including `docs/proposals/`, to any authenticated principal. The container image builds the frontend, so a deployment serves `/assets/*` and the SPA catch-all instead of the API-only root. The health check stays public because the container, compose, and host probes call it without credentials.

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
| `GET`    | `/api/v1/projects/{name}/target-model-entities`      | `project:read`                               |
| `GET`    | `/api/v1/projects/{name}/target-model-docs`          | `project:read`                               |
| `GET`    | `/api/v1/projects/{name}/target-models`              | `project:read`                               |
| `GET`    | `/api/v1/projects/{name}/layout`                     | `project:read`                               |
| `PUT`    | `/api/v1/projects/{name}/layout`                     | `project:edit`                               |
| `DELETE` | `/api/v1/projects/{name}/layout`                     | `project:edit`                               |
| `POST`   | `/api/v1/projects/{name}/files`                      | `project:edit`                               |
| `GET`    | `/api/v1/projects/{name}/files`                      | `project:read`                               |
| `DELETE` | `/api/v1/projects/{name}/files/{filename}`            | `project:edit`                               |
| `GET`    | `/api/v1/projects/{name}/files/capabilities`         | `project:read`                               |
| `POST`   | `/api/v1/projects/{name}/files/{filename}/share`     | `project:edit`; `application:manage_shared_sources` |

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
| `POST`   | `/api/v1/projects/{project_name}/entities/{entity_name}/column-availability` | `project:read` |
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
| `GET`    | `/api/v1/data-providers`                                        | `authenticated`                     | Read-only curated provider-schema registry; no mutation route and no stored resource                                |
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
| `POST`   | `/api/v1/data-sources/{data_source_name}/query/columns`         | project or shared-source read       | Uses `project:read` when `project_name` is supplied; otherwise uses `shared_data_source:read`                       |

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
| `PATCH`  | `/api/v1/projects/{project_name}/mapping/retry-fixed-entity/{entity_name}` | `project:edit`    |

`GET /api/v1/dispatchers` returns only registered output-dispatcher metadata (key, target type, description, and file extension) and exposes no project data, so it requires an authenticated principal and no project role. The route that consumes those dispatchers, `POST /api/v1/projects/{name}/execute`, requires `project:execute`.

### Ingester, Filters, Logs, And Release Notes

| Method | Path                                  | Requirement                                                                                      | Notes |
|--------|---------------------------------------|--------------------------------------------------------------------------------------------------|-------|
| `GET`  | `/api/v1/ingesters`                   | `authenticated`                                                                                 |       |
| `POST` | `/api/v1/ingesters/{key}/validate`    | `application:run_ingesters`; `project:execute when key=sead_change_request`                     | `project:execute` applies only to the retired `sead_change_request` key and requires `project_name` in the request body. |
| `POST` | `/api/v1/ingesters/{key}/ingest`      | `application:run_ingesters`; `project:execute when key=sead_change_request`                      | `project:execute` applies only to the retired `sead_change_request` key and requires `project_name` in the request body. |
| `POST` | `/api/v1/ingesters/sead_change_request/from-project/validate` | `project:execute` | |
| `POST` | `/api/v1/ingesters/sead_change_request/from-project/ingest`   | `project:execute` | |
| `GET`  | `/api/v1/filters/types`               | `authenticated`                                                                                 |       |
| `GET`  | `/api/v1/logs/{log_type}`             | `authenticated`                                                                                 |       |
| `GET`  | `/api/v1/logs/{log_type}/download`    | `authenticated`                                                                                 |       |
| `GET`  | `/api/v1/whats-new`                   | `authenticated`                                                                                 |       |
| `GET`  | `/api/v1/whats-new/{version}/content` | `authenticated`                                                                                 |       |

Application and error logs are global: no project-scoped log file exists, so any authenticated principal may read or download them. The `application:read_logs` action remains defined but is not required by any route.

`GET /api/v1/whats-new` and `GET /api/v1/whats-new/{version}/content` return release-note metadata and markdown published in `docs/whats-new/`, so they require an authenticated principal and no project role.

`GET /api/v1/ingesters` returns registered ingester metadata (key, name, description, version, and supported formats) and `GET /api/v1/filters/types` returns filter configuration schemas, so both require an authenticated principal and no project role.

`POST /api/v1/ingesters/{key}/validate` and `POST /api/v1/ingesters/{key}/ingest` require `application:run_ingesters`, which the `operator` deployment role holds. When `key=sead_change_request`, they also require `project:execute` on the `project_name` in the request body; the handlers then reject this retired file-based path. The other ingesters do not use a project locator. Source and output path containment and destination database selection for generic ingester operations remain tracked in [Security Hardening Follow-up](proposals/SECURITY_HARDENING_FOLLOWUP/SECURITY_HARDENING_FOLLOWUP.md); data registration requires separate authorization classification. The dedicated Change Request target-bundle operation is covered by [Change Request Target Bundle Access](proposals/done/CHANGE_REQUEST_TARGET_BUNDLE_ACCESS/CHANGE_REQUEST_TARGET_BUNDLE_ACCESS.md).

`POST /api/v1/ingesters/sead_change_request/from-project/validate` and `POST /api/v1/ingesters/sead_change_request/from-project/ingest` require `project:execute` for the project named in the request body and no deployment role. They run the Change Request ingester against that authorized project's normalized tables. A principal holding `application:run_ingesters` but no `project:execute` grant on the named project is still denied.

## Maintenance

Before merging a route change:

1. Declare the route's requirement in its authorization dependency, or use `declare_authenticated_route` / `declare_public_route` for routes classified by the trusted-proxy middleware.
2. Update the route row and its notes in this inventory.
3. Update [AUTHORIZATION.md](AUTHORIZATION.md) if the policy, principal contract, resource lifecycle, or denial behavior changes.
4. Run the route tests to confirm that route methods, paths, and requirement labels match the assembled application.

The checks in `backend/tests/authorization/test_route_authentication.py` require metadata for every API route, compare the documented requirements with endpoint and dependency metadata, keep API rows aligned with registered methods and paths, and cover direct and mounted routes outside the API prefix.
