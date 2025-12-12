# Shape Shifter - AI Coding Agent Instructions

## Project Architecture

**Shape Shifter** is a declarative data transformation framework using YAML configurations to harmonize diverse data sources into target schemas. The system processes entities through a dependency-ordered pipeline.

### Core Processing Pipeline
1. **Extract** (`src/extract.py`) - Load data from sources (CSV, SQL, fixed values)
2. **Filter** (`src/filter.py`) - Apply post-load filters (e.g., `exists_in`)
3. **Link** (`src/link.py`) - Resolve foreign key relationships with constraint validation
4. **Unnest** (`src/unnest.py`) - Transform wide to long format (melt operations)
5. **Translate** (`src/mapping.py`) - Map column names to target schema
6. **Store** - Output to CSV, Excel, or database

The orchestrator is `ArbodatSurveyNormalizer` in `src/normalizer.py` which uses `ProcessState` for topological sorting of entity dependencies.

### Key Components

**Configuration Model** (`src/config_model.py`):
- `TablesConfig` - Root configuration with entities and options
- `TableConfig` - Individual entity/table configuration
- `ForeignKeyConfig` - Foreign key relationship with constraints
- `ForeignKeyConstraints` - Cardinality, uniqueness, match requirements
- `UnnestConfig` - Melt operation configuration

**Constraint Validation** (`src/constraints.py`):
- Uses Registry pattern with stage-based validators (`pre-merge`, `post-merge`, `post-merge-match`)
- `ForeignKeyConstraintValidator` orchestrates validation around merge operations
- Each validator inherits from `ConstraintValidator` and uses `@Validators.register(key=..., stage=...)`
- Merge indicator columns track match status for validation

**Configuration Validation** (`src/specifications.py`):
- `CompositeConfigSpecification` runs all validators on configuration load
- Validates entity existence, circular dependencies, data sources, SQL requirements, foreign key configs
- New validators should inherit from `ConfigSpecification` and be added to `CompositeConfigSpecification.__init__()`

## Critical Patterns

### Registry Pattern
The project uses a generic `Registry` base class (`src/utility.py`) for plugin-style extensibility:

```python
class MyRegistry(Registry):
    items: dict[str, type[MyClass]] = {}

MyInstances = MyRegistry()

@MyInstances.register(key="name")
class MyImplementation(MyClass):
    pass
```

Used in: `ValidatorRegistry`, `FilterRegistry`, `DispatchRegistry`, `DataLoaderRegistry`, `TransformerRegistry`

### Async/Await Pattern
Data loaders are **async** - all loader `.load()` methods return coroutines:
```python
# Correct
data = await loader.load()

# For mocking in tests
async def async_load(*args, **kwargs):
    return mock_data
mock_loader.load = async_load
```

### Test Decorator Pattern
Use `@with_test_config` decorator for tests needing configuration provider:
```python
@pytest.mark.asyncio
@with_test_config
async def test_something(self, test_provider):
    # test_provider is automatically set up and torn down
    result = await normalizer.normalize()
```

### Configuration Resolution
Configurations support:
- `@value: entities.entity_name.property` - Reference other config values
- `@include: file.yml` - Include external files
- `@load: options.translations` - Load translations
- `${ENV_VAR}` - Environment variable substitution (use `replace_env_vars()`)

## Development Workflow

### Setup
```bash
uv venv                    # Create virtual environment
uv pip install -e ".[dev]" # Install with dev dependencies
```

### Testing
```bash
make test                         # Run all tests
uv run pytest tests -v            # Same, verbose
uv run pytest tests/test_file.py -v  # Single file
uv run pytest -k test_name        # Single test by name
```

**Key test files**:
- `tests/test_append_processing.py` - Append configuration tests
- `tests/test_constraints.py` - Foreign key constraint validation
- `tests/test_specifications.py` - Configuration validation

### Linting
```bash
make lint           # Run all linters
make black          # Format code
make pylint         # Run pylint
make check-imports  # Validate imports
```

### Running Transformations
```bash
# Direct Python execution
PYTHONPATH=. python src/arbodat/survey2excel.py \
  --config-file input/arbodat.yml \
  --mode csv \
  input.csv output_dir/

# Or use make targets
make csv    # Run CSV export example
make excel  # Run Excel export example
```

## Code Conventions

### Import Rules
- **Absolute imports only**: `from src.module import Class` (never `from .module`)
- Enforced by Ruff with `ban-relative-imports = "parents"`
- Line length: 140 characters

### Naming Conventions
- **Entity names**: snake_case (e.g., `sample_type`)
- **Surrogate IDs**: Must end with `_id` (e.g., `sample_type_id`)
- **Column names**: snake_case
- **Foreign key columns**: Follow pattern `entity_id`

### Error Handling
- Use `loguru.logger` for logging (already configured)
- Use `logger.warning()` for constraint violations that don't halt execution
- Raise `ForeignKeyConstraintViolation` for fatal constraint errors
- Use `logger.debug()` for detailed processing steps

### Data Processing
- **Always** reset DataFrame index after operations that might change it
- Use `data.copy()` when modifying DataFrames to avoid SettingWithCopyWarning
- Treat empty strings as `pd.NA` for empty row detection
- Use `unique()` from `src.utility` to deduplicate lists while preserving order

## Configuration YAML Structure

```yaml
entities:
  entity_name:
    type: data | fixed | sql          # Data source type
    data_source: name                 # Required for SQL type
    query: "SELECT ..."               # Required for SQL type
    surrogate_id: entity_name_id      # Generated integer ID
    keys: [natural_keys]              # Natural key columns
    columns: [col1, col2]             # Columns to extract
    source: other_entity              # Source entity (null = root)
    depends_on: [entity1, entity2]    # Processing dependencies
    
    foreign_keys:
      - entity: remote_entity
        local_keys: [key1]
        remote_keys: [key1]
        how: inner | left | outer | cross
        constraints:
          cardinality: one_to_one | many_to_one | one_to_many
          require_unique_left: true
          allow_null_keys: false
    
    unnest:                           # Melt wide to long
      id_vars: [id_cols]
      value_vars: [cols_to_melt]
      var_name: new_col_name
      value_name: new_value_name
    
    append:                           # Augment data
      - type: fixed
        values: [[val1, val2]]
      - type: sql
        data_source: name
        query: "SELECT ..."
    
    filters:                          # Post-extract filters
      - type: exists_in
        entity: other_entity
        column: col_name
        remote_column: remote_col

options:
  data_sources:
    source_name:
      driver: postgresql | access
      # Connection params...
```

## Common Tasks

### Adding a New Validator
1. Create class inheriting `ConstraintValidator` in `src/constraints.py`
2. Implement `is_applicable()` and `validate()` methods
3. Register with `@Validators.register(key="constraint_name", stage="pre-merge|post-merge|post-merge-match")`
4. Add tests in `tests/test_constraints.py`

### Adding a New Data Loader
1. Create class inheriting `DataLoader` in `src/loaders/`
2. Implement async `load()` method
3. Register with `@DataLoaders.register(key="driver_name")`
4. Add to `options.data_sources` in config

### Adding Configuration Validation
1. Create class inheriting `ConfigSpecification` in `src/specifications.py`
2. Implement `is_satisfied_by()` returning bool
3. Use `self.add_error()` and `self.add_warning()` for messages
4. Add to `CompositeConfigSpecification.__init__()` list

### Debugging Entity Processing
Enable debug logging to see processing order and dependency resolution:
```python
from src.utility import setup_logging
setup_logging(verbose=True)  # Shows ProcessState decisions
```

Check `normalizer.table_store` dict to inspect intermediate DataFrames.

## Documentation
- [CONFIGURATION_REFERENCE.md](docs/CONFIGURATION_REFERENCE.md) - Complete YAML reference
- [FOREIGN_KEY_CONSTRAINTS.md](docs/FOREIGN_KEY_CONSTRAINTS.md) - Constraint validation details
- [VALIDATION_IMPROVEMENTS.md](docs/VALIDATION_IMPROVEMENTS.md) - Configuration validation specs
- [constraint_examples.py](docs/constraint_examples.py) - Constraint usage examples

## External Dependencies
- **UCanAccess**: MS Access support via JDBC (requires Java, installed via `scripts/install-uncanccess.sh`)
- **pandas**: Primary data manipulation library
- **loguru**: Logging framework
- **pytest-asyncio**: Async test support
