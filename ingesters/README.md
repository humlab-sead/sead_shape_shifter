# Ingesters

This directory contains ingester implementations for Shape Shifter. Ingesters are pluggable modules that handle ingestion of Shape Shifter output into external systems.

## Architecture

Ingesters are decoupled from the backend API infrastructure:
- **Protocol Definition**: `backend/app/ingesters/protocol.py` defines the `Ingester` interface
- **Registry**: `backend/app/ingesters/registry.py` handles discovery and registration
- **Implementations**: This directory (`ingesters/`) contains concrete implementations

## Creating a New Ingester

### 1. Directory Structure

Create a new directory under `ingesters/`:

```
ingesters/
  your_ingester/
    __init__.py
    ingester.py         # Main ingester class (required)
    ... (other modules as needed)
```

### 2. Implement the Protocol

```python
# ingesters/your_ingester/ingester.py
from backend.app.ingesters.protocol import (
    Ingester,
    IngesterConfig,
    IngesterMetadata,
    ValidationResult,
    IngestionResult,
)
from backend.app.ingesters.registry import Ingesters


@Ingesters.register(key="your_ingester")
class YourIngester:
    """Your ingester description."""

    def __init__(self, config: IngesterConfig):
        self.config = config
        # Initialize your ingester

    @classmethod
    def get_metadata(cls) -> IngesterMetadata:
        return IngesterMetadata(
            key="your_ingester",
            name="Your Ingester Name",
            description="What your ingester does",
            version="1.0.0",
            supported_formats=["xlsx", "csv"],
            requires_config=True,
        )

    async def validate(self, source: str) -> ValidationResult:
        """Validate source data without making changes."""
        # Implement validation logic
        return ValidationResult(is_valid=True, errors=[], warnings=[])

    async def ingest(self, source: str) -> IngestionResult:
        """Perform the actual data ingestion."""
        # Implement ingestion logic
        return IngestionResult(
            success=True,
            message="Ingestion completed",
            records_inserted=100,
        )
```

### 3. Register in __init__.py

```python
# ingesters/your_ingester/__init__.py
from ingesters.your_ingester.ingester import YourIngester

__all__ = ["YourIngester"]
```

### 4. Enable in Configuration

The ingester will be auto-discovered at application startup. To explicitly enable/disable:

```yaml
# backend/app/core/config.py or config file
ingesters:
  enabled: ["sead", "your_ingester"]
  search_paths: ["ingesters"]
```

## Available Ingesters

### SEAD Clearinghouse
- **Key**: `sead`
- **Path**: `ingesters/sead/`
- **Description**: Ingests data into SEAD Clearinghouse PostgreSQL database
- **Formats**: Excel (.xlsx)
- **Status**: Production-ready

## Testing

Add tests for your ingester in `backend/tests/ingesters/`:

```python
# backend/tests/ingesters/test_your_ingester.py
from ingesters.your_ingester import YourIngester
from backend.app.ingesters.protocol import IngesterConfig


def test_metadata():
    metadata = YourIngester.get_metadata()
    assert metadata.key == "your_ingester"


async def test_validation():
    config = IngesterConfig(...)
    ingester = YourIngester(config)
    result = await ingester.validate("test_file.xlsx")
    assert result.is_valid
```

## API Usage

Once registered, your ingester is available via the REST API:

```bash
# List all ingesters
GET /api/v1/ingesters

# Validate data
POST /api/v1/ingesters/your_ingester/validate
{
  "source": "/path/to/file.xlsx",
  "config": {...}
}

# Ingest data
POST /api/v1/ingesters/your_ingester/ingest
{
  "source": "/path/to/file.xlsx",
  "submission_name": "my_submission",
  "data_types": "sample_data",
  "config": {...}
}
```

## CLI Usage

```bash
# List available ingesters
python -m backend.app.scripts.ingest list-ingesters

# Validate data
python -m backend.app.scripts.ingest validate your_ingester /path/to/file.xlsx

# Ingest data
python -m backend.app.scripts.ingest ingest your_ingester /path/to/file.xlsx \
  --submission-name "my_submission" \
  --data-types "sample_data"
```

## Best Practices

1. **Error Handling**: Always wrap validation/ingestion in try-except and return structured errors
2. **Configuration**: Use `IngesterConfig.extra` dict for ingester-specific settings
3. **Logging**: Use `loguru.logger` for consistent logging
4. **Testing**: Provide explicit config values in tests to avoid ConfigStore dependencies
5. **Documentation**: Add docstrings and update this README when adding new ingesters

## Troubleshooting

### Ingester Not Discovered
- Check directory name matches registration key
- Verify `ingester.py` exists and contains `@Ingesters.register()` decorator
- Check logs for import errors during startup
- Ensure `ingesters/` is in Python path (should be automatic with editable install)

### Import Errors
- Ingesters should import protocol from `backend.app.ingesters.protocol`
- Internal imports within ingester should use `from ingesters.<name>.module import X`
- Don't import from `backend.app.ingesters.sead` (old location)

### Configuration Issues
- Use explicit values in `extra` dict to avoid `ConfigValue` lookups
- Check backend logs for configuration validation errors
- Verify database credentials and connection settings
