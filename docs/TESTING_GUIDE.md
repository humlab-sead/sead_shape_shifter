# Testing Guide - Shape Shifter

## Overview

This comprehensive guide covers all testing strategies, procedures, and best practices for the Shape Shifter data transformation framework and its Configuration Editor UI.

## Table of Contents

- [Testing Philosophy](#testing-philosophy)
- [Test Types](#test-types)
- [Backend Testing](#backend-testing)
- [Frontend Testing](#frontend-testing)
- [Cross-Browser Testing](#cross-browser-testing)
- [Integration Testing](#integration-testing)
- [Manual Testing](#manual-testing)
- [Performance Testing](#performance-testing)
- [Accessibility Testing](#accessibility-testing)
- [Test Checklists](#test-checklists)
- [Test Data Management](#test-data-management)
- [Continuous Integration](#continuous-integration)
- [Troubleshooting](#troubleshooting)

---

## Testing Philosophy

### Core Principles

1. **Test Early, Test Often**: Integrate testing throughout the development lifecycle
2. **Test Coverage**: Aim for 80%+ code coverage on critical paths
3. **Test Pyramid**: More unit tests, fewer integration tests, minimal E2E tests
4. **Fast Feedback**: Tests should run quickly to enable rapid iteration
5. **Reliable Tests**: Tests should be deterministic and not flaky
6. **Clear Failures**: Test failures should clearly indicate what broke and why

### Testing Strategy

```
       /\
      /  \     E2E Tests (Few)
     /    \    - Full user workflows
    /------\   - Cross-browser validation
   /        \  - Critical paths only
  /          \
 / Integration\ Tests (Some)
/    Tests     \ - API integration
---------------  - Component integration
|              | - Database operations
|              |
|     Unit     | Tests (Many)
|    Tests     | - Business logic
|              | - Utility functions
|              | - Validators
|______________|
```

---

## Test Types

### 1. Unit Tests

**Purpose**: Test individual functions, methods, and classes in isolation

**Tools**:
- Backend: pytest
- Frontend: Vitest

**Characteristics**:
- Fast execution (<1ms per test)
- No external dependencies
- High coverage of edge cases
- Mock all external dependencies

### 2. Integration Tests

**Purpose**: Test interactions between components, modules, and services

**Tools**:
- Backend: pytest with fixtures
- Frontend: Vitest with MSW (Mock Service Worker)
- API: curl, pytest-requests

**Characteristics**:
- Test component interactions
- May use test databases
- Mock external services
- Verify data flow

### 3. End-to-End (E2E) Tests

**Purpose**: Test complete user workflows through the full stack

**Tools**:
- Playwright (future)
- Manual testing procedures

**Characteristics**:
- Slowest tests
- Highest confidence
- Test critical paths
- Use production-like environment

### 4. Visual Regression Tests

**Purpose**: Detect unintended UI changes

**Tools**:
- Percy (future)
- Manual cross-browser testing

**Characteristics**:
- Screenshot comparison
- Browser compatibility
- Responsive design verification

---

## Backend Testing

### Setup

```bash
cd /home/roger/source/sead_shape_shifter
uv venv
uv pip install -e ".[dev]"
```

### Running Tests

```bash
# Run all tests
make test

# Run with coverage
uv run pytest tests --cov=src --cov-report=html

# Run specific test file
uv run pytest tests/test_constraints.py -v

# Run specific test
uv run pytest -k test_foreign_key_validation

# Run with verbose output
uv run pytest tests -v

# Run only failed tests from last run
uv run pytest --lf
```

### Test Structure

```python
import pytest
from src.utility import with_test_config

@pytest.mark.asyncio
@with_test_config
async def test_entity_processing(self, test_provider):
    """Test entity processing with foreign key constraints."""
    # Arrange
    config = test_provider.get_config()
    normalizer = create_normalizer(config)
    
    # Act
    result = await normalizer.normalize()
    
    # Assert
    assert result is not None
    assert 'entity_name' in result
```

### Testing Async Code

All data loaders are async - use `pytest.mark.asyncio`:

```python
@pytest.mark.asyncio
async def test_csv_loader():
    """Test CSV data loader."""
    loader = CSVLoader(file_path="test.csv")
    data = await loader.load()
    assert len(data) > 0
```

### Mocking Async Functions

```python
async def mock_load(*args, **kwargs):
    return pd.DataFrame({"col1": [1, 2, 3]})

mock_loader.load = mock_load
```

### Test Fixtures

Common fixtures in `conftest.py`:

```python
@pytest.fixture
def sample_data():
    """Provide sample DataFrame for testing."""
    return pd.DataFrame({
        'id': [1, 2, 3],
        'name': ['A', 'B', 'C']
    })

@pytest.fixture
def config_provider(tmp_path):
    """Provide test configuration."""
    config_file = tmp_path / "test_config.yml"
    # ... setup config
    return ConfigProvider(config_file)
```

### Key Test Files

- `tests/test_constraints.py` - Foreign key constraint validation
- `tests/test_specifications.py` - Configuration validation
- `tests/test_append_processing.py` - Append configuration tests
- `tests/test_normalizer.py` - Entity processing tests
- `tests/test_unnest.py` - Wide-to-long transformation tests

---

## Frontend Testing

### Setup

```bash
cd frontend
npm install
```

### Running Tests

```bash
# Run all tests
npm test

# Run with coverage
npm run test:coverage

# Run in watch mode
npm run test:watch

# Run specific test file
npm test -- DataSourceSelector.test.jsx

# Run with UI
npm run test:ui
```

### Component Testing

```javascript
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import DataSourceSelector from './DataSourceSelector';

describe('DataSourceSelector', () => {
  it('renders data sources', async () => {
    render(<DataSourceSelector />);
    
    const selector = screen.getByRole('combobox');
    expect(selector).toBeInTheDocument();
  });
  
  it('calls onChange when selection changes', async () => {
    const handleChange = vi.fn();
    render(<DataSourceSelector onChange={handleChange} />);
    
    const selector = screen.getByRole('combobox');
    fireEvent.change(selector, { target: { value: 'test_sqlite' } });
    
    expect(handleChange).toHaveBeenCalledWith('test_sqlite');
  });
});
```

### Testing Async Components

```javascript
import { waitFor } from '@testing-library/react';

it('loads data sources from API', async () => {
  render(<DataSourceList />);
  
  await waitFor(() => {
    expect(screen.getByText('test_sqlite')).toBeInTheDocument();
  });
});
```

### Mocking API Calls

```javascript
import { setupServer } from 'msw/node';
import { http, HttpResponse } from 'msw';

const server = setupServer(
  http.get('/api/v1/data-sources', () => {
    return HttpResponse.json([
      { name: 'test_sqlite', driver: 'sqlite' }
    ]);
  })
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

### Testing User Interactions

```javascript
import userEvent from '@testing-library/user-event';

it('handles button click', async () => {
  const user = userEvent.setup();
  render(<SubmitForm />);
  
  const button = screen.getByRole('button', { name: /submit/i });
  await user.click(button);
  
  expect(screen.getByText('Submitted!')).toBeInTheDocument();
});
```

---

## Cross-Browser Testing

### Supported Browsers

| Browser | Minimum Version | Testing Priority | Notes |
|---------|----------------|------------------|-------|
| Chrome  | 120+          | **High**         | Primary development browser |
| Firefox | 115+          | **High**         | Second most used |
| Edge    | 120+          | **Medium**       | Chromium-based |
| Safari  | 16+           | **Medium**       | macOS/iOS users |

### Manual Cross-Browser Testing

#### 1. Start Development Servers

```bash
# Terminal 1: Backend
cd backend
uv run uvicorn app.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend
npm run dev
```

Frontend: http://localhost:5176

#### 2. Core Functionality Checklist

**All Browsers:**

- [ ] Configuration list view loads
- [ ] YAML editor displays and is editable
- [ ] Syntax highlighting works
- [ ] Validation panel displays results
- [ ] Error/warning counts accurate
- [ ] Expand/collapse functionality works
- [ ] Save configuration works
- [ ] Success notifications appear

#### 3. Feature-Specific Testing

**Validation Result Caching:**

1. Open a configuration
2. Click "Validate All"
3. Note request time in Network tab
4. Click "Validate All" again immediately
5. **Expected**: No new API request (cached)
6. Wait 5+ minutes
7. Click "Validate All" again
8. **Expected**: New API request (cache expired)

**Browser Notes:**
- Chrome: Check "Preserve log" in Network tab
- Firefox: Network tab auto-clears on reload
- Safari: Network tab under "Develop" menu

**Tooltips:**

1. Hover over "Validate All" button
2. Hover over validation tabs
3. Hover over entity validation buttons
4. Hover over "Apply Fix" buttons

**Expected:**
- Tooltip appears within 500ms
- Text is readable
- Tooltip disappears on mouse-out
- No overlapping elements

**Safari Note**: Tooltips may appear slower

**Loading Indicators:**

1. Click "Validate All"
2. Observe loading skeleton

**Expected:**
- Skeleton appears immediately
- Realistic multi-line structure
- Smooth pulsing animation
- Instant replacement when data loads
- No flash of empty content

**Performance Tip**: Throttle to "Slow 3G" to see skeleton longer

**Success Animations:**

1. Make YAML change
2. Save configuration
3. Observe success notification

**Expected:**
- Smooth scale-in transition (~300ms)
- No stuttering
- Auto-dismiss after 3 seconds
- GPU-accelerated (no jank)

**Debounced Validation:**

1. Type rapidly in YAML editor
2. Monitor Network tab

**Expected:**
- Validation waits 500ms after last keystroke
- Only one request after typing stops
- No "validation storm"
- Typing remains responsive

### Browser-Specific Testing

#### Chrome (Primary)

**DevTools**: `F12` or `Ctrl+Shift+I` / `Cmd+Option+I`

**Key Tests:**
- Console warnings/errors
- Network timing
- Performance profiling
- Memory usage

#### Firefox

**DevTools**: `F12` or `Ctrl+Shift+I` / `Cmd+Option+I`

**Key Tests:**
- CSS Grid Inspector
- Accessibility inspector
- Storage inspector (cache)

**Common Issues:**
- CSS variable differences
- Flexbox quirks
- Font rendering

#### Edge

**DevTools**: Same as Chrome (Chromium-based)

**Key Tests:**
- Windows-specific rendering
- High DPI scaling
- Touch input

#### Safari

**Enable Developer Tools**:
1. Safari → Settings → Advanced
2. Check "Show Develop menu in menu bar"

**DevTools**: `Cmd+Option+I`

**Key Tests:**
- WebKit-specific rendering
- Touch gestures
- Mobile Safari simulation

**Common Issues:**
- CSS Grid gaps
- Flexbox `gap` property
- Backdrop filters
- Scrollbar styling

### Performance Metrics

**Target Metrics (All Browsers):**

1. **Initial Page Load**: < 2 seconds
2. **Validation Response**: < 5 seconds
3. **UI Responsiveness**: 60 FPS during animations
4. **Memory Usage**: < 100MB after 10 minutes

**Measuring Performance:**

```javascript
// In DevTools Console
performance.mark('validation-start');
// Click "Validate All"
performance.mark('validation-end');
performance.measure('validation', 'validation-start', 'validation-end');
console.table(performance.getEntriesByType('measure'));
```

### Cross-Browser Test Results Template

```markdown
### Cross-Browser Test Results - [Date]

**Tester**: [Name]

| Feature | Chrome | Firefox | Edge | Safari | Notes |
|---------|--------|---------|------|--------|-------|
| Config List | ✅ | ✅ | ✅ | ⚠️ | Safari: Slow loading |
| YAML Editor | ✅ | ✅ | ✅ | ✅ | - |
| Validation Cache | ✅ | ✅ | ✅ | ❌ | Safari: Cache not working |
| Tooltips | ✅ | ✅ | ✅ | ⚠️ | Safari: Delayed |
| Loading Skeleton | ✅ | ✅ | ✅ | ✅ | - |
| Success Animation | ✅ | ✅ | ✅ | ✅ | - |

**Legend:**
- ✅ Pass - Works as expected
- ⚠️ Minor Issue - Works with minor problems
- ❌ Fail - Does not work
- ⏸️ Blocked - Cannot test
```

---

## Integration Testing

### Backend API Testing

#### Prerequisites

```bash
# Check backend running
curl -s http://localhost:8000/api/v1/health | python3 -m json.tool
# Expected: {"status": "healthy", "version": "0.1.0"}

# Check frontend running
timeout 3 curl -s http://localhost:5173 > /dev/null && echo "✓ OK" || echo "✗ Failed"

# Check test database
ls -lh input/test_query_tester.db
```

#### API Test Checklist

**Health Check:**

```bash
curl -s http://localhost:8000/api/v1/health | python3 -m json.tool
```

**Data Sources:**

```bash
# List data sources
curl -s http://localhost:8000/api/v1/data-sources | python3 -m json.tool

# Get specific data source
curl -s http://localhost:8000/api/v1/data-sources/test_sqlite | python3 -m json.tool
```

**Schema Introspection:**

```bash
# List tables
curl -s http://localhost:8000/api/v1/data-sources/test_sqlite/tables | python3 -m json.tool

# Get table schema
curl -s "http://localhost:8000/api/v1/data-sources/test_sqlite/tables/users/schema" | python3 -m json.tool

# Preview table data
curl -s "http://localhost:8000/api/v1/data-sources/test_sqlite/tables/users/preview?limit=3" | python3 -m json.tool
```

**Error Handling:**

```bash
# Non-existent data source
curl -s http://localhost:8000/api/v1/data-sources/invalid_source | python3 -m json.tool
# Expected: 404 error

# Non-existent table
curl -s "http://localhost:8000/api/v1/data-sources/test_sqlite/tables/invalid_table/schema" | python3 -m json.tool
# Expected: Error message
```

#### Quick Backend Test Script

```bash
cd /home/roger/source/sead_shape_shifter

echo "=== Quick Backend Test ==="
curl -s http://localhost:8000/api/v1/health | python3 -c "import sys, json; d=json.load(sys.stdin); print('✓ Health:', d['status'])" && \
curl -s http://localhost:8000/api/v1/data-sources | python3 -c "import sys, json; d=json.load(sys.stdin); print('✓ Data sources:', [x['name'] for x in d])" && \
curl -s http://localhost:8000/api/v1/data-sources/test_sqlite/tables | python3 -c "import sys, json; d=json.load(sys.stdin); print('✓ Tables:', [x['name'] for x in d])" && \
curl -s "http://localhost:8000/api/v1/data-sources/test_sqlite/tables/users/schema" | python3 -c "import sys, json; d=json.load(sys.stdin); print('✓ Schema:', len(d['columns']), 'columns')" && \
echo "=== All APIs Working ==="
```

### Frontend Integration Testing

#### Application Loading

- [ ] Frontend loads at http://localhost:5173
- [ ] No JavaScript errors in console
- [ ] Navigation menu visible
- [ ] Page renders correctly

#### Query Tester Integration

**Navigation:**

- [ ] Click "Query Tester" in menu
- [ ] Page displays two tabs: "SQL Editor" and "Visual Builder"
- [ ] Default tab is "SQL Editor"

**Visual Builder - Basic Flow:**

1. Click "Visual Builder" tab
2. Component loads without errors
3. Data source selector enabled
4. Table selector disabled initially
5. Column selector disabled initially

**Data Source Selection:**

1. Click data source dropdown
2. **Expected**: "test_sqlite" appears
3. Select "test_sqlite"
4. **Expected**: Table selector enables, loading indicator appears

**Table Selection:**

1. Click table dropdown
2. **Expected**: 3 tables appear (orders, products, users)
3. Select "users" table
4. **Expected**: Column selector enables, columns load automatically

**Column Selection:**

1. Click column selector
2. **Expected**: 6 columns appear (user_id, username, email, age, created_at, is_active)
3. Click "Select All"
4. **Expected**: All columns selected, SQL preview shows `SELECT * FROM "users" LIMIT 100`
5. Unselect some columns
6. **Expected**: SQL updates to show only selected columns

**WHERE Conditions:**

1. Expand "WHERE Conditions" section
2. Click "Add Condition"
3. Set: `age > 30`
4. **Expected**: SQL shows `WHERE "age" > 30`
5. Add second condition: `is_active = 1`
6. **Expected**: SQL shows both conditions with AND
7. Toggle to OR
8. **Expected**: SQL changes to use OR

**Test All Operators:**

- [ ] Equals (=)
- [ ] Not Equals (!=)
- [ ] Less than (<)
- [ ] Greater than (>)
- [ ] IS NULL
- [ ] IS NOT NULL
- [ ] LIKE
- [ ] NOT LIKE
- [ ] IN
- [ ] NOT IN
- [ ] BETWEEN

**ORDER BY:**

1. Expand "ORDER BY" section
2. Click "Add ORDER BY"
3. Set: username ASC
4. **Expected**: SQL includes `ORDER BY "username" ASC`
5. Add second order: age DESC
6. **Expected**: SQL shows `ORDER BY "username" ASC, "age" DESC`

**LIMIT:**

1. Change LIMIT to 5
2. **Expected**: SQL shows `LIMIT 5`
3. Clear LIMIT field
4. **Expected**: LIMIT clause removed
5. Set back to 100

**Generate and Use Query:**

1. Click "Generate SQL"
2. **Expected**: SQL preview updates, "Use This Query" button enables
3. Click "Use This Query"
4. **Expected**: Switches to SQL Editor tab, SQL loaded into editor

**Clear Builder:**

1. Click "Clear" button
2. **Expected**: All selections reset, SQL preview cleared

### API Error Simulation

**Test Error Handling:**

```bash
# Stop backend
pkill -f "uvicorn backend.app.main:app"
```

1. Try selecting data source in UI
2. **Expected**: Error message appears, UI handles gracefully
3. Check console for error logging

```bash
# Restart backend
cd /home/roger/source/sead_shape_shifter && \
CONFIG_FILE=input/query_tester_config.yml \
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 > /tmp/backend.log 2>&1 &
```

4. Refresh page
5. **Expected**: Functionality restored

### Complex Query End-to-End Test

**Build Complex Query:**

1. Select data source: test_sqlite
2. Select table with 10+ columns
3. Select 5-7 specific columns
4. Add 3 WHERE conditions with OR logic
5. Add 2 ORDER BY columns (ASC + DESC)
6. Set LIMIT to 500
7. **Expected**: Valid SQL generated with all clauses

**Execute Complex Query:**

1. Click "Use This Query"
2. Switch to SQL Editor
3. Click "Execute Query"
4. **Expected**: Results display correctly
5. **Expected**: Pagination works
6. **Expected**: Export to CSV works

---

## Manual Testing

### Configuration Editor Testing

#### Create New Configuration

1. Navigate to configuration list
2. Click "Create New Configuration"
3. Enter configuration name
4. **Expected**: New config created, editor opens

#### Edit Configuration

1. Open existing configuration
2. Modify YAML content
3. Click "Save"
4. **Expected**: Success notification, changes saved
5. Refresh page
6. **Expected**: Changes persisted

#### Validation Workflow

1. Open configuration with errors
2. Click "Validate All"
3. **Expected**: Validation results appear
4. **Expected**: Error count displayed
5. Click "Structural" tab
6. **Expected**: Structural validations shown
7. Click "Data" tab
8. **Expected**: Data validations shown
9. Expand error details
10. **Expected**: Error message and location shown

#### Auto-Fix Feature

1. Open configuration with fixable errors
2. Run validation
3. Find suggestion with "Apply Fix" button
4. Click "Apply Fix"
5. **Expected**: YAML updated automatically
6. **Expected**: Success notification
7. Run validation again
8. **Expected**: Error resolved

#### Entity Validation

1. Select entity from entity list
2. Click "Validate Entity"
3. **Expected**: Only that entity's validations run
4. **Expected**: Results filtered to entity

### Query Builder Testing

#### Basic SQL Generation

1. Select data source
2. Select table
3. Select columns
4. **Expected**: Valid SQL generated
5. Verify SQL syntax

#### Complex Query Building

1. Build query with:
   - Multiple columns
   - 3+ WHERE conditions
   - 2+ ORDER BY clauses
   - Custom LIMIT
2. **Expected**: All clauses in SQL
3. **Expected**: Correct syntax

#### Query Execution

1. Generate query
2. Transfer to SQL Editor
3. Execute query
4. **Expected**: Results display
5. **Expected**: Statistics accurate
6. Export to CSV
7. **Expected**: File downloads
8. Open CSV file
9. **Expected**: Data correct

### Error Scenarios

#### Syntax Errors

1. Enter invalid YAML
2. Run validation
3. **Expected**: Syntax error displayed
4. **Expected**: Line number indicated

#### Missing References

1. Reference non-existent entity
2. Run validation
3. **Expected**: Error about missing entity

#### Circular Dependencies

1. Create circular entity dependencies
2. Run validation
3. **Expected**: Error about circular dependency

#### Invalid SQL

1. Enter malformed SQL in Query Tester
2. Execute query
3. **Expected**: Syntax error message
4. **Expected**: No server crash

#### Destructive SQL Prevention

1. Enter DELETE query
2. Execute
3. **Expected**: "Destructive operation not allowed" error
4. Test with: INSERT, UPDATE, DROP, CREATE, ALTER, TRUNCATE
5. **Expected**: All blocked

---

## Performance Testing

### Backend Performance

#### Metrics to Monitor

1. **Configuration Loading**: < 1 second
2. **Validation Execution**: < 5 seconds
3. **Entity Processing**: < 10 seconds per entity
4. **API Response Time**: < 500ms (excluding data processing)

#### Performance Test Script

```python
import time
import asyncio
from src.normalizer import ShapeShifter

async def test_performance():
    start = time.time()
    
    # Load configuration
    config_time = time.time()
    normalizer = ShapeShifter("config.yml")
    print(f"Config load: {time.time() - config_time:.2f}s")
    
    # Process entities
    process_time = time.time()
    result = await normalizer.normalize()
    print(f"Processing: {time.time() - process_time:.2f}s")
    
    print(f"Total: {time.time() - start:.2f}s")

asyncio.run(test_performance())
```

### Frontend Performance

#### Metrics to Monitor

1. **Initial Load**: < 2 seconds
2. **Component Render**: < 100ms
3. **API Call**: < 1 second
4. **UI Interaction**: < 50ms
5. **Animation Frame Rate**: 60 FPS

#### Performance Testing in DevTools

```javascript
// Measure component render
performance.mark('render-start');
// Component renders
performance.mark('render-end');
performance.measure('render', 'render-start', 'render-end');
console.table(performance.getEntriesByType('measure'));
```

### Load Testing

#### API Load Test

```bash
# Install Apache Bench
sudo apt-get install apache2-utils

# Test health endpoint
ab -n 1000 -c 10 http://localhost:8000/api/v1/health

# Test data sources endpoint
ab -n 500 -c 5 http://localhost:8000/api/v1/data-sources
```

**Target Metrics:**
- **Requests per second**: > 100
- **Mean response time**: < 100ms
- **Failed requests**: 0

#### Stress Testing

```bash
# Concurrent validation requests
for i in {1..10}; do
  curl -X POST http://localhost:8000/api/v1/validate &
done
wait
```

**Expected:**
- All requests complete successfully
- No timeouts
- No memory leaks
- Server remains responsive

### Memory Profiling

#### Backend Memory

```bash
# Install memory_profiler
uv pip install memory-profiler

# Profile script
python -m memory_profiler src/normalizer.py
```

**Target**: < 500MB peak memory usage

#### Frontend Memory

1. Open DevTools → Memory
2. Take heap snapshot
3. Interact with application
4. Take another snapshot
5. Compare snapshots

**Expected:**
- No detached DOM nodes
- No memory leaks
- < 100MB after 10 minutes of use

---

## Accessibility Testing

### Keyboard Navigation

**Test Checklist:**

- [ ] Tab through all interactive elements
- [ ] Tab order is logical
- [ ] Enter/Space activates buttons
- [ ] Arrow keys navigate lists
- [ ] Escape closes modals/dialogs
- [ ] Focus indicators clearly visible
- [ ] No keyboard traps

### Screen Reader Testing

**Tools:**
- **Windows**: NVDA (free) with Firefox
- **macOS**: VoiceOver (built-in) with Safari
- **Linux**: Orca with Firefox

**Test Checklist:**

- [ ] All buttons have accessible labels
- [ ] Form inputs have associated labels
- [ ] Validation errors announced
- [ ] Loading states announced
- [ ] Success messages announced
- [ ] Table headers properly marked
- [ ] Landmarks (navigation, main, etc.) defined

### ARIA Attributes

**Verify:**

- [ ] `role` attributes appropriate
- [ ] `aria-label` on icon-only buttons
- [ ] `aria-describedby` for hints/errors
- [ ] `aria-live` for dynamic content
- [ ] `aria-expanded` for collapsible sections
- [ ] `aria-current` for navigation

### Color Contrast

**Tools:**
- WAVE browser extension
- axe DevTools
- Chrome Lighthouse

**Requirements:**
- **Normal text**: 4.5:1 minimum
- **Large text**: 3:1 minimum
- **UI components**: 3:1 minimum

### Accessibility Test Tools

```bash
# Install axe-core
npm install -D @axe-core/playwright

# Run accessibility tests
npx playwright test --project=accessibility
```

---

## Test Checklists

### Pre-Release Checklist

**Backend:**

- [ ] All unit tests passing
- [ ] Integration tests passing
- [ ] No linting errors
- [ ] Code coverage > 80%
- [ ] API documentation updated
- [ ] Performance benchmarks met
- [ ] Security scan clean

**Frontend:**

- [ ] All component tests passing
- [ ] Integration tests passing
- [ ] No console errors/warnings
- [ ] Cross-browser testing complete
- [ ] Accessibility audit passed
- [ ] Performance metrics met
- [ ] UI matches designs

**Integration:**

- [ ] API integration tests passing
- [ ] E2E critical paths tested
- [ ] Error handling verified
- [ ] Data validation working
- [ ] Export functionality working

**Documentation:**

- [ ] README updated
- [ ] API docs current
- [ ] User guide updated
- [ ] Developer guide updated
- [ ] CHANGELOG updated

### Feature Testing Checklist

**For Each New Feature:**

- [ ] Unit tests written (80%+ coverage)
- [ ] Integration tests added
- [ ] Manual testing performed
- [ ] Cross-browser testing done
- [ ] Accessibility verified
- [ ] Performance validated
- [ ] Documentation updated
- [ ] Error handling tested
- [ ] Edge cases covered
- [ ] Backwards compatibility verified

### Bug Fix Checklist

**For Each Bug Fix:**

- [ ] Bug reproduced in test
- [ ] Root cause identified
- [ ] Fix implemented
- [ ] Test passes
- [ ] Regression tests added
- [ ] Related areas tested
- [ ] Documentation updated (if needed)
- [ ] Code reviewed

---

## Test Data Management

### Test Databases

#### SQLite Test Database

```bash
# Create test database
sqlite3 input/test_query_tester.db < scripts/create_test_db.sql
```

**Tables:**
- `users` - Sample user data (100 rows)
- `products` - Sample product data (50 rows)
- `orders` - Sample order data (200 rows)

#### PostgreSQL Test Database

```bash
# Create test database
psql -U postgres -c "CREATE DATABASE shape_shifter_test;"

# Load test data
psql -U postgres -d shape_shifter_test -f scripts/test_data.sql
```

### Test Fixtures

**Backend Fixtures:**

```python
@pytest.fixture
def sample_config():
    """Sample configuration for testing."""
    return {
        'entities': {
            'users': {
                'type': 'csv',
                'source': 'test_users.csv',
                'keys': ['user_id']
            }
        }
    }

@pytest.fixture
def sample_dataframe():
    """Sample DataFrame for testing."""
    return pd.DataFrame({
        'id': [1, 2, 3],
        'name': ['Alice', 'Bob', 'Charlie'],
        'age': [25, 30, 35]
    })
```

**Frontend Fixtures:**

```javascript
export const mockDataSources = [
  { name: 'test_sqlite', driver: 'sqlite', path: 'test.db' },
  { name: 'test_postgres', driver: 'postgresql', host: 'localhost' }
];

export const mockTableSchema = {
  name: 'users',
  columns: [
    { name: 'user_id', type: 'INTEGER', primary_key: true },
    { name: 'username', type: 'TEXT' },
    { name: 'email', type: 'TEXT' }
  ],
  primary_keys: ['user_id']
};
```

### Seed Data Scripts

```bash
# Generate test data
python scripts/generate_test_data.py \
  --entities 3 \
  --rows-per-entity 100 \
  --output input/test_data/
```

---

## Continuous Integration

### GitHub Actions Workflow

```yaml
name: CI

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
          pip install uv
          uv pip install -e ".[dev]"
      - name: Run tests
        run: uv run pytest tests --cov=src --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3
  
  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      - name: Install dependencies
        run: cd frontend && npm ci
      - name: Run tests
        run: cd frontend && npm test
      - name: Run linting
        run: cd frontend && npm run lint
```

### Pre-Commit Hooks

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install
```

**.pre-commit-config.yaml:**

```yaml
repos:
  - repo: local
    hooks:
      - id: pytest
        name: pytest
        entry: pytest
        language: system
        pass_filenames: false
        always_run: true
      
      - id: black
        name: black
        entry: black
        language: system
        types: [python]
      
      - id: ruff
        name: ruff
        entry: ruff check
        language: system
        types: [python]
```

### Test Coverage Requirements

**Backend:**
- **Overall coverage**: 80% minimum
- **Critical modules**: 90% minimum
  - `src/constraints.py`
  - `src/specifications.py`
  - `src/normalizer.py`
- **Exclude from coverage**:
  - `tests/`
  - `scripts/`
  - `__init__.py` files

**Frontend:**
- **Overall coverage**: 70% minimum
- **Components**: 80% minimum
- **Utilities**: 90% minimum
- **Exclude**:
  - `*.config.js`
  - `*.test.jsx`

---

## Troubleshooting

### Common Test Failures

#### Import Errors

**Problem**: `ModuleNotFoundError: No module named 'src'`

**Solution**:
```bash
# Use absolute imports
PYTHONPATH=. python -m pytest tests/

# Or install package in editable mode
uv pip install -e .
```

#### Async Test Failures

**Problem**: `RuntimeError: Event loop is closed`

**Solution**:
```python
# Ensure pytest-asyncio installed
# Add decorator to async tests
@pytest.mark.asyncio
async def test_async_function():
    result = await async_operation()
    assert result
```

#### Database Lock Errors

**Problem**: `database is locked` in SQLite tests

**Solution**:
```python
# Use separate test database per test
@pytest.fixture
def test_db(tmp_path):
    db_path = tmp_path / "test.db"
    # Create and return database
    return db_path
```

#### API Connection Errors

**Problem**: `Connection refused` in integration tests

**Solution**:
```bash
# Ensure backend is running
curl http://localhost:8000/api/v1/health

# Check port not already in use
lsof -i :8000

# Restart backend
pkill -f uvicorn
uvicorn backend.app.main:app --port 8000
```

#### Frontend Build Failures

**Problem**: `Module not found` or `Cannot find module`

**Solution**:
```bash
# Clear node_modules and reinstall
cd frontend
rm -rf node_modules package-lock.json
npm install

# Clear Vite cache
rm -rf node_modules/.vite
```

### Test Environment Issues

#### Python Version Mismatch

```bash
# Check Python version
python --version

# Use correct Python with uv
uv python install 3.11
uv venv --python 3.11
```

#### Missing Dependencies

```bash
# Backend
uv pip install -e ".[dev]"

# Frontend
cd frontend
npm install
```

#### Configuration File Not Found

```bash
# Set environment variable
export CONFIG_FILE=input/test_config.yml

# Or pass as argument
python script.py --config-file input/test_config.yml
```

### Performance Test Issues

#### Slow Tests

**Problem**: Tests take too long

**Solutions**:
1. Use smaller test datasets
2. Mock expensive operations
3. Parallel test execution:
   ```bash
   pytest -n auto
   ```
4. Skip slow tests during development:
   ```python
   @pytest.mark.slow
   def test_expensive_operation():
       pass
   
   # Run without slow tests
   pytest -m "not slow"
   ```

#### Memory Leaks

**Problem**: Memory usage grows during tests

**Solutions**:
1. Clear caches between tests:
   ```python
   @pytest.fixture(autouse=True)
   def clear_caches():
       # Clear application caches
       yield
       # Cleanup
   ```
2. Use weak references for observers
3. Profile memory usage:
   ```bash
   python -m memory_profiler tests/test_file.py
   ```

---

## Testing Resources

### Documentation

- [pytest Documentation](https://docs.pytest.org/)
- [Vitest Guide](https://vitest.dev/guide/)
- [Playwright Documentation](https://playwright.dev/)
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)

### Tools

**Testing Frameworks:**
- pytest - Python testing
- Vitest - JavaScript testing
- Playwright - E2E testing

**Code Coverage:**
- pytest-cov - Python coverage
- Vitest coverage - JavaScript coverage
- Codecov - Coverage reporting

**Accessibility:**
- WAVE - Browser extension
- axe DevTools - Accessibility testing
- Lighthouse - Chrome audit tool

**Performance:**
- Chrome DevTools - Performance profiling
- memory_profiler - Python memory profiling
- Apache Bench - Load testing

### Best Practices

1. **Write Tests First**: TDD approach when possible
2. **Keep Tests Fast**: Unit tests < 1ms, integration < 1s
3. **Test One Thing**: Each test should verify one behavior
4. **Clear Test Names**: `test_feature_scenario_expectedResult`
5. **Use Fixtures**: Avoid duplication with fixtures
6. **Mock External Dependencies**: Keep tests isolated
7. **Test Edge Cases**: Null, empty, boundary values
8. **Clean Up**: Always clean up test data/state
9. **Document Tests**: Complex tests need explanations
10. **Review Coverage**: Regularly check coverage reports

---

## Summary

This testing guide provides comprehensive procedures for:

- **Backend Testing**: pytest, fixtures, async testing
- **Frontend Testing**: Vitest, component testing
- **Cross-Browser Testing**: Manual procedures for Chrome, Firefox, Edge, Safari
- **Integration Testing**: API testing, E2E workflows
- **Performance Testing**: Metrics, profiling, load testing
- **Accessibility Testing**: Keyboard navigation, screen readers, ARIA
- **Test Management**: Checklists, fixtures, CI/CD integration

Follow these procedures to ensure the Shape Shifter system maintains high quality, reliability, and user experience across all browsers and platforms.
