# Add Validator Prompt

Create new constraint validator or data validator following Shape Shifter patterns.

## Prompt Template

```
Create a {VALIDATOR_TYPE} validator for {VALIDATION_PURPOSE}:

### Validator Type
Choose one:
- **Constraint Validator** - Config-level validation (pre/post-merge stages)
- **Data Validator** - Data-level validation (DataFrame content)

---

## For Constraint Validator

### 1. Create Validator Class (`src/constraints.py`)
```python
from src.constraints import ConstraintValidator, Validators

@Validators.register(key="{validator_key}", stage="{pre-merge|post-merge}")
class {ValidatorName}(ConstraintValidator):
    """
    {DESCRIPTION}
    
    Validates: {WHAT_IT_VALIDATES}
    Stage: {WHEN_IT_RUNS}
    """
    
    def validate(
        self,
        config: dict[str, Any],
        entity_name: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Validate {WHAT}.
        
        Args:
            config: Entity configuration or full project config
            entity_name: Entity name (None if project-level)
        
        Returns:
            List of validation issues with structure:
            {
                "severity": "error|warning|info",
                "entity": entity_name,
                "field": field_name,
                "message": "Description",
                "code": "ERROR_CODE",
                "suggestion": "How to fix"
            }
        """
        issues = []
        
        # Validation logic here
        
        return issues
```

### 2. Choose Stage
- **pre-merge**: Validates before entity merge with inherited config
- **post-merge**: Validates after full entity config resolution

### 3. Add Tests (`tests/test_constraints.py`)
```python
async def test_{validator_key}_validator():
    """Test {validator_name} validator."""
    config = {
        # Test configuration
    }
    
    validator = {ValidatorName}()
    issues = validator.validate(config, entity_name="test_entity")
    
    # Assertions
    assert len(issues) == {expected_count}
    assert issues[0]["code"] == "{ERROR_CODE}"
```

---

## For Data Validator

### 1. Create Pure Domain Validator (`src/validators/data_validators.py`)
```python
from dataclasses import dataclass
import pandas as pd

@dataclass
class ValidationIssue:
    """Domain representation of validation issue."""
    severity: str  # "error", "warning", "info"
    entity: str | None
    field: str | None
    message: str
    code: str
    suggestion: str | None = None

class {ValidatorName}:
    """
    {DESCRIPTION}
    
    Pure validator - receives DataFrames, returns ValidationIssues.
    No infrastructure dependencies.
    """
    
    @staticmethod
    def validate(
        df: pd.DataFrame,
        entity_config: dict[str, Any],
        entity_name: str
    ) -> list[ValidationIssue]:
        """
        Validate {WHAT}.
        
        Args:
            df: DataFrame to validate
            entity_config: Entity configuration (resolved)
            entity_name: Entity name for error messages
        
        Returns:
            List of ValidationIssue objects
        """
        issues = []
        
        # Validation logic here
        
        return issues
```

### 2. Update Orchestrator (`backend/app/validators/data_validation_orchestrator.py`)
```python
# Add validator call in validate_all_entities()
issues.extend({ValidatorName}.validate(df, entity_config, entity_name))
```

### 3. Add Tests (`backend/tests/validators/test_data_validators.py`)
```python
def test_{validator_name}():
    """Test {validator_name} with mock DataFrame."""
    df = pd.DataFrame({
        # Test data
    })
    
    entity_config = {
        # Test config
    }
    
    issues = {ValidatorName}.validate(df, entity_config, "test_entity")
    
    assert len(issues) == {expected_count}
    assert issues[0].code == "{ERROR_CODE}"
```

---

## Validation Issue Structure

All validators return structured issues:
```python
{
    "severity": "error",      # error|warning|info
    "entity": "entity_name",  # Or None for project-level
    "field": "field_name",    # Specific field with issue
    "message": "Clear description of problem",
    "code": "VALIDATION_CODE",  # Unique error code
    "suggestion": "How to fix this issue"  # Optional
}
```

## Best Practices
- ✅ Pure functions (especially data validators)
- ✅ Clear error messages with actionable suggestions
- ✅ Unique error codes for each issue type
- ✅ Test both valid and invalid cases
- ✅ Handle edge cases (empty data, missing fields)
- ❌ No external dependencies in domain validators
- ❌ No async in pure validators
```

## Example Usage

```
Create a data validator for checking required columns exist:

Validator Type: Data Validator
Purpose: Validate all columns in entity config exist in DataFrame
Error Code: COLUMN_NOT_FOUND

[... follow implementation steps ...]
```

## Related Documentation
- [Pure Domain Validators Pattern](../../AGENTS.md#pure-domain-validators-awesome-pattern-)
- [Dependency Injection Pattern](../../AGENTS.md#dependency-injection-for-circular-imports-)
- [Registry Pattern](../../AGENTS.md#registry-pattern-core)
