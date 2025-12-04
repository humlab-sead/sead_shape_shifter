from typing import Any

import pandas as pd
from loguru import logger


class LinkToRemoteService:
    """Service to link local Arbodat PK values to remote SEAD identities based on provided mapping configuration."""

    # TODO: Enable mapping from compound local keys.

    def __init__(self, remote_link_cfgs: dict[str, dict[str, Any]]):
        self.remote_link_cfgs: dict[str, dict[str, Any]] = remote_link_cfgs

    def link_to_remote(self, entity_name: str, table: pd.DataFrame) -> pd.DataFrame:
        """Uses content from mapping.yml (ConfigValue("mapping")) to Arbodat PK values to SEAD identities.
        The mapping configuration consists of mappings for various (but not all) entities.
        Each mapping has the following structure:
            entity-name:
                local_key: "arbodat-key"
                remote_key: "sead-integer-identity"
                mapping:
                    "value-1": n
                    "value-2": m
        The mapping process involves finding the specified entity in the normalized data, and for each row,
        replacing the value in the entity's primary key column with the corresponding remote_key (SEAD identity)
        from the mapping configuration.

        example:
            taxon:
                local_key: "PCODE"
                remote_key: "taxon_id"
                mapping:
                    "PLANT001": 101
                    "PLANT002": 102

        """
        link_cfg: dict[str, Any] = self.remote_link_cfgs.get(entity_name, {})

        if not link_cfg:
            logger.info(f"{entity_name}[mapping]: No remote linking configuration found. Skipping remote linking for this entity.")
            return table

        local_key: str = link_cfg.get("local_key", "") or ""
        remote_key: str = link_cfg.get("remote_key", "") or ""
        mapping: dict[str, int] = link_cfg.get("mapping", {})

        if not local_key or not remote_key or not mapping:
            logger.warning(f"{entity_name}[mapping]: Incomplete mapping details for entity. Skipping mapping for this entity.")
            return table

        if local_key not in table.columns:
            logger.warning(f"{entity_name}[mapping]: Local key '{local_key}' not found in entity. Skipping mapping for this entity.")
            return table

        table[remote_key] = table[local_key].map(mapping)

        return table
