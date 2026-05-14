from typing import Any

import pandas as pd

from src.model import TableConfig


def process_merged_branch(entity: str, table_cfg: TableConfig, sub_table_cfg: TableConfig, sub_data: pd.DataFrame) -> pd.DataFrame:
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
    branch_source: str | None = sub_table_cfg.entity_cfg.get("source")

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
        branch_src: str | None = branch_cfg.get("source")
        source_cfg: dict[str, Any] = table_cfg.entities_cfg.get(branch_src, {}) if branch_src else {}
        fk_column_name: str = source_cfg.get("public_id") or f"{branch_src}_id"

        if branch_src == branch_source:
            # Populate from the source entity's system_id carried through sub_data
            if "system_id" in sub_data.columns:
                sub_data[fk_column_name] = sub_data["system_id"].astype("Int64")
            else:
                sub_data[fk_column_name] = pd.array([pd.NA] * len(sub_data), dtype="Int64")
        else:
            sub_data[fk_column_name] = pd.NA

        sub_data[fk_column_name] = sub_data[fk_column_name].astype("Int64")

    # Drop the source system_id so it doesn't pollute the merged entity's own identity column
    if "system_id" in sub_data.columns:
        sub_data = sub_data.drop(columns=["system_id"])

    return sub_data
