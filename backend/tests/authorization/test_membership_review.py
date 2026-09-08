"""Tests for trusted group-membership review."""

import json
from datetime import UTC, datetime
from uuid import uuid4

import httpx
from click.testing import CliRunner

from backend.app.authorization.membership import HttpGroupMembershipResolver, MembershipLookupStatus
from backend.app.authorization.models import Grant, GrantSubjectType, ResourceRecord, ResourceType
from backend.app.authorization.repository import SQLiteAuthorizationRepository
from backend.app.scripts.authorization import cli


def test_http_membership_resolver_encodes_group_and_returns_members(monkeypatch) -> None:
    requested_urls: list[str] = []

    def fake_get(url: str, timeout: float) -> httpx.Response:
        requested_urls.append(url)
        return httpx.Response(200, json={"members": ["alice", " bob "]})

    monkeypatch.setattr(httpx, "get", fake_get)

    snapshot = HttpGroupMembershipResolver("https://directory/groups/{group_id}/members", "directory").resolve_members("team/admin")

    assert requested_urls == ["https://directory/groups/team%2Fadmin/members"]
    assert snapshot.status == MembershipLookupStatus.RESOLVED
    assert snapshot.principal_ids == frozenset({"alice", "bob"})
    assert snapshot.provider == "directory"


def test_http_membership_resolver_reports_unavailable_provider(monkeypatch) -> None:
    def fake_get(url: str, timeout: float) -> httpx.Response:
        return httpx.Response(503, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", fake_get)

    snapshot = HttpGroupMembershipResolver("https://directory/groups/{group_id}", "directory").resolve_members("editors")

    assert snapshot.status == MembershipLookupStatus.UNAVAILABLE
    assert snapshot.principal_ids == frozenset()
    assert snapshot.error


def test_http_membership_resolver_reports_missing_group(monkeypatch) -> None:
    def fake_get(url: str, timeout: float) -> httpx.Response:
        return httpx.Response(404)

    monkeypatch.setattr(httpx, "get", fake_get)

    snapshot = HttpGroupMembershipResolver("https://directory/groups/{group_id}", "directory").resolve_members("unknown")

    assert snapshot.status == MembershipLookupStatus.NOT_FOUND
    assert snapshot.principal_ids == frozenset()


def test_list_grants_effective_json_includes_membership_snapshot(tmp_path, monkeypatch) -> None:
    database = tmp_path / "authorization.sqlite3"
    repository = SQLiteAuthorizationRepository(database)
    resource = ResourceRecord(uuid4(), ResourceType.PROJECT, "project-a")
    repository.create_resource(resource)
    repository.add_grant(Grant("editors", resource.resource_id, "editor", datetime.now(UTC), "admin", GrantSubjectType.GROUP))
    repository.close()

    monkeypatch.setattr(httpx, "get", lambda url, timeout: httpx.Response(200, json={"members": ["alice", "bob"]}))
    result = CliRunner().invoke(
        cli,
        [
            "list-grants",
            "--database",
            str(database),
            "--effective",
            "--membership-url",
            "https://directory/groups/{group_id}/members",
            "--actor",
            "operator",
            "--json",
        ],
    )

    assert result.exit_code == 0
    record = json.loads(result.output)[0]
    assert record["membership"]["status"] == "resolved"
    assert record["membership"]["principal_ids"] == ["alice", "bob"]
    audit_repository = SQLiteAuthorizationRepository(database)
    audit_event = audit_repository.list_audit_events()[-1]
    assert audit_event.event_type == "membership_lookup"
    assert audit_event.actor_principal_id == "operator"
    assert audit_event.provider == "trusted-membership-provider"
    assert audit_event.outcome == "resolved"
    audit_repository.close()


def test_list_grants_strict_effective_review_fails_for_unavailable_group(tmp_path, monkeypatch) -> None:
    database = tmp_path / "authorization.sqlite3"
    repository = SQLiteAuthorizationRepository(database)
    resource = ResourceRecord(uuid4(), ResourceType.PROJECT, "project-a")
    repository.create_resource(resource)
    repository.add_grant(Grant("editors", resource.resource_id, "editor", datetime.now(UTC), "admin", GrantSubjectType.GROUP))
    repository.close()

    def unavailable(url: str, timeout: float) -> httpx.Response:
        return httpx.Response(503, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", unavailable)
    result = CliRunner().invoke(
        cli,
        [
            "list-grants",
            "--database",
            str(database),
            "--effective",
            "--membership-url",
            "https://directory/groups/{group_id}/members",
            "--actor",
            "operator",
            "--strict",
        ],
    )

    assert result.exit_code != 0
    assert "did not resolve" in result.output
