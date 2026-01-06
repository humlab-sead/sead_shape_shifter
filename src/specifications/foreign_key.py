from typing import Any

import pandas as pd

from src.model import ForeignKeyConfig, ShapeShiftProject, TableConfig

# pylint: disable=line-too-long


class ForeignKeyConfigSpecification:
    """Specification that tests if a foreign key relationship is resolveble.
    Returns True if all local and remote keys exist, False if any are missing,
    or None if resolvable after unnesting some local keys are in unnest columns.
    """

    def __init__(self, cfg: "ShapeShiftProject") -> None:
        self.cfg: ShapeShiftProject = cfg
        self.error: str = ""
        self.deferred: bool = False

    def clear(self) -> None:
        self.error = ""
        self.deferred = False

    def is_satisfied_by(self, *, fk_cfg: ForeignKeyConfig) -> bool | None:
        self.clear()
        missing_fields: set[str]
        cfg_local_table: TableConfig = self.cfg.get_table(fk_cfg.local_entity)
        cfg_remote_table: TableConfig = self.cfg.get_table(fk_cfg.remote_entity)

        if fk_cfg.how == "cross":
            if fk_cfg.local_keys or fk_cfg.remote_keys:
                self.error = (
                    f"{fk_cfg.local_entity} -> {fk_cfg.remote_entity}: "
                    f"'cross' join should not specify local_keys or remote_keys"
                )
                return False
            return True

        if len(fk_cfg.local_keys) == 0 or len(fk_cfg.remote_keys) == 0:
            self.error = (
                f"{fk_cfg.local_entity} -> {fk_cfg.remote_entity}: "
                f"local_keys and remote_keys must be specified for non-cross joins"
            )
            return False

        if len(fk_cfg.local_keys) != len(fk_cfg.remote_keys):
            self.error = (
                f"{fk_cfg.local_entity} -> {fk_cfg.remote_entity}: "
                f"number of local_keys ({len(fk_cfg.local_keys)}) does not match "
                f"number of remote_keys ({len(fk_cfg.remote_keys)})"
            )
            return False

        missing_fields = self.get_missing_fields(
            required_fields=set(fk_cfg.local_keys),
            available_fields=set(cfg_local_table.keys_columns_and_fks) | set(cfg_local_table.unnest_columns),
        )

        if missing_fields:
            self.error = (
                f"{fk_cfg.local_entity} -> {fk_cfg.remote_entity}: "
                f"local keys {missing_fields} not found in local entity '{fk_cfg.local_entity}'"
            )
            return False

        missing_fields: set[str] = self.get_missing_fields(
            required_fields=set(fk_cfg.remote_keys), available_fields=set(cfg_remote_table.get_columns())
        )

        if missing_fields:
            self.error = (
                f"{fk_cfg.local_entity} -> {fk_cfg.remote_entity}: "
                f"remote keys {missing_fields} not found in remote entity '{fk_cfg.remote_entity}'"
            )
            return False

        return True

    def get_missing_fields(self, *, required_fields: set[str], available_fields: set[str]) -> set[str]:
        """Return the set of required keys that are missing from found keys."""
        return {key for key in required_fields if key not in available_fields}


class ForeignKeyDataSpecification(ForeignKeyConfigSpecification):
    """Checks if local and remote keys are present in the actual table data (pandas.DataFrames)."""

    def __init__(self, table_store: dict[str, pd.DataFrame], cfg: "ShapeShiftProject") -> None:
        super().__init__(cfg)
        self.table_store: dict[str, pd.DataFrame] = table_store

    def is_satisfied_by(self, *, fk_cfg: ForeignKeyConfig) -> bool:
        missing_fields: set[str]

        assert fk_cfg.local_entity in self.table_store, f"Local DataFrame for entity '{fk_cfg.local_entity}' not found"
        assert fk_cfg.remote_entity in self.table_store, f"Remote DataFrame for entity '{fk_cfg.remote_entity}' not found"

        is_config_ok: bool | None = super().is_satisfied_by(fk_cfg=fk_cfg)
        if is_config_ok is not True:
            return False

        if missing_fields := self.get_missing_local_fields(fk_cfg=fk_cfg):
            if missing_fields == self.cfg.get_table(fk_cfg.local_entity).unnest_columns:
                self.deferred = True
            else:
                self.error = (
                    f"{fk_cfg.local_entity} -> {fk_cfg.remote_entity}: "
                    f"local keys {missing_fields} not found in local entity data '{fk_cfg.local_entity}'"
                )
                return False

        if self.get_missing_pending_fields(fk_cfg=fk_cfg):
            self.deferred = True
            return True

        if missing_fields := self.get_missing_remote_fields(fk_cfg=fk_cfg):
            self.error = (
                f"{fk_cfg.local_entity} -> {fk_cfg.remote_entity}: "
                f"remote keys {missing_fields} not found in remote entity data '{fk_cfg.remote_entity}'"
            )
            return False

        return True

    def get_missing_local_fields(self, *, fk_cfg: ForeignKeyConfig) -> set[str]:
        """Check for missing local keys in the local entity data."""
        table: pd.DataFrame = self.table_store[fk_cfg.local_entity]
        return self.get_missing_fields(
            required_fields=set(fk_cfg.local_keys),
            available_fields=set(table.columns).union(self.cfg.get_table(fk_cfg.local_entity).unnest_columns),
        )

    def get_missing_pending_fields(self, *, fk_cfg: ForeignKeyConfig) -> set[str]:
        """Check for missing pending keys in the local entity data."""
        return self.get_missing_fields(
            required_fields=set(self.cfg.get_table(fk_cfg.local_entity).unnest_columns),
            available_fields=set(self.table_store[fk_cfg.local_entity].columns),
        )

    def get_missing_remote_fields(self, *, fk_cfg: ForeignKeyConfig) -> set[str]:
        """Check for missing remote keys in the remote entity data."""
        return self.get_missing_fields(
            required_fields=set(fk_cfg.remote_keys), available_fields=set(self.table_store[fk_cfg.remote_entity].columns)
        )
