"""Apply a pending fixed-entity mapping result under the project lock.

The retry operation receives the pending ``mapping_sync`` payload from a
partial save response. It never recomputes changes from the current rows.
Instead, it checks each affected key's recorded post-save row state and
pre-write link state, applies only the remaining changes, and reports the
changed keys when review is required. It holds the same per-project lock used
by other backend sidecar writers.
"""

from __future__ import annotations

from loguru import logger

from backend.app.exceptions import ResourceConflictError, ValidationError
from backend.app.mappers.project_mapper import ProjectMapper
from backend.app.middleware.correlation import get_correlation_id
from backend.app.models.mapping_sync import MappingSyncPending, MappingSyncRetryResult
from backend.app.services.entity_values_service import EntityValuesService
from backend.app.services.fixed_entity_mapping_change_service import FixedEntityMappingChangeService
from backend.app.services.fixed_entity_mapping_sync_service import FixedEntityMappingSyncService
from backend.app.services.project_service import ProjectService
from backend.app.utils.fixed_schema import derive_fixed_schema
from src.reconciliation.fixed_entity_mapping_changes import FixedRowChangeSet, RowSnapshot
from src.reconciliation.fixed_entity_mapping_retry import plan_fixed_entity_mapping_retry
from src.reconciliation.mapping_manager import MappingManager, MappingVersionConflictError


class FixedEntityMappingRetryService:
    """Retry a pending fixed-entity mapping request under the project lock."""

    def __init__(
        self,
        project_service: ProjectService,
        mapping_manager: MappingManager | None = None,
        change_service: FixedEntityMappingChangeService | None = None,
        sync_service: FixedEntityMappingSyncService | None = None,
        values_service: EntityValuesService | None = None,
    ) -> None:
        """Initialize with shared services so all retry writers use one manager."""
        self.project_service: ProjectService = project_service
        self.manager: MappingManager = mapping_manager or MappingManager()
        self.change_service: FixedEntityMappingChangeService = change_service or FixedEntityMappingChangeService(self.manager)
        self.sync_service: FixedEntityMappingSyncService = sync_service or FixedEntityMappingSyncService(self.manager)
        self.values_service: EntityValuesService = values_service or EntityValuesService(
            self.project_service,
            self.change_service,
            self.sync_service,
        )

    def retry(self, project_name: str, entity_name: str, pending: MappingSyncPending) -> MappingSyncRetryResult:
        """Apply a pending mapping request, reporting conflicts without writing."""
        with self.project_service._get_lock(project_name):
            return self._retry_locked(project_name, entity_name, pending)

    def _retry_locked(self, project_name: str, entity_name: str, pending: MappingSyncPending) -> MappingSyncRetryResult:
        """Apply the pending request while the caller holds the project lock."""
        entity_data = self.project_service.get_entity_by_name(project_name, entity_name)
        self._verify_entity_and_storage(entity_name, entity_data, pending)

        change_set: FixedRowChangeSet = ProjectMapper.pending_to_fixed_change_set(pending)
        project_path: str = self.project_service.load_project(project_name).filename or project_name

        # A whole-file version race is a fast-path check only. Re-read and
        # recheck the affected keys once before reporting a conflict.
        for _attempt in range(2):
            current_rows: RowSnapshot | None = self._read_current_rows(project_name, entity_name, entity_data, pending)
            snapshot = self.sync_service.load_snapshot(project_path)
            plan = plan_fixed_entity_mapping_retry(
                entity_name=entity_name,
                local_key=change_set.local_key,  # type: ignore[arg-type]
                public_id=change_set.public_id,  # type: ignore[arg-type]
                current_rows=current_rows,
                catalog=snapshot.catalog,
                upserts=change_set.upserts,
                deletes=change_set.deletes,
                proposed_entry=change_set.proposed_entry,
            )

            if plan.has_conflicts:
                raise self._conflict(entity_name, list(plan.conflict_keys), entry_conflict=plan.entry_conflict)

            if plan.is_no_op:
                return MappingSyncRetryResult(status="noop", changed=False, sidecar_version=snapshot.content_version)

            apply_set = FixedRowChangeSet(
                entity_name=entity_name,
                eligible=True,
                local_key=change_set.local_key,
                public_id=change_set.public_id,
                proposed_entry=change_set.proposed_entry if plan.create_entry else None,
                upserts=plan.upserts_to_apply,
                deletes=plan.deletes_to_apply,
            )

            try:
                result = self.sync_service.apply_change_set(
                    change_set=apply_set,
                    snapshot=snapshot,
                    project_path=project_path,
                    row_version=pending.expected_row_version,
                    created_by=get_correlation_id(),
                    raise_on_error=True,
                )
            except MappingVersionConflictError:
                logger.warning("Mapping retry version race; re-reading and rechecking affected keys.")
                continue

            return MappingSyncRetryResult(status="applied", changed=result.changed, sidecar_version=result.sidecar_version)

        raise self._conflict(entity_name, [], entry_conflict=False)

    def _read_current_rows(
        self,
        project_name: str,
        entity_name: str,
        entity_data: dict,
        pending: MappingSyncPending,
    ) -> RowSnapshot | None:
        """Read the currently saved rows for the pending request's storage kind."""
        if pending.storage_kind == "external":
            return self.values_service.load_saved_fixed_snapshot(project_name, entity_name)
        return self.change_service.saved_inline_snapshot(entity_data)

    @staticmethod
    def _verify_entity_and_storage(entity_name: str, entity_data: dict, pending: MappingSyncPending) -> None:
        """Verify the entity is fixed, stores rows as recorded, and produces the stored columns."""
        if entity_data.get("type") != "fixed":
            raise ValidationError(
                message=f"Entity '{entity_name}' is not a fixed entity.",
                context={"entity": entity_name},
            )

        values_field = entity_data.get("values")
        is_external: bool = isinstance(values_field, str) and values_field.startswith("@load:")
        if pending.storage_kind == "external" and not is_external:
            raise FixedEntityMappingRetryService._conflict(entity_name, [], config_conflict=True)
        if pending.storage_kind == "inline" and is_external:
            raise FixedEntityMappingRetryService._conflict(entity_name, [], config_conflict=True)

        fixed_schema = derive_fixed_schema(entity_data)
        if not fixed_schema:
            raise FixedEntityMappingRetryService._conflict(entity_name, [], config_conflict=True)

        key_columns = [pending.local_key] if isinstance(pending.local_key, str) else list(pending.local_key)
        required_columns = set(key_columns) | {pending.public_id}
        missing_columns = sorted(required_columns - set(fixed_schema["full_columns"]))
        if missing_columns:
            raise FixedEntityMappingRetryService._conflict(entity_name, [], config_conflict=True)

    @staticmethod
    def _conflict(
        entity_name: str,
        changed_keys: list[str],
        *,
        entry_conflict: bool = False,
        config_conflict: bool = False,
    ) -> ResourceConflictError:
        """Build a 409 conflict carrying the changed keys and any entry conflict."""
        context: dict[str, object] = {"changed_keys": sorted(changed_keys)}
        if entry_conflict:
            context["entry_conflict"] = True
        if config_conflict:
            context["config_conflict"] = True
        return ResourceConflictError(
            message=f"Mapping changes for entity '{entity_name}' conflict with the current state; review the affected keys.",
            resource_type="mapping-sync",
            resource_id=entity_name,
            context=context,
        )


def get_fixed_entity_mapping_retry_service() -> FixedEntityMappingRetryService:
    """Return a fixed-entity mapping retry service bound to the project service."""
    from backend.app.services.project_service import get_project_service

    return FixedEntityMappingRetryService(get_project_service())
