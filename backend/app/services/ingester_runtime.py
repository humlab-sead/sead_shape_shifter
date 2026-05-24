"""Backend runtime dependency injection for ingesters."""

from __future__ import annotations

import re
from typing import Any
from uuid import UUID

import psycopg
from loguru import logger
from psycopg import sql

from backend.app.clients.reconciliation_client import ReconciliationClient, ReconciliationQuery
from backend.app.clients.sims_client import SimsClient
from backend.app.core.config import Settings
from backend.app.models.sims import IdentitySignal, IdentityType, ResolutionRequest, ResolveRequest
from ingesters.sead_change_request.contracts import SubmissionContext


def inject_ingester_runtime_dependencies(ingester_key: str | None, extra: dict[str, Any], settings: Settings) -> dict[str, Any]:
    """Inject backend-owned runtime collaborators for ingesters that need them."""
    if ingester_key != "sead_change_request":
        return extra

    resolved_extra = dict(extra)
    resolved_extra.setdefault(
        "sims_client",
        SeadChangeRequestSimsAdapter(
            SimsClient(base_url=settings.SIMS_SERVICE_URL),
            scope_name=resolved_extra.get("sims_scope_name"),
            created_by=resolved_extra.get("sims_created_by"),
        ),
    )
    resolved_extra.setdefault(
        "reconciliation_client",
        SeadChangeRequestReconciliationAdapter(
            ReconciliationClient(base_url=settings.RECONCILIATION_SERVICE_URL),
            query_columns=resolved_extra.get("reconciliation_query_columns"),
            entity_types=resolved_extra.get("reconciliation_entity_types"),
        ),
    )
    return resolved_extra


def inject_ingester_database_dependencies(ingester_key: str | None, extra: dict[str, Any], db_config: dict[str, Any]) -> dict[str, Any]:
    """Inject database-backed runtime collaborators when DB config is available."""
    if ingester_key != "sead_change_request":
        return extra

    if not db_config.get("dbname") or not db_config.get("user"):
        return extra

    resolved_extra = dict(extra)
    resolved_extra.setdefault(
        "collision_checker",
        SeadChangeRequestTargetCollisionChecker(
            host=db_config.get("host", "localhost"),
            port=int(db_config.get("port", 5432)),
            dbname=db_config["dbname"],
            user=db_config["user"],
            password=db_config.get("password"),
        ),
    )
    return resolved_extra


class SeadChangeRequestSimsAdapter:
    """Thin adapter from the ingester orchestration seam to the backend SIMS client."""

    def __init__(self, sims_client: SimsClient, *, scope_name: str | None = None, created_by: str | None = None) -> None:
        self._sims_client = sims_client
        self._scope_name = scope_name
        self._created_by = created_by

    async def allocate_entity(self, entity_name: str, row: dict[str, Any], submission_context: SubmissionContext) -> dict[str, Any]:
        """Resolve the row in SIMS and return Binding Set information.

        The current SIMS client exposes tracked-identity UUIDs and Binding Sets, but not
        target-facing integer IDs required by Delivery 1 materialization.
        """
        request = ResolveRequest(
            scope_name=self._build_scope_name(submission_context),
            submission_name=submission_context.submission_name,
            created_by=self._created_by,
            requests=[
                ResolutionRequest(
                    entity_type=entity_name,
                    primary_signal=IdentitySignal(
                        identity_type=IdentityType.BUSINESS_KEY,
                        identity_value=self._build_identity_value(entity_name, row),
                    ),
                )
            ],
        )
        response = await self._sims_client.resolve(request)
        tracked_identity_uuid = None
        target_id = None
        if response.outcomes:
            tracked_identity_uuid = response.outcomes[0].tracked_identity_uuid
            target_id = response.outcomes[0].target_id

        return {
            "target_id": target_id,
            "binding_set_uuid": str(response.binding_set.binding_set_uuid),
            "binding_set_state": response.binding_set.lifecycle_state.value,
            "tracked_identity_uuid": str(tracked_identity_uuid) if tracked_identity_uuid is not None else None,
            "note": (
                f"SIMS resolved '{entity_name}' into Binding Set '{response.binding_set.binding_set_uuid}'"
                if target_id is not None
                else (
                    f"SIMS resolved '{entity_name}' into Binding Set '{response.binding_set.binding_set_uuid}', "
                    "but the current SIMS client does not expose a target-facing integer ID"
                )
            ),
        }

    async def derive_bridge_row(self, entity_name: str, row: dict[str, Any], submission_context: SubmissionContext) -> dict[str, Any]:
        """Return a successful bridge derivation decision for downstream materialization.

        Bridge rows do not need SIMS allocation of their own target-facing ID.
        They become insertable once parent rows have resolved target IDs and the
        downstream uniqueness checks pass.
        """
        return {
            "state": "derived_bridge_row",
            "target_id": None,
            "binding_set_uuid": submission_context.binding_set_uuid,
            "binding_set_state": None,
            "note": (f"Bridge row '{entity_name}' will be materialized from resolved parent IDs and checked via unique_sets"),
        }

    async def get_binding_set_state(self, binding_set_uuid: str) -> str:
        """Read the current Binding Set lifecycle state from SIMS."""
        binding_set = await self._sims_client.get_binding_set(UUID(binding_set_uuid))
        return binding_set.lifecycle_state.value

    async def confirm_binding_set(self, binding_set_uuid: str) -> str:
        """Confirm the Binding Set and return the resulting lifecycle state."""
        binding_set = await self._sims_client.confirm_binding_set(UUID(binding_set_uuid))
        return binding_set.lifecycle_state.value

    async def associate_change_request(self, binding_set_uuid: str, change_request_name: str) -> None:
        """Associate the generated change request name with the Binding Set."""
        await self._sims_client.associate_change_request(UUID(binding_set_uuid), change_request_name)

    def _build_scope_name(self, submission_context: SubmissionContext) -> str:
        if self._scope_name:
            return self._scope_name
        return f"sead-change-request:{submission_context.project_name}"

    def _build_identity_value(self, entity_name: str, row: dict[str, Any]) -> str:
        serialized_pairs: list[str] = []
        for key in sorted(row):
            value = row[key]
            if _is_missing_value(value):
                continue
            serialized_pairs.append(f"{key}={value}")

        if not serialized_pairs:
            return entity_name

        return f"{entity_name}:" + "|".join(serialized_pairs)


class SeadChangeRequestReconciliationAdapter:
    """Thin adapter from the ingester orchestration seam to the backend reconciliation client."""

    def __init__(
        self,
        reconciliation_client: ReconciliationClient,
        *,
        query_columns: dict[str, list[str]] | None = None,
        entity_types: dict[str, str] | None = None,
    ) -> None:
        self._reconciliation_client = reconciliation_client
        self._query_columns = query_columns or {}
        self._entity_types = entity_types or {}

    async def reconcile_entity(self, entity_name: str, row: dict[str, Any]) -> int | None:
        """Run a single-row reconciliation query and return the extracted target ID."""
        query_text = self._build_query_text(entity_name, row)
        if query_text is None:
            logger.warning(f"Cannot reconcile '{entity_name}': row has no non-empty queryable values")
            return None

        query = ReconciliationQuery(
            query=query_text,
            entity_type=self._entity_types.get(entity_name, entity_name),
        )
        results = await self._reconciliation_client.reconcile_batch({"row-0": query})
        candidates = results.get("row-0", [])
        best_candidate = self._pick_best_candidate(candidates)
        if best_candidate is None:
            return None

        return self._extract_target_id(best_candidate.id)

    def _build_query_text(self, entity_name: str, row: dict[str, Any]) -> str | None:
        columns = self._query_columns.get(entity_name)
        if not columns:
            columns = [key for key in row if key != "system_id" and not key.endswith("_id")]

        values = [str(row[column]).strip() for column in columns if column in row and not _is_missing_value(row[column])]
        values = [value for value in values if value]
        if not values:
            return None
        return " ".join(values)

    @staticmethod
    def _pick_best_candidate(candidates: list[Any]) -> Any | None:
        if not candidates:
            return None

        exact_matches = [candidate for candidate in candidates if getattr(candidate, "match", False)]
        if exact_matches:
            return max(exact_matches, key=lambda candidate: getattr(candidate, "score", 0) or 0)
        return max(candidates, key=lambda candidate: getattr(candidate, "score", 0) or 0)

    @staticmethod
    def _extract_target_id(candidate_id: str) -> int | None:
        match = re.search(r"(\d+)$", candidate_id)
        if match is None:
            logger.warning(f"Could not extract integer target ID from reconciliation candidate '{candidate_id}'")
            return None
        return int(match.group(1))


class SeadChangeRequestTargetCollisionChecker:
    """Read-only PostgreSQL collision checker for Delivery 1 target-side preflight checks."""

    def __init__(
        self,
        *,
        host: str,
        port: int,
        dbname: str,
        user: str,
        password: str | None = None,
        default_schema: str = "public",
    ) -> None:
        self._connection_kwargs: dict[str, Any] = {
            "host": host,
            "port": port,
            "dbname": dbname,
            "user": user,
        }
        if password is not None:
            self._connection_kwargs["password"] = password
        self._default_schema = default_schema

    async def target_id_exists(self, table_name: str, public_id_column: str, target_id: int) -> bool:
        statement = sql.SQL("SELECT EXISTS(SELECT 1 FROM {} WHERE {} = %s)").format(
            self._table_identifier(table_name),
            sql.Identifier(public_id_column),
        )
        return await self._fetch_exists(statement, (target_id,))

    async def row_exists(self, table_name: str, filters: dict[str, object]) -> bool:
        if not filters:
            return False

        conditions = sql.SQL(" AND ").join(sql.SQL("{} = %s").format(sql.Identifier(column)) for column in filters)
        statement = sql.SQL("SELECT EXISTS(SELECT 1 FROM {} WHERE {})").format(
            self._table_identifier(table_name),
            conditions,
        )
        return await self._fetch_exists(statement, tuple(filters.values()))

    async def _fetch_exists(self, statement: sql.SQL | sql.Composed, params: tuple[object, ...]) -> bool:
        async with await psycopg.AsyncConnection.connect(**self._connection_kwargs) as connection:
            async with connection.cursor() as cursor:
                await cursor.execute(statement, params)
                row = await cursor.fetchone()
        return bool(row[0]) if row is not None else False

    def _table_identifier(self, table_name: str) -> sql.Composed | sql.Identifier:
        if "." in table_name:
            schema_name, relation_name = table_name.split(".", maxsplit=1)
            return sql.Identifier(schema_name, relation_name)
        return sql.Identifier(self._default_schema, table_name)


def _is_missing_value(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, float):
        return value != value
    return False
