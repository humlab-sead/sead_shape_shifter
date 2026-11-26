---
agent: agent
description: Write tests for Shape Shifter core processing pipeline components (loaders, constraints, normalizer)
---

Create tests for `{COMPONENT}` in the core processing pipeline.

**File**: `tests/test_{component}.py`

```python
import pytest
from unittest.mock import Mock, patch, AsyncMock
import pandas as pd
from src.{component} import {ClassToTest}

class Test{ClassName}:

    @pytest.mark.asyncio
    async def test_{scenario}_success(self):
        config = { /* test configuration */ }
        instance = {ClassToTest}(config)
        result = await instance.{method}()
        assert result is not None

    @pytest.mark.asyncio
    async def test_{scenario}_error(self):
        instance = {ClassToTest}({})
        with pytest.raises({ExceptionType}):
            await instance.{method}()
```

### Data Loaders (`tests/loaders/`)

```python
@pytest.mark.asyncio
async def test_loader_success():
    config = {"driver": {"param": "value"}}
    loader = LoaderClass("source_id", config["driver"])
    with patch.object(loader, "_connect", return_value=AsyncMock()):
        with patch.object(loader, "_get_tables", return_value=["table1"]):
            result = await loader.load()
    assert isinstance(result, pd.DataFrame)
```

### Constraint Validators (`tests/specifications/test_constraints.py`)

Build the validator with an entity, FK and constraints config, then call `validate(ValidationContext(...))`. A violation raises `ForeignKeyConstraintViolation` unless `raise_on_violation=False`. Follow the existing tests in that file for setup.

### Core Pipeline (`tests/process/` or `tests/integration/`)

```python
@pytest.mark.asyncio
async def test_pipeline_end_to_end():
    """Test full Extract → Filter → Link → Store pipeline."""
    from src.normalizer import ShapeShifter
    shifter = ShapeShifter(config)
    result = await shifter.run()
    assert result.success
```

### Rules
- Use `@pytest.mark.asyncio` for all async tests
- Mock data sources — never hit real databases in unit tests
- Use plain DataFrames for data validator tests (no mocks needed)
- Use `conftest.py` fixtures for shared config setup

## Related Documentation
- [TESTING.md](../../docs/TESTING.md)
- [testing.instructions.md](../instructions/testing.instructions.md)
