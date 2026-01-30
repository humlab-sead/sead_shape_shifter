from typing import Any

import pandas as pd
from loguru import logger

from src.model import ForeignKeyConfig, ShapeShiftProject, TableConfig
from src.process_state import DeferredLinkingTracker
from src.specifications import ForeignKeyDataSpecification
from src.specifications.constraints import ForeignKeyConstraintValidator


class ForeignKeyLinker:

    def __init__(self, project: ShapeShiftProject, table_store: dict[str, pd.DataFrame]) -> None:
        self.project: ShapeShiftProject = project
        self.table_store: dict[str, pd.DataFrame] = table_store
        self.validators: list[ForeignKeyConstraintValidator] = []
        self.deferred_tracker: DeferredLinkingTracker = DeferredLinkingTracker()

    def link_foreign_key(
        self,
        local_df: pd.DataFrame,
        fk: ForeignKeyConfig,
        remote_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """Link foreign key between local and remote dataframes with optional constraint validation.

        Args:
            local_df: Local dataframe to link from
            fk: Foreign key configuration
            remote_df: Remote dataframe to link to

        Returns:
            Linked dataframe with foreign key column added

        Raises:
            ForeignKeyConstraintViolation: If any constraints are violated
        """

        validator: ForeignKeyConstraintValidator = ForeignKeyConstraintValidator(fk.local_entity, fk).validate_before_merge(
            local_df, remote_df
        )

        # Store validator to collect issues later
        self.validators.append(validator)

        remote_extra_cols: list[str] = fk.get_valid_remote_columns(remote_df)
        remote_cfg: TableConfig = self.project.get_table(entity_name=fk.remote_entity)

        # We need to rename remote system id to remote public id for the merge
        # The local FK will be named after the remote public id, but contains the remote system ids

        renames: dict[str, str] = {remote_cfg.system_id: remote_cfg.public_id} | fk.resolved_extra_columns()

        remote_df = remote_df[[remote_cfg.system_id] + remote_extra_cols].rename(columns=renames)

        opts: dict[str, Any] = self._resolve_link_opts(fk, validator)

        linked_df: pd.DataFrame = local_df.merge(remote_df, **opts)

        validator.validate_after_merge(local_df, remote_df, linked_df, merge_indicator_col=validator.merge_indicator_col)

        if fk.extra_columns and fk.drop_remote_id:
            linked_df = linked_df.drop(columns=[remote_cfg.public_id], errors="ignore")

        return linked_df

    def _resolve_link_opts(self, fk: ForeignKeyConfig, validator: ForeignKeyConstraintValidator):
        opts: dict[str, Any] = {"how": fk.how or "inner", "suffixes": ("", f"_{fk.remote_entity}")}
        opts |= {"left_on": fk.local_keys, "right_on": fk.remote_keys} if fk.how != "cross" else {}
        opts |= validator.validate_merge_opts()
        return opts

    def link_entity(self, entity_name: str) -> bool:
        """Link foreign keys for the specified entity in the data store."""

        table_cfg: TableConfig = self.project.get_table(entity_name=entity_name)
        local_df: pd.DataFrame = self.table_store[entity_name]
        deferred: bool = False

        for fk in table_cfg.foreign_keys:

            specification: ForeignKeyDataSpecification = ForeignKeyDataSpecification(cfg=self.project, table_store=self.table_store)

            satisfied: bool | None = specification.is_satisfied_by(fk_cfg=fk)

            if not satisfied:
                logger.error(f"{entity_name}[linking]: {specification.get_report()}")
                continue

            if specification.deferred:
                deferred = True
                continue

            if specification.is_already_linked(fk_cfg=fk):
                continue

            local_df = self.link_foreign_key(local_df, fk, self.table_store[fk.remote_entity])

        self.table_store[entity_name] = local_df

        self.deferred_tracker.track(entity_name=entity_name, deferred=deferred)

        return deferred
