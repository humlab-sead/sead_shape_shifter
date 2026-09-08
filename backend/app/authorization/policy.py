"""Central role-to-action authorization policy."""

from backend.app.authorization.models import Action, ApplicationRole, ResourceType

PROJECT_ROLE_ACTIONS: dict[str, frozenset[Action]] = {
    "viewer": frozenset({Action.READ}),
    "editor": frozenset({Action.READ, Action.EDIT}),
    "executor": frozenset({Action.READ, Action.EXECUTE}),
    "owner": frozenset({Action.READ, Action.EDIT, Action.EXECUTE, Action.DELETE, Action.MANAGE_GRANTS}),
}

SHARED_SOURCE_ROLE_ACTIONS: dict[str, frozenset[Action]] = {
    "reader": frozenset({Action.READ}),
}

APPLICATION_ROLE_ACTIONS: dict[ApplicationRole, frozenset[Action]] = {
    ApplicationRole.PROJECT_CREATOR: frozenset({Action.CREATE_PROJECT}),
    ApplicationRole.OPERATOR: frozenset({Action.READ_ALL_SHARED_SOURCES, Action.MANAGE_SHARED_SOURCES, Action.RUN_INGESTERS}),
    ApplicationRole.ADMIN: frozenset(Action),
}


class AuthorizationPolicy:
    """Evaluate explicit role mappings without implicit allow rules."""

    def allows_resource_role(self, resource_type: ResourceType, role: str, action: Action) -> bool:
        """Return whether a resource role permits an action for its resource type."""
        if resource_type in {ResourceType.PROJECT, ResourceType.PROJECT_CHILD}:
            return action in PROJECT_ROLE_ACTIONS.get(role, frozenset())
        if resource_type in {ResourceType.SHARED_DATA_SOURCE, ResourceType.SHARED_DATA_SOURCE_CHILD}:
            return action in SHARED_SOURCE_ROLE_ACTIONS.get(role, frozenset())
        return False

    def allows_application_role(self, role: str, action: Action) -> bool:
        """Return whether an application role permits an application action."""
        try:
            application_role = ApplicationRole(role)
        except ValueError:
            return False
        return action in APPLICATION_ROLE_ACTIONS.get(application_role, frozenset())
