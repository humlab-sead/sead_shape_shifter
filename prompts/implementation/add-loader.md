# Add Data Loader Prompt

Create new data source loader following Shape Shifter's driver schema pattern.

## Prompt Template

```
Create a data loader for {DATA_SOURCE_TYPE}:

### 1. Choose Loader Category
- **SQL Loader** → `src/loaders/sql_loaders.py`
- **File Loader** → `src/loaders/file_loaders.py`
- **Excel Loader** → `src/loaders/excel_loaders.py`
- **API Loader** → Create new `src/loaders/api_loaders.py`

### 2. Implement Loader Class

```python
from typing import ClassVar
import pandas as pd
from src.loaders.base import DataLoader, DataLoaders
from src.loaders.driver_metadata import DriverSchema, FieldMetadata

@DataLoaders.register(key="{driver_key}")
class {LoaderName}(DataLoader):
    """
    {DESCRIPTION}
    
    Loads data from {SOURCE_TYPE}.
    
    Configuration:
        {field1}: {description}
        {field2}: {description}
    """
    
    # Define driver schema directly in class ⭐
    schema: ClassVar[DriverSchema] = DriverSchema(
        driver="{driver_key}",
        display_name="{Display Name}",
        description="{User-facing description}",
        category="{database|file|api}",
        fields=[
            FieldMetadata(
                name="field_name",
                type="string",  # string|number|boolean|password
                required=True,
                default=None,
                description="Field description",
                placeholder="Example value",
            ),
            # Add all configuration fields
        ],
    )
    
    async def load(self) -> pd.DataFrame:
        """
        Load data from {SOURCE_TYPE}.
        
        Returns:
            DataFrame with loaded data
        
        Raises:
            Exception: If connection or query fails
        """
        try:
            # 1. Establish connection
            connection = await self._connect()
            
            # 2. Load data
            data = await self._fetch_data(connection)
            
            # 3. Convert to DataFrame
            df = pd.DataFrame(data)
            
            # 4. Apply transformations
            df = self._apply_column_mapping(df)
            
            return df
            
        except Exception as e:
            self.logger.error(f"Failed to load from {SOURCE_TYPE}: {e}")
            raise
        finally:
            # Cleanup connection if needed
            pass
    
    async def _connect(self):
        """Establish connection to data source."""
        # Connection logic
        pass
    
    async def _fetch_data(self, connection) -> list[dict]:
        """Fetch data from source."""
        # Query/read logic
        pass
```

### 3. Driver Schema Pattern ⭐

**Critical**: Schema defined in loader class, not separate file.

```python
schema: ClassVar[DriverSchema] = DriverSchema(
    driver="driver_key",           # Unique identifier (same as register key)
    display_name="User Display",   # Shown in UI
    description="Purpose",          # Help text
    category="database",            # database|file|api
    fields=[
        # Connection fields
        FieldMetadata(
            name="host",
            type="string",
            required=True,
            description="Database host address",
            placeholder="localhost",
        ),
        FieldMetadata(
            name="port",
            type="number",
            required=False,
            default=5432,
            description="Database port",
        ),
        FieldMetadata(
            name="password",
            type="password",           # Masked in UI
            required=True,
            description="Database password",
        ),
        # Query fields
        FieldMetadata(
            name="query",
            type="string",
            required=False,
            description="SQL query or table name",
            placeholder="SELECT * FROM table",
        ),
    ],
)
```

### 4. Field Types
- `string` - Text input
- `number` - Numeric input
- `boolean` - Checkbox
- `password` - Masked input

### 5. Add Tests (`tests/loaders/test_{category}_loaders.py`)

```python
import pytest
from unittest.mock import Mock, patch, AsyncMock
import pandas as pd
from src.loaders.{category}_loaders import {LoaderName}

@pytest.mark.asyncio
async def test_{loader_name}_load_success():
    """Test successful data loading."""
    config = {
        "{driver_key}": {
            "host": "localhost",
            "port": {port},
            # ... all required fields
        }
    }
    
    loader = {LoaderName}(
        data_source_id="{driver_key}",
        data_source_config=config["{driver_key}"],
    )
    
    # Mock connection/query
    with patch.object(loader, "_connect", return_value=AsyncMock()):
        with patch.object(loader, "_fetch_data", return_value=[{"col": "val"}]):
            df = await loader.load()
    
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert "col" in df.columns

@pytest.mark.asyncio
async def test_{loader_name}_connection_error():
    """Test connection failure handling."""
    config = {"{driver_key}": {"host": "invalid"}}
    loader = {LoaderName}("{driver_key}", config["{driver_key}"])
    
    with pytest.raises(Exception):
        await loader.load()
```

### 6. Benefits of Driver Schema Pattern
✅ Single source of truth (schema with implementation)
✅ Impossible to forget updating schema
✅ Type safety with Pydantic validation
✅ Auto-discovered by DriverSchemaRegistry
✅ No separate YAML/JSON to maintain

### 7. Integration Points
- Backend endpoint: `GET /api/v1/data-sources/drivers` auto-discovers schema
- Frontend: Data source editor renders form from schema
- Validation: Pydantic validates config against schema
```

## Example Usage

```
Create a data loader for MongoDB:

Data Source Type: MongoDB database
Category: database
Required Fields: host, port, database, collection
Optional Fields: username, password, query_filter

[... follow implementation steps ...]
```

## Related Documentation
- [Driver Schema Pattern](../../.github/copilot-instructions.md#driver-schema-pattern-loaders)
- [Registry Pattern](../../AGENTS.md#registry-pattern-core)
- [Async/Await](../../AGENTS.md#asyncawait)
