# Bug Fix: env2dict Corruption and Directive Resolution

## Issue Summary

Two critical bugs are corrupting YAML project files:

1. **env2dict off-by-one error**: Removes first character from keys when prefix is empty
2. **Resolved directives saved**: @value: directives are resolved and saved back to YAML

## Bug Details

### Bug #1: env2dict Slice

**File:** `src/utility.py:389`

**Current Code:**
```python
def env2dict(prefix: str, data: dict[str, str] | None = None, lower_key: bool = True) -> dict[str, str]:
    """Loads environment variables starting with prefix into."""
    if data is None:
        data = {}
    if not prefix:
        return data  # Early return, but this line is AFTER the bug check
    if lower_key:
        prefix = prefix.lower()
    for key, value in os.environ.items():
        if lower_key:
            key = key.lower()
        if key.startswith(prefix):
            dotset(data, key[len(prefix) + 1 :].replace("_", ":"), value)  # BUG HERE
    return data
```

**Problem:**
- When `prefix = ""`, `key.startswith("")` is always `True` for all keys
- `key[len("") + 1:]` = `key[1:]` removes first character
- The early return on line 5 doesn't help because empty string passes the check

**Fix:**
```python
def env2dict(prefix: str, data: dict[str, str] | None = None, lower_key: bool = True) -> dict[str, str]:
    """Loads environment variables starting with prefix into."""
    if data is None:
        data = {}
    if not prefix:  # Already handles empty prefix
        return data
    if lower_key:
        prefix = prefix.lower()
    for key, value in os.environ.items():
        if lower_key:
            key = key.lower()
        if key.startswith(prefix):
            # FIX: Only slice if there's actually a separator
            # Expected format: PREFIX_KEY_NAME
            if key.startswith(prefix + "_"):
                dotset(data, key[len(prefix) + 1:].replace("_", ":"), value)
            else:
                logger.warning(f"Skipping env var '{key}' - starts with prefix '{prefix}' but missing underscore separator")
    return data
```

### Bug #2: Config Resolution Before Save

**Investigation:** Need to find where `Config.resolve_references()` or `project.resolve()` is being called before `ProjectMapper.to_core_dict()`.

**Expected Flow:**
1. Load YAML → API Project (directives preserved)
2. User edits → API Project (directives still preserved)
3. Save → `to_core_dict(API Project)` → YAML (directives preserved)

**Actual Flow (buggy):**
1. Load YAML → API Project  
2. Somewhere: `project.resolve()` or `Config.resolve_references()` called
3. Save → `to_core_dict(API Project with resolved values)` → YAML (directives lost!)

**Search for:**
- Any code path that calls `resolve()` on a project and then saves it
- ValidationService that calls `Config.resolve_references()` before validation
- Check if validation results are being saved back

## Testing

**Test the fix:**

```python
# Test env2dict with empty prefix
def test_env2dict_empty_prefix():
    os.environ['TEST_VAR'] = 'value'
    result = env2dict("", {})
    assert result == {}  # Should return empty, not corrupt

# Test env2dict with proper prefix
def test_env2dict_with_prefix():
    os.environ['CONFIG_DB_HOST'] = 'localhost'
    result = env2dict("CONFIG", {})
    assert result == {'db': {'host': 'localhost'}}

# Test env2dict without separator
def test_env2dict_missing_separator():
    os.environ['CONFIGVALUE'] = 'bad'  # No underscore
    result = env2dict("CONFIG", {})
    assert result == {}  # Should skip, not corrupt
```

## Recovery Steps

1. **Restore from backup:** Use project backups to recover uncorrupted YAML
2. **Apply fixes** to `src/utility.py` and investigate resolve() calls
3. **Add validation** to prevent saving resolved configs
4. **Add test coverage** for env2dict edge cases

## Related Files

- `src/utility.py:376-391` - env2dict function
- `src/configuration/config.py:218` - env2dict invocation
- `backend/app/services/project_service.py:285` - save flow
- `backend/app/mappers/project_mapper.py:104-157` - to_core_dict
- `backend/app/services/validation_service.py:135` - Config.resolve_references call

## Prevention

1. **Add assertion** in `YamlService.save()` to detect resolved values:
   ```python
   def save(self, data: dict[str, Any], filename: Path, ...):
       # Defensive check: warn if directives are missing
       unresolved = Config.find_unresolved_directives(data)
       if not unresolved:
           logger.warning(f"Saving config with no @value: directives - may be incorrectly resolved!")
   ```

2. **Add test** to ensure save preserves directives:
   ```python
   def test_save_preserves_directives():
       project = load_project_with_directives()
       saved = save_project(project)
       reloaded = load_project(saved)
       # Should still have @value: directives
       assert "@value:" in str(reloaded)
   ```
