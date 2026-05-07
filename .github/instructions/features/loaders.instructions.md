---
applyTo: "src/loaders/**,backend/app/services/data_source*,backend/app/services/schema*,tests/loaders/**"
---

# Loaders – AI Coding Instructions

## All Loaders Are Async

Every `DataLoader` subclass must implement:
```python
async def load(self, entity_name: str, table_cfg: "TableConfig") -> pd.DataFrame: ...
async def test_connection(self) -> ConnectTestResult: ...
```

Never make these synchronous. Do not call `asyncio.run()` inside a loader.

## `DriverSchema` on the Class

Each loader declares its configuration schema as a `ClassVar`:
```python
class MyLoader(DataLoader):
    schema: ClassVar[DriverSchema] = DriverSchema(
        driver="my_driver",
        display_name="My Driver",
        description="...",
        fields=[FieldMetadata(name="host", type="string", required=True), ...],
        category="database",  # or "file"
    )
```

- `schema` must be a `ClassVar` — not an instance attribute.
- `DriverSchema.fields` is a `list[FieldMetadata]` — each field has `name`, `type`, `required`, `default`, `description`.
- `FieldMetadata.type` must be one of: `"string"`, `"integer"`, `"boolean"`, `"password"`, `"file_path"`.
- `"file_path"` fields should specify `extensions` (e.g. `["xlsx", "csv"]`).

## Loader Registry

- Register with `@DataLoaders.register(key="<driver_key>")`.
- `ShapeShifter.resolve_loader()` dispatches by `data_source.driver` — the `key` must match the driver name in YAML.
- `DataLoaders.get(key)` returns the loader class; instantiate with `(data_source=data_source)`.

## UCanAccess (MS Access)

- `init_jvm_for_ucanaccess(ucanaccess_dir)` must be called **once** at application startup — JPype cannot restart the JVM.
- Call it before any `UCanAccessLoader` is instantiated.
- JAR files are loaded from `lib/ucanaccess/` — see `scripts/install-uncanccess.sh` for setup.
- All UCanAccess operations use `jaydebeapi` over the JDBC bridge — SQL syntax is MS Access SQL, not PostgreSQL.

## Local File Resolution

- `location: local` in `options` triggers relative path resolution in `ShapeShifter._resolve_project_local_file_options()`.
- The loader itself does not resolve relative paths — the normalizer rewrites the path before calling `load()`.

## `ConnectTestResult`

Returned by `test_connection()`. Must always be returned — never raise on connection failure:
```python
return ConnectTestResult(success=False, message=str(e), connection_time_ms=0, metadata={})
```

## Common Mistakes

- Making `load()` synchronous — breaks the async pipeline.
- Putting `schema` as an instance variable instead of `ClassVar`.
- Calling `init_jvm_for_ucanaccess()` inside `load()` — JVM init belongs at startup.
- Registering a loader with a key that doesn't match the YAML `driver` name.
- Raising exceptions from `test_connection()` instead of returning `ConnectTestResult(success=False, ...)`.
- Using PostgreSQL SQL syntax in UCanAccess queries.

## Testing Expectations

- Mock `DataSourceConfig` and `TableConfig` — do not hit real databases.
- Test `get_schema()` returns a valid `DriverSchema` with required fields.
- Test `load()` with a mock connection that returns a DataFrame.
- Test `test_connection()` returns `ConnectTestResult` on both success and failure.
- Use `pytest.mark.asyncio` for all tests.
