# Environment Variable Resolution in Data Sources

## Overview

The Shape Shifter data source system now supports automatic resolution of environment variables when testing connections. This allows you to store sensitive configuration (like database credentials) in environment variables rather than hardcoding them.

## How It Works

### In Configuration Files (Core System)

When loading configurations through the core system (e.g., `arbodat-database.yml`), environment variables are automatically resolved by the `src.configuration` framework.

Example from `sead-options.yml`:
```yaml
driver: postgres
options:
  host: ${SEAD_HOST}
  port: ${SEAD_PORT}
  dbname: ${SEAD_DBNAME}
  username: ${SEAD_USER}
```

### In API/Backend (Data Source Testing)

When testing data source connections via the API, the `DataSourceService` now automatically resolves environment variables before attempting the connection.

**Before Resolution:**
```json
{
  "name": "sead",
  "driver": "postgresql",
  "options": {
    "host": "${SEAD_HOST}",
    "port": "${SEAD_PORT}",
    "database": "${SEAD_DBNAME}",
    "username": "${SEAD_USER}"
  }
}
```

**After Resolution (automatic):**
```json
{
  "name": "sead",
  "driver": "postgresql",
  "options": {
    "host": "localhost",
    "port": "5432",
    "database": "sead_production",
    "username": "sead_user"
  }
}
```

## Password Management with .pgpass

For PostgreSQL connections, the recommended approach is to use `.pgpass` file for password management rather than storing passwords in configuration or environment variables.

### Setting up .pgpass

1. Create `~/.pgpass` file:
   ```bash
   touch ~/.pgpass
   chmod 600 ~/.pgpass
   ```

2. Add connection credentials (one per line):
   ```
   hostname:port:database:username:password
   ```

   Example:
   ```
   localhost:5432:sead_production:sead_user:mypassword123
   localhost:5432:*:postgres:adminpassword
   ```

3. PostgreSQL will automatically use `.pgpass` when no password is provided in the connection

### Benefits

- **Security**: Passwords never appear in configuration files or environment variables
- **Convenience**: No need to pass passwords in connection strings
- **Standard**: `.pgpass` is the PostgreSQL-recommended approach
- **Multi-environment**: Different passwords for different databases in one file

## API Usage

### Testing Connection with Environment Variables

When creating or testing a data source via the API, you can use environment variable references:

```typescript
// Frontend API call
const dataSource = {
  name: 'production_db',
  driver: 'postgresql',
  options: {
    host: '${DB_HOST}',
    port: '${DB_PORT}',
    database: '${DB_NAME}',
    username: '${DB_USER}'
    // No password - will use .pgpass
  }
};

// Test connection
const result = await api.testConnection(dataSource);
// Environment variables are resolved automatically before testing
```

### Setting Environment Variables

**In shell:**
```bash
export SEAD_HOST=localhost
export SEAD_PORT=5432
export SEAD_DBNAME=sead_production
export SEAD_USER=sead_user
```

**In .env file (development):**
```env
SEAD_HOST=localhost
SEAD_PORT=5432
SEAD_DBNAME=sead_production
SEAD_USER=sead_user
```

**In systemd service (production):**
```ini
[Service]
Environment="SEAD_HOST=prod-db.example.com"
Environment="SEAD_PORT=5432"
Environment="SEAD_DBNAME=sead_production"
Environment="SEAD_USER=sead_user"
```

## Implementation Details

### Architecture: Layer-Based Resolution

The system follows a **clean separation of concerns** where environment variable resolution happens **exclusively in the mapper layer** when converting between API and Core entities.

#### Layer Responsibilities

| Layer | Responsibility | Environment Variables |
|-------|---------------|----------------------|
| **API Models** (`backend/app/models/`) | Data transfer, validation | Raw, unresolved (`${VAR}`) |
| **Services** (`backend/app/services/`) | Business logic | Works with raw API entities |
| **Mapper** (`backend/app/mappers/`) | Translation + **Resolution** | **Resolves here** |
| **Core** (`src/`) | Processing, execution | Always resolved |

#### Why This Approach?

1. **Single Responsibility**: The `DataSourceMapper.to_core_config()` method is the **only** place that resolves environment variables
2. **Clear Boundaries**: API layer = raw config, Core layer = resolved config
3. **No Redundancy**: Services never need to remember to call `resolve_config_env_vars()`
4. **Type Safety**: Core entities are guaranteed to be fully resolved
5. **Easier Testing**: Mock the mapper for tests that need unresolved configs

### Mapper Layer

The `DataSourceMapper` class handles the boundary between API and Core layers:

```python
from backend.app.mappers.data_source_mapper import DataSourceMapper
from backend.app.models.data_source import DataSourceConfig as ApiConfig
from src.model import DataSourceConfig as CoreConfig

class DataSourceMapper:
    @staticmethod
    def to_core_config(api_config: ApiConfig) -> CoreConfig:
        """Map API config to Core config.
        
        IMPORTANT: This method resolves environment variables during mapping.
        API entities remain "raw" with ${ENV_VAR} syntax, but core entities
        are always fully resolved and ready for use.
        """
        # Resolution happens here at the API/Core boundary
        api_config = api_config.resolve_config_env_vars()
        
        # Map to core format with resolved values
        return CoreConfig(
            name=api_config.name,
            cfg={
                "driver": api_config.driver,
                "options": {...}  # Fully resolved
            }
        )
```

### Service Layer

Services work with **raw API entities** and rely on the mapper for resolution:

```python
# SchemaIntrospectionService example
class SchemaIntrospectionService:
    async def get_tables(self, data_source_name: str) -> list[TableMetadata]:
        # Get raw API config (with ${ENV_VARS})
        api_config = self.data_source_service.get_data_source(data_source_name)
        
        # Mapper handles resolution when creating core config
        core_config = DataSourceMapper.to_core_config(api_config)
        
        # Core loader receives fully resolved config
        loader = DataLoaders.get(core_config.driver)(core_config)
        return await loader.get_tables()
```

**Important:** Environment variables are **preserved in API entities** and only resolved when mapping to Core:

- `list_data_sources()` - Returns API configs **with unresolved env vars** (e.g., `${SEAD_HOST}`) for UI display/editing
- `get_data_source(name)` - Returns API config **with unresolved env vars** for editing
- `test_connection(config)` - Mapper resolves env vars **when creating core config** for testing
- `get_tables(name)` - Mapper resolves env vars **when creating loader** for introspection

This approach allows users to:
1. **See and edit** the environment variable references in the UI (e.g., `${SEAD_HOST}`)
2. **Test connections** with actual resolved values from the environment
3. **Keep configuration portable** across environments

### Resolution Rules

1. Environment variable syntax: `${VAR_NAME}`
2. If variable exists: Replaces with actual value
3. If variable doesn't exist: Replaces with empty string
4. Nested dictionaries: Resolved recursively (e.g., in `options`)
5. Non-string values: Passed through unchanged

### Example Code

```python
from backend.app.services.data_source_service import DataSourceService
from backend.app.models.data_source import DataSourceConfig
from backend.app.mappers.data_source_mapper import DataSourceMapper

# Create API config with env var references (stays raw)
api_config = DataSourceConfig(
    name="my_db",
    driver="postgresql",
    options={
        "host": "${DB_HOST}",
        "port": "${DB_PORT}",
        "database": "${DB_NAME}",
        "username": "${DB_USER}",
    }
)

# API config remains raw throughout the service layer
service = DataSourceService(config_store)

# Mapper resolves env vars when converting to core config
core_config = DataSourceMapper.to_core_config(api_config)
# Now core_config has resolved values: host="localhost", etc.

# Test connection using core config
result = await service.test_connection(api_config)
# Internally, test_connection uses mapper to get resolved core config
```

## UI Behavior

When working with data sources in the UI:

1. **Listing/Viewing**: Environment variables appear as `${VAR_NAME}` (unresolved)
2. **Editing**: You can edit the `${VAR_NAME}` references directly
3. **Testing**: Click "Test Connection" to resolve vars and verify connectivity
4. **Saving**: Environment variable references are saved as-is in configuration

**Example:**
```
Database name field shows: ${SEAD_DBNAME}
When you test connection: Resolved to actual value (e.g., "sead_production")
After saving: Stored as ${SEAD_DBNAME} in config file
```

### Testing

Comprehensive test coverage in `backend/tests/test_env_var_resolution.py`:

- ✅ Environment variable resolution in dictionaries
- ✅ Environment variable resolution in Pydantic models
- ✅ Nested dictionary resolution (options)
- ✅ Missing environment variables (returns empty string)
- ✅ Password preservation during resolution
- ✅ `list_data_sources()` keeps env vars unresolved for UI editing
- ✅ Mapper resolves env vars when creating core configs
- ✅ Services work with raw API entities, mapper handles resolution

Run tests:
```bash
pytest backend/tests/test_env_var_resolution.py -v
pytest backend/tests/test_data_source_mapper.py -v
```

## Security Considerations

1. **Never commit passwords** to version control
2. **Use .pgpass** for PostgreSQL password management
3. **Restrict .pgpass permissions**: `chmod 600 ~/.pgpass`
4. **Use environment variables** for host/port/database/username
5. **Use secrets management** in production (Vault, AWS Secrets Manager, etc.)
6. **Audit access** to environment configuration

## Migration Guide

If you have existing data sources with hardcoded values, you can migrate them to use environment variables:

**Before:**
```yaml
driver: postgres
options:
  host: localhost
  port: 5432
  database: sead_production
  username: sead_user
```

**After:**
```yaml
driver: postgres
options:
  host: ${SEAD_HOST}
  port: ${SEAD_PORT}
  database: ${SEAD_DBNAME}
  username: ${SEAD_USER}
```

Then set the environment variables in your deployment environment.
