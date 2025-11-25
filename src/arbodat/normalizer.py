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

from src.arbodat.config_model import ForeignKeyConfig, ForeignKeySpecification, TableConfig, TablesConfig, UnnestConfig
from src.configuration.resolve import ConfigValue


def add_surrogate_id(target: pd.DataFrame, id_name: str) -> pd.DataFrame:
    """Add an integer surrogate ID starting at 1."""
    target = target.reset_index(drop=True).copy()
    target[id_name] = range(1, len(target) + 1)
    return target


def get_subset(
    source: pd.DataFrame,
    columns: list[str],
    drop_duplicates: bool | list[str] = False,
    raise_if_missing: bool = True,
    surrogate_id: str | None = None,
) -> pd.DataFrame:
    """Return data with only the columns that actually exist and drop duplicates if requested."""
    if source is None:
        raise ValueError("Source DataFrame must be provided")

    if any(c not in source.columns for c in columns):
        missing: list[str] = [c for c in columns if c not in source.columns]
        if raise_if_missing:
            raise ValueError(f"Columns not found in DataFrame: {missing}")
        else:
            logger.warning(f"Columns not found in DataFrame and will be skipped: {missing}")

    existing: list[str] = [c for c in columns if c in source.columns]
    result: pd.DataFrame = source[existing]

    if drop_duplicates:
        if isinstance(drop_duplicates, list):
            result = result.drop_duplicates(subset=drop_duplicates)
        else:
            result = result.drop_duplicates()

    if surrogate_id and surrogate_id not in result.columns:
        result = add_surrogate_id(result, surrogate_id)

    return result


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

    def add_surrogate_id(self, target: pd.DataFrame, id_name: str) -> pd.DataFrame:
        """Add an integer surrogate ID starting at 1."""
        target = target.reset_index(drop=True).copy()
        target[id_name] = range(1, len(target) + 1)
        return target

    @staticmethod
    def load(path: str | Path, sep: str = "\t") -> "ArbodatSurveyNormalizer":
        """
        Read Arbodat CSV (usually tab-separated).
        If sep='\t' fails badly, you can change to ',' when calling.
        """
        df: pd.DataFrame = pd.read_csv(path, sep=sep, dtype=str, keep_default_na=False)
        return ArbodatSurveyNormalizer(df)

    def create_fixed_data_entity(self, entity_name: str) -> pd.DataFrame:
        """Create a fixed data entity based on configuration."""
        table_cfg: TableConfig = self.config.get_table(entity_name)

        if not table_cfg.is_fixed_data:
            raise ValueError(f"Entity '{entity_name}' is not configured as fixed data")

        if not table_cfg.values:
            raise ValueError(f"Fixed data entity '{entity_name}' has no values defined")

        if len(table_cfg.columns or []) <= 1:
            surrogate_name: str = table_cfg.surrogate_name
            if not surrogate_name:

                if len(table_cfg.columns or []) == 0:
                    raise ValueError(f"Fixed data entity '{entity_name}' must have a surrogate_name or one column defined")

                surrogate_name = table_cfg.columns[0]
            data: pd.DataFrame = pd.DataFrame({surrogate_name: table_cfg.values})
        else:
            # Multiple columns, values is a list of rows, all having the same length as columns
            if not isinstance(table_cfg.values, list) or not all(isinstance(row, list) for row in table_cfg.values):
                raise ValueError(f"Fixed data entity '{entity_name}' with multiple columns must have values as a list of lists")

            if not all(len(row) == len(table_cfg.columns) for row in table_cfg.values):
                raise ValueError(f"Fixed data entity '{entity_name}' has mismatched number of columns and values")

            data = pd.DataFrame(table_cfg.values, columns=table_cfg.columns)

        return data

    def extract_entity(self, entity_name: str) -> pd.DataFrame:
        """Extract entity DataFrame based on configuration."""

        table_cfg: TableConfig = self.config.get_table(entity_name)

        if table_cfg.is_fixed_data:
            raise ValueError(f"Entity '{entity_name}' is configured as fixed data and cannot be extracted")

        data: pd.DataFrame = pd.DataFrame({table_cfg.surrogate_name: table_cfg.values})
        if table_cfg.surrogate_id:
            data = self.add_surrogate_id(data, table_cfg.surrogate_id)
            return data

        source: pd.DataFrame = self.resolve_source(table_cfg.source)

        if not isinstance(table_cfg.columns, list) or not all(isinstance(c, str) for c in table_cfg.columns):
            raise ValueError(f"Invalid columns configuration for entity '{entity_name}': {table_cfg.columns}")

        data: pd.DataFrame = get_subset(
            source,
            table_cfg.usage_columns,
            drop_duplicates=table_cfg.drop_duplicates,
            surrogate_id=table_cfg.surrogate_id,
            raise_if_missing=False,
        )

        return data

    def _find_next_entity_to_process(self) -> str | None:
        processed: set[str] = set(self.data.keys())
        logger.info(f"Processed entities so far: {processed}")
        for entity_name in set(self.config.table_names) - processed:
            logger.info(f"Checking if entity '{entity_name}' can be processed...")
            unmet_dependencies: set[str] = set(self.config.get_table(entity_name).depends_on) - processed
            if unmet_dependencies:
                logger.info(f"Entity '{entity_name}' has unmet dependencies: {unmet_dependencies}")
                continue
            logger.info(f"Entity '{entity_name}' can be processed next.")
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

            logger.info(f"normalizing entity '{entity}'...")

            data: pd.DataFrame

            if table_cfg.is_fixed_data:
                data = self.create_fixed_data_entity(entity)
            else:
                data = self.extract_entity(entity)

            self.register(entity, data)

            deferred: bool = self.link_entity(entity)

            if table_cfg.unnest:
                try:
                    data = self.unnest_entity(entity, data, table_cfg.unnest)
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
        specification: ForeignKeySpecification = ForeignKeySpecification()

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

            if entity_name == "site_location":
                logger.info(f"Debugging site_location linking...")

            if remote_id in local_df.columns:
                logger.info(f"Entity '{entity_name}' already has foreign key column '{remote_id}'")
                continue

            specification: ForeignKeySpecification = ForeignKeySpecification()
            satisfied: bool | None = specification.is_satisfied_by(cfg=self.config, fk_cfg=fk)
            if not satisfied is True:
                # raise ValueError(f"Foreign key specification not satisfied for entity '{entity_name}' linking to '{remote_entity}'")
                missing: set[str] = set(local_keys) - set(local_df.columns)
                if missing:
                    logger.info(f"Deferring link since local keys '{missing}' not found in entity '{entity_name}'")

                missing_remote: set[str] = set(remote_keys) - set(remote_df.columns)
                if missing_remote:
                    logger.info(f"Deferring link since remote keys '{missing_remote}' not found in entity '{remote_entity}'")

                deferred = True
                continue

            # Perform the merge to link entities
            linked_df: pd.DataFrame = local_df.merge(
                remote_df[[remote_id] + remote_keys],
                left_on=local_keys,
                right_on=remote_keys,
                how="left",
                suffixes=("", f"_{remote_entity}"),
            )

            self.data[entity_name] = linked_df

            logger.info(f"Linked entity '{entity_name}' to '{remote_entity}' via keys {local_keys} -> {remote_keys}")

        return deferred

    def store(self, target: str, mode: Literal["xlsx", "csv", "db"]) -> None:
        """Write to Excel or CSV based on the specified mode."""
        if mode == "xlsx":
            with pd.ExcelWriter(target, engine="openpyxl") as writer:
                for entity_name, table in self.data.items():
                    table.to_excel(writer, sheet_name=entity_name, index=False)
        elif mode == "csv":
            output_dir = Path(target)
            output_dir.mkdir(parents=True, exist_ok=True)
            for entity_name, table in self.data.items():
                table.to_csv(output_dir / f"{entity_name}.csv", index=False)
        else:
            raise NotImplementedError(f"Unsupported storage mode: {mode}")

    def unnest(self) -> None:
        """Unnest data frames based on configuration."""
        for entity, table in self.data.items():

            unnest_config: UnnestConfig | None = self.config.get_table(entity).unnest

            if not unnest_config:
                continue

            table_unnested: pd.DataFrame = self.unnest_entity(entity, table, unnest_config)
            self.data[entity] = table_unnested

    def unnest_entity(self, entity: str, table: pd.DataFrame, unnest_config: UnnestConfig) -> pd.DataFrame:

        id_vars: list[str] = unnest_config.id_vars or []
        value_vars: list[str] = unnest_config.value_vars or []
        var_name: str = unnest_config.var_name or "variable"
        value_name: str = unnest_config.value_name or "value"

        if value_name in table.columns:
            logger.info(f"Entity '{entity}': is melted already, skipping unnesting")
            return table

        if not id_vars or not value_vars or not var_name or not value_name:
            raise ValueError(f"Invalid unnest configuration for entity '{entity}': {unnest_config}")

        if not all(col in table.columns for col in id_vars):
            missing: list[str] = [col for col in id_vars if col not in table.columns]
            raise ValueError(f"Cannot unnest entity '{entity}': missing id_vars columns: {missing}")

        if any(col in table.columns for col in value_vars):
            logger.info("Deferring unnesting no value_vars exist in the table")

        table_unnested: pd.DataFrame = pd.melt(
            table,
            id_vars=id_vars,
            value_vars=value_vars,
            var_name=var_name,
            value_name=value_name,
        )

        return table_unnested

    def translate(self) -> None:
        """Translate Arbodat column names to english snake-cased names."""
        translations: dict[str, str] = ConfigValue[dict[str, str]]("translations").resolve() or {}

        def fx(col: str) -> str:
            return translations.get(col, col)

        for entity, table in self.data.items():
            columns: list[str] = table.columns.tolist()
            translated_columns: list[str] = [fx(col) for col in columns]
            table.columns = translated_columns
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
