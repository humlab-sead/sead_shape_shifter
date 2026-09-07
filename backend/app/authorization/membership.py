"""Trusted group-membership lookup for authorization review."""

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol
from urllib.parse import quote

import httpx


class MembershipLookupStatus(StrEnum):
    """Result states returned by a membership provider."""

    RESOLVED = "resolved"
    NOT_FOUND = "not_found"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class MembershipSnapshot:
    """A point-in-time group membership lookup result."""

    group_id: str
    principal_ids: frozenset[str]
    provider: str
    fetched_at: datetime
    status: MembershipLookupStatus
    error: str | None = None


class GroupMembershipResolver(Protocol):
    """Resolve group members from a trusted identity authority."""

    def resolve_members(self, group_id: str) -> MembershipSnapshot:
        """Return the current review result for one group."""


class HttpGroupMembershipResolver:
    """Read group members from a configured trusted HTTP provider."""

    def __init__(self, url_template: str, provider: str, timeout_seconds: float = 5.0) -> None:
        if "{group_id}" not in url_template:
            raise ValueError("Membership lookup URL must contain {group_id}")
        self.url_template = url_template
        self.provider = provider
        self.timeout_seconds = timeout_seconds

    def resolve_members(self, group_id: str) -> MembershipSnapshot:
        """Fetch one group's members without changing authorization state."""
        fetched_at = datetime.now(UTC)
        url = self.url_template.replace("{group_id}", quote(group_id, safe=""))
        try:
            response = httpx.get(url, timeout=self.timeout_seconds)
            if response.status_code == httpx.codes.NOT_FOUND:
                return MembershipSnapshot(group_id, frozenset(), self.provider, fetched_at, MembershipLookupStatus.NOT_FOUND)
            if response.is_error:
                response.raise_for_status()
            payload = response.json()
            members = payload.get("members") if isinstance(payload, dict) else None
            if not isinstance(members, list) or not all(isinstance(member, str) and member.strip() for member in members):
                raise ValueError("Membership provider returned an invalid members list")
            return MembershipSnapshot(
                group_id,
                frozenset(member.strip() for member in members),
                self.provider,
                fetched_at,
                MembershipLookupStatus.RESOLVED,
            )
        except (httpx.HTTPError, ValueError) as error:
            return MembershipSnapshot(group_id, frozenset(), self.provider, fetched_at, MembershipLookupStatus.UNAVAILABLE, str(error))
