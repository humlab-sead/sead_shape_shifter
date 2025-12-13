# Backend Integration with Shape Shifter Core

## Architecture Overview

This project consists of two Python packages:

1. **shape-shifter** (root): Core data transformation framework
   - Location: `./src/`
   - Package: `src.*` modules (configuration, normalizer, etc.)
   
2. **shape-shifter-editor-backend** (backend): REST API for configuration editing
   - Location: `./backend/`
   - Depends on: Main shape-shifter package
   - Imports: `src.configuration.provider`, `src.config_model`, etc.

## Solution: Package Dependency

The backend is configured to depend on the main `shape-shifter` package. This approach:

✅ Maintains clean separation between core and API  
✅ Follows standard Python packaging practices  
✅ Works for both development and production  
✅ Eliminates PYTHONPATH hacks  
✅ Allows independent deployment if needed  

## Installation

### Automated (Recommended)

```bash
# Install both main package and backend
make ui-install
```

This will:
1. Install main package in editable mode: `uv pip install -e .`
2. Install backend with dependencies: `cd backend && uv pip install -e ".[dev]"`
3. Install frontend dependencies: `cd frontend && pnpm install`

### Manual

```bash
# 1. Install main package (from root directory)
uv pip install -e .

# 2. Install backend (from root directory)
cd backend
uv pip install -e ".[dev]"
cd ..

# 3. Install frontend (from root directory)
cd frontend
pnpm install
cd ..
```

## Running the Backend

### Using Make (Recommended)

```bash
# Start backend server with default test config
make backend-run

# Or specify a custom config
CONFIG_FILE=input/arbodat.yml make backend-run
```

### Manual

```bash
cd backend
CONFIG_FILE=input/query_tester_config.yml \
  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## How It Works

### 1. Main Package Configuration

**File:** `pyproject.toml` (root)

```toml
[project]
name = "shape-shifter"
version = "1.2.0"

[tool.setuptools]
packages = { find = { where = ["."], include = ["src*"] } }
```

This exposes `src/` modules when the package is installed.

### 2. Backend Dependencies

**File:** `backend/pyproject.toml`

```toml
[project]
name = "shape-shifter-editor-backend"
dependencies = [
    "shape-shifter",  # Main package dependency
    "fastapi==0.115.6",
    ...
]
```

The backend declares its dependency on the main package.

### 3. Editable Installation

During development, both packages are installed in **editable mode** (`-e` flag):

```bash
pip install -e .                    # Main package
pip install -e ./backend            # Backend package
```

Editable mode means:
- Changes to source code take effect immediately
- No need to reinstall after code changes
- Imports work as if packages were installed from PyPI

### 4. Import Resolution

Backend code can now import directly:

```python
# backend/app/api/dependencies.py
from src.configuration.provider import ConfigProvider, get_config_provider
from src.configuration.config_model import ConfigLike
```

Python resolves these imports through the installed `shape-shifter` package.

## Alternative Approaches (Not Recommended)

### ❌ PYTHONPATH Manipulation

```bash
# DON'T DO THIS
export PYTHONPATH=/path/to/project:$PYTHONPATH
```

**Problems:**
- Fragile across different environments
- Breaks in production/Docker
- Not portable
- IDE integration issues

### ❌ sys.path Hacking

```python
# DON'T DO THIS
import sys
sys.path.insert(0, '..')
```

**Problems:**
- Relative paths break easily
- Not testable
- Anti-pattern in Python

### ❌ Monolithic Structure

Merging backend into main project as `src/backend/`

**Problems:**
- Couples API to core logic
- Backend dependencies pollute main package
- Harder to deploy independently

## Deployment Scenarios

### Development

```bash
# Install both packages in editable mode
make ui-install

# Run backend and frontend
make backend-run
make frontend-run
```

### Production (Docker)

**Dockerfile:**
```dockerfile
FROM python:3.13-slim

# Install main package
COPY pyproject.toml setup.py ./
COPY src/ src/
RUN pip install .

# Install backend
COPY backend/pyproject.toml backend/
COPY backend/app/ backend/app/
RUN pip install ./backend

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Production (Separate Servers)

If deploying backend separately:

```bash
# Build and publish main package to private PyPI
cd /path/to/shape-shifter
python -m build
twine upload --repository private dist/*

# Install backend with main package from PyPI
cd /path/to/deployment
pip install shape-shifter --extra-index-url https://private-pypi.com
pip install ./backend
```

## Troubleshooting

### Import Errors: "No module named 'src'"

**Cause:** Main package not installed

**Solution:**
```bash
uv pip install -e .  # From root directory
```

### Import Errors in Backend

**Cause:** Backend dependencies not installed

**Solution:**
```bash
cd backend
uv pip install -e ".[dev]"
```

### Configuration Not Loading

**Cause:** CONFIG_FILE environment variable not set

**Solution:**
```bash
CONFIG_FILE=input/query_tester_config.yml make backend-run
```

### Changes Not Taking Effect

**Cause:** Package installed in non-editable mode

**Solution:**
```bash
uv pip uninstall shape-shifter shape-shifter-editor-backend
make ui-install  # Reinstall in editable mode
```

## Testing

### Backend Tests

```bash
# Run backend tests (uses installed main package)
make backend-test

# Or manually
cd backend
uv run pytest -v
```

### Integration Tests

Backend tests automatically have access to `src.*` modules through the installed package dependency.

## IDE Configuration

### VS Code

Add to `.vscode/settings.json`:

```json
{
  "python.analysis.extraPaths": [
    "./src",
    "./backend"
  ]
}
```

### PyCharm

1. Go to Settings → Project → Project Structure
2. Mark `src/` as "Sources Root"
3. Mark `backend/app/` as "Sources Root"

## Benefits of This Approach

1. **Standard Python Practice**: Uses established packaging conventions
2. **Clean Architecture**: Clear separation between core and API
3. **Portable**: Works in any environment (dev, CI/CD, production)
4. **Testable**: Tests work without path manipulation
5. **IDE-Friendly**: IDEs understand package structure
6. **Deployable**: Can deploy backend independently if needed
7. **Maintainable**: Clear dependencies between components

## Summary

The backend integration uses **proper Python package dependencies** rather than PYTHONPATH or sys.path manipulation. This follows best practices and makes the codebase maintainable, testable, and deployable.

**Key Commands:**
```bash
make ui-install       # Install everything
make backend-run      # Run backend
make backend-test     # Test backend
```
