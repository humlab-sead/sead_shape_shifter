# Enforce Integer Type for _id Columns in Fixed Entities

## Status

- Completed
- Scope: Backend entity loading and frontend entity editor (FixedValuesGrid)
- Goal: Prevent silent merge failures caused by type mismatches in FK relationships through consistent server-side and client-side type handling

### Implemented on branch

- Backend load-time coercion is implemented through `FixedEntityTypeCoercer` and a dedicated `FixedEntityConfigMapper`.
- Backend validation is implemented in both `FixedEntityFieldsSpecification` and `FixedEntityPersistenceStrategy`.
- Optional backend `column_types` support is implemented, including allowlist validation, precedence over `_id` inference, and API/Core round-trip preservation.
- Backend load responses now include fixed-entity normalization warnings, and structured warning logs are emitted with project, entity, row, column, and value details.
- Frontend `_id` inference and strict integer parsing are implemented in `FixedValuesGrid` and its clipboard helpers.
- Frontend surfaces load-time normalization warnings in the project detail view, and incoming fixed-grid rows are normalized on load so explicit save persists corrected types.
- Dynamic-entity materialization now freezes values through a fixed-safe serialization path, normalizes pandas null-like scalars, and preserves non-default types through inferred `column_types`.
- Focused regression and unit tests are in place for backend coercion, backend validation, normalization behavior, project-load warnings, and frontend clipboard/type helpers.

### Completed in documentation

- `docs/OPERATIONS.md` documents load-time normalization warnings, logging, and explicit-save persistence behavior.
- `docs/CONFIGURATION_GUIDE.md` documents fixed-entity `_id` normalization rules and optional `column_types`.
- `docs/USER_GUIDE.md` documents the user-facing fixed-entity editing flow, warning banner, and save behavior.

### Residual follow-up outside this proposal

- Manual arbodat validation remains useful as a release confidence check, but it is no longer a blocker for the implemented scope.

## Summary

When users edit fixed-value entities via FixedValuesGrid or load them from YAML files, columns ending with `_id` can be assigned string values instead of integers. This creates type inconsistencies that cause silent Pandas merge failures during entity normalization. The fix is three-fold:

1. **Server-side**: Implement strict type coercion in the ProjectMapper when loading fixed entities from YAML, with explicit accept/reject rules, warnings for normalizations, and hard errors for invalid non-empty values.
2. **Client-side**: Implement column type inference in FixedValuesGrid to detect columns ending with `_id`, parse inputs as integers, and validate types before emitting YAML.
3. **Optional explicit schema typing**: Add backend-recognized optional `column_types` in YAML for deterministic typing where needed, without introducing new editor UX in this change.

## Problem

Fixed-value entity columns ending with `_id` represent foreign keys and must be integers. Currently, FixedValuesGrid treats all values as strings by default, allowing users to add rows with mixed types:

```yaml
method:
  columns: [system_id, method_id, ..., sead_method_group_id, ...]
  values:
    - [9, 105, null, ..., 17, null]           # integers (correct)
    - [10, 76, null, ..., 17, null]           # integers (correct)
    - [11, '53', null, ..., null, null]       # method_id is string (incorrect)
```

During entity normalization in Pandas:
- The `method_id` column becomes dtype `object` (mixed types)
- FK links try to join `method_id: '53'` (string) with parent integer IDs
- The merge silently produces no match; rows are lost or joined incorrectly
- No error is raised; the user sees incomplete results downstream

This has already occurred in `arbodat-roger/shapeshifter.yml`, where `method_id` and `sead_method_group_id` contain both integers and strings.

## Scope

**Server-side:**
- Implement a `FixedEntityTypeCoercer` in the ProjectMapper pipeline to detect `_id` columns and coerce string values to integers when loading from YAML
- Treat non-empty invalid integer values as errors (do not coerce to `null`)
- Define and implement a strict coercion policy matrix for `_id` values
- Validate row shape (`len(row) == len(columns)`) before any type coercion
- Define user-visible behavior for auto-normalization warnings and save-time rewrite semantics
- Keep type policy logic in `src` so core/domain never imports backend/application modules
- Add validation in `FixedEntityFieldsSpecification` to ensure `_id` columns contain only integers or `null`
- Update `FixedEntityPersistenceStrategy` to validate types before YAML save

**Client-side:**
- Implement type inference in FixedValuesGrid to detect `_id` columns
- Add strict integer parsing for `_id` columns (no permissive `parseInt` truncation)
- Reject invalid `_id` edits/paste with inline error state (do not silently coerce to `null`)
- Validate types on row emit (add/edit/paste) before emitting to parent component
- Add unit tests for type coercion on new rows, edits, and clipboard paste

**Schema (backend-recognized, no new UX in this proposal):**
- Add optional `column_types` support to fixed entities in project YAML
- Enforce declared types when present; otherwise fall back to inference
- Defer editor controls, badges, and advanced type-management UX to a follow-up proposal

## Non-Goals

- Type inference beyond the `_id` naming convention (date, boolean, and custom type detection are out of scope)
- Retroactive file repair: mass-rewriting or committing repaired values back to existing YAML files outside normal user save flow
- Complex schema validation (basic shape and type consistency only)

Clarification:
- In scope: runtime normalization in memory during backend load.
- Out of scope: automatic background edits/commits to existing YAML files.

## Current Backend Behavior

Fixed entities are loaded via the following flow:

1. **API Model** (`backend/app/models/entity.py`): `values` field accepts `list[list[Any]]` with no type coercion
2. **ProjectMapper** (`backend/app/mappers/project_mapper.py`): Uses `DefaultEntityConfigMapper` (no-op) for fixed entities
3. **Core Model** (`src/model.py`): `TableConfig.safe_values` provides raw values without type validation
4. **Validation** (`src/specifications/entity.py`): `FixedEntityFieldsSpecification` validates structure but not types
5. **Persistence** (`backend/app/services/project/entity_persistence_strategies.py`): `FixedEntityPersistenceStrategy` validates shape consistency but not types

**Problem**: A column named `method_id` can contain mixed integers and strings (e.g., `[105, 76, '53']`). During normalization, Pandas creates an `object` dtype column, and FK joins silently fail.

## Current Frontend Behavior

FixedValuesGrid defines a `valueParser` only for the `system_id` column:

```typescript
valueParser: isSystemId ? (params: any) => {
  const val = params.newValue
  return val !== null && val !== undefined ? parseInt(String(val), 10) : val
} : undefined,
```

All other columns, including those ending with `_id`, use the default ag-grid string handling. New rows added via the UI receive string values for all non-system_id columns.

## Proposed Design

### Part 1: Server-Side Type Coercion and Validation

#### 1.0 Strict Coercion Policy and Precedence

Policy for `_id` columns:

| Input | Result |
|---|---|
| `53` | Accept |
| `"53"` | Accept, coerce to `53`, emit warning/log |
| `""` | Coerce to `null` |
| `null` | Keep `null` |
| `"53.0"` | Reject |
| `"abc"` | Reject |
| `true` / `false` | Reject (never treat bool as int) |

Precedence and lifecycle behavior:
1. **Load-time shape validation runs first**: rows must exactly match declared columns (`len(row) == len(columns)`).
2. **Shape failures are hard errors** (no coercion attempt on malformed rows).
3. **Load-time coercion runs second** on shape-valid rows using the policy above.
4. **Coercible values** are normalized in memory and recorded as warnings.
5. **Non-coercible non-empty values** raise `FixedEntityTypeValidationError` and stop processing.
6. **Persistence validation** is defense-in-depth and must reject any invalid typed values that bypass load-time checks.
7. **File rewrite behavior**: normalized values are written to YAML only on explicit save; no background file mutation on load.
8. **User-visible feedback**: when normalization occurs, show a non-blocking warning summary and include structured backend logs.

#### 1.1 FixedEntityTypeCoercer in ProjectMapper

Create a shared coercer/type-policy module in `src/types/`:

```python
# src/types/fixed_entity_types.py

class FixedEntityTypeCoercer:
    """Coerces fixed entity values to correct types based on column naming conventions."""

    @dataclass
    class CoercionIssue:
        row_index: int
        column_index: int
        column_name: str
        raw_value: Any
        expected_type: str
        reason: str

    class FixedEntityTypeValidationError(ValueError):
        """Raised when fixed-entity type coercion finds non-empty invalid values."""

        def __init__(self, *, entity_name: str, issues: list["FixedEntityTypeCoercer.CoercionIssue"]) -> None:
            self.entity_name = entity_name
            self.issues = issues
            super().__init__(
                f"Entity '{entity_name}' has {len(issues)} invalid typed value(s) during coercion"
            )

    class FixedEntityShapeValidationError(ValueError):
        """Raised when fixed-entity rows do not match declared column count."""
    
    @staticmethod
    def infer_column_type(column_name: str) -> type:
        """
        Infer Python type from column name.
        Columns ending with '_id' are foreign keys and must be integers.
        """
        if column_name.endswith('_id'):
            return int
        return str
    
    @staticmethod
    def coerce_value(value: Any, target_type: type) -> tuple[Any, str | None]:
        """
        Coerce a value to target type.

        Returns:
            (coerced_value, error_reason)

        Rules:
        - `None` and empty string become `None`
        - Quoted integer strings (for example `"53"`) are accepted and normalized
        - Non-empty invalid integer values return an error reason
        - Bool values are rejected even though bool is a subclass of int in Python
        """
        if value is None:
            return None, None

        if isinstance(value, str) and value.strip() == "":
            return None, None

        if target_type is int:
            if isinstance(value, bool):
                return value, "invalid_integer_bool_not_allowed"

            if isinstance(value, int):
                return value, None

            if isinstance(value, str):
                if value.isdigit() or (value.startswith("-") and value[1:].isdigit()):
                    return int(value), None
                return value, "invalid_integer_format"

            # Reject floats and other non-string numeric-like values for determinism.
            if isinstance(value, float):
                return value, "invalid_integer_float_not_allowed"

            try:
                return int(value), None
            except (ValueError, TypeError):
                return value, "invalid_integer"

        return str(value), None
    
    @staticmethod
    def coerce_fixed_entity_values(
        entity_data: dict[str, Any],
        columns: list[str],
        entity_name: str,
    ) -> list[list[Any]]:
        """
        Coerce all values in a fixed entity to correct types.
        
        Args:
            entity_data: Entity configuration dict (must contain 'values' key)
            columns: List of column names
        
        Returns:
            Coerced values (list of lists with properly typed elements)
        """
        values = entity_data.get('values')
        if not values or not isinstance(values, list):
            return values

        for row_idx, row in enumerate(values):
            if len(row) != len(columns):
                raise FixedEntityTypeCoercer.FixedEntityShapeValidationError(
                    f"Entity '{entity_name}' row {row_idx} has {len(row)} values; expected {len(columns)} based on declared columns"
                )
        
        coerced = []
        issues: list[FixedEntityTypeCoercer.CoercionIssue] = []

        for row_idx, row in enumerate(values):
            coerced_row = []
            for idx, value in enumerate(row):
                col_name = columns[idx]
                target_type = FixedEntityTypeCoercer.infer_column_type(col_name)

                coerced_value, error_reason = FixedEntityTypeCoercer.coerce_value(value, target_type)
                coerced_row.append(coerced_value)

                if error_reason is not None:
                    issues.append(
                        FixedEntityTypeCoercer.CoercionIssue(
                            row_index=row_idx,
                            column_index=idx,
                            column_name=col_name,
                            raw_value=value,
                            expected_type="int",
                            reason=error_reason,
                        )
                    )

            coerced.append(coerced_row)

        if issues:
            raise FixedEntityTypeCoercer.FixedEntityTypeValidationError(entity_name=entity_name, issues=issues)
        
        return coerced
```

Warning and rewrite behavior:
- If coercion changes values without errors (for example `"53"` -> `53`), keep a structured warning list.
- Return warnings to API/UI for non-blocking display.
- Write normalized values to YAML only when the user performs save.

Integrate with a dedicated fixed-entity mapper in backend (consuming `src` policy):

```python
# In backend/app/mappers/entity_config_mapper.py

from src.types.fixed_entity_types import FixedEntityTypeCoercer

@EntityConfigMapperFactory.register_mapper("fixed")
class FixedEntityConfigMapper(EntityConfigMapper):
    """Mapper for fixed-type entities with type coercion."""
    
    def to_core(self, entity_dict: dict[str, Any], project_name: str) -> dict[str, Any]:
        """
        Coerce fixed entity values to correct types.
        """
        entity_name = entity_dict.get('name', '<unknown>')
        columns = entity_dict.get('columns', [])
        entity_dict['values'] = FixedEntityTypeCoercer.coerce_fixed_entity_values(
            entity_dict,
            columns,
            entity_name=entity_name,
        )
        return entity_dict
```

#### 1.2 Type Validation in FixedEntityFieldsSpecification

Add type checking to `src/specifications/entity.py`:

```python
# In src/specifications/entity.py, FixedEntityFieldsSpecification class

def _validate_column_types(self, values: list[list[Any]], columns: list[str], public_id: str) -> None:
    """
    Validate that _id columns contain only integers or None.
    """
    from src.types.fixed_entity_types import infer_fixed_entity_column_type
    
    for row_idx, row in enumerate(values):
        if len(row) != len(columns):
            self.add_error(
                f"Entity row {row_idx} has {len(row)} values, expected {len(columns)} to match declared columns"
            )
            continue

        for col_idx, value in enumerate(row):
            col_name = columns[col_idx]
            expected_type = infer_fixed_entity_column_type(col_name)
            
            if value is not None and expected_type is int:
                if type(value) is not int:
                    self.add_error(
                        f"Column '{col_name}' (row {row_idx}) has value '{value}' "
                        f"(type {type(value).__name__}), expected strict int or null (bool is not allowed)"
                    )

# Call from is_satisfied_by():
if not dict_rows and values:
    self._validate_column_types(values, columns, public_id)
```

#### 1.3 Type Validation in FixedEntityPersistenceStrategy

Update `backend/app/services/project/entity_persistence_strategies.py`:

```python
# In FixedEntityPersistenceStrategy

@staticmethod
def _validate_types(entity_data: dict[str, Any]) -> None:
    """Ensure all _id columns are integers before persisting to YAML."""
    columns = entity_data.get("columns", [])
    values = entity_data.get("values")
    
    if not values or not isinstance(values, list):
        return
    
    from src.types.fixed_entity_types import infer_fixed_entity_column_type

    for row_idx, row in enumerate(values):
        if len(row) != len(columns):
            raise SchemaValidationError(
                f"Entity '{entity_data.get('name', '<unknown>')}' row {row_idx}: expected {len(columns)} values, got {len(row)}"
            )
    
    for row_idx, row in enumerate(values):
        for col_idx, value in enumerate(row):
            if value is not None:
                col_name = columns[col_idx]
                expected_type = infer_fixed_entity_column_type(col_name)
                
                if expected_type is int and type(value) is not int:
                    raise SchemaValidationError(
                        f"Column '{col_name}' row {row_idx}: expected strict int, got {type(value).__name__} (bool is not allowed)"
                    )

# Call from validate_fixed_entity_shape():
@staticmethod
def _validate_fixed_entity_shape(entity_name: str, entity_data: dict[str, Any]) -> None:
    # ... existing shape validation ...
    FixedEntityPersistenceStrategy._validate_types(entity_data)
```

### Part 2: Client-Side Type Coercion and Validation

#### 2.1 Column Type Inference

Add a helper function to detect column type from naming convention:

```typescript
function inferColumnType(columnName: string): 'number' | 'string' {
  // Columns ending with '_id' are foreign keys and must be integers
  if (columnName.endsWith('_id')) return 'number'
  return 'string'
}
```

#### 2.2 valueParser for All Columns

Modify the column definition to apply type-aware parsing:

```typescript
function parseStrictInteger(value: unknown): number | null {
    if (value === null || value === undefined || value === '') return null
    const text = String(value).trim()
    if (!/^-?\d+$/.test(text)) return null
    return Number(text)
}

const columnDefs = computed<ColDef[]>(() => {
  return props.columns.map((col, index) => {
    const isSystemId = col === 'system_id'
    const isPublicId = col === props.publicId
    const columnType = inferColumnType(col)

    return {
      field: `col_${index}`,
      headerName: col,
      editable: !isSystemId,
      // ... other props ...
      valueParser: (params: any) => {
        const val = params.newValue

        if (columnType === 'number') {
                    const parsed = parseStrictInteger(val)

                    // Accept null-like values; reject malformed integers (for example "53abc", "53.9").
                    if (parsed === null && val !== null && val !== undefined && String(val).trim() !== '') {
                        setCellValidationError(index, params.node?.rowIndex, 'Expected integer ID')
                        return params.oldValue
                    }

                    clearCellValidationError(index, params.node?.rowIndex)
                    return parsed
        }

        return String(val)
      },
    }
  })
})
```

#### 2.3 Validation on Emit

When emitting `update:modelValue`, ensure types are consistent:

```typescript
function emitModelValueUpdate(rows: any[][]) {
    const errors: string[] = []

    const typedRows = rows.map((row, rowIdx) =>
        row.map((val, colIdx) => {
      const columnName = props.columns[colIdx]
            if (inferColumnType(columnName) === 'number') {
                const parsed = parseStrictInteger(val)

                if (parsed === null && val !== null && val !== undefined && String(val).trim() !== '') {
                    errors.push(`Row ${rowIdx + 1}, column ${columnName}: expected integer ID`)
                    return val
                }

                return parsed
      }
      return val
    })
  )

    if (errors.length > 0) {
        emit('validation-errors', errors)
        return
    }

  lastEmittedModelSignature.value = serializeModelValue(typedRows)
  emit('update:modelValue', typedRows)
}
```

#### 2.4 Test Coverage

Add tests in `frontend/src/components/entities/__tests__/FixedValuesGrid.test.ts` (or create if needed):

- Type coercion on cell edit: `'53'` → `53`
- Type coercion on new row: add row and verify `_id` columns default to `null` (not empty string)
- Type coercion on paste: `'105\t53'` → `105, 53`
- Non-`_id` columns remain strings: `'text'` → `'text'`
- Invalid input: `'abc'` in `_id` column is rejected (previous value retained + validation error)
- Invalid input: `'53abc'` in `_id` column is rejected (no truncation to `53`)
- Invalid input: `'53.9'` in `_id` column is rejected (no truncation to `53`)

### Part 3: Optional Explicit Schema Typing (Backend-Recognized)

#### 3.1 YAML Shape

Add optional `column_types` to fixed entities:

```yaml
method:
    type: fixed
    columns: [system_id, method_id, name, sead_method_group_id]
    column_types:
        system_id: int
        method_id: int
        name: string
        sead_method_group_id: int
    values:
        - [9, 105, "Sampling", 17]
```

Rules:
- `column_types` is optional for backward compatibility.
- When present, `column_types` is authoritative.
- When absent, inference applies (`_id` → integer, otherwise string).

Implementation boundary for this proposal:
- Backend recognizes and enforces `column_types` if provided.
- No new FixedValuesGrid controls for selecting/managing `column_types` in this change.
- Existing editor continues to operate with naming-based inference for now.
- A follow-up proposal may introduce type-management UX after core fix ships.

## Risks and Tradeoffs

**Risk: Silent conversion on edit (client-side)**
- Users may not realize strings are being coerced to integers
- **Mitigation**: Add column header hint (e.g., suffix `(integer)` for `_id` columns) and consider adding validation styling (red border for invalid input)

**Risk: Permissive integer parsing in UI**
- Using `parseInt` can incorrectly accept malformed IDs (`"53abc" -> 53`, `"53.9" -> 53`)
- **Mitigation**: Use strict integer parsing and reject malformed values with inline error state

**Risk: Ambiguous repair-vs-reject behavior**
- If coercion rules are underspecified, teams may get inconsistent behavior across load, edit, and save flows
- **Mitigation**: Adopt the strict policy matrix, enforce load-time precedence, and surface warnings/errors with row/column context

**Risk: Existing mixed-type YAML files**
- Files like `arbodat-roger/shapeshifter.yml` already have mixed types in `_id` columns
- **Mitigation**: Backend coercer normalizes values in memory on load for safe execution. Persisting repaired values to disk only happens through explicit save; bulk retroactive file cleanup remains out of scope.

**Trade-off: Tight coupling to naming convention**
- Type inference relies on `_id` suffix; different naming would not be caught
- **Justification**: SEAD schema always uses `_id` for FK columns; safe assumption for this codebase

**Trade-off: Backend coercion happens automatically without user visibility**
- Users may not realize their YAML data is being transformed
- **Mitigation**: Show warning summaries in UI, log coercions server-side, and rewrite YAML only on explicit save

**Trade-off: Explicit types add configuration overhead**
- Users must maintain `column_types` when they opt in
- **Mitigation**: Keep `column_types` optional and backend-recognized only in this change; defer UX management tooling to a follow-up proposal

## Testing and Validation

**Server-side:**
1. Unit tests for `FixedEntityTypeCoercer` policy matrix: `53`, `"53"`, `""`, `null`, `"53.0"`, `"abc"`, `true/false`
2. Unit tests for shape validation: reject rows where `len(row) != len(columns)` before coercion
3. **Normalization-boundary regression test (required):** load YAML where child FK is `"53"` and parent ID is `53`, run the actual normalization/merge path, assert FK resolves and no rows are lost
4. Integration test: Load a project YAML with mixed-type `_id` columns; verify backend coerces strings to integers
5. Integration test: Malformed rows with extra/missing cells fail with shape validation error
6. Integration test: Invalid non-empty integer input (for example `'abc'` in `_id`) fails load with actionable error message including entity name, row number, column name, original value, and expected type
7. Integration test: YAML boolean in `_id` field (for example `true`) is rejected as invalid integer
8. Test `FixedEntityFieldsSpecification` validation: reject mismatched types after valid coercion paths
9. Test `FixedEntityPersistenceStrategy` validation: reject type mismatches before YAML save
10. Integration test: Normalized values are not written to file until explicit save
11. Integration test: normalization warnings are returned to UI and logged

**Client-side:**
1. Unit tests (listed above) must pass
2. Manual test: Edit `method` entity in arbodat project, add row, verify `method_id` is integer in YAML
3. Manual test: Paste data with mixed types (integers and strings); verify all coerced to integers
4. Manual test: Enter malformed `_id` values (`53abc`, `53.9`); verify edit is rejected and error is shown
5. Regression test: Ensure non-`_id` columns still accept and preserve strings

**Integration:**
1. End-to-end test: Load arbodat project, edit fixed entity via frontend, save, reload backend; verify types are preserved
2. Verify mixed-type YAML values are normalized in memory on backend load
3. Verify mixed-type YAML is normalized in memory on load and persisted only after save

**Optional schema typing:**
1. `column_types` is honored by backend when present
2. Inference remains default when `column_types` is absent
3. YAML with `column_types` round-trips through load/save without schema loss

## Acceptance Criteria

**Server-side:**
- [x] `FixedEntityTypeCoercer` class implemented with `infer_column_type()`, `coerce_value()`, and `coerce_fixed_entity_values()` methods
- [x] `FixedEntityConfigMapper` registered for type `"fixed"` and calls coercer in `to_core()`
- [x] Core/domain code (`src/**`) does not import backend/application modules for type policy or validation
- [x] Non-empty invalid integer values never coerce to `null`; they raise `FixedEntityTypeValidationError`
- [x] Integer validation uses strict int semantics (`type(value) is int` or equivalent), excluding bool
- [x] Strict policy matrix for `_id` coercion is implemented exactly as specified
- [x] Shape validation is a hard gate: rows with extra/missing values are rejected before type coercion
- [x] `FixedEntityFieldsSpecification` includes `_validate_column_types()` to reject invalid types after coercion
- [x] `FixedEntityPersistenceStrategy` includes `_validate_types()` to ensure types are correct before YAML save
- [x] Unit tests cover policy matrix and bool/float rejection edge cases
- [x] Normalization-boundary regression test proves mixed string/int FK values no longer cause silent merge mismatch or row loss
- [x] Integration test: Load mixed-type YAML and verify backend coerces types
- [x] Coercion error messages include entity name, row number, column name, original value, expected type, and reason (sufficient for manual YAML correction)
- [x] DEBUG-level logging for coercion events (file, entity, row, column, old value, new value)
- [x] Coercion warnings are surfaced to UI and file changes are persisted only on explicit save
- [x] Materialized dynamic entities are frozen as fixed-safe values without leaking `np.nan`, `pd.NA`, `NaT`, or dtype-driven drift

**Client-side:**
- [x] `inferColumnType()` function implemented and tested
- [x] `valueParser` applied to all `_id` columns in FixedValuesGrid
- [x] Frontend uses strict integer parser for `_id` values (no permissive `parseInt` truncation)
- [x] Invalid `_id` inputs are rejected with inline validation errors (not silently converted to `null`)
- [x] Emitted rows have consistent integer types for `_id` columns
- [x] Unit tests cover: edit, add, paste, and invalid input scenarios
- [ ] Manual test passes with arbodat `method` entity

**Optional explicit schema typing (current proposal scope):**
- [x] Fixed entity schema supports optional `column_types`
- [x] Declared types override inference when present
- [x] Inference remains default when `column_types` is absent
- [x] `column_types` persists through backend load/save without loss

**Deferred to follow-up proposal:**
- [ ] FixedValuesGrid per-column type selector UX
- [ ] Type badges and conversion-summary UX
- [ ] Advanced strict/non-strict UX controls for explicit types

**Documentation:**
- [x] `docs/OPERATIONS.md` updated to document automatic type coercion behavior and logging
- [x] `docs/CONFIGURATION_GUIDE.md` updated to document fixed-entity normalization behavior and optional `column_types`
- [x] `docs/USER_GUIDE.md` updated to document fixed-entity warnings and explicit-save behavior
- [ ] Component comments updated in FixedValuesGrid clarifying type handling

## Recommended Delivery Order

1. **Backend foundation** (Phase 1):
    - Status: Completed
   - Implement `FixedEntityTypeCoercer` with all methods
    - Implement row-shape hard-gate validation (`len(row) == len(columns)`)
   - Register `FixedEntityConfigMapper` and integrate coercer
   - Add unit tests for coercer
    - Add normalization-boundary regression test for actual merge path (`"53"` child FK vs `53` parent ID)
    - Test backend coercion with mixed-type YAML and malformed row shapes

2. **Backend validation** (Phase 2):
    - Status: Completed
   - Add `_validate_column_types()` to `FixedEntityFieldsSpecification`
   - Add `_validate_types()` to `FixedEntityPersistenceStrategy`
    - Add warning/error payloads and DEBUG-level logging
   - Integration tests for validation

3. **Frontend implementation** (Phase 3):
    - Status: Completed for the implemented scope; manual arbodat validation is still pending
    - Implement `inferColumnType()`, `parseStrictInteger()`, and reject-on-invalid `valueParser` logic
   - Add test suite
   - Manual validation with arbodat data

4. **Optional schema typing hardening** (Phase 4):
    - Status: Completed for backend support; UI management remains deferred
    - Add backend tests for `column_types` precedence over inference
    - Add backend round-trip tests for YAML persistence of `column_types`
    - Document deferred UX work as a separate proposal

5. **Polish** (Phase 5):
    - Status: Completed for proposal scope; optional UX polish remains deferred
   - Update `docs/OPERATIONS.md` with coercion and logging behavior
   - Update `docs/CONFIGURATION_GUIDE.md` and `docs/USER_GUIDE.md` for fixed-entity normalization behavior
   - Materialization regression coverage added for typed/null-like value freezing
   - Optional UI hints (e.g., column headers with type annotations) remain deferred

## Implementation Handoff

Use these defaults as implementation decisions for this proposal.

### 1. Canonical Error Contract

Use one structured error format for fixed-entity type/shape failures:

```json
{
    "code": "fixed_entity_type_error",
    "entity": "method",
    "row": 3,
    "column": "method_id",
    "original_value": "abc",
    "expected_type": "int",
    "reason": "invalid_integer_format",
    "message": "Entity 'method', row 3, column 'method_id': value 'abc' is invalid; expected int."
}
```

Rules:
- For multi-error scenarios, return an `errors` array with stable per-item schema.
- Always include: `entity`, `row`, `column`, `original_value`, `expected_type`.

### 2. Normalization-Boundary Regression Test Placement

Place the required FK regression in the normalization/process integration suite (not mapper-only tests).

Recommended test path:
- `tests/integration/process/test_fixed_entity_fk_merge_regression.py`

Required scenario:
1. Child FK value is `"53"`.
2. Parent ID value is `53`.
3. Run the actual normalization pipeline.
4. Assert FK resolution is correct.
5. Assert no rows are lost.

### 3. `column_types` Allowlist Enforcement

Backend must fail fast on unsupported explicit type names.

Allowed values in this phase:
- `int`
- `string`
- `float`
- `bool`
- `date`

Unknown declared types must raise actionable validation error including:
- entity
- column
- provided type
- allowed types list

### 4. Save-Flow Semantics for Runtime Normalization

Runtime behavior:
- Normalize/coerce in memory on load.
- Do not modify project files on load/validate/open.

Persistence behavior:
- Write normalized values only on explicit save action.

Required verification:
1. Load-only integration test confirms file content is unchanged.
2. Explicit-save integration test confirms normalized values are persisted.

## Final Recommendation

Implement type inference and validation on both backend and frontend to enforce integer types for `_id` columns. This prevents silent merge failures and ensures YAML data consistency:

- **Backend coercion** (ProjectMapper) normalizes mixed-type data in memory on load, preventing downstream failures
- **Backend validation** (Specification + Persistence) ensures types remain valid throughout the application lifecycle
- **Frontend type enforcement** (FixedValuesGrid) prevents users from entering incorrect types in the UI
- **Optional explicit schema typing** (`column_types` in YAML) provides deterministic typing where inference is insufficient, without blocking urgent fixes on new UI work

The implemented scope is complete. Any remaining work is follow-up UX or manual release validation rather than unfinished proposal scope.
