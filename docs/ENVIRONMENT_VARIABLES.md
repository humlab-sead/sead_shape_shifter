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

### Service Layer

The `DataSourceService` class provides two methods for environment variable resolution:

1. **`_resolve_env_vars(config_dict: dict)`** - Resolves env vars in a dictionary (recursive)
2. **`_resolve_config_env_vars(config: DataSourceConfig)`** - Resolves env vars in a Pydantic model

**Important:** Environment variables are **only resolved when testing connections**, not when listing/editing:

- `list_data_sources()` - Returns configs **with unresolved env vars** (e.g., `${SEAD_HOST}`) for UI display/editing
- `get_data_source(name)` - Returns config **with unresolved env vars** for editing
- `test_connection(config)` - Resolves env vars **before testing** the connection

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

# Create config with env var references
config = DataSourceConfig(
    name="my_db",
    driver="postgresql",
    options={
        "host": "${DB_HOST}",
        "port": "${DB_PORT}",
        "database": "${DB_NAME}",
        "username": "${DB_USER}",
    }
)

# Test connection - env vars resolved automatically
service = DataSourceService(config_store)
result = await service.test_connection(config)
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
- ✅ `test_connection()` resolves env vars before testing

Run tests:
```bash
pytest backend/tests/test_env_var_resolution.py -v
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
