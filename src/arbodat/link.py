from typing import Any

import pandas as pd
from loguru import logger

from src.arbodat.config_model import ForeignKeyConfig, TableConfig, TablesConfig
from src.arbodat.specifications import ForeignKeyDataSpecification


def link_foreign_key(entity_name: str, local_df: pd.DataFrame, fk, remote_id: str, remote_df: pd.DataFrame):
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

    opts: dict[str, Any] = {"how": fk.how or "inner", "suffixes": ("", f"_{fk.remote_entity}")}
    if fk.how != "cross":
        opts["left_on"] = fk.local_keys
        opts["right_on"] = fk.remote_keys

    size_before_merge: int = len(local_df)
    linked_df: pd.DataFrame = local_df.merge(remote_select_df, **opts)
    size_after_merge: int = len(linked_df)
    logger.debug(f"[Linking {entity_name}] merge size: before={size_before_merge}, after={size_after_merge}")

    if fk.remote_extra_columns and fk.drop_remote_id:
        linked_df = linked_df.drop(columns=[remote_id], errors="ignore")
    return linked_df


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

        if remote_id in local_df.columns:
            logger.debug(f"Linking {entity_name}: skipped since FK '{remote_id}' already exists.")
            continue

        specification: ForeignKeyDataSpecification = ForeignKeyDataSpecification(cfg=config, table_store=data)

        satisfied: bool | None = specification.is_satisfied_by(fk_cfg=fk)
        if satisfied is False:
            logger.error(specification.error)
            continue

        if specification.deferred:
            deferred = True
            continue

        linked_df: pd.DataFrame = link_foreign_key(entity_name, local_df, fk, remote_id, remote_df)

        local_df = linked_df
        logger.debug(f"[Linking {entity_name}] added link to '{fk.remote_entity}' via {fk.local_keys} -> {fk.remote_keys}")

    data[entity_name] = local_df

    return deferred
