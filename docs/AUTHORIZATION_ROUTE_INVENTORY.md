# Authorization Route Inventory

## Purpose

This inventory records the authorization requirement declared by every registered API route. It is derived from FastAPI dependency metadata on the current branch. Update this document when adding, removing, or changing a route or its authorization dependency.

`UNDECLARED` means the route has no `authorization_requirement` metadata. It does not mean the route is anonymously accessible: trusted-proxy middleware requires authentication for all paths except `/api/v1/health` when enabled. Each undeclared route still needs classification before authorization cutover.

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
| `application:read_logs`             | View or download application logs                          |
| `UNDECLARED`                        | No route authorization metadata; classification is pending |

## Public And Static Paths

| Method       | Path                | Requirement  | Notes                                                                           |
|--------------|---------------------|--------------|---------------------------------------------------------------------------------|
| `GET`        | `/api/v1/health`    | Public       | Explicit trusted-proxy middleware exception for container health checks         |
| Static mount | `/docs/*`           | `UNDECLARED` | Repository documentation static mount; classify before cutover                  |
| Static mount | `/assets/*`         | `UNDECLARED` | Present only when the production frontend build exists; classify before cutover |
| `GET`        | `/{full_path:path}` | `UNDECLARED` | Frontend SPA catch-all when the production frontend build exists                |
| `GET`        | `/`                 | `UNDECLARED` | API-only root route when no frontend build exists                               |

## API Routes

### Help And Sessions

| Method   | Path                                     | Requirement    |
|----------|------------------------------------------|----------------|
| `GET`    | `/api/v1/help-docs/{doc_path:path}`      | `UNDECLARED`   |
| `POST`   | `/api/v1/sessions`                       | `UNDECLARED`   |
| `GET`    | `/api/v1/sessions/current`               | `project:edit` |
| `DELETE` | `/api/v1/sessions/current`               | `project:edit` |
| `GET`    | `/api/v1/sessions/{project_name}/active` | `project:read` |

### Projects

| Method   | Path                                                 | Requirement                                  |
|----------|------------------------------------------------------|----------------------------------------------|
| `GET`    | `/api/v1/projects`                                   | `UNDECLARED`                                 |
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
| `GET`    | `/api/v1/projects/active/name`                       | `UNDECLARED`                                 |
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

| Method   | Path                                                            | Requirement                         |
|----------|-----------------------------------------------------------------|-------------------------------------|
| `GET`    | `/api/v1/data-sources/drivers`                                  | `UNDECLARED`                        |
| `GET`    | `/api/v1/data-sources/entity-types`                             | `UNDECLARED`                        |
| `GET`    | `/api/v1/data-sources`                                          | `UNDECLARED`                        |
| `GET`    | `/api/v1/data-sources/files`                                    | `UNDECLARED`                        |
| `GET`    | `/api/v1/data-sources/excel/metadata`                           | `UNDECLARED`                        |
| `POST`   | `/api/v1/data-sources/files`                                    | `application:manage_shared_sources` |
| `GET`    | `/api/v1/data-sources/{filename}`                               | `shared_data_source:read`           |
| `POST`   | `/api/v1/data-sources`                                          | `application:manage_shared_sources` |
| `PUT`    | `/api/v1/data-sources/{filename}`                               | `application:manage_shared_sources` |
| `DELETE` | `/api/v1/data-sources/{filename}`                               | `application:manage_shared_sources` |
| `POST`   | `/api/v1/data-sources/{filename}/test`                          | `shared_data_source:read`           |
| `GET`    | `/api/v1/data-sources/{name}/status`                            | `shared_data_source:read`           |
| `GET`    | `/api/v1/data-sources/{name}/tables`                            | `shared_data_source:read`           |
| `POST`   | `/api/v1/data-sources/tables`                                   | `UNDECLARED`                        |
| `GET`    | `/api/v1/data-sources/{name}/tables/{table_name}/schema`        | `shared_data_source:read`           |
| `POST`   | `/api/v1/data-sources/tables/schema`                            | `UNDECLARED`                        |
| `GET`    | `/api/v1/data-sources/{name}/tables/{table_name}/preview`       | `shared_data_source:read`           |
| `GET`    | `/api/v1/data-sources/{name}/tables/{table_name}/type-mappings` | `shared_data_source:read`           |
| `POST`   | `/api/v1/data-sources/{name}/tables/{table_name}/import`        | `shared_data_source:read`           |
| `POST`   | `/api/v1/data-sources/{name}/cache/invalidate`                  | `application:manage_shared_sources` |
| `POST`   | `/api/v1/data-sources/{data_source_name}/query/execute`         | `shared_data_source:read`           |
| `POST`   | `/api/v1/data-sources/{data_source_name}/query/validate`        | `shared_data_source:read`           |
| `POST`   | `/api/v1/data-sources/{data_source_name}/query/columns`         | `shared_data_source:read`           |

### Suggestions, Preview, And Reconciliation

| Method   | Path                                                                                                         | Requirement    |
|----------|--------------------------------------------------------------------------------------------------------------|----------------|
| `POST`   | `/api/v1/suggestions/analyze`                                                                                | `UNDECLARED`   |
| `POST`   | `/api/v1/suggestions/entity`                                                                                 | `UNDECLARED`   |
| `POST`   | `/api/v1/projects/{project_name}/entities/{entity_name}/preview`                                             | `project:read` |
| `POST`   | `/api/v1/projects/{project_name}/entities/{entity_name}/sample`                                              | `project:read` |
| `DELETE` | `/api/v1/projects/{project_name}/preview-cache`                                                              | `project:edit` |
| `POST`   | `/api/v1/projects/{project_name}/entities/{entity_name}/foreign-keys/{fk_index}/test`                        | `project:read` |
| `GET`    | `/api/v1/reconciliation/health`                                                                              | `UNDECLARED`   |
| `GET`    | `/api/v1/reconciliation/manifest`                                                                            | `UNDECLARED`   |
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

### Mapping, Execution, And Materialization

| Method   | Path                                                                      | Requirement       |
|----------|---------------------------------------------------------------------------|-------------------|
| `GET`    | `/api/v1/projects/{project_name}/mapping/{entity_name}`                   | `project:read`    |
| `GET`    | `/api/v1/projects/{project_name}/mapping/{entity_name}/{local_key_value}` | `project:read`    |
| `PUT`    | `/api/v1/projects/{project_name}/mapping/{entity_name}/{local_key_value}` | `project:edit`    |
| `DELETE` | `/api/v1/projects/{project_name}/mapping/{entity_name}/{local_key_value}` | `project:edit`    |
| `GET`    | `/api/v1/dispatchers`                                                     | `UNDECLARED`      |
| `POST`   | `/api/v1/projects/{name}/execute`                                         | `project:execute` |
| `GET`    | `/api/v1/projects/{name}/execute/download`                                | `project:read`    |
| `GET`    | `/api/v1/projects/{project_name}/entities/{entity_name}/can-materialize`  | `project:read`    |
| `POST`   | `/api/v1/projects/{project_name}/entities/{entity_name}/materialize`      | `project:edit`    |
| `POST`   | `/api/v1/projects/{project_name}/entities/{entity_name}/unmaterialize`    | `project:edit`    |
| `PATCH`  | `/api/v1/projects/{project_name}/mapping/from-materialized/{entity_name}` | `project:edit`    |

### Ingester, Filters, Logs, And Release Notes

| Method | Path                                  | Requirement             |
|--------|---------------------------------------|-------------------------|
| `GET`  | `/api/v1/ingesters`                   | `UNDECLARED`            |
| `POST` | `/api/v1/ingesters/{key}/validate`    | `UNDECLARED`            |
| `POST` | `/api/v1/ingesters/{key}/ingest`      | `UNDECLARED`            |
| `GET`  | `/api/v1/filters/types`               | `UNDECLARED`            |
| `GET`  | `/api/v1/logs/{log_type}`             | `application:read_logs` |
| `GET`  | `/api/v1/logs/{log_type}/download`    | `application:read_logs` |
| `GET`  | `/api/v1/whats-new`                   | `UNDECLARED`            |
| `GET`  | `/api/v1/whats-new/{version}/content` | `UNDECLARED`            |

## Maintenance

Before merging a route change:

1. Update the route's row with its declared resource type and action, or `UNDECLARED` while classification is pending.
2. Confirm that the route's FastAPI dependency exposes matching `authorization_requirement` metadata.
3. Update [AUTHORIZATION.md](AUTHORIZATION.md) if the policy, principal contract, or denial behavior changes.
4. Add regression coverage for the route requirement.

The planned automated completeness check remains tracked in [CENTRALIZED_AUTHORIZATION_SYSTEM_TASK_PLAN.md](proposals/MITIGATE_SECURITY_ISSUES/CENTRALIZED_AUTHORIZATION_SYSTEM_TASK_PLAN.md).
