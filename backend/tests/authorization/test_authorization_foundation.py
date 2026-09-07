"""Tests for the centralized authorization foundation."""

from datetime import UTC, datetime
from uuid import uuid4

from backend.app.authorization.models import Action, ApplicationRole, Grant, Principal, ResourceRecord, ResourceType
from backend.app.authorization.policy import AuthorizationPolicy
from backend.app.authorization.repository import SQLiteAuthorizationRepository
from backend.app.authorization.service import AuthorizationService


def _principal(principal_id: str = "alice") -> Principal:
    return Principal(principal_id, "trusted-proxy", datetime.now(UTC))


def test_resource_role_policy_covers_every_action_and_resource_type() -> None:
    policy = AuthorizationPolicy()
    expected_permissions = {
        ResourceType.PROJECT: {
            "viewer": {Action.READ},
            "editor": {Action.READ, Action.EDIT},
            "executor": {Action.READ, Action.EXECUTE},
            "owner": {Action.READ, Action.EDIT, Action.EXECUTE, Action.DELETE, Action.MANAGE_GRANTS},
        },
        ResourceType.PROJECT_CHILD: {
            "viewer": {Action.READ},
            "editor": {Action.READ, Action.EDIT},
            "executor": {Action.READ, Action.EXECUTE},
            "owner": {Action.READ, Action.EDIT, Action.EXECUTE, Action.DELETE, Action.MANAGE_GRANTS},
        },
        ResourceType.SHARED_DATA_SOURCE: {"reader": {Action.READ}},
        ResourceType.SHARED_DATA_SOURCE_CHILD: {"reader": {Action.READ}},
    }
    all_resource_roles = {role for permissions in expected_permissions.values() for role in permissions}

    for resource_type in ResourceType:
        for role in all_resource_roles | {"unknown"}:
            allowed_actions = expected_permissions[resource_type].get(role, set())
            for action in Action:
                assert policy.allows_resource_role(resource_type, role, action) is (action in allowed_actions)


def test_application_role_policy_covers_every_action() -> None:
    policy = AuthorizationPolicy()
    expected_permissions = {
        ApplicationRole.PROJECT_CREATOR: {Action.CREATE_PROJECT},
        ApplicationRole.OPERATOR: {Action.READ_ALL_SHARED_SOURCES, Action.MANAGE_SHARED_SOURCES, Action.RUN_INGESTERS},
        ApplicationRole.ADMIN: set(Action),
    }

    for role in (*ApplicationRole, "unknown"):
        allowed_actions = expected_permissions.get(role, set())
        for action in Action:
            assert policy.allows_application_role(role, action) is (action in allowed_actions)


def test_unknown_role_and_action_are_denied(tmp_path) -> None:
    repository = SQLiteAuthorizationRepository(tmp_path / "authorization.sqlite3")
    project = ResourceRecord(uuid4(), ResourceType.PROJECT, "project-a")
    repository.create_resource(project)
    repository.add_grant(Grant("alice", project.resource_id, "unknown", datetime.now(UTC), "admin"))

    service = AuthorizationService(repository)

    assert not service.is_allowed(_principal(), Action.EDIT, project)
    assert not service.is_allowed(_principal(), Action.READ_LOGS, project)
    repository.close()


def test_project_grant_is_inherited_by_child_and_persists(tmp_path) -> None:
    path = tmp_path / "authorization.sqlite3"
    repository = SQLiteAuthorizationRepository(path)
    project = ResourceRecord(uuid4(), ResourceType.PROJECT, "project-a")
    output = ResourceRecord(uuid4(), ResourceType.PROJECT_CHILD, "output-1", parent_resource_id=project.resource_id)
    repository.create_resource(project)
    repository.create_resource(output)
    repository.add_grant(Grant("alice", project.resource_id, "viewer", datetime.now(UTC), "admin"))
    repository.close()

    reopened = SQLiteAuthorizationRepository(path)
    service = AuthorizationService(reopened)

    assert service.authorize(_principal(), Action.READ, output) is not None
    assert service.authorize(_principal("bob"), Action.READ, output) is None
    reopened.close()


def test_deleted_resource_name_can_be_reused_without_inheriting_grants(tmp_path) -> None:
    repository = SQLiteAuthorizationRepository(tmp_path / "authorization.sqlite3")
    deleted = ResourceRecord(uuid4(), ResourceType.PROJECT, "reused-name")
    repository.create_resource(deleted)
    repository.add_grant(Grant("alice", deleted.resource_id, "owner", datetime.now(UTC), "admin"))
    repository.update_resource_lifecycle(deleted.resource_id, "deleted")
    replacement = ResourceRecord(uuid4(), ResourceType.PROJECT, "reused-name")
    repository.create_resource(replacement)

    assert replacement.resource_id != deleted.resource_id
    assert not AuthorizationService(repository).is_allowed(_principal(), Action.READ, replacement)
    repository.close()


def test_register_shared_data_source_creates_resource_and_reader_grant(tmp_path) -> None:
    repository = SQLiteAuthorizationRepository(tmp_path / "authorization.sqlite3")

    resource = AuthorizationService(repository).register_shared_data_source(_principal(), "source-a")

    assert resource.resource_type == ResourceType.SHARED_DATA_SOURCE
    assert resource.locator == "source-a"
    assert repository.get_resource_by_locator(ResourceType.SHARED_DATA_SOURCE, "source-a") == resource
    grants = repository.list_grants("alice")
    assert len(grants) == 1
    assert grants[0].resource_id == resource.resource_id
    assert grants[0].role == "reader"
    repository.close()
