---
description: "Use when editing mappers between API and Core models, or code that resolves @include:, @value:, @load: or ${ENV_VAR} directives in project configuration."
applyTo: "backend/app/mappers/**,backend/tests/mappers/**"
---
# Mappers and Directives

## Where Directives Are Resolved

- YAML files and API models keep `@include:`, `@value:`, `@load:` and `${ENV_VAR}` as written. Core processing needs resolved values.
- `ProjectMapper.to_core(api_project)` is the entry point for converting a project from API to Core. It builds the Core dict, resolves file paths from each entity's `location`, and resolves directives with the allowed directories and environment variables from `settings`. Do not convert projects any other way.
- Do not add new calls that resolve directives elsewhere. Existing calls that you may meet:
  - `ValidationService.validate_project()` calls `resolve_directives()` on a project dict before structural validation.
  - `ShapeShiftService` calls `project.clone().resolve(strict=True, ...)` before normalizing a Core project.
  - Data sources do not go through `ProjectMapper`. `DataSourceMapper.to_core_config()` checks them against `data_source_policy`, which resolves their environment variables.

## Never Save a Resolved Project

Conversion to Core is one-way. Do not pass the `cfg` of a project returned by `to_core()` to `to_api_config()` and save the result: the saved YAML would contain resolved values in place of the directives, including values read from environment variables.

To change a saved project, edit the API `Project` returned by `ProjectService.load_project()` and save that object. Use the Core project only to read or compute.

## ProjectMapper Methods

| Method | Direction | Directives |
|--------|-----------|------------|
| `to_api_config(cfg_dict, name, filename)` | Parsed YAML dict to API `Project` | Keeps them |
| `to_core_dict(api_config)` | API `Project` to dict, used when saving YAML | Keeps them |
| `to_core(api_config, validate_mapping_sidecar=True)` | API `Project` to `ShapeShiftProject` | Resolves them |

- The project name comes from the file name. `metadata.name` in the YAML is ignored.
- Entity fields come from the Pydantic `Entity` model. Do not add hardcoded field lists to the mapper.
- Keep the YAML sparse: do not write fields that were never set, or default values such as `check_column_names: true`.
- `ProjectMapper._api_entity_to_dict()` removes the API-only `name` field from each entity.

## Other Mappers

- Type-specific entity conversions (file paths, fixed entities) belong in `entity_config_mapper.py`. Add a subclass of `EntityConfigMapper` and select it in `EntityConfigMapperFactory`.
- Convert API project names (`a:b`) and filesystem paths (`a/b`) with `ProjectNameMapper`.
- Convert Core issues to API `ValidationError` with `ValidationMapper`.
- Core (`src/`) must not import a mapper or an API model.

## Testing

- Tests are in `backend/tests/mappers/`. Directive and environment variable resolution tests are also in `backend/tests/test_env_var_resolution.py`.
- When you change a conversion, test that directives are unchanged after `to_api_config()` and `to_core_dict()`, and resolved after `to_core()`.
