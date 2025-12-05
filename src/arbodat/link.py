from typing import Any

import pandas as pd
from loguru import logger

from src.arbodat.config_model import ForeignKeyConfig, TableConfig, TablesConfig
from src.arbodat.link_validator import ForeignKeyConstraintValidator
from src.arbodat.specifications import ForeignKeyDataSpecification


def link_foreign_key(
    entity_name: str, local_df: pd.DataFrame, fk: ForeignKeyConfig, remote_id: str, remote_df: pd.DataFrame
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

    remote_extra_cols: list[str] = fk.get_valid_remote_columns(remote_df)

    remote_select_df: pd.DataFrame = remote_df[[remote_id] + remote_extra_cols]

    if fk.remote_extra_columns:
        remote_select_df = remote_select_df.rename(columns=fk.remote_extra_columns)

    opts: dict[str, Any] = _resolve_link_opts(fk, validator)

    linked_df: pd.DataFrame = local_df.merge(remote_select_df, **opts)

    validator.validate_after_merge(local_df, remote_df, linked_df)

    if fk.remote_extra_columns and fk.drop_remote_id:
        linked_df = linked_df.drop(columns=[remote_id], errors="ignore")
    return linked_df


def _resolve_link_opts(fk: ForeignKeyConfig, validator: ForeignKeyConstraintValidator):
    opts: dict[str, Any] = {"how": fk.how or "inner", "suffixes": ("", f"_{fk.remote_entity}")}
    opts |= {"left_on": fk.local_keys, "right_on": fk.remote_keys} if fk.how != "cross" else {}
    opts |= validator.validate_merge_opts()
    return opts


def link_entity(entity_name: str, config: TablesConfig, data: dict[str, pd.DataFrame]) -> bool:
    """Link foreign keys for the specified entity in the data store."""
    table_cfg: TableConfig = config.get_table(entity_name=entity_name)
    foreign_keys: list[ForeignKeyConfig] = table_cfg.foreign_keys or []
    deferred: bool = False
    local_df: pd.DataFrame = data[entity_name]

    for fk in foreign_keys:

        if len(fk.local_keys) != len(fk.remote_keys):
            raise ValueError(f"Foreign key for entity '{entity_name}': local keys {fk.local_keys}, remote keys {fk.remote_keys}")

        if fk.remote_entity not in config.table_names:
            raise ValueError(f"Remote entity '{fk.remote_entity}' not found in configuration for linking with '{entity_name}'")

        remote_cfg: TableConfig = config.get_table(fk.remote_entity)
        remote_id: str | None = remote_cfg.surrogate_id or f"{fk.remote_entity}_id"
        remote_df: pd.DataFrame = data[fk.remote_entity]

        if remote_id in local_df.columns or all(col in local_df.columns for col in fk.remote_extra_columns.values()):
            logger.debug(f"{entity_name}[linking]: skipped since FK '{remote_id}' and/or extra columns already exist.")
            continue

        specification: ForeignKeyDataSpecification = ForeignKeyDataSpecification(cfg=config, table_store=data)

        satisfied: bool | None = specification.is_satisfied_by(fk_cfg=fk)
        if satisfied is False:
            logger.error(f"{entity_name}[linking]: {specification.error}")
            continue

        if specification.deferred:
            deferred = True
            continue

        linked_df: pd.DataFrame = link_foreign_key(entity_name, local_df, fk, remote_id, remote_df)

        local_df = linked_df
        logger.debug(f"{entity_name}[linking]: added link to '{fk.remote_entity}' via {fk.local_keys} -> {fk.remote_keys}")

    data[entity_name] = local_df

    return deferred
