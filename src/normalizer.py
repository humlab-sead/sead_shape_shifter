"""
Normalize data from various data sources into structured tables
and write them as CSVs or sheets in a single Excel file.

"""

from pathlib import Path
from typing import Any, Self

import pandas as pd
from loguru import logger

from src.dispatch import Dispatcher, Dispatchers
from src.extract import SubsetService, add_surrogate_id, drop_duplicate_rows, drop_empty_rows, translate
from src.filter import apply_filters
from src.link import ForeignKeyLinker
from src.loaders import DataLoader
from src.loaders.base_loader import DataLoaders
from src.mapping import LinkToRemoteService
from src.model import DataSourceConfig, ShapeShiftProject, TableConfig
from src.unnest import unnest

# Debug flag to control verbose normalization logging
# Set to True to see detailed "Normalizing entity..." logs for each entity
# When False, only INFO level logs for overall progress are shown
_ENABLE_NORMALIZATION_DEBUG = False


class ProcessState:
    """Helper class to track processing state of entities during normalization."""

    def __init__(self, project: ShapeShiftProject, table_store: dict[str, pd.DataFrame], target_entities: set[str] | None = None) -> None:
        self.project: ShapeShiftProject = project
        self.table_store: dict[str, pd.DataFrame] = table_store
        # Resolve target entities through the project to ensure dependencies are included consistently.
        self.target_entities: set[str] = project.resolve_target_entities(target_entities)

        # def _initialize_process_state(self, target_entities: set[str] | None = None) -> ProcessState:

    def get_next_entity_to_process(self) -> str | None:
        """Get the next entity that can be processed based on dependencies."""
        # logger.debug(f"Processed entities so far: {self.processed_entities}")

        for entity_name in self.unprocessed_entities:
            # logger.debug(f"{entity_name}[check]: Checking if entity '{entity_name}' can be processed...")
            unmet_dependencies: set[str] = self.get_unmet_dependencies(entity=entity_name)
            if unmet_dependencies:
                # logger.debug(f"{entity_name}[check]: Entity has unmet dependencies: {unmet_dependencies}")
                continue
            # logger.debug(f"{entity_name}[check]: Entity can be processed next.")
            return entity_name
        return None

    def get_unmet_dependencies(self, entity: str) -> set[str]:
        return self.project.get_table(entity_name=entity).depends_on - self.processed_entities

    def get_all_unmet_dependencies(self) -> dict[str, set[str]]:
        unmet_dependencies: dict[str, set[str]] = {
            entity: self.get_unmet_dependencies(entity=entity) for entity in self.unprocessed_entities
        }
        return {k: v for k, v in unmet_dependencies.items() if v}

    def log_unmet_dependencies(self) -> None:
        for entity, unmet in self.get_all_unmet_dependencies().items():
            logger.error(f"{entity}[check]: Entity has unmet dependencies: {unmet}")

    @property
    def processed_entities(self) -> set[str]:
        """Return the set of processed entities."""
        return set(self.table_store.keys())

    @property
    def unprocessed_entities(self) -> set[str]:
        """Return the set of unprocessed target entities."""
        return self.target_entities - self.processed_entities


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
        self.state: ProcessState = ProcessState(
            project=self.project, table_store=self.table_store, target_entities=self.project.resolve_target_entities(target_entities)
        )
        self.linker: ForeignKeyLinker = ForeignKeyLinker(table_store=self.table_store)

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

    def register(self, name: str, df: pd.DataFrame) -> pd.DataFrame:
        self.table_store[name] = df
        return df

    async def get_subset(self, subset_service: SubsetService, entity: str, table_cfg: TableConfig) -> pd.DataFrame:

        dfs: list[pd.DataFrame] = []
        delay_drop_duplicates: bool = table_cfg.is_drop_duplicate_dependent_on_unnesting()

        for sub_table_cfg in table_cfg.get_sub_table_configs():
            # logger.debug(f"{entity}[normalizing]: Processing sub-table '{sub_table_cfg.entity_name}'...")
            sub_source: pd.DataFrame = await self.resolve_source(table_cfg=sub_table_cfg)
            sub_data: pd.DataFrame = subset_service.get_subset(
                source=sub_source,
                columns=self.get_subset_columns(sub_table_cfg),
                entity_name=sub_table_cfg.entity_name,
                extra_columns=sub_table_cfg.extra_columns,
                drop_duplicates=sub_table_cfg.drop_duplicates if not delay_drop_duplicates else False,
                replacements=sub_table_cfg.replacements if sub_table_cfg.replacements else None,
                raise_if_missing=False,
                drop_empty=False,
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

            # source: pd.DataFrame = await self.resolve_source(table_cfg=table_cfg)
            if not isinstance(table_cfg.columns, list):
                raise ValueError(f"Invalid columns configuration for entity '{entity}': must be a list")

            if not all(isinstance(col, str) for col in table_cfg.columns):
                raise ValueError(f"Invalid columns configuration for entity '{entity}': all columns must be strings")

            # Process all configured tables (base + append items)
            data: pd.DataFrame = await self.get_subset(subset_service, entity, table_cfg)

            if table_cfg.filters:
                data = apply_filters(name=entity, df=data, cfg=table_cfg, data_store=self.table_store)

            delay_drop_duplicates: bool = table_cfg.is_drop_duplicate_dependent_on_unnesting()
            # Apply post-concatenation deduplication if append_mode is "distinct"
            # if table_cfg.has_append and table_cfg.append_mode == "distinct" and not delay_drop_duplicates:
            if table_cfg.drop_duplicates and not delay_drop_duplicates:
                data = drop_duplicate_rows(
                    data=data, columns=table_cfg.drop_duplicates if table_cfg.drop_duplicates else True, entity_name=entity
                )
                # logger.info(f"{entity}[append]: Applied UNION DISTINCT, rows after dedup: {len(data)}")

            self.register(entity, data)

            self.linker.link_entity(entity_name=entity, config=self.project)

            if table_cfg.unnest:
                self.unnest_entity(entity=entity)
                self.linker.link_entity(entity_name=entity, config=self.project)
            if delay_drop_duplicates and table_cfg.drop_duplicates:
                self.table_store[entity] = drop_duplicate_rows(
                    data=self.table_store[entity],
                    fd_check=table_cfg.check_functional_dependency,
                    columns=table_cfg.drop_duplicates,
                    entity_name=entity,
                )

            self._check_duplicate_keys(entity, table_cfg)

            if table_cfg.drop_empty_rows:
                self.table_store[entity] = drop_empty_rows(
                    data=self.table_store[entity], entity_name=entity, subset=table_cfg.drop_empty_rows
                )

            # Add surrogate ID if requested and not present
            if table_cfg.surrogate_id and table_cfg.surrogate_id not in self.table_store[entity].columns:
                self.table_store[entity] = add_surrogate_id(self.table_store[entity], table_cfg.surrogate_id)

            self.link()  # Try to resolve any pending deferred links after each entity is processed
        return self

    def get_subset_columns(self, sub_table_cfg):
        columns: list[str] = sub_table_cfg.keys_columns_and_fks
        if sub_table_cfg.unnest:
            # Ignore columns that will be un-nested
            columns = [col for col in columns if col not in sub_table_cfg.unnest_columns]
        return columns

    def _check_duplicate_keys(self, entity, table_cfg) -> None:
        """Check for duplicate keys in the processed table and log an error if found."""

        if not table_cfg.keys:
            return

        missing_keys: list[str] = table_cfg.keys - set(self.table_store[entity].columns)
        if missing_keys:
            # We cannot check for duplicates if keys are missing, just return
            return

        has_duplicate_keys: bool = bool(self.table_store[entity].duplicated(subset=list(table_cfg.keys)).any())
        if has_duplicate_keys:
            # raise ValueError(f"{entity}[keys]: Duplicate keys found for keys {table_cfg.keys}.")
            logger.error(f"{entity}[keys]: DUPLICATE KEYS FOUND FOR KEYS {table_cfg.keys}.")

    def link(self) -> Self:
        """Link entities based on foreign key configuration."""
        for entity_name in self.state.processed_entities:
            deferred: bool = self.linker.link_entity(entity_name=entity_name, config=self.project)

            if deferred:
                logger.warning(f"{entity_name}[linking]: entity has deferred foreign keys after final linking.")

        return self

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
        """Add "system_id" with same value as surrogate_id. Set surrogate_id to None."""
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
