# Target Model Schema Reference

This file is generated from `src/target_model/models.py`. Do not edit it by hand.
Run `python scripts/generate_target_model_schema_reference.py` to regenerate it.

## What This Covers

This reference lists the YAML sections and keys accepted by the strict Pydantic target-model schema.
Unknown keys in these sections are rejected because each model uses `extra="forbid"`.

## YAML Paths

- `model`: ModelMetadata (required)
- `entities`: map[string, EntitySpec] (optional)
- `entities.<entity_name>`: EntitySpec (map value)
- `entities.<entity_name>.role`: enum[string] | null (optional)
- `entities.<entity_name>.required`: boolean (optional)
- `entities.<entity_name>.description`: string | null (optional)
- `entities.<entity_name>.domains`: list[string] (optional)
- `entities.<entity_name>.domains[]`: string (list item)
- `entities.<entity_name>.target_table`: string | null (optional)
- `entities.<entity_name>.public_id`: string | null (optional)
- `entities.<entity_name>.identity_columns`: list[string] (optional)
- `entities.<entity_name>.identity_columns[]`: string (list item)
- `entities.<entity_name>.columns`: map[string, ColumnSpec] (optional)
- `entities.<entity_name>.columns.<column_name>`: ColumnSpec (map value)
- `entities.<entity_name>.columns.<column_name>.required`: boolean (optional)
- `entities.<entity_name>.columns.<column_name>.generated`: boolean (optional)
- `entities.<entity_name>.columns.<column_name>.allowed_values`: list[string | integer | number | boolean] (optional)
- `entities.<entity_name>.columns.<column_name>.allowed_values[]`: string | integer | number | boolean (list item)
- `entities.<entity_name>.columns.<column_name>.type`: string | null (optional)
- `entities.<entity_name>.columns.<column_name>.nullable`: boolean | null (optional)
- `entities.<entity_name>.columns.<column_name>.description`: string | null (optional)
- `entities.<entity_name>.unique_sets`: list[list[string]] (optional)
- `entities.<entity_name>.unique_sets[]`: list[string] (list item)
- `entities.<entity_name>.foreign_keys`: list[ForeignKeySpec] (optional)
- `entities.<entity_name>.foreign_keys[]`: ForeignKeySpec (list item)
- `entities.<entity_name>.foreign_keys[].entity`: string (required)
- `entities.<entity_name>.foreign_keys[].required`: boolean (optional)
- `entities.<entity_name>.foreign_keys[].via`: string | null (optional)
- `entities.<entity_name>.identity_tracking`: enum[string] | null (optional)
- `entities.<entity_name>.reconciliation`: enum[string] | null (optional)
- `entities.<entity_name>.aggregate_parent`: string | null (optional)
- `naming`: NamingConventions | null (optional)
- `constraints`: list[GlobalConstraint] (optional)
- `constraints[]`: GlobalConstraint (list item)
- `constraints[].type`: string (required)

## TargetModel

Top-level target model file structure.

| Field | Type | Required | Default | Allowed |
|---|---|---|---|---|
| model | ModelMetadata | Yes | - | - |
| entities | map[string, EntitySpec] | No | {} | - |
| naming | NamingConventions \| null | No | null | null |
| constraints | list[GlobalConstraint] | No | [] | - |

Additional keys allowed: No

## ModelMetadata

Values under the `model` section that identify the specification.

| Field | Type | Required | Default | Allowed |
|---|---|---|---|---|
| name | string | Yes | - | - |
| format_version | string | No | "1" | - |
| version | string | Yes | - | - |
| description | string \| null | No | null | null |

Additional keys allowed: No

## EntitySpec

Values under `entities.<entity_name>` for each target entity.

| Field | Type | Required | Default | Allowed |
|---|---|---|---|---|
| role | enum[string] \| null | No | null | "fact", "lookup", "classifier", "bridge", null |
| required | boolean | No | false | - |
| description | string \| null | No | null | null |
| domains | list[string] | No | [] | - |
| target_table | string \| null | No | null | null |
| public_id | string \| null | No | null | null |
| identity_columns | list[string] | No | [] | - |
| columns | map[string, ColumnSpec] | No | {} | - |
| unique_sets | list[list[string]] | No | [] | - |
| foreign_keys | list[ForeignKeySpec] | No | [] | - |
| identity_tracking | enum[string] \| null | No | null | "tracked", "reconciled", "derived", "child", null |
| reconciliation | enum[string] \| null | No | null | "allocate", "reconcile-exact", "reconcile-fuzzy", "lookup-only", "lookup-extensible", "derive", null |
| aggregate_parent | string \| null | No | null | null |

Additional keys allowed: No

## ColumnSpec

Values under `entities.<entity_name>.columns.<column_name>` for each declared column.

| Field | Type | Required | Default | Allowed |
|---|---|---|---|---|
| required | boolean | No | false | - |
| generated | boolean | No | false | - |
| allowed_values | list[string \| integer \| number \| boolean] | No | [] | - |
| type | string \| null | No | null | null |
| nullable | boolean \| null | No | null | null |
| description | string \| null | No | null | null |

Additional keys allowed: No

## ForeignKeySpec

Values under `entities.<entity_name>.foreign_keys[]` for each foreign key requirement.

| Field | Type | Required | Default | Allowed |
|---|---|---|---|---|
| entity | string | Yes | - | - |
| required | boolean | No | false | - |
| via | string \| null | No | null | null |

Additional keys allowed: No

## NamingConventions

Optional naming rules under the `naming` section.

| Field | Type | Required | Default | Allowed |
|---|---|---|---|---|
| public_id_suffix | string \| null | No | null | null |

Additional keys allowed: No

## GlobalConstraint

Entries under the optional `constraints[]` list.

| Field | Type | Required | Default | Allowed |
|---|---|---|---|---|
| type | string | Yes | - | - |

Additional keys allowed: No
