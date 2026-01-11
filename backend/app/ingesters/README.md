# Shape Shifter Ingester System

The ingester system provides a modular, extensible architecture for importing data from external sources into Shape Shifter.

## Architecture

The system follows a protocol-based design pattern where all ingesters implement a common `Ingester` protocol:

```python
@runtime_checkable
class Ingester(Protocol):
    @classmethod
    def get_metadata(cls) -> IngesterMetadata: ...
    
    def __init__(self, config: IngesterConfig): ...
    
    async def validate(self, source: str) -> ValidationResult: ...
    
    async def ingest(self, source: str) -> IngestionResult: ...
```

## Components

### Core Infrastructure
- **`protocol.py`**: Defines the `Ingester` protocol and result types
- **`registry.py`**: Auto-discovery registry for ingesters
- **`__init__.py`**: Triggers registration of all ingesters

### SEAD Ingester (`sead/`)
Complete implementation for SEAD Clearinghouse Import system:
- **`ingester.py`**: Main ingester class implementing the protocol
- **Core modules**: metadata, policies, specification, submission, repository, utility, process
- **Dispatchers**: csv_processor, xml_processor
- **Uploaders**: csv_uploader, xml_uploader

## Usage

### API (FastAPI)

List available ingesters:
```http
GET /api/v1/ingesters
```

Validate data source:
```http
POST /api/v1/ingesters/sead/validate
{
  "source": "/path/to/data.xlsx",
  "config": {
    "ignore_columns": ["date_updated", "*_uuid"]
  }
}
```

Ingest data:
```http
POST /api/v1/ingesters/sead/ingest
{
  "source": "/path/to/data.xlsx",
  "config": {
    "database": {
      "host": "localhost",
      "port": 5432,
      "dbname": "sead_staging",
      "user": "sead_user"
    }
  },
  "submission_name": "dendro_2026_01",
  "data_types": "dendro",
  "output_folder": "/output",
  "do_register": true,
  "explode": true
}
```

### CLI

List ingesters:
```bash
python -m backend.app.scripts.ingest list-ingesters
```

Validate:
```bash
python -m backend.app.scripts.ingest validate sead /path/to/data.xlsx
```

Ingest:
```bash
python -m backend.app.scripts.ingest ingest sead /path/to/data.xlsx \
  --submission-name "dendro_2026_01" \
  --data-types "dendro" \
  --database-host localhost \
  --database-name sead_staging \
  --register \
  --explode
```

### Frontend (Vue 3)

```typescript
import { useIngesterStore } from '@/stores/ingester'

const ingesterStore = useIngesterStore()

// List ingesters
await ingesterStore.fetchIngesters()

// Validate
await ingesterStore.validate('sead', {
  source: '/path/to/data.xlsx',
  config: {}
})

// Ingest
await ingesterStore.ingest('sead', {
  source: '/path/to/data.xlsx',
  submission_name: 'dendro_2026_01',
  data_types: 'dendro',
  config: {},
  do_register: true,
  explode: true
})
```

## Adding a New Ingester

1. Create directory: `backend/app/ingesters/<name>/`
2. Implement ingester class:
```python
from backend.app.ingesters.protocol import Ingester, IngesterConfig
from backend.app.ingesters.registry import Ingesters

@Ingesters.register(key="my_ingester")
class MyIngester(Ingester):
    @classmethod
    def get_metadata(cls) -> IngesterMetadata:
        return IngesterMetadata(
            key="my_ingester",
            name="My Data Source",
            description="Import from MySystem",
            version="1.0.0",
            supported_formats=["csv", "xlsx"]
        )
    
    def __init__(self, config: IngesterConfig):
        self.config = config
    
    async def validate(self, source: str) -> ValidationResult:
        # Validation logic
        return ValidationResult(is_valid=True, errors=[], warnings=[])
    
    async def ingest(self, source: str) -> IngestionResult:
        # Ingestion logic
        return IngestionResult(
            success=True,
            records_processed=100,
            message="Success"
        )
```

3. Import in `__init__.py`:
```python
from .my_ingester.ingester import MyIngester  # noqa: F401
```

4. Add tests in `backend/tests/ingesters/test_my_ingester.py`

## Testing

```bash
# Run all ingester tests
pytest backend/tests/ingesters/

# Run API tests
pytest backend/tests/api/test_ingesters.py

# Run CLI tests
pytest backend/tests/scripts/test_ingest_cli.py

# Run all ingester-related tests
pytest backend/tests/ingesters/ backend/tests/api/test_ingesters.py backend/tests/scripts/test_ingest_cli.py
```

## Configuration

Ingesters receive configuration through the `IngesterConfig` dataclass:

```python
@dataclass
class IngesterConfig:
    host: str | None = None
    port: int | None = None
    dbname: str | None = None
    user: str | None = None
    submission_name: str | None = None
    data_types: str | None = None
    output_folder: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)
```

Use `extra` dict for ingester-specific parameters.

## Best Practices

1. **Validation First**: Always validate before ingesting
2. **Async Methods**: Use async/await for I/O operations
3. **Structured Errors**: Return clear error messages in `ValidationResult` and `IngestionResult`
4. **Config Isolation**: Accept explicit parameters to avoid ConfigStore dependencies in tests
5. **Connection Management**: Use context managers for database connections
6. **Explicit Configuration**: Pass explicit values in `extra` dict for testability

## See Also

- [AGENTS.md](../../AGENTS.md#ingester-development-pattern) - Complete ingester development guide
- [Implementation Plan](../../../INGESTER_INTEGRATION_PLAN.md) - Detailed integration plan
- [Backend API Docs](../../../docs/BACKEND_API.md) - API endpoint reference
