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
from src.loaders.base_loader import DataLoaders, LoaderType
from src.mapping import LinkToRemoteService
from src.model import DataSourceConfig, ShapeShiftProject, TableConfig
from src.path_resolution import resolve_managed_file_path
from src.process_state import ProcessState
from src.transforms.drop import drop_duplicate_rows, drop_empty_rows
from src.transforms.extra_columns import ExtraColumnEvaluator
from src.transforms.filter import apply_filters
from src.transforms.link import ForeignKeyLinker
from src.transforms.translate import translate
from src.transforms.unnest import unnest
from src.transforms.utility import add_system_id  # Renamed from add_surrogate_id


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
        self.extra_col_evaluator: ExtraColumnEvaluator = ExtraColumnEvaluator()
        self.unresolved_extra_columns: dict[str, dict[str, dict[str, Any]]] = {}

    def resolve_loader(self, table_cfg: TableConfig) -> DataLoader | None:
        """Resolve the DataLoader, if any, for the given TableConfig."""
        if table_cfg.data_source:
            data_source: DataSourceConfig = self.project.get_data_source(table_cfg.data_source)
            return DataLoaders.get(key=data_source.driver)(data_source=data_source)

        if table_cfg.type and table_cfg.type in DataLoaders.items:
            return DataLoaders.get(key=table_cfg.type)(data_source=None)

        return None

    def _resolve_project_local_file_options(self, table_cfg: TableConfig, loader: DataLoader) -> None:
        """Resolve `location: local` file paths relative to the project file directory."""
        if loader.loader_type() != LoaderType.FILE:
            return

        project_filename: str | None = self.project.filename
        if not project_filename:
            return

        options: dict[str, Any] = dict(table_cfg.options or {})
        filename: str | None = options.get("filename")
        location: str | None = options.get("location")

        if location != "local" or not isinstance(filename, str) or not filename.strip():
            return

        file_path = Path(filename)
        if file_path.is_absolute():
            return

        project_dir = Path(project_filename).resolve().parent
        options["filename"] = str(resolve_managed_file_path(filename, location="local", local_root=project_dir))
        table_cfg.entity_cfg["options"] = options

    async def resolve_source(self, table_cfg: TableConfig) -> pd.DataFrame:
        """Resolve the source DataFrame for the given entity based on its configuration."""
        logger.trace(f"Resolving source for entity '{table_cfg.entity_name}'")
        loader: DataLoader | None = self.resolve_loader(table_cfg=table_cfg)
        if loader:
            self._resolve_project_local_file_options(table_cfg, loader)
            logger.trace(f"{table_cfg.entity_name}[source]: Loading data using loader '{loader.__class__.__name__}'...")
            return await loader.load(entity_name=table_cfg.entity_name, table_cfg=table_cfg)

        source_table: str | None = table_cfg.source or self.default_entity
        if source_table and source_table in self.table_store:
            logger.trace(f"{table_cfg.entity_name}[source]: Using source table '{source_table}' from table_store...")
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
            # Apply column renaming for append items (align_by_position or column_mapping)
            # Pass parent's columns for align_by_position
            sub_data = sub_table_cfg.apply_column_renaming(sub_data, parent_columns=table_cfg.columns)

            # Special processing for merged entity branches
            if table_cfg.type == "merged":
                sub_data = self._process_merged_branch(entity, table_cfg, sub_table_cfg, sub_data)

            dfs.append(sub_data)

        # Concatenate all dataframes while excluding all-NA columns from dtype inference.
        # The dropped columns are restored afterward to preserve the expected schema.
        non_empty_dfs: list[pd.DataFrame] = [df for df in dfs if not df.empty]
        if not non_empty_dfs:
            logger.warning(f"{entity}[normalizing]: All sub-tables are empty after processing.")

        concat_columns: list[str] = list(dict.fromkeys(col for df in non_empty_dfs for col in df.columns))
        sanitized_dfs: list[pd.DataFrame] = [df.dropna(axis=1, how="all") for df in non_empty_dfs]

        data: pd.DataFrame = (
            pd.concat(sanitized_dfs, ignore_index=True).reindex(columns=concat_columns)
            if non_empty_dfs
            else pd.DataFrame(columns=table_cfg.keys_columns_and_fks) if len(dfs) == 0 else dfs[0]
        )

        return data

    def _process_merged_branch(
        self, entity: str, table_cfg: TableConfig, sub_table_cfg: TableConfig, sub_data: pd.DataFrame
    ) -> pd.DataFrame:
        """Process a single branch for a merged entity.

        Adds:
        - Branch discriminator column (e.g., 'analysis_entity_branch')
        - FK propagation columns (sparse, nullable Int64 FKs)

        Args:
            entity: Name of the merged entity
            table_cfg: Configuration for the merged entity
            sub_table_cfg: Configuration for this specific branch
            sub_data: DataFrame containing branch data

        Returns:
            DataFrame with added columns for merging
        """
        # Extract branch metadata from sub_table_cfg
        branch_name: str = sub_table_cfg.entity_cfg.get("_branch_name", "unknown")
        branch_source: str = sub_table_cfg.entity_cfg.get("source")

        # 1. Add branch discriminator column
        discriminator_column: str = f"{entity}_branch"
        sub_data[discriminator_column] = branch_name

        # 2. Add sparse FK propagation columns — one per branch source, named from the
        # source entity's public_id when available, otherwise {source_entity}_id.
        # The current branch's column is populated from the source entity's system_id;
        # all other branches receive NULL (sparse pattern).
        # system_id is available in sub_data because get_sub_table_configs() explicitly
        # includes it in the branch column list, and normalize() adds it per-entity before
        # downstream merged entities are processed.
        for branch_cfg in table_cfg.branches:
            branch_src: str = branch_cfg.get("source")
            source_cfg: dict[str, Any] = table_cfg.entities_cfg.get(branch_src, {}) if branch_src else {}
            fk_column_name: str = source_cfg.get("public_id") or f"{branch_src}_id"

            if branch_src == branch_source:
                # Populate from the source entity's system_id carried through sub_data
                if "system_id" in sub_data.columns:
                    sub_data[fk_column_name] = sub_data["system_id"].astype("Int64")
                else:
                    sub_data[fk_column_name] = pd.array(pd.NA, dtype="Int64")
            else:
                sub_data[fk_column_name] = pd.NA

            sub_data[fk_column_name] = sub_data[fk_column_name].astype("Int64")

        # Drop the source system_id so it doesn't pollute the merged entity's own identity column
        if "system_id" in sub_data.columns:
            sub_data = sub_data.drop(columns=["system_id"])

        return sub_data

    async def normalize(self) -> Self:
        """Extract all configured entities and store them."""
        subset_service: SubsetService = SubsetService()

        while len(self.state.unprocessed_entities) > 0:

            entity: str | None = self.state.get_next_entity_to_process()

            if entity is None:
                self.state.log_unmet_dependencies()
                raise ValueError(f"Circular or unresolved dependencies detected: {self.state.unprocessed_entities}")

            table_cfg: TableConfig = self.project.get_table(entity)

            if not all(isinstance(col, str) for col in table_cfg.columns):
                raise ValueError(f"Invalid columns configuration for entity '{entity}': all columns must be strings")

            # Process all configured tables (base + append items)
            data: pd.DataFrame = await self.get_subset(subset_service, entity, table_cfg)

            # Evaluate extra_columns immediately after loading (before FK linking)
            # This ensures columns added via extra_columns (including key columns) are available for FK validation
            if table_cfg.extra_columns:
                data, deferred = self.extra_col_evaluator.evaluate_extra_columns(
                    df=data,
                    extra_columns=table_cfg.extra_columns,
                    entity_name=entity,
                    defer_missing=True,  # Defer columns that reference FK-added columns
                )
                if deferred:
                    logger.trace(f"{entity}[extra_columns]: Deferred {len(deferred)} columns until after FK linking")

            if table_cfg.filters:
                data = apply_filters(name=entity, df=data, cfg=table_cfg, data_store=self.table_store, stage="extract")

            delay_drop_duplicates: bool = table_cfg.is_drop_duplicate_dependent_on_unnesting()
            # Apply post-concatenation deduplication if append_mode is "distinct"
            # if table_cfg.has_append and table_cfg.append_mode == "distinct" and not delay_drop_duplicates:
            if table_cfg.drop_duplicates and not delay_drop_duplicates:
                data = self.drop_duplicates(entity, table_cfg, data)
                # logger.info(f"{entity}[append]: Applied UNION DISTINCT, rows after dedup: {len(data)}")

            self.table_store[entity] = data

            self.linker.link_entity(entity_name=entity)

            # Re-evaluate deferred extra_columns after FK linking (in case they reference FK-added columns)
            self._evaluate_deferred_extra_columns(entity)

            if table_cfg.filters:
                self.table_store[entity] = apply_filters(
                    name=entity,
                    df=self.table_store[entity],
                    cfg=table_cfg,
                    data_store=self.table_store,
                    stage="after_link",
                )

            if table_cfg.unnest:
                self.unnest_entity(entity=entity)
                self.linker.link_entity(entity_name=entity)
                # Re-evaluate deferred extra_columns after unnesting (in case unnest added new columns)
                self._evaluate_deferred_extra_columns(entity)

                if table_cfg.filters:
                    self.table_store[entity] = apply_filters(
                        name=entity,
                        df=self.table_store[entity],
                        cfg=table_cfg,
                        data_store=self.table_store,
                        stage="after_unnest",
                    )

            if delay_drop_duplicates and table_cfg.drop_duplicates:
                self.table_store[entity] = self.drop_duplicates(entity, table_cfg, self.table_store[entity])

            self._check_duplicate_keys(entity, table_cfg)

            if table_cfg.drop_empty_rows:
                self.table_store[entity] = drop_empty_rows(
                    data=self.table_store[entity], entity_name=entity, subset=table_cfg.drop_empty_rows
                )

            # Add system_id if requested and not present (always uses "system_id" column name)
            if table_cfg.system_id and table_cfg.system_id not in self.table_store[entity].columns:
                self.table_store[entity] = add_system_id(self.table_store[entity], table_cfg.system_id)

            # Add public_id column immediately so downstream merged entities see a complete source table
            self.table_store[entity] = table_cfg.add_public_id_column(self.table_store[entity])

            self.retry_linking()

            # Verify extra_columns were evaluated for this entity
            if table_cfg.extra_columns:
                unresolved_extra_columns = self.extra_col_evaluator.get_unresolved_extra_columns(
                    self.table_store[entity],
                    table_cfg.extra_columns,
                )

                if unresolved_extra_columns:
                    self.unresolved_extra_columns[entity] = unresolved_extra_columns
                else:
                    self.unresolved_extra_columns.pop(entity, None)

                self.extra_col_evaluator.verify_extra_columns(self.table_store[entity], table_cfg.extra_columns, entity)

            # Reorder columns immediately so each entity is fully formed before downstream entities process it
            self.table_store[entity] = self.project.reorder_columns(entity, self.table_store[entity])

        self._link_deferred_foreign_keys()

        return self

    def _link_deferred_foreign_keys(self, max_retries: int = 5) -> None:
        """Perform additional linking passes for any entities with deferred foreign key dependencies."""
        # Enhanced final linking pass for deferred FK dependencies
        # Retry linking for entities with deferred FKs (e.g., circular references)
        if not self.linker.deferred_tracker.deferred:
            return

        logger.info(f"Starting final linking pass for deferred FK dependencies: {self.linker.deferred_tracker.deferred}")

        for _ in range(max_retries):
            if not self.linker.deferred_tracker.deferred:
                break

            self.retry_linking()

        if self.linker.deferred_tracker.deferred:
            logger.warning(f"Entities with unresolved deferred links after normalization: {self.linker.deferred_tracker.deferred}")
        else:
            logger.info("Final linking pass successful: All deferred FK dependencies resolved")

    def drop_duplicates(self, entity_name: str, table_cfg: TableConfig, data: pd.DataFrame) -> pd.DataFrame:
        return drop_duplicate_rows(
            data=data,
            columns=table_cfg.drop_duplicates if table_cfg.drop_duplicates else True,
            entity_name=entity_name,
            fd_check=table_cfg.check_functional_dependency,
            strict_fd_check=table_cfg.strict_functional_dependency,
        )

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

    def _evaluate_deferred_extra_columns(self, entity_name: str) -> None:
        """Re-evaluate deferred extra_columns for an entity after FK linking or unnesting.

        This handles interpolated strings that reference columns added by FK linking
        (e.g., extra_columns from remote FK tables) or by unnesting operations.

        The evaluator is idempotent - it skips columns already in the DataFrame.

        Args:
            entity_name: Name of entity to process deferred columns for
        """
        table_cfg: TableConfig = self.project.get_table(entity_name)
        if not table_cfg.extra_columns:
            return  # No extra_columns configured

        df: pd.DataFrame = self.table_store[entity_name]

        # Pass ALL extra_columns - evaluator will skip existing ones (idempotent)
        result, still_deferred = self.extra_col_evaluator.evaluate_extra_columns(
            df=df,
            extra_columns=table_cfg.extra_columns,  # Full dict, not filtered
            entity_name=entity_name,
            defer_missing=True,  # Allow re-deferral if columns still missing
        )

        # Update table store with newly evaluated columns
        self.table_store[entity_name] = result

        # Log status
        if still_deferred:
            logger.trace(f"{entity_name}[deferred]: Still waiting for columns: {list(still_deferred.keys())}")
        else:
            logger.trace(f"{entity_name}[deferred]: Successfully evaluated all deferred extra_columns")

    def retry_linking(self) -> None:
        """Retry linking only for entities currently in deferred set."""
        for entity_name in list(self.linker.deferred_tracker.deferred):  # Create copy to avoid mutation during iteration
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

    def add_public_id_columns(self) -> Self:
        """Add 'public_id' column to each entity table that has one configured."""
        for entity_name in self.table_store.keys():
            if entity_name not in self.project.table_names:
                continue
            table_cfg: TableConfig = self.project.get_table(entity_name=entity_name)
            self.table_store[entity_name] = table_cfg.add_public_id_column(table=self.table_store[entity_name])
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
