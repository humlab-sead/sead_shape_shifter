"""Manual test to verify sead data source shows env vars in UI."""

from pathlib import Path

from backend.app.models.data_source import DataSourceConfig
from backend.app.services.data_source_service import DataSourceService
from src.configuration.interface import ConfigLike
from src.configuration.provider import ConfigStore

# pylint: disable=redefined-outer-name, unused-argument, import-outside-toplevel, invalid-name

project_root: Path = Path(__file__).parent.parent.parent

config_file: Path = project_root / "input" / "arbodat-database.yml"

print(f"Loading config from: {config_file}")
print()

# Initialize config store
ConfigStore.reset_instance()
store: ConfigStore = ConfigStore.get_instance()
store.configure_context(source=str(config_file))
config: ConfigLike | None = store.config()

assert config is not None

# Create service
service = DataSourceService(project_root / "input" )

# List data sources
print("=" * 80)
print("DATA SOURCES")
print("=" * 80)
data_sources: list[DataSourceConfig] = service.list_data_sources()

for ds in data_sources:
    print(f"\n{ds.name} ({ds.driver})")
    print("-" * 40)

    if ds.options:
        for key, value in ds.options.items():
            # Highlight env vars
            if isinstance(value, str) and "${" in value:
                print(f"  {key}: {value} 🔑")
            else:
                print(f"  {key}: {value}")

    # Check specific fields
    for field in ["host", "port", "database", "dbname", "username", "filename"]:
        value = getattr(ds, field, None)
        if value:
            if isinstance(value, str) and "${" in value:
                print(f"  {field}: {value} 🔑")
            else:
                print(f"  {field}: {value}")

print()
print("=" * 80)
print("Expected for 'sead' data source:")
print("  host: ${SEAD_HOST}")
print("  port: ${SEAD_PORT}")
print("  dbname: ${SEAD_DBNAME}")
print("  username: ${SEAD_USER}")
print("=" * 80)
