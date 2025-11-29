"""
Normalize an Arbodat "Data Survey" CSV export into several tables
and write them as sheets in a single Excel file.

Usage:
    python arbodat_normalize_to_excel.py input.csv output.xlsx

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
from src.arbodat.utility import get_subset
from src.configuration.resolve import ConfigValue


class ArbodatSurveyNormalizer:

    def __init__(self, df: pd.DataFrame) -> None:
        self.data: dict[str, pd.DataFrame] = {"survey": df}
        self.config: TablesConfig = TablesConfig()

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
        """ Read Arbodat CSV (usually tab-separated). """
        df: pd.DataFrame = pd.read_csv(path, sep=sep, dtype=str, keep_default_na=False)
        return ArbodatSurveyNormalizer(df)

    def extract_entity(self, entity_name: str) -> pd.DataFrame:
        """Extract entity DataFrame based on configuration."""

        table_cfg: TableConfig = self.config.get_table(entity_name)

        if table_cfg.is_fixed_data:
            raise ValueError(f"Entity '{entity_name}' is configured as fixed data and cannot be extracted")

        source: pd.DataFrame = self.resolve_source(table_cfg.source)

        if not isinstance(table_cfg.columns, list) or not all(isinstance(c, str) for c in table_cfg.columns):
            raise ValueError(f"Invalid columns configuration for entity '{entity_name}': {table_cfg.columns}")

        data: pd.DataFrame = get_subset(
            source,
            table_cfg.usage_columns,
            extra_columns=table_cfg.extra_columns,
            drop_duplicates=table_cfg.drop_duplicates,
            surrogate_id=table_cfg.surrogate_id,
            raise_if_missing=False,
        )

        return data

    def _find_next_entity_to_process(self) -> str | None:
        processed: set[str] = set(self.data.keys())
        logger.debug(f"Processed entities so far: {processed}")
        for entity_name in set(self.config.table_names) - processed:
            logger.debug(f"Checking if entity '{entity_name}' can be processed...")
            unmet_dependencies: set[str] = set(self.config.get_table(entity_name).depends_on) - processed
            if unmet_dependencies:
                logger.debug(f"Entity '{entity_name}' has unmet dependencies: {unmet_dependencies}")
                continue
            logger.debug(f"Entity '{entity_name}' can be processed next.")
            return entity_name
        return None

    def normalize(self) -> None:
        """Extract all configured entities and store them."""
        unprocessed: set[str] = set(self.config.table_names)
        while len(unprocessed) > 0:

            entity: str | None = self._find_next_entity_to_process()

            if entity is None:
                raise ValueError(f"Circular or unresolved dependencies detected among entities: {unprocessed}")

            table_cfg: TableConfig = self.config.get_table(entity)

            logger.debug(f"Normalizing entity '{entity}'...")

            data: pd.DataFrame

            if table_cfg.is_fixed_data:
                data = create_fixed_table(entity_name=entity, table_cfg=table_cfg)
            else:
                data = self.extract_entity(entity)

            self.register(entity, data)

            deferred: bool = self.link_entity(entity)

            if table_cfg.unnest:
                try:
                    data = self.unnest_entity(entity=entity)
                except ValueError as e:
                    logger.warning(f"Skipping unnesting for entity '{entity}': {e}")

            if deferred:
                self.link_entity(entity)

            self.link()

            unprocessed.discard(entity)

        self.link(is_final=True)

    def link(self, is_final: bool = False) -> bool:
        """Link entities based on foreign key configuration."""
        deferred: bool = False
        for entity_name in self.data.keys():
            deferred = deferred and self.link_entity(entity_name)
        return deferred

    def link_entity(self, entity_name: str) -> bool:

        table_cfg: TableConfig = self.config.get_table(entity_name)
        foreign_keys: list[ForeignKeyConfig] = table_cfg.foreign_keys or []
        deferred: bool = False

        for fk in foreign_keys:

            local_keys: list[str] = fk.local_keys
            remote_keys: list[str] = fk.remote_keys
            remote_entity: str = fk.remote_entity
            
            if len(local_keys) != len(remote_keys):
                raise ValueError(
                    f"Foreign key configuration mismatch for entity '{entity_name}': local keys {local_keys} and remote keys {remote_keys} have different lengths"
                )

            remote_id: str | None = self.config.get_table(remote_entity).surrogate_id or f"{remote_entity}_id"
            if remote_entity not in self.data or remote_id is None:
                raise ValueError(f"Remote entity '{remote_entity}' or surrogate_id not found for linking with '{entity_name}'")

            local_df: pd.DataFrame = self.data[entity_name]
            remote_df: pd.DataFrame = self.data[remote_entity]

            if remote_id in local_df.columns:
                logger.debug(f"Linking {entity_name}: skipped since FK '{remote_id}' already exists.")
                continue

            specification: ForeignKeyDataSpecification = ForeignKeyDataSpecification(cfg=self.config, table_store=self.data)

            satisfied: bool | None = specification.is_satisfied_by(fk_cfg=fk)
            if satisfied is False:
                logger.error(specification.error)
                continue

            if specification.deferred:
                deferred = deferred or True
                continue

            # Perform the merge to link entities
            linked_df: pd.DataFrame = local_df.merge(
                remote_df[[remote_id] + remote_keys + list(fk.remote_extra_columns.keys())],
                left_on=local_keys,
                right_on=remote_keys,
                how="left",
                suffixes=("", f"_{remote_entity}"),
            )

            if fk.remote_extra_columns and fk.drop_remote_id:
                linked_df = linked_df.drop(columns=[remote_id], errors="ignore")

            self.data[entity_name] = linked_df

            logger.debug(f"[Linking {entity_name}] added link to '{remote_entity}' via {local_keys} -> {remote_keys}")

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

    def translate(self) -> None:
        """Translate column names using translation from config."""
        translations: dict[str, str] = ConfigValue[dict[str, str]]("translation").resolve() or {}

        def fx(col: str, columns: list[str]) -> str:
            translated_column: str = translations.get(col, col)
            if translated_column in columns:
                return col
            return translated_column

        for entity, table in self.data.items():
            columns: list[str] = table.columns.tolist()
            table.columns = [fx(col, columns) for col in columns]
            self.data[entity] = table

    def drop_foreign_key_columns(self) -> None:
        """Drop foreign key columns used for linking that are no longer needed after linking. Keep if in columns list."""
        for entity_name in self.data.keys():
            columns: list[str] = self.config.get_table(entity_name).columns or []
            foreign_keys: list[ForeignKeyConfig] = self.config.get_table(entity_name).foreign_keys or []
            fk_columns: set[str] = set()
            for fk in foreign_keys:
                local_keys: list[str] = fk.local_keys or []
                fk_columns.update(key for key in local_keys if key not in columns)
            if fk_columns:
                table: pd.DataFrame = self.data[entity_name]
                table = table.drop(columns=fk_columns, errors="ignore")
                self.data[entity_name] = table

    def move_keys_to_front(self) -> None:
        """Reorder columns in this order: primary key, foreign key column, extra columns, other columns."""
        for entity_name in self.data.keys():
            if entity_name not in self.config.table_names:
                continue
            table_cfg: TableConfig = self.config.get_table(entity_name)
            table: pd.DataFrame = self.data[entity_name]
            cols_to_move: list[str] = (
                [table_cfg.surrogate_id]
                + [self.config.get_table(fk.remote_entity).surrogate_id for fk in table_cfg.foreign_keys]
                + table_cfg.extra_column_names
            )
            existing_cols_to_move: list[str] = [col for col in cols_to_move if col in table.columns]
            other_cols: list[str] = [col for col in table.columns if col not in existing_cols_to_move]
            new_column_order: list[str] = existing_cols_to_move + other_cols
            table = table[new_column_order]
            self.data[entity_name] = table
