# SEAD Clearinghouse Ingester - Architecture Overview

**Note**: This document describes the SEAD ingester architecture within the Shape Shifter project. The SEAD ingester is located at `ingesters/sead/` and implements the `Ingester` protocol defined in `backend/app/ingesters/protocol.py`.

## System Purpose

The SEAD Clearinghouse Ingester transforms Excel-based data submissions into CSV format and loads them into a PostgreSQL database following the SEAD ClearingHouse schema. It validates data integrity, applies transformation policies, and manages the submission lifecycle.

## Core Workflow

```
Excel File → Submission → Validation → CSV Dispatch → Database Upload → Explode to Public Schema
     ↓           ↓            ↓              ↓                ↓                    ↓
  Load Data   Apply       Check         Generate         Stage in DB         Final Tables
             Policies   Specifications   4 CSV Files    Staging Tables      (clearinghouse)
```

### Three-Stage Pipeline

1. **Load & Transform**: Excel → `Submission` object → apply policies → validated data
2. **Dispatch**: `Submission` → CSV files (4 files: tables, columns, records, recordvalues)
3. **Upload & Process**: CSV → staging tables → explode to public clearinghouse schema

## Key Components

### Data Model

**Submission** ([submission.py](submission.py))
- Container for Excel data loaded as pandas DataFrames
- One DataFrame per database table
- Provides access to data tables and schema metadata

**SeadSchema** ([metadata.py](metadata.py))
- Database schema metadata (tables, columns, FKs, PKs)
- Loaded from PostgreSQL `information_schema` or test fixtures
- Provides lookup methods and cached properties

### Business Logic

**Policies** ([policies.py](policies.py))
- Auto-registered transformation rules using `@UpdatePolicies.register()`
- Execute in priority order (configured in `config.yml`)
- Examples: add missing columns, resolve FKs, drop ignored columns
- Can be enabled/disabled per-policy

**Specifications** ([specification.py](specification.py))
- Auto-registered validation rules using `@SpecificationRegistry.register()`
- Check data integrity: required columns, type compatibility, FK references
- Collect errors, warnings, and info messages

### Orchestration

**ImportService** ([process.py](process.py))
- Coordinates the entire import workflow
- Selects dispatcher, runs validation, triggers upload/explode
- Entry point: `process(process_target: int | str | Submission)`

**SubmissionRepository** ([repository.py](repository.py))
- Manages database connections with context manager pattern
- Registers submissions, extracts to staging, explodes to public tables
- Uses PostgreSQL stored procedures for database operations

### Data Transformation

**CsvProcessor** ([dispatchers/to_csv.py](dispatchers/to_csv.py))
- Generates 4 CSV files directly from `Submission`
- Handles FK resolution (system_id → public_id lookup)
- Formats values according to data types

**SchemaService** ([metadata.py](metadata.py))
- Loads schema from database or mock sources
- Provides access to primary key values
- Filters ignored columns

## Design Patterns

### Registry Pattern

Auto-registration using decorators:

```python
@UpdatePolicies.register()
class AddPrimaryKeyColumnIfMissingPolicy(PolicyBase):
    def update(self) -> None:
        # Transformation logic
```

- Policies execute in priority order
- Specifications validate independently
- Both can be extended without modifying core code

### Configuration Injection

Uses `ConfigValue` for dependency injection:

```python
ignore_columns: list[str] = ConfigValue("options.ignore_columns").resolve()
```

**Priority order**: CLI args → options file → environment vars → YAML config

### Builder Pattern

Test fixtures use builder functions:

```python
schema = build_schema([
    build_table("tbl_sites", "site_id", columns={...})
])
```

Fast, focused test data creation without loading large fixtures.

## Data Flow

### Submission Data Conventions

- **`system_id`**: Internal temporary ID (required on all tables, unique per table)
- **`pk_name`**: Actual public database primary key (e.g., `site_id`, `dataset_id`)
- **New records**: Rows with `NULL` in `pk_name` column
- **Existing records**: Rows with non-NULL `pk_name` (updates)
- **Lookup tables**: Small reference tables managed by special policies

### CSV File Format

Four tab-separated files generated per submission:

1. **tables.csv**: `table_type, record_count`
2. **columns.csv**: `table_type, column_name, column_type`
3. **records.csv**: `class_name, system_id, public_id`
4. **recordvalues.csv**: `class_name, system_id, public_id, column_name, column_type, fk_system_id, fk_public_id, column_value`

### Database Staging

CSV files → `clearing_house.tbl_clearinghouse_submission_csv_content_*` tables → public schema tables via stored procedures

## Technology Stack

### Core
- **Python 3.13** - Language runtime
- **uv** - Package manager (fast, modern alternative to pip/poetry)
- **pandas 2.3+** - DataFrame operations for data transformation
- **psycopg 3.2+** - PostgreSQL database adapter

### Configuration
- **click** - CLI framework
- **python-dotenv** - Environment variable loading
- **PyYAML** - Configuration file parsing

### Development
- **pytest** - Testing framework
- **pytest-cov** - Coverage reporting
- **black** - Code formatting
- **isort** - Import sorting
- **pylint + ruff** - Linting

### Excel Processing
- **openpyxl** - Read/write Excel files
- **xlrd** - Legacy Excel support
- **xlsx2csv** - Fast Excel to CSV conversion

## Directory Structure

```
ingesters/sead/
├── dispatchers/       # CSV generation (CsvProcessor)
│   ├── __init__.py
│   └── to_csv.py
├── uploader/          # Database upload (CSV uploader)
│   ├── __init__.py
│   └── csv_uploader.py
├── tests/             # Test suite (unit + integration)
│   ├── unit/          # Fast tests, no DB (100+ tests, ~0.3s)
│   ├── integration/   # DB-dependent tests
│   ├── test_data/     # CSV fixtures for schema metadata
│   ├── conftest.py    # Pytest fixtures
│   └── builders.py    # Test data factories
├── ingester.py        # Main SeadIngester class (protocol implementation)
├── metadata.py        # Schema management
├── policies.py        # Data transformation rules
├── specification.py   # Validation rules
├── submission.py      # Data container
├── process.py         # Workflow orchestration
├── repository.py      # Database operations
├── utility.py         # Helper functions
├── README.md          # User documentation
└── ARCHITECTURE.md    # This file
```

## Extension Points

### Adding New Policies

1. Create class inheriting from `PolicyBase`
2. Decorate with `@UpdatePolicies.register()`
3. Implement `update(self) -> None`
4. Add priority in `config.yml`

### Adding New Specifications

1. Create class inheriting from `SpecificationBase`
2. Decorate with `@SpecificationRegistry.register()`
3. Implement `is_satisfied_by(submission, table_name) -> bool`
4. Use `self.error()`, `self.warn()`, `self.info()` for messages

### Adding New Dispatchers

1. Create class inheriting from `IDispatcher`
2. Decorate with `@Dispatchers.register(key="format_name")`
3. Implement `dispatch(target, schema, submission, table_names) -> None`

## Performance Characteristics

- **Policy execution**: O(n × tables × columns) where n = policy count
- **Validation**: O(specifications × tables × rows)
- **CSV generation**: O(tables × rows × columns)
- **Database upload**: Batch operations via stored procedures

### Optimization Strategies

1. **Minimal fixtures in tests**: Use builders instead of loading full CSV fixtures
2. **Cached properties**: Schema lookups computed once and cached
3. **Batch operations**: CSV bulk upload instead of row-by-row inserts
4. **Policy ordering**: Critical policies first, expensive policies last
5. **Lazy loading**: Schema loaded on-demand, not eagerly

## Configuration Hierarchy

```
CLI Arguments (highest priority)
    ↓
Options File (--options-filename)
    ↓
Environment Variables (SEAD_IMPORT_*)
    ↓
YAML Config File (config.yml)
    ↓
Defaults (lowest priority)
```

Configuration sections:
- `options`: Runtime options (database, output paths)
- `policies`: Policy-specific configuration
- `logging`: Log handler configuration

## Error Handling

- **Validation errors**: Collected in `SpecificationMessages`, can raise or return
- **Policy errors**: Logged and re-raised to halt execution
- **Database errors**: Wrapped in context manager, auto-rollback on exception
- **File I/O errors**: Explicit error messages with file paths

## Testing Strategy

**Unit Tests** (tests/unit/):
- Use `build_schema()`, `build_table()`, `build_column()` builders
- Mock database with `MockSchemaService`
- Focus on single component behavior
- Fast execution (< 1 second total)

**Integration Tests** (tests/integration/):
- Use minimal fixtures, not full CSV files
- Mark with `@pytest.mark.integration`
- Test component interactions
- Database-dependent (skipped if DB unavailable)

**Running Tests**:
```bash
# All tests
uv run pytest ingesters/sead/tests/

# Unit tests only
uv run pytest ingesters/sead/tests/unit/

# Integration tests only
uv run pytest ingesters/sead/tests/integration/
```

**Coverage Target**: 65%+ overall, 80%+ for core modules
