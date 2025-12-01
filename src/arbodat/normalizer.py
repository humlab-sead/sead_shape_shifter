"""
Normalize an Arbodat "Data Survey" CSV export into several tables
and write them as sheets in a single Excel file.

Usage:
    python arbodat_normalize_to_excel.py input.csv output.xlsx
Strengths
Clear Separation of Concerns

ProcessState handles dependency resolution
ArbodatSurveyNormalizer orchestrates the normalization pipeline
Configuration-driven approach makes it adaptable
Dependency Management

Topological sorting via get_next_entity_to_process() ensures correct processing order
Error reporting for circular/unmet dependencies
Flexible Data Sources

Supports extraction from source spreadsheet
Fixed/hardcoded tables
SQL database (via config)
Previously extracted tables (via resolve_source())
Comprehensive Transformation Pipeline

Extract → Link → Unnest → Translate → Store
Each phase is well-defined
"""

from pathlib import Path
from typing import Literal

import pandas as pd
from loguru import logger

from src.arbodat.config_model import ForeignKeyConfig, TableConfig, TablesConfig
from src.arbodat.dispatch import Dispatcher, Dispatchers
from src.arbodat.fixed import create_fixed_table
from src.arbodat.specifications import ForeignKeyDataSpecification
from src.arbodat.unnest import unnest
from src.arbodat.utility import get_subset, translate


class ProcessState:
    """Helper class to track processing state of entities during normalization."""

    def __init__(self, config: TablesConfig) -> None:
        self.config: TablesConfig = config
        self.unprocessed: set[str] = set(self.config.table_names)

    def get_next_entity_to_process(self) -> str | None:
        """Get the next entity that can be processed based on dependencies."""
        logger.debug(f"Processed entities so far: {self.processed_entities}")
        for entity_name in set(self.config.table_names) - self.processed_entities:
            logger.debug(f"Checking if entity '{entity_name}' can be processed...")
            unmet_dependencies = self.get_unmet_dependencies(entity=entity_name)
            if unmet_dependencies:
                logger.debug(f"Entity '{entity_name}' has unmet dependencies: {unmet_dependencies}")
                continue
            logger.debug(f"Entity '{entity_name}' can be processed next.")
            return entity_name
        return None

    def get_unmet_dependencies(self, entity: str) -> set[str]:
        return set(self.config.get_table(entity_name=entity).depends_on) - self.processed_entities

    def discard(self, entity: str) -> None:
        """Mark an entity as processed and remove it from the unprocessed set."""
        self.unprocessed.discard(entity)

    def get_all_unmet_dependencies(self) -> dict[str, set[str]]:
        unmet_dependencies: dict[str, set[str]] = {entity: self.get_unmet_dependencies(entity=entity) for entity in self.unprocessed}
        return {k: v for k, v in unmet_dependencies.items() if v}

    def log_unmet_dependencies(self) -> None:
        for entity, unmet in self.get_all_unmet_dependencies().items():
            logger.error(f"Entity '{entity}' has unmet dependencies: {unmet}")

    @property
    def processed_entities(self) -> set[str]:
        """Return the set of processed entities."""
        return set(self.config.table_names) - self.unprocessed


class ArbodatSurveyNormalizer:

    def __init__(self, df: pd.DataFrame) -> None:
        self.data: dict[str, pd.DataFrame] = {"survey": df}
        self.config: TablesConfig = TablesConfig()
        self.state: ProcessState = ProcessState(config=self.config)

    @property
    def survey(self) -> pd.DataFrame:
        return self.data["survey"]

    def resolve_source(self, source: pd.DataFrame | str | None = None) -> pd.DataFrame:
        if isinstance(source, str):
            if not source in self.data:
                raise ValueError(f"Source table '{source}' not found in stored data")
            return self.data[source]
        return self.survey

    def register(self, name: str, df: pd.DataFrame) -> pd.DataFrame:
        self.data[name] = df
        return df

    @staticmethod
    def load(path: str | Path, sep: str = "\t") -> "ArbodatSurveyNormalizer":
        """Read Arbodat CSV (usually tab-separated)."""
        df: pd.DataFrame = pd.read_csv(path, sep=sep, dtype=str, keep_default_na=False)
        return ArbodatSurveyNormalizer(df)

    def extract_entity(self, entity_name: str) -> pd.DataFrame:
        """Extract entity DataFrame based on configuration."""

        table_cfg: TableConfig = self.config.get_table(entity_name)

        if table_cfg.is_fixed_data:
            raise ValueError(f"Entity '{entity_name}' is configured as fixed data and cannot be extracted")

        source: pd.DataFrame = self.resolve_source(source=table_cfg.source)

        if not isinstance(table_cfg.columns, list) or not all(isinstance(c, str) for c in table_cfg.columns):
            raise ValueError(f"Invalid columns configuration for entity '{entity_name}': {table_cfg.columns}")

        data: pd.DataFrame = get_subset(
            source=source,
            columns=table_cfg.usage_columns,
            extra_columns=table_cfg.extra_columns,
            drop_duplicates=table_cfg.drop_duplicates,
            surrogate_id=table_cfg.surrogate_id,
            raise_if_missing=False,
        )

        if table_cfg.drop_empty_rows:
            """Discard rows that are empty in all **data** columns (excluding keys and foreign keys)."""
            data_columns: list[str] = table_cfg.data_columns
            if data_columns:
                data = data.dropna(subset=data_columns, how="all")

        return data

    def normalize(self) -> None:
        """Extract all configured entities and store them."""
        while len(self.state.unprocessed) > 0:

            entity: str | None = self.state.get_next_entity_to_process()

            if entity is None:
                self.state.log_unmet_dependencies()
                raise ValueError(f"Circular or unresolved dependencies detected: {self.state.unprocessed}")

            table_cfg: TableConfig = self.config.get_table(entity)

            logger.debug(f"Normalizing entity '{entity}'...")
            if entity == "location":
                logger.debug(f"Debugging: {entity}")

            data: pd.DataFrame

            if table_cfg.is_fixed_data:
                data = create_fixed_table(entity_name=entity, table_cfg=table_cfg)
            else:
                data = self.extract_entity(entity)

            self.register(entity, data)

            self.link_entity(entity_name=entity)

            if table_cfg.unnest:
                try:
                    data = self.unnest_entity(entity=entity)
                    self.link_entity(entity_name=entity)
                except ValueError as e:
                    logger.warning(f"Skipping unnesting for entity '{entity}': {e}")

            self.link()  # Try to resolve any pending deferred links after each entity is processed

            self.state.discard(entity=entity)

    def link(self):
        """Link entities based on foreign key configuration."""
        for entity_name in self.state.processed_entities:
            self.link_entity(entity_name=entity_name)

    def link_entity(self, entity_name: str) -> bool:

        table_cfg: TableConfig = self.config.get_table(entity_name=entity_name)
        foreign_keys: list[ForeignKeyConfig] = table_cfg.foreign_keys or []
        deferred: bool = False
        local_df: pd.DataFrame = self.data[entity_name]

        for fk in foreign_keys:

            if len(fk.local_keys) != len(fk.remote_keys):
                raise ValueError(f"Foreign key for entity '{entity_name}': local keys {fk.local_keys}, remote keys {fk.remote_keys}")

            if fk.remote_entity not in self.config.table_names:
                raise ValueError(f"Remote entity '{fk.remote_entity}' not found in configuration for linking with '{entity_name}'")

            remote_cfg: TableConfig = self.config.get_table(fk.remote_entity)
            remote_id: str | None = remote_cfg.surrogate_id or f"{fk.remote_entity}_id"
            remote_df: pd.DataFrame = self.data[fk.remote_entity]

            if remote_id in local_df.columns:
                logger.debug(f"Linking {entity_name}: skipped since FK '{remote_id}' already exists.")
                continue

            specification: ForeignKeyDataSpecification = ForeignKeyDataSpecification(cfg=self.config, table_store=self.data)

            satisfied: bool | None = specification.is_satisfied_by(fk_cfg=fk)
            if satisfied is False:
                logger.error(specification.error)
                continue

            if specification.deferred:
                deferred = True
                continue

            remote_extra_cols: list[str] = fk.remote_keys + list(fk.remote_extra_columns.keys())
            missing_remote_cols: list[str] = [col for col in remote_extra_cols if col not in remote_df.columns]
            if missing_remote_cols:
                logger.warning(
                    f"Skipping extra link columns for entity '{entity_name}' to '{fk.remote_entity}': missing remote columns {missing_remote_cols} in remote table"
                )
                remote_extra_cols = [col for col in remote_extra_cols if col in remote_df.columns]

            remote_select_df: pd.DataFrame = remote_df[[remote_id] + remote_extra_cols]

            # Rename extra columns to their target names
            if fk.remote_extra_columns:
                remote_select_df = remote_select_df.rename(columns=fk.remote_extra_columns)

            size_before_merge: int = len(local_df)
            linked_df: pd.DataFrame = local_df.merge(
                right=remote_select_df,
                left_on=fk.local_keys,
                right_on=fk.remote_keys,
                how=fk.how or "inner",
                suffixes=("", f"_{fk.remote_entity}"),
            )
            size_after_merge: int = len(linked_df)
            logger.debug(f"[Linking {entity_name}] merge size: before={size_before_merge}, after={size_after_merge}")

            if fk.remote_extra_columns and fk.drop_remote_id:
                linked_df = linked_df.drop(columns=[remote_id], errors="ignore")

            local_df = linked_df
            logger.debug(f"[Linking {entity_name}] added link to '{fk.remote_entity}' via {fk.local_keys} -> {fk.remote_keys}")

        self.data[entity_name] = local_df

        return deferred

    def store(self, target: str, mode: Literal["xlsx", "csv", "db"]) -> None:
        """Write to specified target based on the specified mode."""
        dispatcher_cls: Dispatcher = Dispatchers.get(mode)
        if dispatcher_cls:
            dispatcher = dispatcher_cls()  # type: ignore
            dispatcher.dispatch(target=target, data=self.data)
        else:
            raise ValueError(f"Unsupported dispatch mode: {mode}")

    def unnest_all(self) -> None:
        """Unnest dataframes based on configuration."""
        for entity in self.data:
            self.data[entity] = self.unnest_entity(entity=entity)

    def unnest_entity(self, *, entity: str) -> pd.DataFrame:
        table_cfg: TableConfig = self.config.get_table(entity)
        if table_cfg.unnest:
            self.data[entity] = unnest(entity=entity, table=self.data[entity], table_cfg=table_cfg)
        return self.data[entity]

    def translate(self, translations_map: dict[str, str]) -> None:
        """Translate column names using translation from config."""
        self.data = translate(self.data, translations_map=translations_map)

    def drop_foreign_key_columns(self) -> None:
        """Drop foreign key columns used for linking that are no longer needed after linking. Keep if in columns list."""
        for entity_name in self.data.keys():
            if entity_name not in self.config.table_names:
                continue
            table_cfg: TableConfig = self.config.get_table(entity_name=entity_name)
            self.data[entity_name] = table_cfg.drop_fk_columns(table=self.data[entity_name])

    def add_system_id_columns(self) -> None:
        """Add "system_id" with same value as surrogate_id. Set surrogate_id to None."""
        for entity_name in self.data.keys():
            if entity_name not in self.config.table_names:
                continue
            table_cfg: TableConfig = self.config.get_table(entity_name=entity_name)
            self.data[entity_name] = table_cfg.add_system_id_column(table=self.data[entity_name])

    def move_keys_to_front(self) -> None:
        """Reorder columns in this order: primary key, foreign key column, extra columns, other columns."""
        for entity_name in self.data.keys():
            if entity_name not in self.config.table_names:
                continue
            self.data[entity_name] = self.config.reorder_columns(entity_name, self.data[entity_name])
