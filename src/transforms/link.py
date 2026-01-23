from typing import Any

import pandas as pd
from loguru import logger

from src.constraints import ForeignKeyConstraintValidator
from src.model import ForeignKeyConfig, ShapeShiftProject, TableConfig
from src.specifications import ForeignKeyDataSpecification


class ForeignKeyLinker:

    def __init__(self, table_store: dict[str, pd.DataFrame]) -> None:
        self.table_store: dict[str, pd.DataFrame] = table_store
        self.validators: list[ForeignKeyConstraintValidator] = []

    def link_foreign_key(
        self, entity_name: str, local_df: pd.DataFrame, fk: ForeignKeyConfig, remote_id: str, remote_df: pd.DataFrame
    ) -> pd.DataFrame:
        """Link foreign key between local and remote dataframes with optional constraint validation.

        Args:
            entity_name: Name of the local entity being linked
            local_df: Local dataframe to link from
            fk: Foreign key configuration
            remote_id: Remote surrogate ID column name
            remote_df: Remote dataframe to link to

        Returns:
            Linked dataframe with foreign key column added

        Raises:
            ForeignKeyConstraintViolation: If any constraints are violated
        """

        validator: ForeignKeyConstraintValidator = ForeignKeyConstraintValidator(entity_name, fk).validate_before_merge(local_df, remote_df)

        # Store validator to collect issues later
        self.validators.append(validator)

        remote_extra_cols: list[str] = fk.get_valid_remote_columns(remote_df)

        remote_df = remote_df[[remote_id] + remote_extra_cols]

        if fk.extra_columns:
            remote_df = remote_df.rename(columns=fk.resolved_extra_columns())

        opts: dict[str, Any] = self._resolve_link_opts(fk, validator)

        linked_df: pd.DataFrame = local_df.merge(remote_df, **opts)

        validator.validate_after_merge(local_df, remote_df, linked_df, merge_indicator_col=validator.merge_indicator_col)

        if fk.extra_columns and fk.drop_remote_id:
            linked_df = linked_df.drop(columns=[remote_id], errors="ignore")

        return linked_df

    def _resolve_link_opts(self, fk: ForeignKeyConfig, validator: ForeignKeyConstraintValidator):
        opts: dict[str, Any] = {"how": fk.how or "inner", "suffixes": ("", f"_{fk.remote_entity}")}
        opts |= {"left_on": fk.local_keys, "right_on": fk.remote_keys} if fk.how != "cross" else {}
        opts |= validator.validate_merge_opts()
        return opts

    def link_entity(self, entity_name: str, config: ShapeShiftProject) -> bool:
        """Link foreign keys for the specified entity in the data store."""

        table_cfg: TableConfig = config.get_table(entity_name=entity_name)
        foreign_keys: list[ForeignKeyConfig] = table_cfg.foreign_keys or []
        local_df: pd.DataFrame = self.table_store[entity_name]
        deferred: bool = False

        for fk in foreign_keys:

            if len(fk.local_keys) != len(fk.remote_keys):
                raise ValueError(f"Foreign key for entity '{entity_name}': local keys {fk.local_keys}, remote keys {fk.remote_keys}")

            if fk.remote_entity not in config.table_names:
                raise ValueError(f"Remote entity '{fk.remote_entity}' not found in configuration for linking with '{entity_name}'")

            # Skip if remote entity hasn't been processed yet
            if fk.remote_entity not in self.table_store:
                logger.debug(f"{entity_name}[linking]: deferring link to '{fk.remote_entity}' - entity not yet processed")
                continue

            remote_cfg: TableConfig = config.get_table(fk.remote_entity)
            remote_id: str | None = remote_cfg.surrogate_id or f"{fk.remote_entity}_id"
            remote_df: pd.DataFrame = self.table_store[fk.remote_entity]

            if fk.has_foreign_key_link(remote_id, local_df):
                # logger.debug(f"{entity_name}[linking]: skipped since FK '{remote_id}' and/or extra columns already exist.")
                continue

            specification: ForeignKeyDataSpecification = ForeignKeyDataSpecification(cfg=config, table_store=self.table_store)

            satisfied: bool | None = specification.is_satisfied_by(fk_cfg=fk)
            if satisfied is False:
                logger.error(f"{entity_name}[linking]: {specification.error}")
                continue

            if specification.deferred:
                deferred = True
                continue

            linked_df: pd.DataFrame = self.link_foreign_key(entity_name, local_df, fk, remote_id, remote_df)

            local_df = linked_df
            # logger.debug(f"{entity_name}[linking]: added link to '{fk.remote_entity}' via {fk.local_keys} -> {fk.remote_keys}")

        self.table_store[entity_name] = local_df

        return deferred
