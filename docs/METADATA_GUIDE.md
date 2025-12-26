# Example Configuration with Metadata

This example demonstrates the new metadata section in Shape Shifter configuration files.

## Configuration Structure

```yaml
# Top-level metadata section (optional but recommended)
metadata:
  name: "My Data Configuration"
  description: "Configuration for importing my data into the target system"
  version: "1.0.0"

# Entity definitions
entities:
  users:
    type: csv
    source: "users.csv"
    keys: ["user_id"]
    columns: ["name", "email", "created_at"]
    
  posts:
    type: sql
    data_source: postgres
    query: "SELECT * FROM posts"
    keys: ["post_id"]
    foreign_keys:
      - entity: users
        local_keys: ["user_id"]
        remote_keys: ["user_id"]

# Global options
options:
  data_sources:
    postgres:
      driver: postgresql
      host: localhost
      port: 5432
      database: mydb
```

## Metadata Fields

### Required
- **name**: A human-readable name for the configuration

### Optional
- **description**: A detailed description of what this configuration does
- **version**: Semantic version string (e.g., "1.0.0", "2.1.3")

## Backward Compatibility

The metadata section is entirely optional. Configurations without metadata will work as before, with the configuration name derived from the filename.

## Examples

### Minimal Configuration (No Metadata)
```yaml
entities:
  sample:
    type: data
    keys: ["id"]
```

### Full Metadata
```yaml
metadata:
  name: "Archaeological Site Data Import"
  description: |
    Imports archaeological site data from multiple sources including
    field surveys, laboratory analyses, and historical records.
  version: "2.1.0"

entities:
  sites:
    # ... entity definition
```

## API Integration

When loaded via the API, the metadata is available through the `Configuration.metadata` property:

```python
from backend.app.mappers.config_mapper import ConfigMapper

# Load configuration
cfg_dict = load_yaml("my_config.yml")
api_config = ConfigMapper.to_api_config(cfg_dict, "my-config")

# Access metadata
print(api_config.metadata.name)         # "My Data Configuration"
print(api_config.metadata.description)  # "Configuration for importing..."
print(api_config.metadata.version)      # "1.0.0"
```

## Core Model Integration

In the core ShapeShiftConfig, metadata is accessible via the `metadata` property:

```python
from src.model import ShapeShiftConfig

config = ShapeShiftConfig.from_file("my_config.yml")

# Access metadata
print(config.metadata.name)         # "My Data Configuration"
print(config.metadata.description)  # "Configuration for importing..."
print(config.metadata.version)      # "1.0.0"
```
