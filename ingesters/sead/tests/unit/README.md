# Unit Tests

This directory contains **pure unit tests** that:
- ✅ Run fast (< 0.5s total)
- ✅ Don't require database connection
- ✅ Don't require external data files
- ✅ Use minimal fixtures from `tests/fixtures.py` and `tests/builders.py`

## Test Files

- **test_config.py** - ConfigStore initialization and configuration loading
- **test_fixtures.py** - Validation of reusable fixture library
- **test_policy.py** - Data transformation policy tests
- **test_to_csv.py** - XML to CSV parser tests
- **test_utility.py** - Utility function tests
- **test_xml.py** - XML processing tests

## Running Unit Tests

```bash
# Run all unit tests
uv run pytest tests/unit/

# Run specific test file
uv run pytest tests/unit/test_policy.py

# Run with coverage
uv run pytest tests/unit/ --cov=importer
```

## Writing New Unit Tests

Use the builder pattern and minimal fixtures:

```python
from tests.fixtures import SIMPLE_SCHEMA, TWO_TABLE_SUBMISSION
from tests.builders import build_schema, build_table, build_column

def test_my_feature(mock_service):
    # Use pre-built fixtures
    schema = SIMPLE_SCHEMA()
    
    # Or build custom minimal schema
    schema = build_schema([
        build_table("my_table", "my_id", columns={
            "my_id": build_column("my_table", "my_id", is_pk=True),
            "name": build_column("my_table", "name", data_type="varchar"),
        })
    ])
    
    # Test logic here
```

See [tests/fixtures.py](../fixtures.py) for available fixtures and [tests/builders.py](../builders.py) for builder functions.
