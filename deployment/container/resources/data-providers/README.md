# Curated Data Provider Registry

This directory holds the reviewed provider-schema registry that Shape Shifter reads at
startup. Each file describes one data provider and the provider schemas it delivers.

These files are reviewed data, not runtime data:

- `podman-compose.yml` mounts this directory read-only at `/app/shared/data-providers`.
- The application exposes a read interface only. It never writes provider records.
- Change a record by editing the file, reviewing the change, and syncing the deployment
  tree. Do not edit files inside a running container.

## File format

Use one `*.yml` file per provider, named after the provider code.

```yaml
code: mal # required, stable provider code
name: MAL # required, human-readable display name
schemas: # required, one or more entries
  - provider_schema: archeobotany/arbodat-pilot # required, stable schema code
    scope_name: provider://mal/archeobotany/arbodat-pilot # required, derived scope
```

| Field | Required | Rule |
| --- | --- | --- |
| `code` | Yes | Stable provider code. Unique across the directory. Never change it after use. |
| `name` | Yes | Display name. A correction is allowed only when review confirms the provider identity is unchanged. |
| `schemas` | Yes | At least one entry. |
| `schemas[].provider_schema` | Yes | Stable schema code. Unique within the provider. A slash is part of the code, not a hierarchy. |
| `schemas[].scope_name` | Yes | Must equal `provider://<code>/<provider_schema>` exactly. Unique across the directory. |

Any other field, a blank value, and a `scope_name` that does not match its
provider/schema pair are rejected. A rejected provider file rejects the whole registry;
the application does not return a partial list.

## Stable identity

A provider-schema pair and its `scope_name` identify one SIMS scope and one key contract.
After a pair is bound to a project, it cannot be reassigned to a different provider or key
contract. Adding a schema is allowed. Removing a pair, reusing a code for another provider,
or moving a schema to another provider requires an explicit identity decision, not a file
edit.

Do not store SEAD provider IDs or SIMS scope UUIDs here. Target provider rows are resolved
at ingestion time, and SIMS owns scope creation.
