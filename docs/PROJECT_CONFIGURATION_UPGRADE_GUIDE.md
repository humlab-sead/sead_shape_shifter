# Upgrade a Shape Shifter project configuration

Use this guide when an older `shapeshifter.yml` reports errors with a newer
Shape Shifter release. Start with structural validation, fix the reported
configuration, then run data validation when the project's source files and
database connections are available.

## 1. Validate the project

From the repository root, run:

```bash
uv run python scripts/validate_project.py path/to/shapeshifter.yml \
  --workflow structural --log-level ERROR
```

Read the reported severities; the command can exit with status 0 while listing
structural errors. Structural validation checks configuration shape, not whether
external data sources can be reached or whether every row will link.

## 2. Declare the columns the project produces

`keys` identify rows for matching and duplicate checks. They do not create
columns. If a key is read by a SQL query or source loader, declare it in
`columns` as well:

```yaml
keys: [project_code, sample_code]
columns: [project_code, sample_code, sample_name]
```

Apply the same rule to foreign-key `local_keys`: each field must be available
when linking runs. Declare extracted fields in `columns`, or produce them with
`extra_columns` or an earlier foreign key. Do not add a name to `keys` or
`local_keys` as a substitute for producing that field.

## 3. Keep unnest inputs distinct

`id_vars` are retained for each output row. `value_vars` are the source
measurements to turn into rows; they must not include an identifier. If a
directive expands to a broad column list, replace it with the intended
measurement fields:

```yaml
unnest:
  id_vars: [project_code, sample_code]
  value_vars: [northing, easting, elevation]
  var_name: coordinate_type
  value_name: coordinate_value
```

A foreign key whose local key is created by `var_name` can link during the
post-unnest linking step. `defer_dependency: true` is for a dependency that
must be postponed to the final linking pass, such as a genuine dependency
cycle; it is not needed just because a key comes from unnesting.

## 4. Check identity and relationship declarations

- Do not use `extra_columns` to redefine an entity's `system_id`, `public_id`,
  or an output field already created by unnest. Remove the duplicate definition
  or rename a separate data field.
- Use the supported `cardinality` values: `one_to_one`, `many_to_one`,
  `one_to_many`, or `many_to_many`. Check spelling of constraint names such as
  `constraints`; unknown names may not have the intended effect.
- In fixed rows, use YAML values that match the declared field type. For
  example, write an integer ID as `5`, not `'5'`.
- Review warnings about source-provided `system_id` values before removing
  them. Non-fixed IDs supplied by a source are currently preserved, but Shape
  Shifter does not verify that they are positive and unique.

## 5. Assign the data provider and schema

Each project should be bound to the registered data provider and provider
schema that describe its source data:

1. In the project editor, open **Metadata**.
2. Select the correct provider and one of its registered schemas.
3. Save the project and confirm both values appear in its metadata.

The provider and schema must be a valid pair from the deployment's curated
provider registry. For example:

```yaml
metadata:
  data_provider_code: mal
  provider_schema: archeobotany/arbodat-pilot
```

Choose the pair that matches the project; do not copy this example without
checking the registry. Existing unbound projects can receive their first
provider/schema pair in the Metadata tab. After the first assignment, the
application does not allow the pair to be changed or removed. Resolve an
incorrect existing binding with the deployment maintainers before proceeding.

## 6. Use a shared target model

Prefer a shared target model when several projects should conform to the same
target schema. In the project editor's **Metadata** settings, select the
appropriate target model marked **Shared**. This avoids project-local copies
that can drift and uses the deployment-managed copy.

The saved reference should use the global target-model directory, for example:

```yaml
metadata:
  target_model: "@load: ${GLOBAL_TARGET_MODEL_DIR}/sead_standard_model.yml"
```

The deployment's `GLOBAL_TARGET_MODEL_DIR` defaults to `shared/target-models`.
The selected model file must be present in that shared directory. Shared files
are managed by deployment maintainers, not edited from the project editor. In
the Project Detail YAML tab, the selected shared model is available for
read-only viewing and documentation downloads.
Changes to a shared model can affect every project that references it. Use a
project-local model only when the project needs a deliberate, distinct
specification.

After selecting the model, run target-model conformance validation in the
project editor. Resolve any conformance findings against the fields that the
project actually produces.

## 7. Validate the result

Rerun structural validation and confirm it reports no errors. Then run data
validation if the required files, environment variables, and external data
sources are available:

```bash
uv run python scripts/validate_project.py path/to/shapeshifter.yml \
  --workflow data --log-level ERROR
```

When a target model is configured, validate conformance as well:

```bash
uv run python scripts/validate_project.py path/to/shapeshifter.yml \
  --workflow target-model-conformance --log-level ERROR
```

Keep source fields, business keys, and target IDs separate. A foreign key's
output column is named by the parent's `public_id`, but its values are the
parent's local `system_id`.
