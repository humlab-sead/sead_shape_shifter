# Adding New Validators - Quick Reference

This guide shows how to extend the specification system with custom validators.

## Adding a New Field Validator

Field validators check individual fields within entity configurations.

### Step 1: Create the Validator Class

Add to `src/specifications/fields.py`:

```python
@FIELD_VALIDATORS.register(key="my_custom_check")
class MyCustomFieldValidator(FieldValidator):
    """Validator to check [describe what it validates].
    
    Requires 'custom_param' kwarg for [describe parameter].
    Fails if [describe failure condition].
    """

    def rule_predicate(self, target_cfg: dict[str, Any], entity_name: str, field: str, **kwargs) -> bool:
        """Return True if validation should FAIL, False if it passes."""
        value = dotget(target_cfg, field)
        custom_param = kwargs.get("custom_param", "default_value")
        
        # Return True to trigger failure
        return value != custom_param

    def rule_fail(self, target_cfg: dict[str, Any], entity_name: str, field: str, **kwargs) -> None:
        """Handle validation failure (log error or warning)."""
        custom_param = kwargs.get("custom_param", "default_value")
        self.rule_handler(
            f"Entity '{entity_name}': Field '{field}' must equal '{custom_param}'. {kwargs.get('message', '')}",
            entity=entity_name,
            column=field,
        )
```

### Step 2: Use in Specifications

Use the validator in any specification via `check_fields()`:

```python
class MyEntitySpecification(ProjectSpecification):
    def is_satisfied_by(self, *, entity_name: str = "unknown", **kwargs) -> bool:
        self.clear()
        
        # Basic usage with error severity
        self.check_fields(entity_name, ["my_field"], "my_custom_check/E")
        
        # With custom parameters
        self.check_fields(
            entity_name, 
            ["my_field"], 
            "my_custom_check/W",
            custom_param="expected_value",
            message="Custom error message"
        )
        
        return not self.has_errors()
```

### Severity Levels

- `/E` - Error (validation fails)
- `/W` - Warning (validation passes with warning)

### Available Utility Functions

```python
from src.utility import dotget, dotexists

# Get nested value (returns None if not found)
value = dotget(config, "path.to.field")

# Check if nested path exists (returns bool)
exists = dotexists(config, "path.to.field")
```

## Adding a New Entity-Level Specification

Entity-level specifications validate entire entity configurations.

### Step 1: Create the Specification Class

Add to `src/specifications/entity.py`:

```python
class MyEntitySpecification(ProjectSpecification):
    """Validates [describe what aspect of entities this validates]."""

    def is_satisfied_by(self, *, entity_name: str = "unknown", **kwargs) -> bool:
        """Check that [describe validation logic]."""
        self.clear()
        
        entity_cfg: dict[str, Any] = self.get_entity_cfg(entity_name)
        
        # Perform validation
        if some_condition:
            self.add_error("Error message", entity=entity_name, field="field_name")
        
        if some_warning_condition:
            self.add_warning("Warning message", entity=entity_name)
        
        return not self.has_errors()
```

### Step 2: Register in EntitySpecification

Add to the `get_specifications()` method in `EntitySpecification`:

```python
def get_specifications(self) -> list[ProjectSpecification]:
    return [
        EntityFieldsSpecification(self.project_cfg),
        # ... existing specifications ...
        MyEntitySpecification(self.project_cfg),  # Add here
    ]
```

## Adding a New Project-Level Specification

Project-level specifications validate the entire project configuration.

### Step 1: Create the Specification Class

Add to `src/specifications/project.py`:

```python
class MyProjectSpecification(ProjectSpecification):
    """Validates [describe what aspect of project config this validates]."""

    def is_satisfied_by(self, **kwargs) -> bool:
        """Check that [describe validation logic]."""
        self.clear()
        
        entities_config = self.project_cfg.get("entities", {})
        options = self.project_cfg.get("options", {})
        
        # Validate across multiple entities
        for entity_name, entity_data in entities_config.items():
            if some_condition:
                self.add_error("Error message", entity=entity_name)
        
        return not self.has_errors()
```

### Step 2: Register in CompositeProjectSpecification

Add to the `get_default_specifications()` method:

```python
def get_default_specifications(self) -> list[ProjectSpecification]:
    return [
        EntitiesSpecification(self.project_cfg),
        CircularDependencySpecification(self.project_cfg),
        DataSourceExistsSpecification(self.project_cfg),
        MyProjectSpecification(self.project_cfg),  # Add here
    ]
```

## Testing Your Validator

### Unit Test Template

Add to `tests/test_specifications.py` (or create new test file):

```python
import pytest
from src.specifications.fields import MyCustomFieldValidator

class TestMyCustomFieldValidator:
    """Test suite for MyCustomFieldValidator."""

    def test_validator_passes_when_condition_met(self):
        """Test that validator passes when field meets condition."""
        config = {"my_field": "expected_value"}
        validator = MyCustomFieldValidator({}, severity="E")
        
        validator.is_satisfied_by_field(
            entity_name="test_entity",
            field="my_field",
            target_cfg=config,
            custom_param="expected_value"
        )
        
        assert len(validator.errors) == 0

    def test_validator_fails_when_condition_not_met(self):
        """Test that validator fails when field doesn't meet condition."""
        config = {"my_field": "wrong_value"}
        validator = MyCustomFieldValidator({}, severity="E")
        
        validator.is_satisfied_by_field(
            entity_name="test_entity",
            field="my_field",
            target_cfg=config,
            custom_param="expected_value"
        )
        
        assert len(validator.errors) == 1
        assert "must equal 'expected_value'" in str(validator.errors[0])

    def test_validator_warning_severity(self):
        """Test that validator generates warnings instead of errors."""
        config = {"my_field": "wrong_value"}
        validator = MyCustomFieldValidator({}, severity="W")
        
        validator.is_satisfied_by_field(
            entity_name="test_entity",
            field="my_field",
            target_cfg=config,
            custom_param="expected_value"
        )
        
        assert len(validator.errors) == 0
        assert len(validator.warnings) == 1
```

### Integration Test Template

```python
def test_my_specification_in_composite():
    """Test that custom specification integrates with composite."""
    from src.specifications import CompositeProjectSpecification
    
    project_cfg = {
        "entities": {
            "test_entity": {
                "my_field": "wrong_value",
                # ... other fields ...
            }
        }
    }
    
    validator = CompositeProjectSpecification(project_cfg)
    result = validator.is_satisfied_by()
    
    assert not result  # Should fail
    assert len(validator.errors) > 0
```

## Common Patterns

### Checking Multiple Fields

```python
def is_satisfied_by(self, *, entity_name: str = "unknown", **kwargs) -> bool:
    self.clear()
    
    # Check multiple fields with same validator
    self.check_fields(entity_name, ["field1", "field2", "field3"], "exists/E")
    
    # Chain multiple validators
    self.check_fields(entity_name, ["field1"], "exists/E,not_empty/E,of_type/E", expected_types=(str,))
    
    return not self.has_errors()
```

### Custom Validation Logic

```python
def is_satisfied_by(self, *, entity_name: str = "unknown", **kwargs) -> bool:
    self.clear()
    entity_cfg = self.get_entity_cfg(entity_name)
    
    # Custom validation that can't use field validators
    value1 = entity_cfg.get("field1")
    value2 = entity_cfg.get("field2")
    
    if value1 and value2 and value1 > value2:
        self.add_error(
            f"field1 ({value1}) must be less than field2 ({value2})",
            entity=entity_name,
            field1=value1,
            field2=value2
        )
    
    return not self.has_errors()
```

### Accessing Other Entities

```python
def is_satisfied_by(self, *, entity_name: str = "unknown", **kwargs) -> bool:
    self.clear()
    entity_cfg = self.get_entity_cfg(entity_name)
    
    # Check if referenced entity exists
    referenced_entity = entity_cfg.get("references")
    if referenced_entity and not self.exists(referenced_entity):
        self.add_error(
            f"References non-existent entity '{referenced_entity}'",
            entity=entity_name,
            referenced_entity=referenced_entity
        )
    
    return not self.has_errors()
```

## Best Practices

1. **Clear Error Messages**: Include entity name, field name, and what went wrong
2. **Document Requirements**: Use docstrings to explain what kwargs are needed
3. **Use Existing Validators**: Combine field validators with `check_fields()` when possible
4. **Test Edge Cases**: Empty configs, missing fields, None values, etc.
5. **Fail Fast**: Return early when validation fails
6. **Consistent Naming**: Use `*Specification` suffix for specifications, `*Validator` for validators
7. **Single Responsibility**: Each validator should check one thing well

## Registry Keys Convention

Field validator keys should be:
- Lowercase with underscores: `my_custom_check`
- Descriptive: `ends_with_id` not `check_id`
- Action-oriented: `is_empty`, `exists`, `not_empty`

## Error Message Template

```python
f"Entity '{entity_name}': Field '{field}' {description of problem}. {kwargs.get('message', '')}"
```

## Documentation Updates

After adding a validator, update:
1. `RULES.md` - Add validation rule description
2. `CONFIGURATION_GUIDE.md` - Add configuration examples
3. `__init__.py` - Export new public specifications
4. Test files - Add comprehensive test coverage
