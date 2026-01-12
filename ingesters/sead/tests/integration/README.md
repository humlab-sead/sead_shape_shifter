# Integration Tests

This directory contains **integration tests** that:
- ⚠️ Require live database connection
- ⚠️ Load full schema from CSV fixtures (1,628 lines)
- ⚠️ May require specific data files
- ⚠️ Run slower than unit tests

## Test Files

- **test_metadata.py** - Database schema loading and metadata tests
- **test_process.py** - Full import workflow tests
- **test_submission.py** - Submission processing with database
- **submissions/** - Domain-specific submission tests (adna, dendro, etc.)

## Running Integration Tests

Integration tests are skipped by default unless database is available:

```bash
# Run all integration tests (requires DB)
uv run pytest tests/integration/

# Run specific integration test
uv run pytest tests/integration/test_metadata.py

# Skip integration tests
uv run pytest tests/unit/  # Only unit tests
```

## Database Requirements

Integration tests require:
- PostgreSQL database (version 12+)
- Database credentials in `.env` file
- Schema loaded via `clearing_house.clearinghouse_import_*` views

Example `.env`:
```
SEAD_IMPORT_HOST=localhost
SEAD_IMPORT_DBNAME=sead_staging
SEAD_IMPORT_USER=postgres
SEAD_IMPORT_PORT=5432
```

## Pytest Markers

Integration tests should be marked:

```python
import pytest

@pytest.mark.integration
def test_database_operation(full_schema_service):
    # Test that requires database
    ...
```

## Test Data

Integration tests use full CSV fixtures from `tests/test_data/`:
- `sead_tables.csv` - Full schema (158 tables)
- `sead_columns.csv` - Full columns (888 rows)
- Test XML files for submission processing

These fixtures are loaded via session-scoped fixtures in `conftest.py`.
