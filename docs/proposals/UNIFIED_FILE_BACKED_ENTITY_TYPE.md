# Proposal: Unified File-Backed Entity Type with Format Auto-Detection

## Status

- Proposed change
- Scope: Core (loaders, model), backend (validation, API model), configuration guide, existing project YAMLs
- Goal: Replace three separate `type:` values with a single `type: file` and a `format` option

## Summary

Replace the three file-backed entity types (`csv`, `xlsx`, `openpyxl`) with a single `type: file` and an optional `options.format` specifier. When `format` is omitted, auto-detect from the filename extension. This removes implementation coupling from the entity type hierarchy and simplifies configuration for users.

## Problem

Shape Shifter currently has three separate registered loader keys that represent the same conceptual thing — a file-backed reference entity:

| Type key | Loader class | Registered aliases |
|---|---|---|
| `csv` | `CsvLoader` | `csv`, `tsv` |
| `xlsx` | `PandasLoader` | `xlsx`, `xls` |
| `openpyxl` | `OpenPyxlLoader` | `openpyxl` |

All three return `LoaderType.FILE` and all share the same structural role. The distinction between them is purely about file format and parsing backend, yet the type key is the only mechanism to specify it. This has several consequences:

- Users must know implementation names (`openpyxl`, `xlsx`) rather than just `file` + filename.
- The two Excel keys (`xlsx`, `openpyxl`) differ only in parser capabilities. In practice, all real projects use `openpyxl` — the `xlsx` (pandas) type has no users.
- Format cannot be inferred from the filename; users must specify it explicitly even when the extension makes it unambiguous.
- The `TableConfig.type` Literal in `model.py` enumerates implementation names as first-class types, coupling the API model to internal class choices.

## Scope

- Introduce `type: file` as the canonical file-backed entity type
- Introduce `options.format` as the explicit format specifier
- Implement auto-detection when `format` is absent, based on filename extension
- Deprecate the legacy type keys (`csv`, `tsv`, `xlsx`, `xls`, `openpyxl`) with backward compatibility maintained
- Update `TableConfig.type` Literal to include `"file"`
- Update `DriverSchema` to reflect the unified type
- Update the configuration guide

## Non-Goals

- Merging the underlying loader class implementations (the dispatch can remain as internal logic)
- Removing legacy type support in the same release (that is a follow-up migration)
- Supporting format detection from file content (magic bytes) — extension-based is sufficient

## Current Behavior

Entity types are mapped directly to `DataLoaders` registry keys:

```python
# src/normalizer.py
if table_cfg.type and table_cfg.type in DataLoaders.items:
    return DataLoaders.get(key=table_cfg.type)(data_source=None)
```

The `type` field appears in YAML and is validated against the Literal in `TableConfig`:

```python
# src/model.py
@property
def type(self) -> Literal["entity", "sql", "fixed", "csv", "xlsx", "openpyxl", "merged"] | None:
    return self.entity_cfg.get("type", None)
```

Typical YAML:
```yaml
entities:
  datasheet:
    type: openpyxl
    options:
      filename: data.xlsx
      location: global
      sheet_name: Sheet1
      range: A1:H30
```

## Proposed Design

### YAML — new canonical form

```yaml
entities:
  datasheet:
    type: file
    options:
      filename: data.xlsx          # extension → openpyxl (auto-detected)
      location: global
      sheet_name: Sheet1
      range: A1:H30

  measurements:
    type: file
    options:
      filename: data.csv           # extension → csv (auto-detected)
      delimiter: ";"

  lookup:
    type: file
    options:
      filename: data.xlsx
      format: xlsx                 # explicit override (uses PandasLoader)
      sheet_name: Lookup
```

### Auto-detection rules

| Extension | Resolved format |
|---|---|
| `.csv` | `csv` |
| `.tsv` | `tsv` |
| `.xlsx`, `.xls` | `openpyxl` (preferred implementation) |
| anything else + no `format` | error: format must be explicit |

Auto-detection uses the filename as it appears in `options.filename` after env-var substitution.

### Loader resolution

The `resolve_loader()` function in `normalizer.py` gains a new branch:

```python
if table_cfg.type == "file":
    fmt = table_cfg.options.get("format") or _detect_format(table_cfg.options.get("filename", ""))
    return DataLoaders.get(key=fmt)(data_source=None)
```

The existing registry keys (`csv`, `xlsx`, `openpyxl`, …) are unchanged internally; `type: file` is a routing alias above them.

### `DriverSchema`

A single unified `DriverSchema` is registered for `"file"`:

```python
DriverSchema(
    driver="file",
    display_name="File",
    category="file",
    fields=[
        FieldMetadata(name="filename",        type="file_path", required=True, extensions=["csv","tsv","xlsx","xls"]),
        FieldMetadata(name="format",          type="enum",      required=False, options=["csv","tsv","xlsx","xls","openpyxl"], description="Auto-detected from extension if omitted"),
        FieldMetadata(name="location",        type="enum",      required=False, options=["local","global"]),
        FieldMetadata(name="sheet_name",      type="string",    required=False, description="Excel only"),
        FieldMetadata(name="range",           type="string",    required=False, placeholder="A1:H30", description="openpyxl only"),
        FieldMetadata(name="delimiter",       type="string",    required=False, default=",", description="CSV/TSV only"),
        FieldMetadata(name="encoding",        type="string",    required=False, default="utf-8", description="CSV/TSV only"),
        FieldMetadata(name="sanitize_header", type="boolean",   required=False, default=True, description="Excel only"),
    ]
)
```

Format-specific options are still silently ignored when not applicable (existing behavior).

### Model change

`TableConfig.type` Literal is extended:

```python
Literal["entity", "sql", "fixed", "csv", "xlsx", "openpyxl", "merged", "file"]
```

Legacy values are retained in the Literal during the deprecation window.

### Deprecation

When `resolve_loader()` encounters a legacy file type key, it logs a deprecation warning:

```
DeprecationWarning: entity "datasheet": type "openpyxl" is deprecated — use type: file instead
```

No behavior change; the loader resolves identically.

## Alternatives Considered

**Keep the current design**: Rejected. The problem compounds as new loaders are added. It also prevents the clean auto-detect UX that makes simple configurations genuinely simpler.

**Use `format` as the only type discriminator (remove `type: file` entirely)**: Rejected. `type:` is a fundamental field used for branching throughout the pipeline. Keeping a named `file` type preserves that structure.

**Merge `PandasLoader` and `OpenPyxlLoader` into one class**: Not necessary for this proposal. The dispatch can remain internal. This can be addressed separately.

## Risks and Tradeoffs

- **Migration burden**: All existing project YAMLs use `type: openpyxl`. Until the legacy keys are removed (follow-up), there is no forced migration, lowering short-term risk.
- **Auto-detect ambiguity**: `.xlsx` files could map to either Excel loader. Choosing `openpyxl` as the default is consistent with observed usage, but makes the `xlsx` (PandasLoader) type effectively unreachable without an explicit `format: xlsx`. This is acceptable given that no real projects use the pandas loader.
- **Mixed DriverSchema**: A single schema that lists format-conditional options may confuse the frontend editor. This is an existing UX limitation (all options shown regardless of format) that can be addressed separately with schema-level `applicable_when` metadata.

## Testing and Validation

- `type: file` with auto-detectable extensions loads correctly via the expected backend loader
- `type: file` with `format:` override routes to the correct loader irrespective of extension
- Unknown extension without explicit `format` raises a clear error
- Legacy type keys still resolve and emit a deprecation warning
- Existing project YAMLs remain valid without modification
- Auto-detection is deterministic and tested with parametric cases

## Acceptance Criteria

- `type: file` is valid in YAML and the configuration guide
- `options.format` is optional; auto-detection works for `.csv`, `.tsv`, `.xlsx`, `.xls`
- All five existing legacy keys continue to load data correctly (no regression)
- Legacy keys emit a `DeprecationWarning` in logs
- `DriverSchema` for `"file"` is available via `DriverSchemaRegistry.all()`
- At least one real project YAML is migrated as a reference example

## Recommended Delivery Order

1. Implement `_detect_format()` helper and update `resolve_loader()` to handle `type: file`
2. Add `"file"` to `TableConfig.type` Literal and backend API model
3. Register the unified `DriverSchema` for `"file"` in `FileLoader` (or a new thin `UnifiedFileLoader` stub)
4. Add deprecation warnings for legacy file type keys
5. Update the configuration guide
6. Migrate at least one project YAML as a reference; leave the rest for a bulk migration task

## Open Questions

- Should auto-detect default `.xlsx` files to `openpyxl` permanently, or should the default change if `PandasLoader` gains parity (e.g., `range` support)?
- Is there value in supporting `format: auto` as an explicit value (equivalent to omitting `format`), or is the absence of the key sufficient?

## Final Recommendation

Adopt `type: file` with `options.format` and auto-detection. The change is low-risk during the deprecation window and cleans up a structural issue that will otherwise grow. The implementation is small and self-contained; the main work is updating the configuration guide and migrating project YAMLs at an appropriate time.
