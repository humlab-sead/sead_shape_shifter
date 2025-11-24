from functools import cached_property
from typing import Any

from src.configuration.resolve import ConfigValue


class UnnestConfig:
    """Configuration for unnesting a column."""

    def __init__(self, data: dict[str, Any]) -> None:
        unnest_data = data.get("unnest", {})
        self.id_vars: list[str] = unnest_data.get("id_vars", []) or []
        self.value_vars: list[str] = unnest_data.get("value_vars", []) or []
        self.var_name: str = unnest_data.get("var_name", "") or ""
        self.value_name: str = unnest_data.get("value_name", "") or ""

        if not self.id_vars or not self.value_vars or not self.var_name or not self.value_name:
            raise ValueError(f"Invalid unnest configuration: {data}")


class TableConfig:
    """Configuration for a database table."""

    def __init__(self, config: dict[str, dict[str, Any]], entity_name: str) -> None:
        self.entity_name: str = entity_name
        self.data: dict[str, Any] = config[entity_name]
        self.foreign_keys: list[ForeignKeyConfig] = [
            ForeignKeyConfig(config, entity_name, fk_data) for fk_data in self.data.get("options", {}).get("foreign_keys", []) or []
        ]
        assert self.data, f"No configuration found for entity '{entity_name}'"

    @property
    def keys(self) -> list[str]:
        return self.data.get("keys", []) or []

    @property
    def surrogate_id(self) -> str:
        return self.data.get("surrogate_id", "")

    @property
    def columns(self) -> list[str]:
        return self.data.get("columns", []) or []

    @property
    def columns2(self) -> list[str]:
        """Get columns with keys first, followed by other columns."""
        return self.keys + [col for col in self.columns if col not in self.keys]

    @property
    def drop_duplicates(self) -> bool | list[str]:
        value = self.data.get("options", {}).get("drop_duplicates", False)
        return value if value else False

    @property
    def unnest(self) -> UnnestConfig | None:
        """Get unnest configuration if it exists."""
        if "unnest" in self.data:
            return UnnestConfig(self.data)
        return None

    @property
    def depends_on(self) -> list[str]:
        return (self.data.get("depends_on", []) or []) + ([self.source] if self.source else [])

    @property
    def source(self) -> str | None:
        return self.data.get("source")

    @property
    def fk_column_set(self) -> set[str]:
        """Get set of all foreign key columns."""
        return {col for fk in self.foreign_keys or [] for col in fk.local_keys}

    @property
    def extra_fk_columns(self) -> set[str]:
        """Get set of foreign key columns not in columns or keys."""
        extra_columns: set[str] = set()
        for fk in self.foreign_keys:
            extra_columns = extra_columns.union(set(fk.local_keys))
        return self.fk_column_set - (set(self.columns2))

    @property
    def usage_columns(self) -> list[str]:
        """Get set of all columns used in keys, columns, and foreign keys."""
        keys_and_data_columns: list[str] = self.columns2
        return keys_and_data_columns + list(x for x in self.fk_column_set if x not in keys_and_data_columns)
    
class TablesConfig:
    """Configuration for database tables."""

    def __init__(self, cfg: None | dict[str, dict[str, Any]] = None) -> None:
        self.config: dict[str, dict[str, Any]] = cfg or ConfigValue[dict[str, dict[str, Any]]]("entities").resolve() or {}
        self.tables: dict[str, TableConfig] = {entity_name: TableConfig(self.config, entity_name) for entity_name in self.config.keys()}

    def get_table(self, entity_name: str) -> "TableConfig":
        return self.tables[entity_name]

    def has_table(self, entity_name: str) -> bool:
        return entity_name in self.tables

    @cached_property
    def table_names(self) -> list[str]:
        return list(self.tables.keys())


class ForeignKeyConfig:
    """Configuration for a foreign key."""

    def __init__(self, config: dict[str, dict[str, Any]], local_entity: str, data: dict[str, Any]) -> None:
        self.local_entity: str = local_entity
        self.local_keys: list[str] = data.get("local_keys", []) or []

        self.remote_entity: str = data.get("entity", "")
        self.remote_keys: list[str] = data.get("remote_keys", []) or []

        if not self.remote_entity:
            raise ValueError(f"Invalid foreign key configuration for entity '{local_entity}': missing remote entity")

        if self.remote_entity not in config:
            raise ValueError(f"Foreign key references unknown entity '{self.remote_entity}' from '{local_entity}'")

        self.remote_surrogate_id: str = config[self.remote_entity].get("surrogate_id", "")
        self.remote_drop_duplicates: bool | list[str] = data.get("drop_duplicates", False)

        if not self.remote_keys:
            raise ValueError(f"Invalid foreign key configuration for entity '{local_entity}': missing remote_keys")
