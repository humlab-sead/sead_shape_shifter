# Core Testing Prompt

Write tests for Shape Shifter core processing pipeline components.

## Prompt Template

```
Create tests for {COMPONENT} in the core processing pipeline:

### Test Structure

File: `tests/test_{component}.py`

```python
import pytest
from unittest.mock import Mock, patch, AsyncMock
import pandas as pd
from src.{component} import {ClassToTest}

# Use decorator for config setup
from tests.conftest import with_test_config

class Test{ClassName}:
    """Test suite for {component} functionality."""
    
    @pytest.mark.asyncio
    @with_test_config
    async def test_{scenario}_success(self, test_provider):
        """Test {scenario} completes successfully."""
        # Arrange
        config = {
            # Test configuration
        }
        instance = {ClassToTest}(config)
        
        # Act
        result = await instance.{method}()
        
        # Assert
        assert result is not None
        assert {assertion}
    
    @pytest.mark.asyncio
    @with_test_config
    async def test_{scenario}_error(self, test_provider):
        """Test {scenario} handles errors correctly."""
        # Arrange - invalid config
        config = {}
        instance = {ClassToTest}(config)
        
        # Act & Assert
        with pytest.raises({ExceptionType}):
            await instance.{method}()
    
    @pytest.mark.asyncio
    @with_test_config
    async def test_{scenario}_edge_case(self, test_provider):
        """Test {scenario} handles edge cases."""
        # Test empty data, null values, etc.
        pass
```

### Testing Patterns by Component

#### 1. Data Loaders (`tests/loaders/`)
```python
@pytest.mark.asyncio
async def test_loader_success():
    """Test successful data loading."""
    config = {"driver": {"param": "value"}}
    loader = LoaderClass("source_id", config["driver"])
    
    # Mock connection
    with patch.object(loader, "connection", return_value=AsyncMock()) as mock_conn:
        # Mock internal methods
        with patch.object(loader, "_get_tables", return_value=["table1"]):
            result = await loader.load()
    
    assert isinstance(result, pd.DataFrame)
    mock_conn.assert_called_once()
```

#### 2. Constraints (`tests/test_constraints.py`)
```python
async def test_validator():
    """Test constraint validation."""
    validator = ValidatorClass()
    config = {
        "entity": {
            "field": "value"
        }
    }
    
    issues = validator.validate(config, entity_name="test")
    
    assert len(issues) == 0  # Or expected count
    # Check issue structure if errors expected
    # assert issues[0]["code"] == "ERROR_CODE"
```

#### 3. Normalizer (`tests/test_normalizer.py`)
```python
@pytest.mark.asyncio
@with_test_config
async def test_normalize_pipeline(test_provider):
    """Test full normalization pipeline."""
    config = {
        "name": "test_project",
        "data_sources": {},
        "entities": {}
    }
    
    normalizer = ShapeShifter(config)
    await normalizer.normalize()
    
    # Verify table_store populated
    assert "entity" in normalizer.table_store
    assert not normalizer.table_store["entity"].empty
```

#### 4. Filters/Transformers
```python
def test_filter_application():
    """Test data filtering."""
    df = pd.DataFrame({
        "col1": [1, 2, 3],
        "col2": ["a", "b", "c"]
    })
    
    filter_config = {"condition": "col1 > 1"}
    result = apply_filter(df, filter_config)
    
    assert len(result) == 2
    assert result["col1"].min() > 1
```

### Test Coverage Requirements
- [x] Success cases (happy path)
- [x] Error handling (invalid config, connection failures)
- [x] Edge cases (empty data, null values, duplicates)
- [x] Integration (component interactions)
- [x] Async behavior (if applicable)

### Mocking Strategy
```python
# Mock external connections
with patch("src.loaders.sqlalchemy.create_engine") as mock_engine:
    mock_engine.return_value = Mock()

# Mock async methods
async_mock = AsyncMock(return_value=expected_data)
with patch.object(instance, "async_method", async_mock):
    result = await instance.call_method()

# Mock internal methods
with patch.object(loader, "_internal_method", return_value=data):
    result = await loader.load()
```

### Run Tests
```bash
# All core tests
uv run pytest tests -v

# Specific test file
uv run pytest tests/test_{component}.py -v

# Specific test
uv run pytest tests/test_{component}.py::Test{Class}::test_{method} -v

# With coverage
uv run pytest tests --cov=src --cov-report=html
```
```

## Example Usage

```
Create tests for the FK linking functionality in the core processing pipeline:

Component: link.py
Classes: Linker, foreign_key_link()
Scenarios: 
- Successful FK resolution
- Missing parent entity
- Circular dependencies
- Self-referencing FKs

[... follow test structure ...]
```

## Related Documentation
- [TESTING_GUIDE.md](../../docs/TESTING_GUIDE.md)
- [Test Patterns](../../AGENTS.md#test-patterns)
- [Async/Await](../../AGENTS.md#asyncawait)
