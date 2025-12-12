# SEAD Shape Shifter

A general-purpose data transformation and normalization framework for harmonizing diverse data sources into a target schema. While initially developed for Arbodat archaeological data integration with the SEAD (Strategic Environmental Archaeology Database) system, the framework is designed to be adaptable to any domain requiring complex data transformations.

## Recent Updates

**v0.2.0 - December 2025**
- ✨ **Enhanced Foreign Key Constraints**: Comprehensive validation system with cardinality, uniqueness, and match requirements
- 🚀 **Improved Validator Registry**: Efficient O(1) lookup for constraint validators using sub-key indexing
- 🧹 **Streamlined API**: Removed redundant validators for cleaner, more maintainable codebase
- 📝 **Better Documentation**: Updated configuration reference and constraint examples
- 🔧 **Bug Fixes**: Fixed validator registration conflicts and improved error messages

## Overview

Shape Shifter provides a declarative YAML-based configuration system for defining complex data transformation pipelines. The system supports:

- **Multiple Data Sources**: CSV files, Excel spreadsheets, SQL databases (PostgreSQL, MS Access via UCanAccess)
- **Entity Relationships**: Define foreign key relationships and dependencies between entities
- **Foreign Key Constraints**: Enforce data integrity with cardinality, uniqueness, and match requirements
- **Data Transformations**: Column mapping, value translation, data type conversions
- **Flexible Processing**: Extract, filter, link, unnest, and normalize data through a multi-phase pipeline
- **Append Operations**: Augment extracted data with fixed values, SQL queries, or data from other entities

## Features

- **Declarative Configuration**: Define entire data transformation pipelines in YAML
- **Dependency Management**: Automatic topological sorting ensures entities are processed in the correct order
- **Foreign Key Resolution**: Establish relationships between entities with surrogate key generation
- **Comprehensive Constraint System**: Validate foreign key relationships with:
  - Cardinality constraints (one-to-one, many-to-one, one-to-many)
  - Match requirements (enforce all rows match)
  - Uniqueness constraints (ensure key uniqueness)
  - Null value handling
- **Data Validation**: Built-in validation for configuration files and data integrity
- **Multiple Output Formats**: Export to CSV, Excel, or directly to databases
- **Extensible Architecture**: Plugin-style loaders for different data sources

## Developer Installation

### Prerequisites

- **Python 3.13 or higher**: Shape Shifter requires Python 3.13+
- **Java Runtime Environment (JRE)**: Required for UCanAccess (MS Access database support)

### Installation Steps

#### 1. Install uv (Python Package Manager)

`uv` is a fast Python package installer and resolver. Install it using one of the following methods:

**On macOS and Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**On Windows:**
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Via pip (alternative):**
```bash
pip install uv
```

**Verify installation:**
```bash
uv --version
```

For more installation options, see the [uv documentation](https://docs.astral.sh/uv/).

#### 2. Clone the Repository

```bash
git clone https://github.com/humlab-sead/sead_shape_shifter.git
cd sead_shape_shifter
```

#### 3. Install Python Dependencies

```bash
# Create virtual environment and install dependencies
uv venv
uv pip install -e .

# Install development dependencies
uv pip install -e ".[dev]"
```

#### 4. Install UCanAccess (For MS Access Database Support)

UCanAccess is a JDBC driver that allows Java applications to read/write MS Access databases. Shape Shifter uses it via JPype to work with `.mdb` and `.accdb` files.

**Automated Installation:**
```bash
# Run the installation script
bash scripts/install-uncanccess.sh
```

This script will:
- Download the latest UCanAccess package from SourceForge
- Extract it to `lib/ucanaccess/`
- Set up all required JAR files

**Manual Installation (Alternative):**
1. Download UCanAccess from [SourceForge](https://sourceforge.net/projects/ucanaccess/)
2. Extract the archive
3. Copy the extracted folder to `lib/ucanaccess/` in the project directory

**Verify Installation:**
```bash
ls lib/ucanaccess/
# Should show: ucanaccess-*.jar, lib/, loader.jar, etc.
```

#### 5. Verify Installation

```bash
# Run tests to verify everything is working
make test

# Or directly with uv
uv run pytest tests -v
```

### Development Tools

The project includes several make targets for common development tasks:

```bash
# Run tests
make test

# Format code with black
make black

# Run linter
make lint

# Run pylint
make pylint

# Check import statements
make check-imports
```

## Quick Start

### Basic Usage

1. **Prepare your configuration file** (`config.yml`):
```yaml
entities:
  site:
    surrogate_id: site_id
    keys: [site_name]
    columns: [site_name, latitude, longitude]
    depends_on: []
  
  sample:
    surrogate_id: sample_id
    keys: [sample_name]
    columns: [sample_name, site_name]
    depends_on: [site]
    foreign_keys:
      - entity: site
        local_keys: [site_name]
        remote_keys: [site_name]
        constraints:
          cardinality: many_to_one
          allow_unmatched_left: false

options:
  data_sources: {}
```

2. **Run the normalization**:
```bash
python src/arbodat/survey2excel.py \
  --config-file config.yml \
  --mode excel \
  input_data.csv \
  output.xlsx
```

### Working with MS Access Databases

Shape Shifter can extract data directly from MS Access databases:

```yaml
entities:
  my_table:
    data_source: access_db
    surrogate_id: id
    keys: [name]
    columns: [name, description]

options:
  data_sources:
    access_db:
      type: access
      path: ./data/my_database.mdb
```

## Foreign Key Constraints

Shape Shifter includes a robust constraint validation system for foreign key relationships. Constraints ensure data integrity during the linking process:

```yaml
foreign_keys:
  - entity: reference_table
    local_keys: [key_column]
    remote_keys: [key_column]
    constraints:
      # Enforce relationship type
      cardinality: many_to_one
      
      # Ensure all rows match
      allow_unmatched_left: false
      
      # Require unique keys
      require_unique_right: true
      
      # Prevent null values
      allow_null_keys: false
```

**Constraint Types:**

- **Cardinality**: `one_to_one`, `many_to_one`, `one_to_many`, `many_to_many`
- **Match Requirements**: `allow_unmatched_left`, `allow_unmatched_right`
- **Uniqueness**: `require_unique_left`, `require_unique_right`
- **Null Handling**: `allow_null_keys`
- **Row Count**: `allow_row_decrease`

Violations raise descriptive errors with context about which entity and constraint failed.

## Configuration

Configuration files use YAML format with three main sections:

- **entities**: Define data entities, their columns, relationships, and transformations
- **options**: Global settings including data source connections
- **unions**: (Optional) Define union operations to combine multiple entities

For detailed configuration documentation, see:
- [Configuration Reference](docs/CONFIGURATION_REFERENCE.md)
- [Foreign Key Constraints](docs/FOREIGN_KEY_CONSTRAINTS.md)
- [Union Configuration](docs/UNION_CONFIGURATION_OPTIONS.md)
- [Configuration Validation](docs/config_validation.md)

## Project Structure

```
sead_shape_shifter/
├── src/
│   ├── config_model.py       # Configuration data models
│   ├── constraints.py         # Foreign key constraint validators
│   ├── normalizer.py          # Main normalization pipeline
│   ├── extract.py             # Data extraction logic
│   ├── link.py                # Foreign key resolution
│   ├── unnest.py              # Data unnesting operations
│   ├── mapping.py             # Column mapping and translation
│   ├── loaders/               # Data source loaders
│   └── arbodat/               # Arbodat-specific implementations
├── tests/                     # Test suite
├── docs/                      # Documentation
├── input/                     # Example input files and configs
├── scripts/                   # Utility scripts
└── lib/                       # External libraries (UCanAccess)
```

## Testing

The project uses pytest for testing:

```bash
# Run all tests
uv run pytest tests -v

# Run specific test file
uv run pytest tests/test_append_processing.py -v

# Run with coverage
uv run pytest tests --cov=src --cov-report=html
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and linting (`make test && make lint`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Code Style

The project uses:
- **Black** for code formatting
- **Ruff** for linting
- **Pylint** for additional code analysis

Run `make lint` before committing to ensure code quality.

## License

This project is part of the SEAD (Strategic Environmental Archaeology Database) initiative.

## Acknowledgments

- SEAD Project Team
- Humlab, Umeå University

## Support

For issues, questions, or contributions, please open an issue on the [GitHub repository](https://github.com/humlab-sead/sead_shape_shifter).
