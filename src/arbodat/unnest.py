import pandas as pd
from loguru import logger

from src.arbodat.config_model import TableConfig, UnnestConfig


def unnest(entity: str, table: pd.DataFrame, table_cfg: TableConfig) -> pd.DataFrame:

    unnest_config: UnnestConfig | None = table_cfg.unnest

    if unnest_config is None:
        return table

    id_vars: list[str] = unnest_config.id_vars or []
    value_vars: list[str] = unnest_config.value_vars or []
    var_name: str = unnest_config.var_name or "variable"
    value_name: str = unnest_config.value_name or "value"

    if value_name and value_name in table.columns:
        logger.info(f"Entity '{entity}': is melted already, skipping unnesting")
        return table

    if not id_vars or not value_vars or not var_name or not value_name:
        raise ValueError(f"Invalid unnest configuration for entity '{entity}': {unnest_config}")

    if not all(col in table.columns for col in id_vars):
        missing: list[str] = [col for col in id_vars if col not in table.columns]
        raise ValueError(f"Cannot unnest entity '{entity}', missing id_vars columns: {missing}")

    missing_value_vars: list[str] = [col for col in value_vars if col not in table.columns]
    if len(missing_value_vars) > 0:
        logger.info(f"Deferring unnesting of entity '{entity}', missing value_vars found: {missing_value_vars}")
        return table

    table_unnested: pd.DataFrame = pd.melt(
        table,
        id_vars=id_vars,
        value_vars=value_vars,
        var_name=var_name,
        value_name=value_name,
    )

    return table_unnested
