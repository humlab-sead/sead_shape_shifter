"""API models for pending fixed-entity mapping synchronization and retry.

A fixed-row save persists its rows before it synchronizes the mapping sidecar.
When the sidecar write does not happen, the save response carries a
:class:`MappingSyncPending` object that records the exact operations together
with each affected key's post-save row state and pre-write link state. The
client submits that object to the retry endpoint, which applies only the
remaining changes or reports the affected keys that changed.

The models contain JSON-safe values only. They never carry raw pandas or NumPy
values or project file paths.
"""

from datetime import datetime
from typing import Literal, Union

from pydantic import BaseModel, Field, field_validator, model_validator


class MappingSyncLink(BaseModel):
    """A full mapping link recorded as an affected key's pre-write state."""

    target_id: int | None = None
    source: str
    confidence: float | None = None
    created_at: datetime
    committed_at: datetime | None = None
    notes: str | None = None
    created_by: str
    reviewed_by: str | None = None


class MappingSyncOperation(BaseModel):
    """One recorded mapping change with its affected-key preconditions.

    ``expected_row_present`` and ``expected_saved_id`` describe the saved row
    after the row write. Row absence is distinct from a present row whose saved
    ID is blank: absence sets ``expected_row_present`` to ``False``, while a
    present row with a blank ID keeps ``expected_row_present`` ``True`` and
    ``expected_saved_id`` ``None``.
    """

    op: Literal["upsert", "delete"]
    key: str = Field(..., min_length=1, description="Encoded local-key value for the affected link.")
    target_id: int | None = Field(default=None, description="Manual mapping target for an upsert operation.")
    expected_row_present: bool = Field(..., description="Whether the affected row exists after the row save.")
    expected_saved_id: int | None = Field(
        default=None,
        description="Saved integer ID after the row save, or None for an absent or blank-ID row.",
    )
    prior_link: MappingSyncLink | None = Field(default=None, description="The affected key's link before the write.")
    row_index: int | None = Field(default=None, description="Row position of the affected key, when known.")

    @model_validator(mode="after")
    def _check_operation_fields(self) -> "MappingSyncOperation":
        """Reject incompatible operation fields for upsert and delete operations."""
        if self.op == "upsert":
            if self.target_id is None:
                raise ValueError("upsert operation requires target_id")
            if not self.expected_row_present:
                raise ValueError("upsert operation requires a present saved row")
            if self.expected_saved_id != self.target_id:
                raise ValueError("upsert operation requires expected_saved_id equal to target_id")
        else:
            if self.target_id is not None:
                raise ValueError("delete operation must not set target_id")
            if self.expected_saved_id is not None:
                raise ValueError("delete operation cannot record an expected saved ID")
        return self


class MappingSyncEntry(BaseModel):
    """The proposed sidecar entry recorded by a pending operation."""

    local_key: Union[str, list[str]] = Field(..., description="Stored local-key column(s) for the proposed entry.")
    public_id: str = Field(..., min_length=1, description="Stored public_id column for the proposed entry.")
    prior_entry_exists: bool = Field(default=False, description="Whether the entry existed before the pending save.")

    @field_validator("local_key")
    @classmethod
    def _non_empty_local_key(cls, value: Union[str, list[str]]) -> Union[str, list[str]]:
        """Reject an empty local-key declaration."""
        if isinstance(value, str):
            if not value:
                raise ValueError("mapping entry local_key must not be empty")
            return value
        if not value or not all(isinstance(column, str) and column for column in value):
            raise ValueError("mapping entry local_key must be a non-empty string or list of strings")
        return value


class MappingSyncPending(BaseModel):
    """The pending mapping result returned with a partial fixed-row save."""

    status: Literal["pending"] = "pending"
    rows_saved: bool = True
    project: str = Field(..., min_length=1, description="Project the pending changes belong to.")
    entity: str = Field(..., min_length=1, description="Fixed entity the pending changes belong to.")
    storage_kind: Literal["inline", "external"] = Field(..., description="Where the saved rows are stored.")
    local_key: Union[str, list[str]] = Field(..., description="Stored local-key column(s) used by the change set.")
    public_id: str = Field(..., min_length=1, description="Stored public_id column used by the change set.")
    operations: list[MappingSyncOperation] = Field(default_factory=list, description="Exact upsert and delete operations.")
    entry: MappingSyncEntry | None = Field(default=None, description="Proposed entry when one must be created.")
    expected_row_version: str = Field(..., min_length=1, description="Saved-row version when the rows were written.")
    expected_sidecar_version: str = Field(..., min_length=1, description="Sidecar content version the save read.")

    @field_validator("local_key")
    @classmethod
    def _non_empty_local_key(cls, value: Union[str, list[str]]) -> Union[str, list[str]]:
        """Reject an empty local-key declaration."""
        if isinstance(value, str):
            if not value:
                raise ValueError("pending mapping local_key must not be empty")
            return value
        if not value or not all(isinstance(column, str) and column for column in value):
            raise ValueError("pending mapping local_key must be a non-empty string or list of strings")
        return value

    @field_validator("operations")
    @classmethod
    def _unique_operation_keys(cls, operations: list[MappingSyncOperation]) -> list[MappingSyncOperation]:
        """Reject duplicate affected keys so retry has one precondition per key."""
        keys: list[str] = [operation.key for operation in operations]
        if len(set(keys)) != len(keys):
            raise ValueError("pending mapping operations contain duplicate keys")
        return operations


class MappingSyncRetryResult(BaseModel):
    """The result of applying a pending fixed-entity mapping request."""

    status: Literal["applied", "noop"]
    rows_saved: bool = True
    changed: bool
    sidecar_version: str
    changed_keys: list[str] = Field(default_factory=list)
