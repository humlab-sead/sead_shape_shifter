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
from typing import Any, Literal

import pandas as pd
from loguru import logger

from src.arbodat.config_model import DataSourceConfig, TableConfig, TablesConfig
from src.arbodat.dispatch import Dispatcher, Dispatchers
from src.arbodat.link import link_entity
from src.arbodat.loaders.database_loaders import SqlLoader, SqlLoaderFactory
from src.arbodat.loaders.fixed_loader import FixedLoader
from src.arbodat.mapping import LinkToRemoteService
from src.arbodat.unnest import unnest
from src.arbodat.extract import add_surrogate_id, get_subset, translate


class ProcessState:
    """Helper class to track processing state of entities during normalization."""

    def __init__(self, config: TablesConfig) -> None:
        self.config: TablesConfig = config
        self.unprocessed: set[str] = set(self.config.table_names)

    def get_next_entity_to_process(self) -> str | None:
        """Get the next entity that can be processed based on dependencies."""
        logger.debug(f"Processed entities so far: {self.processed_entities}")
        for entity_name in set(self.config.table_names) - self.processed_entities:
            logger.debug(f"{entity_name}[check]: Checking if entity '{entity_name}' can be processed...")
            unmet_dependencies = self.get_unmet_dependencies(entity=entity_name)
            if unmet_dependencies:
                logger.debug(f"{entity_name}[check]: Entity has unmet dependencies: {unmet_dependencies}")
                continue
            logger.debug(f"{entity_name}[check]: Entity can be processed next.")
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
            logger.error(f"{entity}[check]: Entity has unmet dependencies: {unmet}")

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

    async def resolve_source(self, table_cfg: TableConfig) -> pd.DataFrame:
        """Resolve the source DataFrame for the given entity based on its configuration."""

        if table_cfg.is_fixed_data:
            return await FixedLoader().load(entity_name=table_cfg.entity_name, table_cfg=table_cfg)

        if table_cfg.is_sql_data:

            if not table_cfg.data_source:
                raise ValueError(f"Entity source must be set to a valid data source for entity '{table_cfg.entity_name}'")

            data_source_cfg: DataSourceConfig = self.config.get_data_source(table_cfg.data_source)
            loader: SqlLoader = SqlLoaderFactory().create_loader(driver=data_source_cfg.driver, db_opts=data_source_cfg.options)

            return await loader.load(entity_name=table_cfg.entity_name, table_cfg=table_cfg)

        if isinstance(table_cfg.source, str):
            if not table_cfg.source in self.data:
                raise ValueError(f"Source table '{table_cfg.source}' not found in stored data")
            return self.data[table_cfg.source]

        return self.survey

    def register(self, name: str, df: pd.DataFrame) -> pd.DataFrame:
        self.data[name] = df
        return df

    @staticmethod
    def load(path: str | Path, sep: str = "\t") -> "ArbodatSurveyNormalizer":
        """Read Arbodat CSV (usually tab-separated)."""
        df: pd.DataFrame = pd.read_csv(path, sep=sep, dtype=str, keep_default_na=False)
        return ArbodatSurveyNormalizer(df)

    async def normalize(self) -> None:
        """Extract all configured entities and store them."""
        while len(self.state.unprocessed) > 0:

            entity: str | None = self.state.get_next_entity_to_process()

            if entity is None:
                self.state.log_unmet_dependencies()
                raise ValueError(f"Circular or unresolved dependencies detected: {self.state.unprocessed}")

            table_cfg: TableConfig = self.config.get_table(entity)

            logger.debug(f"{entity}[normalizing]: Normalizing entity...")
            if entity == "dataset":
                logger.debug(f"{entity}[debugging]: breakpoint for dataset entity")

            source: pd.DataFrame = await self.resolve_source(table_cfg=table_cfg)

            if not isinstance(table_cfg.columns, list) or not all(isinstance(c, str) for c in table_cfg.columns):
                raise ValueError(f"Invalid columns configuration for entity '{entity}': {table_cfg.columns}")

            data: pd.DataFrame = get_subset(
                source=source,
                columns=table_cfg.usage_columns,
                entity_name=entity,
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

            if table_cfg.surrogate_id:
                data = add_surrogate_id(data, table_cfg.surrogate_id)

            self.register(entity, data)

            link_entity(entity_name=entity, config=self.config, data=self.data)

            if table_cfg.unnest:
                try:
                    data = self.unnest_entity(entity=entity)
                    link_entity(entity_name=entity, config=self.config, data=self.data)
                except ValueError as e:
                    logger.warning(f"{entity}[normalizing]: Skipping unnesting: {e}")

            self.link()  # Try to resolve any pending deferred links after each entity is processed

            self.state.discard(entity=entity)

    def link(self):
        """Link entities based on foreign key configuration."""
        for entity_name in self.state.processed_entities:
            link_entity(entity_name=entity_name, config=self.config, data=self.data)

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

    def map_to_remote(self, link_cfgs: dict[str, dict[str, Any]]) -> None:
        """Map local Arbodat PK values to SEAD identities using mapping configuration."""
        if not link_cfgs:
            return
        service = LinkToRemoteService(remote_link_cfgs=link_cfgs)
        for entity_name in self.data.keys():
            if entity_name not in link_cfgs:
                continue
            self.data[entity_name] = service.link_to_remote(entity_name, self.data[entity_name])
