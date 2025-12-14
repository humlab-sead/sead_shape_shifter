# Developer Guide: Testing Strategy

## Overview

Shape Shifter Configuration Editor employs a comprehensive testing strategy covering unit tests, integration tests, and end-to-end testing. This guide covers testing practices, patterns, and tooling.

## Testing Pyramid

```
        ┌──────────────────┐
        │   E2E Tests      │  ~10% (Manual + Automated)
        │   (Selenium)     │
        └──────────────────┘
      ┌────────────────────────┐
      │   Integration Tests    │  ~20% (API + Service)
      │   (pytest)             │
      └────────────────────────┘
    ┌──────────────────────────────┐
    │      Unit Tests              │  ~70% (Functions + Classes)
    │      (pytest + vitest)       │
    └──────────────────────────────┘
```

**Distribution:**
- **Unit Tests:** 70% - Fast, isolated, many
- **Integration Tests:** 20% - Medium speed, verify interactions
- **E2E Tests:** 10% - Slow, expensive, critical paths only

## Backend Testing

### Test Structure

```
backend/tests/
├── unit/
│   ├── test_validation_service.py
│   ├── test_auto_fix_service.py
│   ├── test_yaml_service.py
│   └── test_cache_service.py
├── integration/
│   ├── test_api_validation.py
│   ├── test_api_configurations.py
│   └── test_api_auto_fix.py
├── fixtures/
│   ├── sample_configs/
│   └── test_data/
└── conftest.py                    # Shared fixtures
```

### Unit Testing Patterns

#### 1. Testing Async Functions

```python
# tests/unit/test_validation_service.py
import pytest
from unittest.mock import AsyncMock, Mock

@pytest.mark.asyncio
async def test_validate_configuration():
    """Test validation service with mocked dependencies."""
    # Arrange
    mock_yaml = AsyncMock()
    mock_yaml.load_configuration.return_value = {
        "entities": {"test": {"columns": ["col1"]}}
    }
    
    service = ValidationService(mock_yaml)
    
    # Act
    result = await service.validate_configuration("test_config", "all")
    
    # Assert
    assert result.config_name == "test_config"
    assert len(result.issues) >= 0
    mock_yaml.load_configuration.assert_called_once_with("test_config")
```

**Key Points:**
- Use `@pytest.mark.asyncio` for async tests
- Mock async functions with `AsyncMock()`
- Mock sync functions with `Mock()`
- Always verify mock calls

#### 2. Fixture-Based Testing

```python
# tests/conftest.py
import pytest
from pathlib import Path

@pytest.fixture
def sample_config():
    """Provide sample configuration for tests."""
    return {
        "entities": {
            "sample_entity": {
                "columns": ["id", "name", "value"],
                "keys": ["id"],
                "source": None
            }
        }
    }

@pytest.fixture
def temp_config_dir(tmp_path):
    """Create temporary directory for config files."""
    config_dir = tmp_path / "configs"
    config_dir.mkdir()
    return config_dir

@pytest.fixture
def yaml_service(temp_config_dir):
    """Create YAMLService with temp directory."""
    return YAMLService(config_dir=temp_config_dir)

# Usage in tests
def test_load_configuration(yaml_service, sample_config):
    yaml_service.save_configuration("test", sample_config)
    loaded = yaml_service.load_configuration("test")
    assert loaded == sample_config
```

**Benefits:**
- Reusable test data
- Isolated test environments
- Clean setup/teardown
- Composable fixtures

#### 3. Parameterized Tests

```python
# tests/unit/test_auto_fix_service.py
import pytest

@pytest.mark.parametrize("action_type,field,old_value,new_value", [
    (FixActionType.REMOVE_COLUMN, "columns", "missing_col", None),
    (FixActionType.ADD_COLUMN, "columns", None, "new_col"),
    (FixActionType.UPDATE_REFERENCE, "foreign_keys", "old_entity", "new_entity"),
])
@pytest.mark.asyncio
async def test_apply_fix_actions(
    auto_fix_service,
    action_type,
    field,
    old_value,
    new_value
):
    """Test different fix action types."""
    action = FixAction(
        type=action_type,
        entity="test_entity",
        field=field,
        old_value=old_value,
        new_value=new_value
    )
    
    result = await auto_fix_service._apply_action(action, config)
    
    assert result.success
```

**Benefits:**
- Test multiple scenarios with same code
- Clear test case documentation
- Easy to add new cases
- Reduced code duplication

#### 4. Exception Testing

```python
# tests/unit/test_yaml_service.py
import pytest
from backend.app.core.errors import ConfigurationNotFoundError

def test_load_nonexistent_config_raises_error(yaml_service):
    """Test that loading non-existent config raises error."""
    with pytest.raises(ConfigurationNotFoundError) as exc_info:
        yaml_service.load_configuration("nonexistent")
    
    assert "nonexistent" in str(exc_info.value)
    assert exc_info.value.status_code == 404

def test_invalid_yaml_raises_validation_error(yaml_service):
    """Test that invalid YAML raises validation error."""
    with pytest.raises(ValidationError):
        yaml_service.parse_yaml("invalid: yaml: content:")
```

#### 5. Mock-Based Testing

```python
# tests/unit/test_auto_fix_service.py
from unittest.mock import Mock, patch

def test_create_backup_uses_correct_path(auto_fix_service):
    """Test that backup is created with correct naming."""
    with patch('app.services.auto_fix_service.shutil.copy2') as mock_copy:
        auto_fix_service._create_backup("test_config")
        
        # Verify copy was called with correct arguments
        mock_copy.assert_called_once()
        args = mock_copy.call_args[0]
        
        assert "test_config.yml" in str(args[0])  # Source
        assert "backup" in str(args[1])           # Destination
        assert ".yml" in str(args[1])             # Extension preserved
```

### Integration Testing

#### API Integration Tests

```python
# tests/integration/test_api_validation.py
import pytest
from httpx import AsyncClient
from backend.app.main import app

@pytest.mark.asyncio
async def test_validate_configuration_endpoint():
    """Test validation endpoint returns correct structure."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/validate",
            json={
                "config_name": "test_config",
                "validation_type": "all"
            }
        )
    
    assert response.status_code == 200
    data = response.json()
    
    assert "config_name" in data
    assert "issues" in data
    assert "summary" in data
    assert isinstance(data["issues"], list)

@pytest.mark.asyncio
async def test_validate_nonexistent_config_returns_404():
    """Test that validating non-existent config returns 404."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/validate",
            json={
                "config_name": "nonexistent",
                "validation_type": "all"
            }
        )
    
    assert response.status_code == 404
    assert "not found" in response.json()["error"].lower()
```

#### Service Integration Tests

```python
# tests/integration/test_validation_cache_integration.py
import pytest
from backend.app.services.validation_service import ValidationService
from backend.app.services.yaml_service import YAMLService
from backend.app.core.cache import CacheService

@pytest.mark.asyncio
async def test_validation_caching_integration():
    """Test that validation results are properly cached."""
    # Setup real services
    yaml_service = YAMLService(config_dir="tests/fixtures/configs")
    cache_service = CacheService(ttl=300)
    validation_service = ValidationService(yaml_service, cache_service)
    
    # First validation - should hit backend
    result1 = await validation_service.validate_configuration(
        "sample_config",
        "all"
    )
    assert not result1.cache_hit
    
    # Second validation - should use cache
    result2 = await validation_service.validate_configuration(
        "sample_config",
        "all"
    )
    assert result2.cache_hit
    assert result1.issues == result2.issues
```

### Test Coverage

#### Running Coverage

```bash
# Run tests with coverage
cd backend
uv run pytest tests/ --cov=app --cov-report=html --cov-report=term

# View coverage report
open htmlcov/index.html
```

#### Coverage Targets

| Component | Target | Current |
|-----------|--------|---------|
| Services | 90%+ | 94% |
| API Endpoints | 85%+ | 88% |
| Models | 100% | 100% |
| Utilities | 90%+ | 92% |
| **Overall** | **90%+** | **91%** |

#### Coverage Configuration

```ini
# backend/pyproject.toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"

[tool.coverage.run]
source = ["app"]
omit = [
    "*/tests/*",
    "*/migrations/*",
    "*/__pycache__/*"
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
]
```

## Frontend Testing

### Test Structure

```
frontend/tests/
├── unit/
│   ├── components/
│   │   ├── ConfigurationEditor.test.tsx
│   │   ├── ValidationPanel.test.tsx
│   │   └── MonacoEditor.test.tsx
│   ├── hooks/
│   │   ├── useValidation.test.ts
│   │   ├── useDebounce.test.ts
│   │   └── useCache.test.ts
│   └── utils/
│       ├── formatters.test.ts
│       └── validators.test.ts
├── integration/
│   ├── ValidationFlow.test.tsx
│   └── AutoFixFlow.test.tsx
└── setup.ts
```

### Component Testing (Vitest + React Testing Library)

#### Basic Component Test

```typescript
// tests/unit/components/ValidationPanel.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import ValidationPanel from '@/components/panels/ValidationPanel';

describe('ValidationPanel', () => {
  it('renders validation issues', () => {
    const issues = [
      {
        code: 'COLUMN_NOT_FOUND',
        severity: 'error',
        entity: 'test_entity',
        message: 'Column not found'
      }
    ];
    
    render(<ValidationPanel issues={issues} />);
    
    expect(screen.getByText('Column not found')).toBeInTheDocument();
    expect(screen.getByText('test_entity')).toBeInTheDocument();
  });
  
  it('calls onApplyFix when Apply Fix button clicked', async () => {
    const onApplyFix = vi.fn();
    const issues = [{
      code: 'COLUMN_NOT_FOUND',
      auto_fixable: true,
      suggestion: { /* ... */ }
    }];
    
    render(<ValidationPanel issues={issues} onApplyFix={onApplyFix} />);
    
    const applyButton = screen.getByRole('button', { name: /apply fix/i });
    fireEvent.click(applyButton);
    
    expect(onApplyFix).toHaveBeenCalledOnce();
  });
});
```

#### Testing Hooks

```typescript
// tests/unit/hooks/useDebounce.test.ts
import { renderHook, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { useDebounce } from '@/hooks/useDebounce';

describe('useDebounce', () => {
  it('debounces value changes', async () => {
    vi.useFakeTimers();
    
    const { result, rerender } = renderHook(
      ({ value }) => useDebounce(value, 500),
      { initialProps: { value: 'initial' } }
    );
    
    expect(result.current).toBe('initial');
    
    // Change value
    rerender({ value: 'changed' });
    expect(result.current).toBe('initial'); // Still old value
    
    // Fast-forward time
    vi.advanceTimersByTime(500);
    
    await waitFor(() => {
      expect(result.current).toBe('changed');
    });
    
    vi.useRealTimers();
  });
});
```

#### Testing with React Query

```typescript
// tests/unit/hooks/useValidation.test.ts
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi } from 'vitest';
import { useValidation } from '@/hooks/useValidation';
import * as api from '@/api/validation';

describe('useValidation', () => {
  it('fetches validation results', async () => {
    const queryClient = new QueryClient();
    const wrapper = ({ children }) => (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );
    
    vi.spyOn(api, 'validateConfiguration').mockResolvedValue({
      config_name: 'test',
      issues: [],
      summary: { total: 0 }
    });
    
    const { result } = renderHook(
      () => useValidation('test', 'all'),
      { wrapper }
    );
    
    expect(result.current.isLoading).toBe(true);
    
    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
      expect(result.current.data?.config_name).toBe('test');
    });
  });
});
```

### Performance Testing

#### React Component Performance

```typescript
// tests/performance/ValidationPanel.perf.test.tsx
import { render } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import ValidationPanel from '@/components/panels/ValidationPanel';

describe('ValidationPanel Performance', () => {
  it('renders 1000 issues in under 100ms', () => {
    const issues = Array.from({ length: 1000 }, (_, i) => ({
      code: `ISSUE_${i}`,
      severity: 'warning',
      entity: `entity_${i}`,
      message: `Issue ${i}`
    }));
    
    const startTime = performance.now();
    render(<ValidationPanel issues={issues} />);
    const endTime = performance.now();
    
    const renderTime = endTime - startTime;
    expect(renderTime).toBeLessThan(100);
  });
});
```

## E2E Testing

### Cross-Browser Testing

```bash
# Run cross-browser validation
FRONTEND_URL=http://localhost:5173 ./test_cross_browser.sh
```

#### Browser Detection

```bash
# test_cross_browser.sh
detect_browsers() {
  CHROME=$(command -v google-chrome || command -v chromium)
  FIREFOX=$(command -v firefox)
  EDGE=$(command -v microsoft-edge)
  
  if [ -n "$CHROME" ]; then
    echo "✓ Chrome/Chromium detected: $($CHROME --version)"
  fi
  if [ -n "$FIREFOX" ]; then
    echo "✓ Firefox detected: $($FIREFOX --version)"
  fi
}
```

#### Automated Validation Tests

```bash
# System check
test_backend_availability() {
  if curl -sf "$BACKEND_URL/health" > /dev/null; then
    echo "✓ PASS - Backend responds at $BACKEND_URL"
  else
    echo "✗ FAIL - Backend not responding"
    exit 1
  fi
}

test_frontend_availability() {
  if curl -sf "$FRONTEND_URL" > /dev/null; then
    echo "✓ PASS - Frontend responds at $FRONTEND_URL"
  else
    echo "✗ FAIL - Frontend not responding"
    exit 1
  fi
}

# Performance baseline
test_api_response_time() {
  START=$(date +%s%3N)
  curl -sf "$BACKEND_URL/health" > /dev/null
  END=$(date +%s%3N)
  DURATION=$((END - START))
  
  if [ $DURATION -lt 5000 ]; then
    echo "✓ PASS - API responds in ${DURATION}ms"
  else
    echo "⚠ WARNING - API slow: ${DURATION}ms"
  fi
}
```

### Manual Testing Procedures

See [CROSS_BROWSER_TESTING.md](CROSS_BROWSER_TESTING.md) for detailed manual testing procedures.

## Test Data Management

### Fixture Organization

```
tests/fixtures/
├── configs/
│   ├── valid/
│   │   ├── simple_config.yml
│   │   ├── complex_config.yml
│   │   └── nested_config.yml
│   ├── invalid/
│   │   ├── missing_entity.yml
│   │   ├── circular_deps.yml
│   │   └── invalid_syntax.yml
│   └── edge_cases/
│       ├── empty_config.yml
│       ├── large_config.yml
│       └── unicode_config.yml
└── data/
    ├── sample_data.csv
    └── test_database.db
```

### Generating Test Data

```python
# tests/fixtures/generators.py
import yaml
from pathlib import Path

def generate_test_config(name: str, entities: int = 5) -> dict:
    """Generate test configuration with specified number of entities."""
    config = {"entities": {}}
    
    for i in range(entities):
        config["entities"][f"entity_{i}"] = {
            "columns": [f"col_{j}" for j in range(3)],
            "keys": [f"col_0"],
            "source": None if i == 0 else f"entity_{i-1}"
        }
    
    return config

def save_test_config(name: str, config: dict, dir: Path):
    """Save test configuration to file."""
    path = dir / f"{name}.yml"
    with open(path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)
```

## Continuous Integration

### GitHub Actions Workflow

```yaml
# .github/workflows/tests.yml
name: Tests

on: [push, pull_request]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          cd backend
          pip install uv
          uv pip install -e ".[dev]"
      - name: Run tests
        run: |
          cd backend
          uv run pytest tests/ --cov=app --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./backend/coverage.xml

  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      - name: Install dependencies
        run: |
          cd frontend
          npm ci
      - name: Run tests
        run: |
          cd frontend
          npm run test:coverage
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./frontend/coverage/coverage-final.json
```

## Best Practices

### 1. Test Naming

```python
# Good - Describes what is being tested
def test_validate_configuration_returns_issues_for_missing_columns():
    pass

# Bad - Generic name
def test_validation():
    pass
```

### 2. Arrange-Act-Assert Pattern

```python
def test_apply_fix_removes_column():
    # Arrange - Setup test data and mocks
    config = {"entities": {"test": {"columns": ["col1", "missing"]}}}
    service = AutoFixService(mock_yaml, mock_config)
    
    # Act - Execute the code under test
    result = service.apply_fix(config, fix_action)
    
    # Assert - Verify the outcome
    assert "missing" not in result["entities"]["test"]["columns"]
```

### 3. Test Independence

```python
# Good - Each test is independent
@pytest.fixture
def fresh_database():
    db = create_test_db()
    yield db
    db.drop_all()

def test_one(fresh_database):
    # Uses fresh database
    pass

def test_two(fresh_database):
    # Uses fresh database, not affected by test_one
    pass
```

### 4. Meaningful Assertions

```python
# Good - Clear assertion messages
assert len(issues) == 3, f"Expected 3 issues, got {len(issues)}"
assert issue.code == "COLUMN_NOT_FOUND", \
    f"Wrong issue code: {issue.code}"

# Bad - No context on failure
assert len(issues) == 3
assert issue.code == "COLUMN_NOT_FOUND"
```

### 5. Test Documentation

```python
def test_validation_caching():
    """
    Test that validation results are cached for 5 minutes.
    
    This test verifies:
    1. First validation makes API call
    2. Second validation within 5 min uses cache
    3. Cache expires after 5 minutes
    4. Cache invalidates on config change
    
    Related:
    - ValidationService.validate_configuration
    - CacheService TTL settings
    """
    pass
```

## Debugging Tests

### Running Specific Tests

```bash
# Single test file
uv run pytest tests/test_auto_fix_service.py -v

# Single test function
uv run pytest tests/test_auto_fix_service.py::test_apply_fix_removes_column -v

# Tests matching pattern
uv run pytest -k "auto_fix" -v

# Failed tests only
uv run pytest --lf -v
```

### Debugging with pdb

```python
def test_complex_scenario():
    # Setup...
    
    import pdb; pdb.set_trace()  # Breakpoint
    
    result = service.do_something()
    
    assert result.success
```

### Verbose Output

```bash
# Show print statements
uv run pytest tests/ -v -s

# Show detailed assertion errors
uv run pytest tests/ -v -vv
```

## Related Documentation

- [Architecture Guide](DEVELOPER_GUIDE_ARCHITECTURE.md)
- [Cross-Browser Testing](CROSS_BROWSER_TESTING.md)
- [Contributing Guide](CONTRIBUTING.md)
- [CI/CD Pipeline](CI_CD.md)

---

**Version:** 1.0  
**Last Updated:** December 14, 2025  
**For:** Shape Shifter Configuration Editor v0.1.0
