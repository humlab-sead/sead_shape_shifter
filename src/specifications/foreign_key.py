from typing import TYPE_CHECKING, Any

import pandas as pd

from src.model import ForeignKeyConfig, ShapeShiftProject, TableConfig
from src.specifications.base import ProjectSpecification, Specification
from src.table_store import TableStore

if TYPE_CHECKING:
    from src.reconciliation.mapping_model import MappingCatalog

# pylint: disable=line-too-long


class ForeignKeyConfigSpecification(Specification):
    """Specification that tests if a foreign key relationship is resolveble.
    Returns True if all local and remote keys exist, False if any are missing,
    or None if resolvable after unnesting some local keys are in unnest columns.
    """

    def __init__(self, project: "ShapeShiftProject") -> None:
        super().__init__()
        self.project: ShapeShiftProject = project
        self.deferred: bool = False

    def clear(self) -> None:
        super().clear()
        self.deferred = False

    def is_satisfied_by(self, *, fk_cfg: ForeignKeyConfig | None = None, **kwargs) -> bool:
        # self.clear()
        missing_fields: set[str]

        assert fk_cfg is not None, "fk_cfg must be provided to check foreign key configuration"  # keep type checker happy

        local_table_cfg: TableConfig = self.project.get_table(fk_cfg.local_entity)
        remote_table_cfg: TableConfig = self.project.get_table(fk_cfg.remote_entity)

        if fk_cfg.how == "cross":
            if fk_cfg.local_keys or fk_cfg.remote_keys:
                self.add_error(
                    f"{fk_cfg.local_entity} -> {fk_cfg.remote_entity}: " f"'cross' join should not specify local_keys or remote_keys",
                    entity=fk_cfg.local_entity,
                )
            return not self.has_errors()

        if not remote_table_cfg.system_id:
            self.add_error(
                f"{fk_cfg.local_entity} -> {fk_cfg.remote_entity}: "
                f"remote entity '{fk_cfg.remote_entity}' must have a system_id defined",
                entity=fk_cfg.local_entity,
            )
            return not self.has_errors()

        if not remote_table_cfg.public_id:
            self.add_error(
                f"{fk_cfg.local_entity} -> {fk_cfg.remote_entity}: "
                f"remote entity '{fk_cfg.remote_entity}' must have a public_id defined",
                entity=fk_cfg.local_entity,
            )
            return not self.has_errors()

        if len(fk_cfg.local_keys) == 0 or len(fk_cfg.remote_keys) == 0:
            self.add_error(
                f"{fk_cfg.local_entity} -> {fk_cfg.remote_entity}: " f"local_keys and remote_keys must be specified for non-cross joins",
                entity=fk_cfg.local_entity,
            )

        if len(fk_cfg.local_keys) != len(fk_cfg.remote_keys):
            self.add_error(
                f"{fk_cfg.local_entity} -> {fk_cfg.remote_entity}: "
                f"number of local_keys ({len(fk_cfg.local_keys)}) does not match "
                f"number of remote_keys ({len(fk_cfg.remote_keys)})",
                entity=fk_cfg.local_entity,
            )

        missing_fields = self.get_missing_fields(
            required_fields=set(fk_cfg.local_keys),
            available_fields=set(local_table_cfg.keys_columns_and_fks) | set(local_table_cfg.unnest_columns),
        )

        if missing_fields:
            self.add_error(
                f"{fk_cfg.local_entity} -> {fk_cfg.remote_entity}: "
                f"local keys {missing_fields} not found in local entity '{fk_cfg.local_entity}'",
                entity=fk_cfg.local_entity,
            )

        missing_fields: set[str] = self.get_missing_fields(
            required_fields=set(fk_cfg.remote_keys), available_fields=set(remote_table_cfg.get_columns())
        )

        if missing_fields:
            self.add_error(
                f"{fk_cfg.local_entity} -> {fk_cfg.remote_entity}: "
                f"remote keys {missing_fields} not found in remote entity '{fk_cfg.remote_entity}'"
                f"{self._identity_key_hint(missing_fields, fk_cfg.remote_entity, remote_table_cfg)}",
                entity=fk_cfg.local_entity,
                field="foreign_keys[].remote_keys",
            )

        return not self.has_errors()

    @staticmethod
    def _identity_key_hint(missing_fields: set[str], remote_entity: str, remote_table_cfg: TableConfig) -> str:
        """Explain the fix when a missing remote key is a remote identity column.

        Returns an empty string when none of the missing keys is the remote
        ``system_id`` or ``public_id``, so unrelated missing columns keep the
        plain message.
        """
        identity_rule: str = (
            "A foreign key stores the parent's 'system_id' values, while the parent's "
            f"'public_id' only names the child column. Join on '{remote_entity}.{remote_table_cfg.system_id}' instead."
        )
        if remote_table_cfg.public_id and remote_table_cfg.public_id in missing_fields:
            return (
                f". '{remote_table_cfg.public_id}' is the remote entity's 'public_id'. "
                "It names the child column but does not hold joinable values here. " + identity_rule
            )
        if remote_table_cfg.system_id in missing_fields:
            return (
                f". '{remote_table_cfg.system_id}' is the remote entity's generated 'system_id'. It is added "
                "during normalization and is not a declared column of the remote entity, so it cannot be "
                f"selected as a join key here. Declare it in the remote entity's 'columns' to join on it."
            )
        return ""

    def get_missing_fields(self, *, required_fields: set[str], available_fields: set[str]) -> set[str]:
        """Return the set of required keys that are missing from found keys."""
        return {key for key in required_fields if key not in available_fields}


class ForeignKeyRemotePublicIdSpecification(ProjectSpecification):
    """Warn when a foreign key joins on a remote ``public_id`` that carries no values.

    A child foreign key stores the parent's ``system_id`` values; the parent's
    ``public_id`` only names the child column. Configuring ``remote_keys`` as the
    parent's ``public_id`` is therefore a mistake whenever that ``public_id`` has
    no value source: the join silently matches nothing.

    The rule fires only when a remote key equals the remote ``public_id`` **and**
    that ``public_id`` has no value source:

    - Fixed entity: the ``public_id`` column is all-null in ``values`` (and the
      entity is not filled by ``append``). A fixed entity whose ``public_id`` is a
      populated data column (for example ``master_dataset.master_set_id``) is left
      alone.
    - Other entities: the ``public_id`` is not a declared ``columns``/``extra_columns``
      field and no committed mapping sidecar populates it.

    Severity is ``warning`` because the link is skipped rather than corrupting data,
    matching ``FK_REMOTE_EMPTY`` and ``FK_DATA_INTEGRITY``.
    """

    def __init__(self, project_cfg: dict[str, Any], mapping_catalog: "MappingCatalog | None" = None) -> None:
        super().__init__(project_cfg)
        self._mapping_catalog: MappingCatalog | None = mapping_catalog

    def is_satisfied_by(self, **kwargs) -> bool:
        """Check every foreign key for a join on an unpopulated remote public_id."""
        self.clear()

        entities_cfg: dict[str, dict[str, Any]] = self.project_cfg.get("entities", {}) or {}
        for entity_name, entity_cfg in entities_cfg.items():
            for fk_cfg in (entity_cfg or {}).get("foreign_keys", []) or []:
                self._check_foreign_key(entity_name=entity_name, fk_cfg=fk_cfg)

        return not self.has_errors()

    def _check_foreign_key(self, *, entity_name: str, fk_cfg: Any) -> None:
        """Add a warning when one foreign key joins on an unpopulated remote public_id."""
        if not isinstance(fk_cfg, dict) or fk_cfg.get("how") == "cross":
            return

        remote_entity: str = fk_cfg.get("entity", "")
        remote_keys: Any = fk_cfg.get("remote_keys", []) or []
        if not remote_entity or not self.entity_exists(remote_entity):
            return
        # An unresolved directive (a plain string) cannot be matched key-by-key; skip it.
        if not isinstance(remote_keys, list):
            return

        remote_cfg: TableConfig = self.get_entity(remote_entity)
        public_id: str = remote_cfg.public_id
        if not public_id or public_id not in remote_keys:
            return

        if self._public_id_has_value_source(remote_cfg):
            return

        self.add_warning(
            f"{entity_name} -> {remote_entity}: remote key '{public_id}' is the remote entity's "
            f"'public_id', which holds no values, so the join matches nothing. "
            f"A foreign key stores the parent's 'system_id' values; the parent's 'public_id' only "
            f"names the child column. Join on '{remote_entity}.{remote_cfg.system_id}' instead.",
            entity=entity_name,
            field="foreign_keys[].remote_keys",
            code="FK_REMOTE_PUBLIC_ID_EMPTY",
        )

    def _public_id_has_value_source(self, remote_cfg: TableConfig) -> bool:
        """Return True when the remote public_id is populated by data, values, or a sidecar."""
        public_id: str = remote_cfg.public_id

        # A committed mapping sidecar populates the public_id at normalization time.
        if self._mapping_catalog is not None and self._mapping_catalog.committed_links_by_entity(remote_cfg.entity_name):
            return True

        if remote_cfg.type == "fixed":
            if remote_cfg.has_append:
                return True
            return self._fixed_public_id_has_value(remote_cfg)

        # Non-fixed entity: a declared data column or extra_column supplies the value.
        return public_id in remote_cfg.safe_columns or public_id in remote_cfg.extra_column_names

    @staticmethod
    def _fixed_public_id_has_value(remote_cfg: TableConfig) -> bool:
        """Return True when any fixed ``values`` row carries a non-null public_id."""
        public_id: str = remote_cfg.public_id
        raw_values: Any = remote_cfg.values
        values: list[Any] = raw_values if isinstance(raw_values, list) else []
        rows: list[list[Any]] = [row for row in values if isinstance(row, list)]
        if not rows:
            return False

        full_columns: list[str] = remote_cfg.values_column_order
        declared_columns: list[str] = remote_cfg.safe_columns
        row_width: int = len(rows[0])

        if row_width == len(full_columns) and public_id in full_columns:
            index: int = full_columns.index(public_id)
        elif row_width == len(declared_columns) and public_id in declared_columns:
            index = declared_columns.index(public_id)
        else:
            # The public_id has no positional slot in these rows, so it carries no value.
            return False

        return any(len(row) > index and row[index] is not None for row in rows)


class ForeignKeyDataSpecification(ForeignKeyConfigSpecification):
    """Checks if local and remote keys are present in the actual table data (pandas.DataFrames)."""

    def __init__(self, table_store: TableStore, cfg: "ShapeShiftProject") -> None:
        super().__init__(cfg)
        self.table_store: TableStore = table_store

    def is_satisfied_by(self, *, fk_cfg: ForeignKeyConfig | None = None, **kwargs) -> bool:

        assert fk_cfg is not None, "fk_cfg must be provided to check foreign key data"  # keep type checker happy

        self.clear()

        missing_fields: set[str]

        if not fk_cfg.local_entity:
            raise ValueError("fk_cfg.local_entity must be specified to check foreign key data")

        if not fk_cfg.remote_entity:
            raise ValueError("fk_cfg.remote_entity must be specified to check foreign key data")

        if fk_cfg.local_entity not in self.table_store:
            raise ValueError(f"Local entity '{fk_cfg.local_entity}' not found in table store for linking with '{fk_cfg.remote_entity}'")

        if fk_cfg.remote_entity not in self.table_store:
            # Skip if remote entity hasn't been processed yet
            self.add_warning(
                f"{fk_cfg.local_entity}[linking]: deferring link to '{fk_cfg.remote_entity}' - entity not yet processed",
                entity=fk_cfg.local_entity,
            )
            self.deferred = True
            return False

        super().is_satisfied_by(fk_cfg=fk_cfg)

        if missing_fields := self.get_missing_local_fields(fk_cfg=fk_cfg):
            if missing_fields == self.project.get_table(fk_cfg.local_entity).unnest_columns:
                self.deferred = True
            else:
                self.add_error(
                    f"{fk_cfg.local_entity} -> {fk_cfg.remote_entity}: "
                    f"local keys {missing_fields} not found in local entity data '{fk_cfg.local_entity}'",
                    entity=fk_cfg.local_entity,
                )

        if self.get_missing_pending_fields(fk_cfg=fk_cfg):
            self.deferred = True

        if missing_fields := self.get_missing_remote_fields(fk_cfg=fk_cfg):
            self.add_error(
                f"{fk_cfg.local_entity} -> {fk_cfg.remote_entity}: "
                f"remote keys {missing_fields} not found in remote entity data '{fk_cfg.remote_entity}'",
                entity=fk_cfg.local_entity,
            )

        return not self.has_errors()

    def is_already_linked(self, *, fk_cfg: ForeignKeyConfig) -> bool:
        """Check if the foreign key columns already exist in the local entity's data."""
        table: pd.DataFrame = self.table_store[fk_cfg.local_entity]
        remote_cfg: TableConfig = self.project.get_table(fk_cfg.remote_entity)
        return fk_cfg.has_foreign_key_link(remote_cfg.public_id, table)

    def get_missing_local_fields(self, *, fk_cfg: ForeignKeyConfig) -> set[str]:
        """Check for missing local keys in the local entity data."""
        table: pd.DataFrame = self.table_store[fk_cfg.local_entity]
        return self.get_missing_fields(
            required_fields=set(fk_cfg.local_keys),
            available_fields=set(table.columns).union(self.project.get_table(fk_cfg.local_entity).unnest_columns),
        )

    def get_missing_pending_fields(self, *, fk_cfg: ForeignKeyConfig) -> set[str]:
        """Check for missing pending keys in the local entity data."""
        return self.get_missing_fields(
            required_fields=set(self.project.get_table(fk_cfg.local_entity).unnest_columns),
            available_fields=set(self.table_store[fk_cfg.local_entity].columns),
        )

    def get_missing_remote_fields(self, *, fk_cfg: ForeignKeyConfig) -> set[str]:
        """Check for missing remote keys in the remote entity data."""
        return self.get_missing_fields(
            required_fields=set(fk_cfg.remote_keys), available_fields=set(self.table_store[fk_cfg.remote_entity].columns)
        )
