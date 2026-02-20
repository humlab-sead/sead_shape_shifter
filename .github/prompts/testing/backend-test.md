# Backend Testing Prompt

Write tests for FastAPI backend services and endpoints.

## Prompt Template

```
Create tests for {COMPONENT} in the backend:

### Test Structure

File: `backend/tests/test_{component}.py`

```python
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
from backend.app.main import app
from backend.app.services.{service} import {ServiceClass}

client = TestClient(app)

class Test{ServiceClass}:
    """Test suite for {service} service."""
    
    def test_{method}_success(self):
        """Test {method} succeeds with valid input."""
        # Arrange
        service = {ServiceClass}()
        mock_state = MagicMock()
        service.state = mock_state  # ⭐ Correct pattern
        
        # Act
        result = service.{method}(params)
        
        # Assert
        assert result is not None
        assert {expected_assertion}
    
    def test_{method}_handles_error(self):
        """Test {method} handles errors correctly."""
        service = {ServiceClass}()
        mock_state = MagicMock()
        mock_state.{method}.side_effect = Exception("Error")
        service.state = mock_state
        
        with pytest.raises(Exception):
            service.{method}(params)

class Test{ComponentName}Endpoints:
    """Test suite for {component} API endpoints."""
    
    def test_endpoint_success(self):
        """Test GET /api/v1/{endpoint} returns data."""
        response = client.get("/api/v1/{endpoint}")
        
        assert response.status_code == 200
        data = response.json()
        assert "expected_field" in data
    
    def test_endpoint_not_found(self):
        """Test endpoint returns 404 for invalid resource."""
        response = client.get("/api/v1/{endpoint}/nonexistent")
        assert response.status_code == 404
    
    def test_endpoint_validation_error(self):
        """Test endpoint validates request body."""
        invalid_data = {"missing": "required_field"}
        response = client.post(
            "/api/v1/{endpoint}",
            json=invalid_data
        )
        assert response.status_code == 422  # Validation error
```

### Testing Patterns by Component Type

#### 1. Service Tests

**Pattern: Mock state via instance attribute** ⭐
```python
def test_project_service():
    """Test ProjectService operations."""
    service = ProjectService()
    
    # Mock state instance attribute (correct pattern)
    mock_state = MagicMock()
    mock_state.load_config.return_value = {"name": "test"}
    service.state = mock_state  # ⭐ Direct assignment
    
    result = service.load_project("test")
    assert result.name == "test"
    mock_state.load_config.assert_called_once_with("test")
```

**❌ Never mock state globally:**
```python
# WRONG - don't do this
with patch('src.configuration.provider.get_application_state'):
    pass  # Unreliable
```

#### 2. Validation Service Tests

```python
@pytest.mark.asyncio
async def test_validation_service():
    """Test ValidationService with dependency injection."""
    # Create service with injected mock orchestrator
    mock_orchestrator = Mock()
    mock_orchestrator.validate_all_entities = AsyncMock(
        return_value=[ValidationIssue(...)]
    )
    
    service = ValidationService(orchestrator=mock_orchestrator)
    errors = await service.validate_data("project", ["entity"])
    
    assert len(errors) > 0
    mock_orchestrator.validate_all_entities.assert_called_once()
```

#### 3. Mapper Tests

```python
def test_mapper_to_core():
    """Test ProjectMapper converts API → Core."""
    api_project = Project(
        name="test",
        data_sources={"db": ApiDataSourceConfig(...)}
    )
    
    core_project = ProjectMapper.to_core(api_project)
    
    assert isinstance(core_project, ShapeShiftProject)
    assert core_project.cfg["name"] == "test"
    # Verify env vars resolved in Core
    assert "${" not in str(core_project.cfg)

def test_mapper_preserves_directives():
    """Test mapper preserves directives in API layer."""
    project_dict = {
        "name": "test",
        "data_sources": {
            "db": {"@include": "sources/db.yml"}
        }
    }
    
    api_project = ProjectMapper.to_api_config(project_dict, "test")
    
    # Directives preserved in API layer
    assert "@include" in str(api_project.model_dump())
```

#### 4. Endpoint Tests

```python
def test_get_projects():
    """Test GET /api/v1/projects endpoint."""
    response = client.get("/api/v1/projects")
    
    assert response.status_code == 200
    projects = response.json()
    assert isinstance(projects, list)

def test_create_project():
    """Test POST /api/v1/projects endpoint."""
    new_project = {
        "name": "test_project",
        "data_sources": {},
        "entities": {}
    }
    
    response = client.post(
        "/api/v1/projects",
        json=new_project
    )
    
    assert response.status_code == 201
    created = response.json()
    assert created["name"] == "test_project"

def test_endpoint_error_handling():
    """Test endpoint handles service errors."""
    with patch("backend.app.services.project_service.ProjectService.load_project") as mock:
        mock.side_effect = FileNotFoundError("Not found")
        
        response = client.get("/api/v1/projects/nonexistent")
        assert response.status_code == 404
```

#### 5. Data Validator Tests

```python
@pytest.mark.asyncio
async def test_data_validation_orchestrator():
    """Test orchestrator with injected strategy."""
    # Create mock strategy
    mock_strategy = Mock(spec=DataFetchStrategy)
    mock_strategy.fetch = AsyncMock(return_value=pd.DataFrame({
        "col1": [1, 2, 3]
    }))
    
    # Inject strategy
    orchestrator = DataValidationOrchestrator(fetch_strategy=mock_strategy)
    
    # Create core project (resolved)
    api_project = Project(...)
    core_project = ProjectMapper.to_core(api_project)
    
    issues = await orchestrator.validate_all_entities(
        core_project=core_project,
        project_name="test",
        entity_names=["entity"]
    )
    
    assert isinstance(issues, list)
    mock_strategy.fetch.assert_called()
```

### Run Tests
```bash
# All backend tests
uv run pytest backend/tests -v

# With PYTHONPATH if import issues
PYTHONPATH=.:backend uv run pytest backend/tests -v

# Specific service
uv run pytest backend/tests/test_{service}.py -v

# With coverage
uv run pytest backend/tests --cov=backend.app --cov-report=html
```

### Code Coverage Target
- Services: 80%+ coverage
- Endpoints: 90%+ coverage (include error cases)
- Mappers: 95%+ coverage (critical layer boundary)
```

## Example Usage

```
Create tests for the ValidationService in the backend:

Component: ValidationService
Methods: validate_project, validate_entities, validate_data
Mock Strategy: Dependency injection for orchestrator
Test Cases: Success, validation errors, data validation

[... follow test structure ...]
```

## Related Documentation
- [Test Patterns](../../AGENTS.md#test-patterns)
- [Dependency Injection](../../AGENTS.md#dependency-injection-for-circular-imports-critical-pattern-)
- [Layer Boundary Architecture](../../AGENTS.md#layer-boundary-architecture-awesome-rule-)
