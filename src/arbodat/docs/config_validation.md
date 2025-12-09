# Configuration Validation Specifications

This document describes the configuration validation system for Arbodat YAML import configurations.

## Overview

The validation system uses the **Specification Pattern** to validate import configurations before processing. It provides comprehensive error reporting and warnings to help identify configuration issues early.

## Usage

### Command Line Validation

```bash
python validate_config.py <config_file.yml>
```

Example:
```bash
python validate_config.py src/arbodat/input/arbodat.yml
```

### Programmatic Validation

```python
from src.arbodat.specifications import CompositeConfigSpecification
import yaml

# Load configuration
with open("config.yml") as f:
    config = yaml.safe_load(f)

# Validate
spec = CompositeConfigSpecification()
is_valid = spec.is_satisfied_by(config)

# Get detailed report
print(spec.get_report())

# Access errors and warnings
if spec.has_errors():
    for error in spec.errors:
        print(f"Error: {error}")

if spec.has_warnings():
    for warning in spec.warnings:
        print(f"Warning: {warning}")
```

## Available Specifications

### 1. `EntityExistsSpecification`
Validates that all referenced entities exist in the configuration.

**Checks:**
- Foreign key references point to existing entities
- `depends_on` references point to existing entities  
- `source` references point to existing entities

**Example Error:**
```
Entity 'child': references non-existent entity 'parent' in foreign key
```

### 2. `CircularDependencySpecification`
Validates that there are no circular dependencies between entities.

**Checks:**
- No cycles in `depends_on` chains
- No cycles through `source` references
- Uses depth-first search to detect cycles

**Example Error:**
```
Circular dependency detected: a -> b -> c -> a
```

### 3. `RequiredFieldsSpecification`
Validates that all required fields are present.

**For Data Tables:**
- Must have `columns` or `keys`

**For Fixed Data Tables:**
- Must have `surrogate_id`
- Must have `columns`
- Must have `values`

**Example Error:**
```
Entity 'table': data table must have 'columns' or 'keys'
```

### 4. `ForeignKeySpecification`
Validates foreign key configurations.

**Checks:**
- Required fields: `entity`, `local_keys`, `remote_keys`
- `local_keys` and `remote_keys` have same length
- `extra_columns` is string, list, or dict

**Example Error:**
```
Entity 'child', foreign key #1: 'local_keys' length (2) does not match 'remote_keys' length (1)
```

### 5. `UnnestSpecification`
Validates unnest/melt configurations.

**Checks:**
- Required fields: `value_vars`, `var_name`, `value_name`
- Warns if `id_vars` is missing

**Example Error:**
```
Entity 'table': unnest configuration missing required 'value_vars'
```

**Example Warning:**
```
Entity 'table': unnest configuration missing 'id_vars' (may cause issues)
```

### 6. `DropDuplicatesSpecification`
Validates drop_duplicates configurations.

**Checks:**
- Must be boolean, string (include directive), or list

**Example Error:**
```
Entity 'table': 'drop_duplicates' must be boolean, string, or list of columns
```

### 7. `SurrogateIdSpecification`
Validates surrogate ID configurations.

**Checks:**
- Surrogate IDs are unique across entities
- Warns if ID doesn't end with `_id`

**Example Error:**
```
Surrogate ID 'id' is used by multiple entities: table1, table2
```

**Example Warning:**
```
Entity 'table': surrogate_id 'pk' does not follow convention (should end with '_id')
```

### 8. `FixedDataSpecification`
Validates fixed data table configurations.

**Checks:**
- SQL queries are not empty
- Value rows match column count
- Warns if `source` is set (shouldn't be for fixed data)

**Example Error:**
```
Entity 'table': value row 1 has 1 items but 2 columns defined
```

**Example Warning:**
```
Entity 'table': fixed data table has 'source' field (should be null)
```

### 9. `CompositeConfigSpecification`
Runs all specifications and aggregates results.

This is the main specification to use for complete validation. It runs all individual specifications and provides a comprehensive report.

## Creating Custom Specifications

You can create custom specifications by extending `ConfigSpecification`:

```python
from src.arbodat.specifications import ConfigSpecification
from typing import Any

class MyCustomSpecification(ConfigSpecification):
    """Validates custom requirements."""
    
    def is_satisfied_by(self, config: dict[str, Any]) -> bool:
        self.clear()
        valid = True
        
        entities_config = config.get("entities", {})
        
        for entity_name, entity_data in entities_config.items():
            # Your validation logic here
            if some_condition:
                self.add_error(f"Entity '{entity_name}': problem description")
                valid = False
            
            if some_warning_condition:
                self.add_warning(f"Entity '{entity_name}': warning description")
        
        return valid

# Use in composite
spec = CompositeConfigSpecification(specifications=[
    MyCustomSpecification(),
    EntityExistsSpecification(),
    # ... other specs
])
```

## Integration with Normalizer

You can integrate validation into the normalization workflow:

```python
from src.arbodat.normalizer import ArbodatSurveyNormalizer
from src.arbodat.specifications import CompositeConfigSpecification
from src.configuration.resolve import ConfigValue

# Load and validate config
config = ConfigValue[dict]("entities").resolve()
spec = CompositeConfigSpecification()

if not spec.is_satisfied_by({"entities": config}):
    print("Configuration validation failed!")
    print(spec.get_report())
    raise ValueError("Invalid configuration")

# Proceed with normalization
normalizer = ArbodatSurveyNormalizer.load("input.csv")
normalizer.normalize()
```

## Benefits

1. **Early Error Detection**: Catch configuration errors before processing data
2. **Clear Error Messages**: Detailed, actionable error messages
3. **Separation of Concerns**: Validation logic separate from processing logic
4. **Extensible**: Easy to add new validation rules
5. **Reusable**: Same specifications can validate config from any source (YAML, JSON, etc.)
6. **GUI-Ready**: Error/warning lists perfect for displaying in a GUI

## Future Enhancements

Potential additions:
- Schema validation against JSON Schema
- Cross-entity consistency checks (e.g., column existence in source data)
- Performance impact analysis
- Recommendation system for optimization
- Auto-fix suggestions for common issues
