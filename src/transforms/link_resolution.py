"""Resolve a linking warning to one saved foreign key.

The resolver reads a validation issue plus a project and returns either the
saved foreign key that raised the warning or a named reason for offering no
troubleshooting action. It reads only its arguments and does not touch data,
files, or the project's tables.
"""

from dataclasses import dataclass
from typing import Any, Literal, Mapping

from src.model import ForeignKeyConfig, ShapeShiftProject

SUPPORTED_JOIN_TYPES: tuple[str, ...] = ("inner", "left")
"""Join types a troubleshooting action can explain."""

ResolutionStatus = Literal[
    "resolved",
    "not_row_count_issue",
    "not_integrity_issue",
    "entity_not_found",
    "missing_metadata",
    "index_out_of_range",
    "signature_mismatch",
    "unsupported_join",
]
"""Outcome of resolving a warning to a saved foreign key."""


@dataclass(frozen=True)
class LinkIssueResolution:
    """Result of resolving one linking warning.

    Attributes:
        status: What happened while resolving the warning.
        entity_name: Local entity named by the warning.
        fk_index: Position of the saved foreign key, when known.
        fk: Saved foreign key that raised the warning, when resolved.
        link_pass: Linking pass recorded in the warning, when it was a string.
    """

    status: ResolutionStatus
    entity_name: str
    fk_index: int | None = None
    fk: ForeignKeyConfig | None = None
    link_pass: str | None = None

    @property
    def is_eligible(self) -> bool:
        """Return True only when a supported saved foreign key was resolved."""
        return self.status == "resolved"


def _resolve_saved_foreign_key(
    project: ShapeShiftProject,
    *,
    local_entity: str,
    metadata: Mapping[str, Any],
) -> LinkIssueResolution:
    """Resolve the warning metadata to one saved foreign key by entity, index, and signature.

    This lookup is shared by each warning kind. It rejects unusable metadata and
    removed or edited saved entries so a stale warning never resolves to the wrong
    link.
    """
    if not project.has_table(local_entity):
        return LinkIssueResolution(status="entity_not_found", entity_name=local_entity)

    fk_index: Any = metadata.get("fk_index")
    fk_signature: Any = metadata.get("fk_signature")

    if isinstance(fk_index, bool) or not isinstance(fk_index, int):
        return LinkIssueResolution(status="missing_metadata", entity_name=local_entity)

    if not isinstance(fk_signature, str):
        return LinkIssueResolution(status="missing_metadata", entity_name=local_entity)

    saved_keys: list[ForeignKeyConfig] = project.get_table(local_entity).foreign_keys

    if not 0 <= fk_index < len(saved_keys):
        return LinkIssueResolution(status="index_out_of_range", entity_name=local_entity, fk_index=fk_index)

    saved_fk: ForeignKeyConfig = saved_keys[fk_index]

    if saved_fk.identity_signature != fk_signature:
        return LinkIssueResolution(status="signature_mismatch", entity_name=local_entity, fk_index=fk_index)

    recorded_pass: Any = metadata.get("link_pass")

    return LinkIssueResolution(
        status="resolved",
        entity_name=local_entity,
        fk_index=fk_index,
        fk=saved_fk,
        link_pass=recorded_pass if isinstance(recorded_pass, str) else None,
    )


def resolve_row_count_issue(
    project: ShapeShiftProject,
    *,
    issue_type: str,
    local_entity: str,
    metadata: Mapping[str, Any],
) -> LinkIssueResolution:
    """Resolve a row-count warning to the saved foreign key that raised it.

    Args:
        project: Project that produced the warning.
        issue_type: Type of the validation issue.
        local_entity: Entity the foreign key belongs to.
        metadata: Issue metadata, which carries the foreign key index and signature.

    Returns:
        LinkIssueResolution describing the saved foreign key or the reason no
        action is offered.
    """
    if issue_type != "row_count_mismatch":
        return LinkIssueResolution(status="not_row_count_issue", entity_name=local_entity)

    resolution: LinkIssueResolution = _resolve_saved_foreign_key(project, local_entity=local_entity, metadata=metadata)
    if not resolution.is_eligible or resolution.fk is None:
        return resolution

    if (resolution.fk.how or "inner") not in SUPPORTED_JOIN_TYPES:
        return LinkIssueResolution(
            status="unsupported_join",
            entity_name=local_entity,
            fk_index=resolution.fk_index,
            fk=resolution.fk,
        )

    return resolution


def resolve_integrity_issue(
    project: ShapeShiftProject,
    *,
    issue_type: str,
    local_entity: str,
    metadata: Mapping[str, Any],
) -> LinkIssueResolution:
    """Resolve an integrity warning to the saved foreign key that raised it.

    Integrity warnings describe values that were not found. Any saved link can be
    inspected, so the join-type restriction used for row counts does not apply.

    Args:
        project: Project that produced the warning.
        issue_type: Type of the validation issue, expected to be ``FK_DATA_INTEGRITY``.
        local_entity: Entity the foreign key belongs to.
        metadata: Issue metadata, which carries the foreign key index and signature.

    Returns:
        LinkIssueResolution describing the saved foreign key or the reason no
        action is offered.
    """
    if issue_type != "FK_DATA_INTEGRITY":
        return LinkIssueResolution(status="not_integrity_issue", entity_name=local_entity)

    return _resolve_saved_foreign_key(project, local_entity=local_entity, metadata=metadata)
