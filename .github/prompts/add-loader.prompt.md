---
agent: agent
description: Create a new data source loader following Shape Shifter's driver schema pattern
---

Create a data loader for `{DATA_SOURCE_TYPE}`:

### 1. Choose Loader Category
- **SQL Loader** → `src/loaders/sql_loaders.py`
- **File Loader** → `src/loaders/file_loaders.py`
- **Excel Loader** → `src/loaders/excel_loaders.py`
- **API Loader** → create new `src/loaders/api_loaders.py`

### 2. Implement Loader Class

```python
from typing import ClassVar
import pandas as pd
from src.loaders.base import DataLoader, DataLoaders
from src.loaders.driver_metadata import DriverSchema, FieldMetadata

@DataLoaders.register(key="{driver_key}")
class {LoaderName}(DataLoader):
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
        ],
    )

    async def load(self) -> pd.DataFrame:
        try:
            connection = await self._connect()
            data = await self._fetch_data(connection)
            df = pd.DataFrame(data)
            return self._apply_column_mapping(df)
        except Exception as e:
            self.logger.error(f"Failed to load from {DATA_SOURCE_TYPE}: {e}")
            raise

    async def _connect(self):
        pass  # connection logic

    async def _fetch_data(self, connection) -> list[dict]:
        pass  # query/read logic
```

### 3. Key Rules
- Schema is defined **inside the loader class** (not in a separate file)
- `load()` must be `async` and return a `pd.DataFrame`
- Use `self.logger` (not `print`) for error reporting
- Register with `@DataLoaders.register(key="...")` — key matches the `driver` field in `shapeshifter.yml`

### 4. Add Tests (`tests/loaders/test_{loader_name}.py`)

```python
import pytest
import pandas as pd
from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
async def test_{driver_key}_loader_success():
    config = {"driver": {"param": "value"}}
    loader = {LoaderName}("source_id", config["driver"])
    with patch.object(loader, "_connect", return_value=AsyncMock()):
        with patch.object(loader, "_fetch_data", return_value=[{"col": "val"}]):
            result = await loader.load()
    assert isinstance(result, pd.DataFrame)
```

## Related Documentation
- [loaders.instructions.md](../instructions/features/loaders.instructions.md)
- [CONFIGURATION_GUIDE.md](../../docs/CONFIGURATION_GUIDE.md)
