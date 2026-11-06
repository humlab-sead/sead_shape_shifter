"""Backend runtime dependency injection for ingesters."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import httpx
import psycopg
from psycopg import sql
from pydantic import ValidationError

from backend.app.clients.sims_client import SimsClient
from backend.app.core.config import Settings
from backend.app.models.sims import (
    CapabilitiesResponse,
    EntityContractDeclaration,
    IdentitySignal,
    IdentityType,
    RegisterScopeContractsRequest,
    ResolutionRequest,
    ResolveRequest,
    ScopeContractConflictDetail,
)
from ingesters.sead_change_request.contracts import (
    DatabaseSequenceReservationError,
    SimsResolveItem,
    SubmissionContext,
    TrustedProjectContext,
)
from ingesters.sead_change_request.input_resolution import TRUSTED_PROJECT_CONTEXT_KEY
from src.business_keys import BusinessKeyError, business_id_for_row


class SimsContractRegistrationError(RuntimeError):
    """Raised when SIMS rejects the trusted provider-scope business-key contract.

    A rejected registration means the scope's ordered key lists differ from the
    registered contract or the caller is not authorized. Identity work must stop
    because the business identity values sent to SIMS would not match the
    approved contract.
    """


def _contract_rejection_reason(response: httpx.Response) -> str:
    """Return a readable reason from a rejected contract registration response."""
    try:
        payload = response.json()
    except ValueError:
        return response.text

    detail = payload.get("detail") if isinstance(payload, dict) else None
    if isinstance(detail, str):
        return detail
    if not isinstance(detail, dict):
        return response.text

    try:
        conflict = ScopeContractConflictDetail.model_validate(detail)
    except ValidationError:
        return response.text

    conflicts = "; ".join(f"{item.entity_type}: registered {item.registered}, submitted {item.submitted}" for item in conflict.conflicts)
    return f"{conflict.message} ({conflicts})" if conflicts else conflict.message


def inject_ingester_runtime_dependencies(ingester_key: str | None, extra: dict[str, Any], settings: Settings) -> dict[str, Any]:
    """Inject backend-owned runtime collaborators for ingesters that need them."""
    if ingester_key != "sead_change_request":
        return extra

    resolved_extra = dict(extra)
    trusted_project_context: TrustedProjectContext | None = resolved_extra.get(TRUSTED_PROJECT_CONTEXT_KEY)
    resolved_extra.setdefault(
        "sims_client",
        SeadChangeRequestSimsAdapter(
            SimsClient(
                base_url=settings.SIMS_SERVICE_URL,
                contract_caller=settings.SIMS_CONTRACT_CALLER,
                contract_registration_token=settings.SIMS_CONTRACT_REGISTRATION_TOKEN,
            ),
            created_by=resolved_extra.get("sims_created_by"),
            business_keys=trusted_project_context.business_keys if trusted_project_context is not None else None,
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
    """Thin adapter from the ingester orchestration seam to the backend SIMS client.

    The scope comes from the resolved submission context, which the backend fills from the
    authorized saved project's registered provider-schema pair. This adapter never accepts
    a caller-supplied scope and never falls back to a project-name scope.

    ``business_keys`` carries the saved project's ordered ``EntityConfig.keys`` per entity.
    When an entity declares keys, the adapter serializes them into one deterministic
    ``business_id``; otherwise it keeps the earlier field-based identity value.

    Before any identity work, the adapter registers the trusted provider-scope contract
    with SIMS for the entity types in the resolve request. SIMS accepts an exact ordered
    match and rejects a different key list or order, so a rejected contract stops the
    batch before any resolve request.
    """

    def __init__(
        self,
        sims_client: SimsClient,
        *,
        created_by: str | None = None,
        business_keys: dict[str, tuple[str, ...]] | None = None,
    ) -> None:
        self._sims_client = sims_client
        self._created_by = created_by
        self._business_keys = business_keys or {}

    async def allocate_entity(self, entity_name: str, row: dict[str, Any], submission_context: SubmissionContext) -> dict[str, Any]:
        """Resolve the row in SIMS as a new or already-bound identity."""
        return await self._resolve_entity(entity_name, row, submission_context)

    async def bind_existing_entity(
        self,
        entity_name: str,
        row: dict[str, Any],
        approved_aggregate_id: int,
        submission_context: SubmissionContext,
    ) -> dict[str, Any]:
        """Bind the source row to its approved existing SIMS aggregate ID."""
        return await self._resolve_entity(
            entity_name,
            row,
            submission_context,
            approved_aggregate_id=approved_aggregate_id,
        )

    async def _resolve_entity(
        self,
        entity_name: str,
        row: dict[str, Any],
        submission_context: SubmissionContext,
        *,
        approved_aggregate_id: int | None = None,
    ) -> dict[str, Any]:
        """Resolve a source row in SIMS and return its aggregate ID and Binding Set."""
        request = ResolveRequest(
            scope_name=self._build_scope_name(submission_context),
            run_id=self._run_id_for(submission_context),
            submission_name=submission_context.submission_name,
            created_by=self._created_by,
            requests=[
                ResolutionRequest(
                    entity_type=entity_name,
                    primary_signal=IdentitySignal(
                        identity_type=IdentityType.BUSINESS_KEY,
                        identity_value=self._build_identity_value(entity_name, row),
                    ),
                    approved_aggregate_id=approved_aggregate_id,
                )
            ],
        )
        await self._ensure_scope_contract(request.scope_name, [entity_name])
        try:
            response = await self._sims_client.resolve(request)
        except httpx.HTTPStatusError as exc:
            if approved_aggregate_id is None or exc.response.status_code != 409:
                raise
            return {
                "target_id": None,
                "binding_set_uuid": None,
                "binding_set_state": None,
                "note": (
                    f"SIMS rejected approved aggregate ID {approved_aggregate_id} "
                    f"(HTTP {exc.response.status_code}): {exc.response.text}"
                ),
            }

        tracked_identity_uuid = None
        target_id = None
        if response.outcomes:
            tracked_identity_uuid = response.outcomes[0].tracked_identity_uuid
            target_id = response.outcomes[0].target_id

        note = (
            f"SIMS resolved '{entity_name}' into Binding Set '{response.binding_set.binding_set_uuid}'"
            if target_id is not None
            else (
                f"SIMS resolved '{entity_name}' into Binding Set '{response.binding_set.binding_set_uuid}', "
                "but the current SIMS client does not expose a SIMS aggregate ID"
            )
        )
        if approved_aggregate_id is not None and target_id != approved_aggregate_id:
            target_id = None
            note = f"SIMS did not return approved aggregate ID {approved_aggregate_id}; " "refusing to use a different aggregate ID"

        return {
            "target_id": target_id,
            "binding_set_uuid": str(response.binding_set.binding_set_uuid),
            "binding_set_state": response.binding_set.lifecycle_state.value,
            "tracked_identity_uuid": str(tracked_identity_uuid) if tracked_identity_uuid is not None else None,
            "note": note,
        }

    async def resolve_batch(
        self,
        items: list[SimsResolveItem],
        submission_context: SubmissionContext,
    ) -> dict[str, Any]:
        """Resolve all collected SIMS work in one idempotent request.

        Builds one ResolveRequest carrying every item's request, using the
        persisted run ID as the idempotency key. Returns the ordered outcomes
        plus the batch Binding Set UUID and lifecycle state.

        The trusted provider-scope contract is registered and checked before the
        resolve request. A rejected registration returns an ``error`` entry so the
        caller blocks every item in the batch.
        """
        request = ResolveRequest(
            scope_name=self._build_scope_name(submission_context),
            run_id=self._run_id_for(submission_context),
            submission_name=submission_context.submission_name,
            created_by=self._created_by,
            requests=[
                ResolutionRequest(
                    entity_type=item.entity_name,
                    primary_signal=IdentitySignal(
                        identity_type=IdentityType.BUSINESS_KEY,
                        identity_value=self._build_identity_value(item.entity_name, item.row),
                    ),
                    approved_aggregate_id=item.approved_aggregate_id,
                )
                for item in items
            ],
        )
        try:
            await self._ensure_scope_contract(request.scope_name, [item.entity_name for item in items])
        except SimsContractRegistrationError as exc:
            return {
                "outcomes": [],
                "binding_set_uuid": None,
                "binding_set_state": None,
                "error": str(exc),
            }
        try:
            response = await self._sims_client.resolve(request)
        except httpx.HTTPStatusError as exc:
            return {
                "outcomes": [],
                "binding_set_uuid": None,
                "binding_set_state": None,
                "error": f"SIMS rejected the batch (HTTP {exc.response.status_code}): {exc.response.text}",
            }
        return {
            "outcomes": [
                {
                    "target_id": outcome.target_id,
                    "tracked_identity_uuid": (str(outcome.tracked_identity_uuid) if outcome.tracked_identity_uuid is not None else None),
                }
                for outcome in response.outcomes
            ],
            "binding_set_uuid": str(response.binding_set.binding_set_uuid),
            "binding_set_state": response.binding_set.lifecycle_state.value,
        }

    async def derive_bridge_row(
        self,
        entity_name: str,
        row: dict[str, Any],  # pylint: disable=unused-argument
        submission_context: SubmissionContext,
    ) -> dict[str, Any]:
        """Return a successful bridge derivation decision for downstream target projection.

        Bridge rows do not need SIMS allocation of their own target-facing ID.
        They become insertable once parent rows have resolved target IDs and the
        downstream uniqueness checks pass.
        """
        return {
            "state": "derived_bridge_row",
            "target_id": None,
            "binding_set_uuid": submission_context.binding_set_uuid,
            "binding_set_state": None,
            "note": (f"Bridge row '{entity_name}' will be projected from resolved parent IDs and checked via unique_sets"),
        }

    async def get_binding_set_state(self, binding_set_uuid: str) -> str:
        """Read the current Binding Set lifecycle state from SIMS."""
        binding_set = await self._sims_client.get_binding_set(UUID(binding_set_uuid))
        return binding_set.lifecycle_state.value

    async def get_capabilities(self) -> CapabilitiesResponse:
        """Return the configured SIMS identity capabilities for preflight."""
        return await self._sims_client.get_capabilities()

    async def confirm_binding_set(self, binding_set_uuid: str) -> str:
        """Confirm the Binding Set and return the resulting lifecycle state."""
        binding_set = await self._sims_client.confirm_binding_set(UUID(binding_set_uuid))
        return binding_set.lifecycle_state.value

    async def associate_change_request(self, binding_set_uuid: str, change_request_name: str) -> None:
        """Associate the generated change request name with the Binding Set."""
        await self._sims_client.associate_change_request(UUID(binding_set_uuid), change_request_name)

    def _build_scope_name(self, submission_context: SubmissionContext) -> str:
        """Return the provider-schema scope bound to the authorized saved project."""
        scope_name = submission_context.scope_name
        if not scope_name or not scope_name.strip():
            raise ValueError(
                "Change Request SIMS scope is not configured; the authorized saved project's provider-schema pair must supply it"
            )
        return scope_name.strip()

    def _run_id_for(self, submission_context: SubmissionContext) -> str:
        """Return the persisted run ID, minting a fallback when absent."""
        return submission_context.run_id or str(uuid4())

    async def _ensure_scope_contract(self, scope_name: str, entity_types: list[str]) -> None:
        """Register or verify the trusted provider-scope business-key contract.

        The declaration covers the entity types in the current resolve request,
        because SIMS checks a contract only for the entity types a request names.
        Each declaration is the saved project's ordered key list for that entity.
        SIMS creates missing contracts, accepts an exact ordered match, and
        rejects a different key list or order with HTTP 409. A rejected
        registration raises ``SimsContractRegistrationError`` so the caller stops
        before any resolve request.

        Entities that declare no keys, and entities that this request does not
        resolve, are left out. Leaving the others out keeps a key difference on a
        never-resolved entity, such as the fixed ``data_provider`` row or a
        derived child, from blocking identity work for the tracked entities.
        """
        requested_entities = sorted({name for name in entity_types if self._business_keys.get(name)})
        declarations = [
            EntityContractDeclaration(entity_type=entity_name, business_keys=list(self._business_keys[entity_name]))
            for entity_name in requested_entities
        ]
        if not declarations:
            return

        try:
            await self._sims_client.register_scope_contracts(
                RegisterScopeContractsRequest(
                    scope_name=scope_name,
                    entities=declarations,
                    created_by=self._created_by,
                )
            )
        except httpx.HTTPStatusError as exc:
            raise SimsContractRegistrationError(
                f"SIMS rejected the provider-scope business-key contract for '{scope_name}' "
                f"(HTTP {exc.response.status_code}): {_contract_rejection_reason(exc.response)}"
            ) from exc

    def _build_identity_value(self, entity_name: str, row: dict[str, Any]) -> str:
        """Return the SIMS business key for one row.

        A tracked entity with declared business keys uses the stable serialized
        ``business_id``. An entity without declared keys keeps the earlier field-based
        value so other entities are unchanged.
        """
        declared_keys = self._business_keys.get(entity_name)
        if declared_keys:
            try:
                return business_id_for_row(declared_keys, row)
            except BusinessKeyError as exc:
                raise ValueError(f"Cannot serialize declared business key for entity '{entity_name}': {exc}") from exc

        serialized_pairs: list[str] = []
        for key in sorted(row):
            value = row[key]
            if _is_missing_value(value):
                continue
            serialized_pairs.append(f"{key}={value}")

        if not serialized_pairs:
            return entity_name

        return f"{entity_name}:" + "|".join(serialized_pairs)


class SeadChangeRequestTargetCollisionChecker:
    """PostgreSQL adapter for target checks and database-sequence ID reservations."""

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

    async def target_id_column_type(self, table_name: str, public_id_column: str) -> str | None:
        """Return a target ID column's PostgreSQL type, or None when it is missing."""
        schema_name, relation_name = self._split_table_name(table_name)
        if not schema_name or not relation_name or not public_id_column:
            raise ValueError("Target table and public-ID column names must be non-empty")

        statement = sql.SQL(
            "SELECT data_type FROM information_schema.columns WHERE table_schema = %s AND table_name = %s AND column_name = %s"
        )
        async with await psycopg.AsyncConnection.connect(**self._connection_kwargs) as connection:
            async with connection.cursor() as cursor:
                await cursor.execute(statement, (schema_name, relation_name, public_id_column))
                row = await cursor.fetchone()
        return str(row[0]) if row is not None else None

    async def reserve_database_id(self, table_name: str, public_id_column: str) -> int:
        """Reserve one target ID from the sequence owned by a table column."""
        schema_name, relation_name = self._split_table_name(table_name)
        if not schema_name or not relation_name or not public_id_column:
            raise DatabaseSequenceReservationError("Target table and public-ID column names must be non-empty")

        statement = sql.SQL("SELECT nextval(pg_get_serial_sequence(%s, %s)::regclass)")
        try:
            async with await psycopg.AsyncConnection.connect(**self._connection_kwargs) as connection:
                async with connection.cursor() as cursor:
                    await cursor.execute(statement, (f"{schema_name}.{relation_name}", public_id_column))
                    row = await cursor.fetchone()
        except psycopg.Error as exc:
            raise DatabaseSequenceReservationError(
                f"Could not reserve a database-sequence ID for '{table_name}.{public_id_column}': {exc}"
            ) from exc

        if row is None or row[0] is None:
            raise DatabaseSequenceReservationError(f"Target column '{table_name}.{public_id_column}' has no associated database sequence")
        if isinstance(row[0], bool) or not isinstance(row[0], int):
            raise DatabaseSequenceReservationError(f"Target sequence for '{table_name}.{public_id_column}' returned an invalid ID")
        return row[0]

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
        return sql.Identifier(*self._split_table_name(table_name))

    def _split_table_name(self, table_name: str) -> tuple[str, str]:
        """Resolve a qualified table name or apply the configured default schema."""
        if "." in table_name:
            schema_name, relation_name = table_name.split(".", maxsplit=1)
            return schema_name, relation_name
        return self._default_schema, table_name


def _is_missing_value(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, float):
        return value != value  # pylint: disable=comparison-with-itself
    return False
