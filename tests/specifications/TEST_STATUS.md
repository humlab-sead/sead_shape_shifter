# Specification Tests - Summary

## Tests Created

Comprehensive test suites have been created for all specification modules:

- `tests/specifications/test_base.py` - ✅ 31 tests passing
- `tests/specifications/test_fields.py` - Needs fixes (logic inversion)
- `tests/specifications/test_entity.py` - Needs fixes (check key names)
- `tests/specifications/test_foreign_key.py` - Needs fixes (ForeignKeyConfig API)
- `tests/specifications/test_project.py` - Mostly passing (2 failures)

## Issues to Fix

### 1. Field Validator Logic Inversion

The `rule_predicate` method returns `True` when validation PASSES, but many validators in `fields.py` have inverted logic.

**Example from `IsEmptyFieldValidator`:**
```python
# Current (incorrect):
def rule_predicate(self, target_cfg: dict[str, Any], entity_name: str, field: str, **kwargs) -> bool:
    return dotget(target_cfg, field) not in (None, "", [], {})  # Returns True when NOT empty

# Should be:
def rule_predicate(self, target_cfg: dict[str, Any], entity_name: str, field: str, **kwargs) -> bool:
    return dotget(target_cfg, field) in (None, "", [], {})  # Returns True when empty (valid)
```

**Affected validators:**
- `IsEmptyFieldValidator`
- `FieldIsStringListValidator`  
- `FieldIsNotEmptyStringValidator`
- `FieldIsNonEmptyValidator`
- `FieldTypeValidator`
- `EndsWithIdValidator`
- `IsOfCategoricalValuesValidator`

### 2. Entity Specification Check Keys

The entity specifications use incorrect field validator keys:

**In `entity.py`:**
```python
# Current (incorrect):
self.check_fields(entity_name, ["columns", "keys"], "field_exists/E")  # Wrong key

# Should be:
self.check_fields(entity_name, ["columns", "keys"], "exists/E")  # Correct key
```

**Affected check keys:**
- `field_exists` → `exists`
- `is_not_empty` → `not_empty`
- `is_string_list` → `string_list`
- `is_empty` → `is_empty` (correct)

### 3. ForeignKeyConfig API

The `ForeignKeyConfig` model uses `entity` not `remote_entity`:

```python
# Test code (incorrect):
fk_cfg = ForeignKeyConfig(local_entity="...", remote_entity="...", ...)

# Should be:
fk_cfg = ForeignKeyConfig(local_entity="...", entity="...", ...)
```

### 4. FieldTypeValidator Error Handling

The `FieldTypeValidator.rule_fail` method crashes when `expected_types` is empty or None:

```python
# Current (crashes):
expected_type_names: str = ", ".join([t.__name__ for t in expected_types])

# Should be:
expected_types = expected_types or ()
expected_type_names: str = ", ".join([t.__name__ for t in expected_types]) if expected_types else "unknown"
```

## Running Tests

```bash
# Run all specification tests
uv run pytest tests/specifications/ -v

# Run specific test file
uv run pytest tests/specifications/test_base.py -v

# Run with coverage
uv run pytest tests/specifications/ --cov=src/specifications --cov-report=term-missing
```

## Test Coverage

- **Base classes**: 100% (31/31 passing)
- **Field validators**: 0% (needs logic fixes)
- **Entity specifications**: 30% (needs check key fixes)
- **Foreign key specs**: 0% (needs API fixes)
- **Project specs**: 90% (2 failures)

## Next Steps

1. Fix `rule_predicate` logic in all field validators
2. Update entity.py to use correct check keys
3. Fix foreign key test API calls
4. Add missing edge cases
5. Achieve 100% test coverage
