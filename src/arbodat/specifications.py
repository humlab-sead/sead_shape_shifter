import pandas as pd

from src.arbodat.config_model import ForeignKeyConfig, TableConfig, TablesConfig


class ForeignKeyConfigSpecification:
    """Specification that tests if a foreign key relationship is resolveble.
    Returns True if all local and remote keys exist, False if any are missing,
    or None if resolvable after unnesting some local keys are in unnest columns.
    """

    def __init__(self, cfg: "TablesConfig") -> None:
        self.cfg: TablesConfig = cfg
        self.error: str = ""
        self.deferred: bool = False

    def clear(self) -> None:
        self.error = ""
        self.deferred = False

    def is_satisfied_by(self, *, fk_cfg: ForeignKeyConfig) -> bool | None:
        self.clear()
        missing_keys: set[str]
        cfg_local_table: TableConfig = self.cfg.get_table(fk_cfg.local_entity)
        cfg_remote_table: TableConfig = self.cfg.get_table(fk_cfg.remote_entity)

        missing_keys = self.get_missing_keys(
            required_keys=set(fk_cfg.local_keys), columns=set(cfg_local_table.usage_columns) | set(cfg_local_table.pending_columns), pending_columns=set()
        )

        if missing_keys:
            self.error = f"Linking {fk_cfg.local_entity} -> {fk_cfg.remote_entity}: local keys {missing_keys} not found in local entity '{fk_cfg.local_entity}'"
            return False

        missing_keys: set[str] = self.get_missing_keys(
            required_keys=set(fk_cfg.remote_keys), columns=set(cfg_remote_table.usage_columns), pending_columns=set()
        )

        if missing_keys:
            self.error = (
                f"Linking {fk_cfg.local_entity} -> {fk_cfg.remote_entity}: remote keys {missing_keys} not found in remote entity '{fk_cfg.remote_entity}'"
            )
            return False

        return True

    def get_missing_keys(self, *, required_keys: set[str], columns: set[str], pending_columns) -> set[str]:

        missing_keys: set[str] = {key for key in required_keys if key not in columns.union(pending_columns)}

        return missing_keys


class ForeignKeyDataSpecification(ForeignKeyConfigSpecification):
    """Checks if local and remote keys are present in the actual table data (pandas.DataFrames)."""

    def __init__(self, table_store: dict[str, pd.DataFrame], cfg: "TablesConfig") -> None:
        super().__init__(cfg)
        self.table_store: dict[str, pd.DataFrame] = table_store

    def is_satisfied_by(self, *, fk_cfg: ForeignKeyConfig) -> bool:
        missing_keys: set[str]

        assert fk_cfg.local_entity in self.table_store, f"Local DataFrame for entity '{fk_cfg.local_entity}' not found"
        assert fk_cfg.remote_entity in self.table_store, f"Remote DataFrame for entity '{fk_cfg.remote_entity}' not found"

        is_config_ok: bool | None = super().is_satisfied_by(fk_cfg=fk_cfg)
        if is_config_ok is not True:
            return False

        table: pd.DataFrame = self.table_store[fk_cfg.local_entity]

        missing_keys = self.get_missing_keys(
            required_keys=set(fk_cfg.local_keys),
            columns=set(table.columns),
            pending_columns=set(self.cfg.get_table(fk_cfg.local_entity).pending_columns),
        )
        if missing_keys:
            if missing_keys == self.cfg.get_table(fk_cfg.local_entity).pending_columns:
                self.deferred = True
            else:
                self.error = (
                    f"Linking {fk_cfg.local_entity} -> {fk_cfg.remote_entity}: local keys {missing_keys} not found in local entity data '{fk_cfg.local_entity}'"
                )
                return False
            
        missing_pending_keys: set[str] = self.get_missing_keys(
            required_keys=self.cfg.get_table(fk_cfg.local_entity).pending_columns,
            columns=set(table.columns),
            pending_columns=set(),
        )

        if missing_pending_keys:
            self.deferred = True
            return False
        
        missing_keys = self.get_missing_keys(
            required_keys=set(fk_cfg.remote_keys), columns=set(self.table_store[fk_cfg.remote_entity].columns), pending_columns=set()
        )
        if missing_keys:
            self.error = (
                f"Linking {fk_cfg.local_entity} -> {fk_cfg.remote_entity}: remote keys {missing_keys} not found in remote entity data '{fk_cfg.remote_entity}'"
            )
            return False

        return True
