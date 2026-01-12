# SEAD Clearinghouse Ingester

Data ingester for the SEAD Clearinghouse database system. This ingester transforms Excel-based data submissions into CSV format and loads them into PostgreSQL following the SEAD ClearingHouse schema.

## Overview

The SEAD ingester implements the Shape Shifter `Ingester` protocol to:
1. Validate Excel data submissions against SEAD schema requirements
2. Apply transformation policies to ensure data consistency
3. Generate CSV files conforming to clearinghouse import format
4. Upload and process data into PostgreSQL staging/public tables

## Architecture

This ingester follows a **three-stage pipeline**:

```
Excel File → Submission → Validation → CSV Dispatch → Database Upload → Explode to Public Schema
```

See [ARCHITECTURE.md](./ARCHITECTURE.md) for detailed component documentation.

## Installation

The SEAD ingester is included with Shape Shifter. Install the full project:

```bash
cd /path/to/sead_shape_shifter
make install              # Full setup: core + api + dev tools
```

Or install just the ingester dependencies:
```bash
uv pip install -e ".[api]"
```

## Usage

### Via CLI

```bash
# Validate an Excel file without importing
python -m backend.app.scripts.ingest validate sead /path/to/data.xlsx \
  --database-host localhost \
  --database-port 5432 \
  --database-name sead_staging \
  --database-user sead_user

# Import and register in database
python -m backend.app.scripts.ingest ingest sead /path/to/data.xlsx \
  --submission-name "dendro_2024_01" \
  --data-types "dendro" \
  --database-host localhost \
  --database-port 5432 \
  --database-name sead_staging \
  --database-user sead_user \
  --register

# Full workflow: validate, import, and explode to public schema
python -m backend.app.scripts.ingest ingest sead /path/to/data.xlsx \
  --submission-name "dendro_2024_01" \
  --data-types "dendro" \
  --config config.json \
  --register \
  --explode
```

### Via Python API

```python
from ingesters.sead.ingester import SeadIngester
from backend.app.ingesters.protocol import IngesterConfig

# Configure the ingester
config = IngesterConfig(
    host="localhost",
    port=5432,
    dbname="sead_staging",
    user="sead_user",
    submission_name="dendro_2024_01",
    data_types="dendro",
    extra={
        "ignore_columns": ["date_updated", "*_uuid"],
        "output_folder": "/output/dendro",
    }
)

# Create ingester instance
ingester = SeadIngester(config)

# Validate before importing
result = ingester.validate("/path/to/data.xlsx")
if not result.is_valid:
    print("Validation errors:", result.errors)
else:
    # Import the data
    result = ingester.ingest("/path/to/data.xlsx")
    print(f"Imported {result.records_processed} records")
```

## Excel File Requirements

The Excel file must satisfy:
- **Format**: Excel 2007+ (`.xlsx`)
- **Sheet Names**: Each table requires a sheet matching the `excel_sheet` name in SEAD metadata
- **Column Names**: Must match database schema (case-sensitive)
- **Required Columns**: 
  - `system_id` - Internal temporary ID (can be auto-added by policy)
  - `<table>_id` - Public database primary key (e.g., `site_id`, `dataset_id`)

## Configuration

Configuration is read in priority order:

1. **CLI arguments** (highest priority)
2. **Config file** (JSON/YAML via `--config`)
3. **Environment variables** (`SEAD_IMPORT_*`)
4. **Defaults** (lowest priority)

### Configuration Options

```json
{
  "database": {
    "host": "localhost",
    "port": 5432,
    "dbname": "sead_staging",
    "user": "sead_user"
  },
  "ignore_columns": [
    "date_updated",
    "*_uuid",
    "(*"
  ],
  "output_folder": "/output",
  "transfer_format": "csv",
  "policies": {
    "add_primary_key_column_if_missing": {
      "priority": 10,
      "disabled": false
    }
  }
}
```

## Data Model Conventions

- **`system_id`**: Internal temporary ID used during submission (required, unique per table)
- **`pk_name`**: Actual public database primary key (e.g., `site_id`, `dataset_id`)
- **New vs Existing**: Rows with null `pk_name` are new; non-null means updating existing records
- **Lookup Tables**: Small reference tables (e.g., `tbl_sample_types`) managed by special policies

## Transformation Policies

Policies are auto-registered transformation rules applied to submissions:

- `AddPrimaryKeyColumnIfMissingPolicy` - Adds PK column with nulls (assumes all new records)
- `UpdateMissingForeignKeyPolicy` - Adds default FK values if missing
- `AddIdentityMappingSystemIdToPublicIdPolicy` - Creates identity mapping for referenced tables
- `IfForeignKeyValueIsMissingAddIdentityMappingToForeignKeyTable` - Auto-creates lookup entries
- `DropIgnoredColumns` - Removes columns matching ignore patterns

Policies execute in **priority order** (configured in `config.yml`) and can be disabled per-policy.

## Validation Specifications

Specifications validate data integrity:

- `SubmissionTableExistsSpecification` - Table exists in submission
- `HasPrimaryKeySpecification` - Primary key column present
- `HasSystemIdSpecification` - System ID column present and unique
- `ForeignKeyExistsAsPrimaryKeySpecification` - FK references valid tables
- `NonNullableColumnHasValueSpecification` - Required fields have values

## Testing

The test suite is organized into unit tests (fast, no DB) and integration tests (require DB).

### Running Tests

```bash
# Run all SEAD ingester tests
cd /path/to/sead_shape_shifter
PYTHONPATH=.:ingesters/sead uv run pytest ingesters/sead/tests/

# Run only unit tests (fast, no DB required)
uv run pytest ingesters/sead/tests/unit/

# Run integration tests (requires database)
uv run pytest ingesters/sead/tests/integration/

# Run with coverage
uv run pytest ingesters/sead/tests/ --cov=ingesters.sead --cov-report=html
```

### Test Structure

```
ingesters/sead/tests/
├── unit/              # Pure unit tests (fast, no DB)
│   ├── test_config.py
│   ├── test_csv_dispatcher.py
│   ├── test_metadata.py
│   ├── test_policy.py
│   ├── test_submission.py
│   └── test_utility.py
├── integration/       # Integration tests (require DB)
│   ├── test_process.py
│   └── submissions/
│       ├── test_adna.py
│       └── test_living_tree.py
├── test_data/         # CSV fixtures for schema metadata
│   ├── sead_tables.csv
│   └── sead_columns.csv
├── conftest.py        # Pytest configuration
├── builders.py        # Test data factories
└── fixtures.py        # Shared test fixtures
```

## Development

### Code Quality

```bash
# Format code
make tidy          # black + isort

# Lint code
make lint          # pylint + ruff
```

### Adding New Policies

1. Create class in `policies.py` inheriting from `PolicyBase`
2. Decorate with `@UpdatePolicies.register()`
3. Implement `update(self) -> None` method
4. Add priority in configuration
5. Add tests in `tests/unit/test_policy.py`

### Adding New Specifications

1. Create class in `specification.py` inheriting from `SpecificationBase`
2. Decorate with `@SpecificationRegistry.register()`
3. Implement `is_satisfied_by(submission, table_name) -> bool`
4. Use `self.error()`, `self.warn()`, `self.info()` for messages
5. Add tests in `tests/unit/test_specification_edge_cases.py`

## Key Files

- `ingester.py` - Main ingester class implementing `Ingester` protocol
- `metadata.py` - Schema management (`SeadSchema`, `SchemaService`)
- `policies.py` - Data transformation rules
- `specification.py` - Validation rules
- `submission.py` - Data container for Excel tables
- `process.py` - Workflow orchestration (`ImportService`)
- `repository.py` - Database operations (`SubmissionRepository`)
- `dispatchers/to_csv.py` - CSV generation
- `uploader/csv_uploader.py` - Database upload

## CSV Output Format

Four tab-separated files generated per submission:

1. **tables.csv**: `table_type, record_count`
2. **columns.csv**: `table_type, column_name, column_type`
3. **records.csv**: `class_name, system_id, public_id`
4. **recordvalues.csv**: `class_name, system_id, public_id, column_name, column_type, fk_system_id, fk_public_id, column_value`

These files are uploaded to PostgreSQL staging tables, then exploded to public clearinghouse schema via stored procedures.

## Technology Stack

- **Python 3.13** - Language runtime
- **pandas 2.3+** - DataFrame operations
- **psycopg 3.2+** - PostgreSQL adapter
- **openpyxl** - Excel file processing
- **pytest** - Testing framework

## License

Same as parent Shape Shifter project.

## Related Documentation

- [ARCHITECTURE.md](./ARCHITECTURE.md) - Detailed architecture and design patterns
- [Shape Shifter Main README](../../README.md) - Parent project documentation
- [Ingester Protocol](../../backend/app/ingesters/README.md) - Protocol definition and guidelines
