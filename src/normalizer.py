"""
Normalize data from various data sources into structured tables
and write them as CSVs or sheets in a single Excel file.

"""

from pathlib import Path
from typing import Any, Self

import pandas as pd
from loguru import logger

from src.dispatch import Dispatcher, Dispatchers
from src.extract import SubsetService
from src.loaders import DataLoader
from src.loaders.base_loader import DataLoaders
from src.mapping import LinkToRemoteService
from src.model import DataSourceConfig, ShapeShiftProject, TableConfig
from src.process_state import ProcessState
from src.transforms.drop import drop_duplicate_rows, drop_empty_rows
from src.transforms.filter import apply_filters
from src.transforms.link import ForeignKeyLinker
from src.transforms.translate import translate
from src.transforms.unnest import unnest
from src.transforms.utility import add_system_id  # Renamed from add_surrogate_id

# Debug flag to control verbose normalization logging
# Set to True to see detailed "Normalizing entity..." logs for each entity
# When False, only INFO level logs for overall progress are shown
_ENABLE_NORMALIZATION_DEBUG = True


class ShapeShifter:

    def __init__(
        self,
        project: ShapeShiftProject | str,
        default_entity: str | None = None,
        table_store: dict[str, pd.DataFrame] | None = None,
        target_entities: set[str] | None = None,
    ) -> None:

        if not project or not isinstance(project, (ShapeShiftProject, str)):
            raise ValueError("A valid configuration must be provided")

        self.default_entity: str | None = default_entity
        self.table_store: dict[str, pd.DataFrame] = table_store or {}
        self.project: ShapeShiftProject = ShapeShiftProject.from_source(project)
        self.state: ProcessState = ProcessState(project=self.project, table_store=self.table_store, target_entities=target_entities)
        self.linker: ForeignKeyLinker = ForeignKeyLinker(table_store=self.table_store, project=self.project)

    def resolve_loader(self, table_cfg: TableConfig) -> DataLoader | None:
        """Resolve the DataLoader, if any, for the given TableConfig."""
        if table_cfg.data_source:
            data_source: DataSourceConfig = self.project.get_data_source(table_cfg.data_source)
            return DataLoaders.get(key=data_source.driver)(data_source=data_source)

        if table_cfg.type and table_cfg.type in DataLoaders.items:
            return DataLoaders.get(key=table_cfg.type)(data_source=None)

        return None

    async def resolve_source(self, table_cfg: TableConfig) -> pd.DataFrame:
        """Resolve the source DataFrame for the given entity based on its configuration."""

        loader: DataLoader | None = self.resolve_loader(table_cfg=table_cfg)
        if loader:
            # logger.debug(f"{table_cfg.entity_name}[source]: Loading data using loader '{loader.__class__.__name__}'...")
            return await loader.load(entity_name=table_cfg.entity_name, table_cfg=table_cfg)

        source_table: str | None = table_cfg.source or self.default_entity
        if source_table and source_table in self.table_store:
            return self.table_store[source_table]

        raise ValueError(f"Unable to resolve source for entity '{table_cfg.entity_name}'")

    async def get_subset(self, subset_service: SubsetService, entity: str, table_cfg: TableConfig) -> pd.DataFrame:

        dfs: list[pd.DataFrame] = []

        for sub_table_cfg in table_cfg.get_sub_table_configs():
            # logger.debug(f"{entity}[normalizing]: Processing sub-table '{sub_table_cfg.entity_name}'...")
            sub_source: pd.DataFrame = await self.resolve_source(table_cfg=sub_table_cfg)
            sub_data: pd.DataFrame = subset_service.get_subset(
                source=sub_source,
                table_cfg=sub_table_cfg,
                drop_empty=False,
                raise_if_missing=False,
            )
            dfs.append(sub_data)

            # Concatenate all dataframes (filter out empty DataFrames to avoid FutureWarning)
        non_empty_dfs: list[pd.DataFrame] = [df for df in dfs if not df.empty]
        if not non_empty_dfs:
            logger.warning(f"{entity}[normalizing]: All sub-tables are empty after processing.")

        data: pd.DataFrame = (
            pd.concat(non_empty_dfs, ignore_index=True)
            if non_empty_dfs
            else pd.DataFrame(columns=table_cfg.keys_columns_and_fks) if len(dfs) == 0 else dfs[0]
        )

        return data

    async def normalize(self) -> Self:
        """Extract all configured entities and store them."""
        subset_service: SubsetService = SubsetService()

        while len(self.state.unprocessed_entities) > 0:

            entity: str | None = self.state.get_next_entity_to_process()

            if entity is None:
                self.state.log_unmet_dependencies()
                raise ValueError(f"Circular or unresolved dependencies detected: {self.state.unprocessed_entities}")

            table_cfg: TableConfig = self.project.get_table(entity)

            if _ENABLE_NORMALIZATION_DEBUG:
                logger.debug(f"{entity}[normalizing]: Normalizing entity...")

            if not isinstance(table_cfg.columns, list):
                raise ValueError(f"Invalid columns configuration for entity '{entity}': must be a list")

            if not all(isinstance(col, str) for col in table_cfg.columns):
                raise ValueError(f"Invalid columns configuration for entity '{entity}': all columns must be strings")

            # Process all configured tables (base + append items)
            data: pd.DataFrame = await self.get_subset(subset_service, entity, table_cfg)

            # Add public_id column if needed (after concatenation, before filters)
            # For entities with append, public_id is filtered from append sources and added here
            if table_cfg.has_append:
                data = table_cfg.add_public_id_column(data)

            if table_cfg.filters:
                data = apply_filters(name=entity, df=data, cfg=table_cfg, data_store=self.table_store)

            delay_drop_duplicates: bool = table_cfg.is_drop_duplicate_dependent_on_unnesting()
            # Apply post-concatenation deduplication if append_mode is "distinct"
            # if table_cfg.has_append and table_cfg.append_mode == "distinct" and not delay_drop_duplicates:
            if table_cfg.drop_duplicates and not delay_drop_duplicates:
                data = drop_duplicate_rows(
                    data=data,
                    columns=table_cfg.drop_duplicates if table_cfg.drop_duplicates else True,
                    entity_name=entity,
                    fd_check=table_cfg.check_functional_dependency,
                    strict_fd_check=table_cfg.strict_functional_dependency,
                )
                # logger.info(f"{entity}[append]: Applied UNION DISTINCT, rows after dedup: {len(data)}")

            self.table_store[entity] = data

            self.linker.link_entity(entity_name=entity)

            if table_cfg.unnest:
                self.unnest_entity(entity=entity)
                self.linker.link_entity(entity_name=entity)

            if delay_drop_duplicates and table_cfg.drop_duplicates:
                self.table_store[entity] = drop_duplicate_rows(
                    data=self.table_store[entity],
                    columns=table_cfg.drop_duplicates,
                    entity_name=entity,
                    fd_check=table_cfg.check_functional_dependency,
                    strict_fd_check=table_cfg.strict_functional_dependency,
                )

            self._check_duplicate_keys(entity, table_cfg)

            if table_cfg.drop_empty_rows:
                self.table_store[entity] = drop_empty_rows(
                    data=self.table_store[entity], entity_name=entity, subset=table_cfg.drop_empty_rows
                )

            # Add system_id if requested and not present (always uses "system_id" column name)
            if table_cfg.system_id and table_cfg.system_id not in self.table_store[entity].columns:
                self.table_store[entity] = add_system_id(self.table_store[entity], table_cfg.system_id)

            self.retry_linking()

        if self.linker.deferred_tracker.deferred:
            logger.warning(f"Entities with unresolved deferred links after normalization: {self.linker.deferred_tracker.deferred}")

        return self

    def _check_duplicate_keys(self, entity: str, table_cfg: TableConfig) -> None:
        """Check for duplicate keys in the processed table and log an error if found."""

        if not table_cfg.keys:
            return

        keys: set[str] = set(table_cfg.keys) if table_cfg.keys else set()
        missing_keys: set[str] = keys - set(self.table_store[entity].columns)

        if missing_keys:
            # We cannot check for duplicates if keys are missing, just return
            return

        has_duplicate_keys: bool = bool(self.table_store[entity].duplicated(subset=list(table_cfg.keys)).any())
        if has_duplicate_keys:
            # raise ValueError(f"{entity}[keys]: Duplicate keys found for keys {table_cfg.keys}.")
            logger.error(f"{entity}[keys]: DUPLICATE KEYS FOUND FOR KEYS {table_cfg.keys}.")

    def retry_linking(self) -> None:
        """Retry linking only for entities currently in deferred set."""
        for entity_name in self.linker.deferred_tracker.deferred:
            self.linker.link_entity(entity_name=entity_name)

    def store(self, target: str, mode: str) -> Self:
        """Write to specified target based on the specified mode."""
        dispatcher_cls: type[Dispatcher] = Dispatchers.get(mode)
        if dispatcher_cls:
            dispatcher = dispatcher_cls(self.project)  # type: ignore
            dispatcher.dispatch(target=target, data=self.table_store)
        else:
            raise ValueError(f"Unsupported dispatch mode: {mode}")
        return self

    def unnest_all(self) -> Self:
        """Unnest dataframes based on configuration."""
        for entity in self.table_store:
            self.table_store[entity] = self.unnest_entity(entity=entity)
        return self

    def unnest_entity(self, *, entity: str) -> pd.DataFrame:
        try:
            table_cfg: TableConfig = self.project.get_table(entity)
            if table_cfg.unnest:
                self.table_store[entity] = unnest(entity=entity, table=self.table_store[entity], table_cfg=table_cfg)
        except Exception as e:  # ldtype: ignore ; pylint: disable=broad-except
            logger.error(f"Error unnesting entity {entity}: {e}")
        return self.table_store[entity]

    def translate(self, translations_map: dict[str, str]) -> Self:
        """Translate column names using translation from config."""
        self.table_store = translate(self.table_store, translations_map=translations_map)
        return self

    def drop_foreign_key_columns(self) -> Self:
        """Drop foreign key columns used for linking that are no longer needed after linking. Keep if in columns list."""
        for entity_name in self.table_store.keys():
            if entity_name not in self.project.table_names:
                continue
            table_cfg: TableConfig = self.project.get_table(entity_name=entity_name)
            self.table_store[entity_name] = table_cfg.drop_fk_columns(table=self.table_store[entity_name])
        return self

    def add_system_id_columns(self) -> Self:
        """Add auto-incrementing 'system_id' column to each entity table."""
        for entity_name in self.table_store.keys():
            if entity_name not in self.project.table_names:
                continue
            table_cfg: TableConfig = self.project.get_table(entity_name=entity_name)
            self.table_store[entity_name] = table_cfg.add_system_id_column(table=self.table_store[entity_name])
        return self

    def move_keys_to_front(self) -> Self:
        """Reorder columns in this order: primary key, foreign key column, extra columns, other columns."""
        for entity_name in self.table_store.keys():
            if entity_name not in self.project.table_names:
                continue
            self.table_store[entity_name] = self.project.reorder_columns(entity_name, self.table_store[entity_name])
        return self

    def map_to_remote(self, link_cfgs: dict[str, dict[str, Any]]) -> Self:
        """Map local PK values to remote identities using mapping configuration."""
        if not link_cfgs:
            return self
        service = LinkToRemoteService(remote_link_cfgs=link_cfgs)
        for entity_name in self.table_store.keys():
            if entity_name not in link_cfgs:
                continue
            self.table_store[entity_name] = service.link_to_remote(entity_name, self.table_store[entity_name])
        return self

    def log_shapes(self, target: str) -> Self:
        """Log the shape of each table as a TSV in same folder as target."""
        try:
            folder: str = target if Path(target).is_dir() else str(Path(target).parent)
            tsv_filename: Path = Path(folder) / "table_shapes.tsv"
            with open(tsv_filename, "w", encoding="utf-8") as f:
                f.write("entity\tnum_rows\tnum_columns\n")
                for name, table in self.table_store.items():
                    f.write(f"{name}\t{table.shape[0]}\t{table.shape[1]}\n")
            logger.info(f"Table shapes written to {tsv_filename}")
        except Exception as e:  # type: ignore ; pylint: disable=broad-except
            logger.error(f"Failed to write table shapes to TSV: {e}")
        return self

    def finalize(self) -> Self:
        """Finalize processing by performing final transformations."""
        # self.drop_foreign_key_columns()
        # self.add_system_id_columns()
        # self.move_keys_to_front()
        # drops = self.config.options.get("finally.drops")
        return self
