# SEAD Shape Shifter

A declarative data transformation framework combining a Python-based processing engine with a web-based configuration editor. Shape Shifter harmonizes diverse data sources into target schemas through YAML-based project definitions, automated validation, and intelligent error correction.

Developed for archaeological data integration with the Strategic Environmental Archaeology Database (SEAD), the framework is designed for general-purpose data transformation across domains.

## Overview

Shape Shifter consists of three integrated components:

### Core Transformation Engine

A Python-based pipeline system for processing data transformations defined in YAML:

- Extract data from CSV, Excel, SQL databases (PostgreSQL, MS Access via UCanAccess)
- Filter records based on configurable criteria
- Link entities through foreign key relationships with constraint validation
- Unnest wide-format data into normalized structures
- Map column names and translate values to target schemas
- Export to CSV, Excel, or database systems

### Web-Based Configuration Editor

A Vue 3 application for creating and managing transformation projects:

- Monaco Editor integration with YAML syntax highlighting
- Real-time structural and data validation
- Visual entity tree navigation and form-based property editing
- Multi-layer caching for improved performance
- Cross-browser compatibility (Chrome, Firefox, Safari, Edge)

### REST API Backend

A FastAPI service providing programmatic access to transformation operations:

- Project file management and validation
- Entity preview with intelligent caching
- Schema introspection for connected databases
- Auto-fix generation and application
- Dependency analysis and topological sorting

## Key Features

### Data Processing

- Declarative YAML configuration for transformation pipelines
- Automatic dependency resolution with topological sorting
- Foreign key relationship management with surrogate key generation
- Comprehensive constraint validation:
  - Cardinality enforcement (one-to-one, many-to-one, one-to-many, many-to-many)
  - Match requirements and uniqueness constraints
  - Null value handling and row count validation
- Multiple output formats (CSV, Excel, database)
- Extensible loader architecture for custom data sources

### Configuration Management

- Monaco Editor integration for YAML editing
- Dual-mode entity editor (visual form and code editor)
- Multi-type validation (structural, data, entity-specific, comprehensive)
- Automated fix suggestions with preview and rollback
- Visual dependency tree and properties panel
- Intelligent caching with hash-based invalidation
- Contextual help and error diagnostics

## Quick Start with Docker

Deploy Shape Shifter using Docker for the fastest setup:

```bash
# Clone the repository
git clone https://github.com/humlab-sead/sead_shape_shifter.git
cd sead_shape_shifter/docker

# Setup and start (uses Makefile for convenience)
make setup          # Create directories and environment files
make docker-build   # Build the container
make docker-up      # Start the application
```

The unified container provides both the backend API and frontend UI:

- Frontend: http://localhost:8012/
- API Documentation: http://localhost:8012/api/v1/docs
- Health Endpoint: http://localhost:8012/api/v1/health

For detailed Docker deployment options, see [docker/README.md](docker/README.md).

## Developer Installation

### Prerequisites

- Python 3.13 or higher
- Java Runtime Environment (for MS Access database support via UCanAccess)
- pnpm (for frontend development)

### Installation Steps

#### 1. Install uv Package Manager

uv is a high-performance Python package installer and resolver:

**macOS and Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Via pip (alternative):**
```bash
pip install uv
```

Verify installation:
```bash
uv --version
```

For additional installation methods, refer to the [uv documentation](https://docs.astral.sh/uv/).

#### 2. Clone and Setup Repository

```bash
git clone https://github.com/humlab-sead/sead_shape_shifter.git
cd sead_shape_shifter
```

#### 3. Install Python Dependencies

Shape Shifter uses a single virtual environment for the core library, backend API, and development tools:

```bash
# Full installation (recommended for development)
make install
# Equivalent to: uv venv && uv pip install -e ".[all]"

# Core library only (no API dependencies)
uv pip install -e .

# Core + API (no development tools)
uv pip install -e ".[api]"
```

#### 4. Install UCanAccess (MS Access Support)

UCanAccess is a JDBC driver enabling Java applications to interact with MS Access databases. Shape Shifter uses it via JPype for `.mdb` and `.accdb` file support.

**Automated installation:**
```bash
bash scripts/install-uncanccess.sh
```

This script downloads the latest UCanAccess package from SourceForge and extracts it to `lib/ucanaccess/`.

**Manual installation (alternative):**
1. Download UCanAccess from [SourceForge](https://sourceforge.net/projects/ucanaccess/)
2. Extract the archive
3. Copy the extracted folder to `lib/ucanaccess/`

**Verification:**
```bash
ls lib/ucanaccess/
# Expected output: ucanaccess-*.jar, lib/, loader.jar, etc.
```

#### 5. Install Frontend Dependencies (Optional)

For frontend development:

```bash
make frontend-install
# Equivalent to: cd frontend && pnpm install
```

#### 6. Verify Installation

```bash
# Run test suite
make test

# Or directly with uv
uv run pytest tests backend/tests -v
```

### Running the Application

Start the backend API and frontend development servers:

```bash
# Start backend API (http://localhost:8013)
make backend-run

# Start frontend dev server (http://localhost:5173)
make frontend-run

# Start both simultaneously
make run-all
```

### Development Commands

```bash
# Testing
make test                    # Run all tests (core + backend + ingesters)
make backend-test            # Run backend tests only
make frontend-test           # Run frontend tests only
make frontend-coverage       # Frontend tests with coverage report

# Code Quality
make lint                    # Full lint (format + check + analyze)
make tidy                    # Format code (isort + black)
make ruff                    # Run ruff linter with auto-fix
make pylint                  # Run pylint analysis
make check-imports           # Verify import statements
make frontend-lint           # Lint frontend code

# Schema Management
make generate-schemas        # Generate JSON schemas from Pydantic models
make check-schemas           # Verify schemas are in sync with models
```

## Usage

### Command-Line Interface

Process data transformations using the CLI:

```bash
# Basic transformation to Excel
python src/shapeshift.py output.xlsx \
  --project projects/my_project.yml \
  --mode xlsx

# Transform with validation
python src/shapeshift.py output.xlsx \
  --project projects/my_project.yml \
  --validate-then-exit

# Export to CSV
python src/shapeshift.py output/ \
  --project projects/my_project.yml \
  --mode csv

# With environment variables
python src/shapeshift.py output.xlsx \
  --project projects/my_project.yml \
  --env-file projects/.env \
  --mode xlsx
```

### Configuration Example

Define data transformation projects using YAML:

```yaml
entities:
  location:
    system_id: system_id
    public_id: location_id
    keys: [location_name]
    columns: [location_name, country, region]
    data_source: locations_csv
    depends_on: []
  
  site:
    system_id: system_id
    public_id: site_id
    keys: [site_name]
    columns: [site_name, location_name, description]
    data_source: sites_csv
    depends_on: [location]
    foreign_keys:
      - entity: location
        local_keys: [location_name]
        remote_keys: [location_name]
        constraints:
          cardinality: many_to_one
          allow_unmatched_left: false
          require_unique_right: true

options:

Identity note:
- `system_id` is an internal Shape Shifter identity. For non-fixed entities, do not import it from SQL or spreadsheets and do not list it in `columns`.
- `public_id` is different: it may come from the source when the source genuinely provides that identifier, or it may be populated later for export/reconciliation.
  data_sources:
    locations_csv:
      type: csv
      path: ./data/locations.csv
    sites_csv:
      type: csv
      path: ./data/sites.csv
```

### Database Integration

Shape Shifter supports multiple database systems:

```yaml
options:
  data_sources:
    postgres_db:
      type: postgresql
      host: localhost
      port: 5432
      dbname: mydb
      user: dbuser
      password: ${DB_PASSWORD}
    
    access_db:
      type: access
      path: ./data/legacy.mdb
```

## Foreign Key Constraints

The constraint validation system ensures data integrity during entity linking:

```yaml
foreign_keys:
  - entity: parent_entity
    local_keys: [parent_id]
    remote_keys: [id]
    constraints:
      # Relationship type
      cardinality: many_to_one
      
      # Match requirements
      allow_unmatched_left: false   # All child rows must match
      allow_unmatched_right: true   # Parents without children allowed
      
      # Uniqueness
      require_unique_right: true    # Parent keys must be unique
      
      # Null handling
      allow_null_keys: false        # Explicit strict override for missing key parts
      
      # Row limits
      allow_row_decrease: false     # Prevent data loss
```

**Constraint Types:**

- **Cardinality**: `one_to_one`, `many_to_one`, `one_to_many`, `many_to_many`
- **Match Requirements**: Control which rows require matching records
- **Uniqueness**: Enforce key uniqueness on either side of the relationship
- **Null Handling**: Omit `allow_null_keys` to use the lookup-style `left` join default, or set it explicitly for strict/optional behavior

For lookup-style `left` joins that resolve a remote identity from alternative keys, missing local key parts are treated as unresolved links by default: the row is kept, the foreign key stays empty, and missing values never match missing values.
- **Row Count**: Prevent unexpected data loss during linking

Constraint violations generate detailed error messages identifying the specific entity and constraint that failed.

## Architecture

Shape Shifter is organized as a mono-repository with three main components:

### Core Processing Engine (`src/`)

The transformation pipeline processes data through distinct phases:

1. **Extract** - Load data from sources (CSV, SQL, fixed values)
2. **Filter** - Apply post-load filters (e.g., `exists_in`)
3. **Link** - Resolve foreign key relationships with constraint validation
4. **Unnest** - Transform wide-format to normalized structures
5. **Translate** - Map column names and translate values to target schema
6. **Store** - Export to CSV, Excel, or database

The `ShapeShifter` orchestrator in `src/normalizer.py` manages pipeline execution using `ProcessState` for topological sorting and dependency resolution.

### Backend API (`backend/app/`)

FastAPI-based REST service with layered architecture:

- **API Layer** (`api/v1/endpoints/`) - FastAPI routers for each feature
- **Services** (`services/`) - Business logic (validation, auto-fix, query execution)
- **Models** (`models/`) - Pydantic v2 schemas for request/response
- **Mappers** (`mappers/`) - Layer boundary translators
- **Core** (`core/`) - Settings and configuration

Key services:
- `validation_service.py` - Multi-type validation (structural, data, entity-specific)
- `auto_fix_service.py` - Automated fix suggestions with backup/rollback
- `shapeshift_service.py` - Entity preview with intelligent caching
- `dependency_service.py` - Dependency analysis with cycle detection

### Frontend (`frontend/`)

Vue 3 application with Composition API:

- **Pinia Stores** (`stores/`) - State management
- **Composables** (`composables/`) - Reusable logic
- **API Layer** (`api/`) - Axios-based API clients
- **Monaco Editor** - YAML editing with syntax highlighting

## Documentation

Comprehensive documentation is available in the `docs/` directory:

- [CONFIGURATION_GUIDE.md](docs/CONFIGURATION_GUIDE.md) - Complete YAML configuration reference
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) - System architecture and component overview
- [DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md) - Development setup and contribution guidelines
- [USER_GUIDE.md](docs/USER_GUIDE.md) - End-user documentation
- [TESTING_GUIDE.md](docs/TESTING_GUIDE.md) - Testing procedures and guidelines
- [AI_VALIDATION_GUIDE.md](docs/AI_VALIDATION_GUIDE.md) - AI-focused validation rules for project files

## Testing

The project uses pytest for Python tests and Vitest for frontend tests:

```bash
# Run all tests
make test

# Run specific test suites
uv run pytest tests -v                     # Core tests
uv run pytest backend/tests -v             # Backend tests
uv run pytest ingesters/sead/tests -v      # Ingester tests

# Run with coverage
uv run pytest tests backend/tests --cov=src --cov=backend/app --cov-report=html

# Frontend tests
make frontend-test          # Run frontend tests
make frontend-coverage      # Run with coverage report
```

## Contributing

Contributions are welcome. Follow these steps to contribute:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Implement changes following project conventions
4. Run tests and linting: `make test && make lint`
5. Commit using [Conventional Commits](https://www.conventionalcommits.org/) format
6. Push to your fork: `git push origin feature/your-feature`
7. Open a pull request with a clear description

### Code Standards

- **Formatting**: Black (line length 140)
- **Import sorting**: isort
- **Linting**: Ruff and Pylint
- **Type hints**: Required for all function signatures
- **Testing**: Maintain or improve test coverage

Run `make lint` before committing to ensure compliance.

### Commit Message Format

Use Conventional Commits for semantic versioning:

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

Example: `feat(backend): add entity dependency analysis service`

## License

This project is part of the SEAD (Strategic Environmental Archaeology Database) initiative at Humlab, Umeå University.

## Acknowledgments

Developed by the SEAD Project Team at Humlab, Umeå University.

## Support

Report issues, ask questions, or contribute at the [GitHub repository](https://github.com/humlab-sead/sead_shape_shifter).
