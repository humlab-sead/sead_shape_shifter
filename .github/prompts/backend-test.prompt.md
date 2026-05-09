---
agent: agent
description: Write tests for FastAPI backend services and endpoints
---

Create tests for `{COMPONENT}` in the backend.

**File**: `backend/tests/test_{component}.py`

```python
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, MagicMock
from backend.app.main import app
from backend.app.services.{service} import {ServiceClass}

client = TestClient(app)
```

### Service Tests

```python
class Test{ServiceClass}:

    def test_{method}_success(self):
        service = {ServiceClass}()
        mock_state = MagicMock()
        mock_state.load_config.return_value = {"name": "test"}
        service.state = mock_state  # ⭐ inject via attribute

        result = service.{method}(params)

        assert result is not None
        mock_state.{method}.assert_called_once()

    def test_{method}_handles_error(self):
        service = {ServiceClass}()
        mock_state = MagicMock()
        mock_state.{method}.side_effect = Exception("Error")
        service.state = mock_state

        with pytest.raises(Exception):
            service.{method}(params)
```

> ❌ Never patch `src.configuration.provider.get_application_state` globally — inject via `service.state` instead.

### Endpoint Tests

```python
class Test{ComponentName}Endpoints:

    def test_get_success(self):
        response = client.get("/api/v1/{resource}")
        assert response.status_code == 200
        assert "expected_field" in response.json()

    def test_get_not_found(self):
        response = client.get("/api/v1/{resource}/nonexistent")
        assert response.status_code == 404

    def test_post_validation_error(self):
        response = client.post("/api/v1/{resource}", json={"missing": "required"})
        assert response.status_code == 422
```

### Validation Service Tests

```python
@pytest.mark.asyncio
async def test_data_validator():
    """Test pure domain validator — no mocks needed."""
    import pandas as pd
    from src.validators.data_validators import {ValidatorClass}

    df = pd.DataFrame({"col1": [1, 2], "col2": ["a", "b"]})
    issues = {ValidatorClass}.validate(df, configured_columns=["col1", "col3"], entity_name="test")

    assert any(i["code"] == "MISSING_COLUMN" for i in issues)
```

### Rules
- Use FastAPI `TestClient` for endpoint tests (sync, no `pytest.mark.asyncio` needed)
- Use `@pytest.mark.asyncio` only for async service/validator tests
- Inject dependencies via instance attributes, not global patches
- Use `MagicMock()` for services, plain DataFrames for data validators

## Related Documentation
- [TESTING.md](../../docs/TESTING.md)
- [python.instructions.md](../instructions/python.instructions.md)
