import pandas as pd

from src.model import ForeignKeyConfig, ShapeShiftProject, TableConfig
from src.specifications.base import Specification

# pylint: disable=line-too-long


class ForeignKeyConfigSpecification(Specification):
    """Specification that tests if a foreign key relationship is resolveble.
    Returns True if all local and remote keys exist, False if any are missing,
    or None if resolvable after unnesting some local keys are in unnest columns.
    """

    def __init__(self, project: "ShapeShiftProject") -> None:
        super().__init__()
        self.project: ShapeShiftProject = project
        self.deferred: bool = False

    def clear(self) -> None:
        super().clear()
        self.deferred = False

    def is_satisfied_by(self, *, fk_cfg: ForeignKeyConfig | None = None, **kwargs) -> bool:
        # self.clear()
        missing_fields: set[str]

        assert fk_cfg is not None, "fk_cfg must be provided to check foreign key configuration"  # keep type checker happy

        local_table_cfg: TableConfig = self.project.get_table(fk_cfg.local_entity)
        remote_table_cfg: TableConfig = self.project.get_table(fk_cfg.remote_entity)

        if fk_cfg.how == "cross":
            if fk_cfg.local_keys or fk_cfg.remote_keys:
                self.add_error(
                    f"{fk_cfg.local_entity} -> {fk_cfg.remote_entity}: " f"'cross' join should not specify local_keys or remote_keys",
                    entity=fk_cfg.local_entity,
                )
            return not self.has_errors()

        if not remote_table_cfg.system_id:
            self.add_error(
                f"{fk_cfg.local_entity} -> {fk_cfg.remote_entity}: "
                f"remote entity '{fk_cfg.remote_entity}' must have a system_id defined",
                entity=fk_cfg.local_entity,
            )
            return not self.has_errors()

        if not remote_table_cfg.public_id:
            self.add_error(
                f"{fk_cfg.local_entity} -> {fk_cfg.remote_entity}: "
                f"remote entity '{fk_cfg.remote_entity}' must have a public_id defined",
                entity=fk_cfg.local_entity,
            )
            return not self.has_errors()

        if len(fk_cfg.local_keys) == 0 or len(fk_cfg.remote_keys) == 0:
            self.add_error(
                f"{fk_cfg.local_entity} -> {fk_cfg.remote_entity}: " f"local_keys and remote_keys must be specified for non-cross joins",
                entity=fk_cfg.local_entity,
            )

        if len(fk_cfg.local_keys) != len(fk_cfg.remote_keys):
            self.add_error(
                f"{fk_cfg.local_entity} -> {fk_cfg.remote_entity}: "
                f"number of local_keys ({len(fk_cfg.local_keys)}) does not match "
                f"number of remote_keys ({len(fk_cfg.remote_keys)})",
                entity=fk_cfg.local_entity,
            )

        missing_fields = self.get_missing_fields(
            required_fields=set(fk_cfg.local_keys),
            available_fields=set(local_table_cfg.keys_columns_and_fks) | set(local_table_cfg.unnest_columns),
        )

        if missing_fields:
            self.add_error(
                f"{fk_cfg.local_entity} -> {fk_cfg.remote_entity}: "
                f"local keys {missing_fields} not found in local entity '{fk_cfg.local_entity}'",
                entity=fk_cfg.local_entity,
            )

        missing_fields: set[str] = self.get_missing_fields(
            required_fields=set(fk_cfg.remote_keys), available_fields=set(remote_table_cfg.get_columns())
        )

        if missing_fields:
            self.add_error(
                f"{fk_cfg.local_entity} -> {fk_cfg.remote_entity}: "
                f"remote keys {missing_fields} not found in remote entity '{fk_cfg.remote_entity}'",
                entity=fk_cfg.local_entity,
            )

        return not self.has_errors()

    def get_missing_fields(self, *, required_fields: set[str], available_fields: set[str]) -> set[str]:
        """Return the set of required keys that are missing from found keys."""
        return {key for key in required_fields if key not in available_fields}


class ForeignKeyDataSpecification(ForeignKeyConfigSpecification):
    """Checks if local and remote keys are present in the actual table data (pandas.DataFrames)."""

    def __init__(self, table_store: dict[str, pd.DataFrame], cfg: "ShapeShiftProject") -> None:
        super().__init__(cfg)
        self.table_store: dict[str, pd.DataFrame] = table_store

    def is_satisfied_by(self, *, fk_cfg: ForeignKeyConfig | None = None, **kwargs) -> bool:

        assert fk_cfg is not None, "fk_cfg must be provided to check foreign key data"  # keep type checker happy

        self.clear()

        missing_fields: set[str]

        if fk_cfg.remote_entity not in self.table_store:
            # Skip if remote entity hasn't been processed yet
            self.add_warning(
                f"{fk_cfg.local_entity}[linking]: deferring link to '{fk_cfg.remote_entity}' - entity not yet processed",
                entity=fk_cfg.local_entity,
            )
            self.deferred = True
            return False

        if fk_cfg.local_entity not in self.table_store:
            raise ValueError(f"Local entity '{fk_cfg.local_entity}' not found in table store for linking with '{fk_cfg.remote_entity}'")

        super().is_satisfied_by(fk_cfg=fk_cfg)

        if missing_fields := self.get_missing_local_fields(fk_cfg=fk_cfg):
            if missing_fields == self.project.get_table(fk_cfg.local_entity).unnest_columns:
                self.deferred = True
            else:
                self.add_error(
                    f"{fk_cfg.local_entity} -> {fk_cfg.remote_entity}: "
                    f"local keys {missing_fields} not found in local entity data '{fk_cfg.local_entity}'",
                    entity=fk_cfg.local_entity,
                )

        if self.get_missing_pending_fields(fk_cfg=fk_cfg):
            self.deferred = True

        if missing_fields := self.get_missing_remote_fields(fk_cfg=fk_cfg):
            self.add_error(
                f"{fk_cfg.local_entity} -> {fk_cfg.remote_entity}: "
                f"remote keys {missing_fields} not found in remote entity data '{fk_cfg.remote_entity}'",
                entity=fk_cfg.local_entity,
            )

        return not self.has_errors()

    def is_already_linked(self, *, fk_cfg: ForeignKeyConfig) -> bool:
        """Check if the foreign key columns already exist in the local entity's data."""
        table: pd.DataFrame = self.table_store[fk_cfg.local_entity]
        remote_cfg: TableConfig = self.project.get_table(fk_cfg.remote_entity)
        return fk_cfg.has_foreign_key_link(remote_cfg.public_id, table)

    def get_missing_local_fields(self, *, fk_cfg: ForeignKeyConfig) -> set[str]:
        """Check for missing local keys in the local entity data."""
        table: pd.DataFrame = self.table_store[fk_cfg.local_entity]
        return self.get_missing_fields(
            required_fields=set(fk_cfg.local_keys),
            available_fields=set(table.columns).union(self.project.get_table(fk_cfg.local_entity).unnest_columns),
        )

    def get_missing_pending_fields(self, *, fk_cfg: ForeignKeyConfig) -> set[str]:
        """Check for missing pending keys in the local entity data."""
        return self.get_missing_fields(
            required_fields=set(self.project.get_table(fk_cfg.local_entity).unnest_columns),
            available_fields=set(self.table_store[fk_cfg.local_entity].columns),
        )

    def get_missing_remote_fields(self, *, fk_cfg: ForeignKeyConfig) -> set[str]:
        """Check for missing remote keys in the remote entity data."""
        return self.get_missing_fields(
            required_fields=set(fk_cfg.remote_keys), available_fields=set(self.table_store[fk_cfg.remote_entity].columns)
        )
