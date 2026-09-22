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

# Child resources use the same role table as their parent resource type.
RESOURCE_ROLE_ACTIONS: dict[ResourceType, dict[str, frozenset[Action]]] = {
    ResourceType.PROJECT: PROJECT_ROLE_ACTIONS,
    ResourceType.PROJECT_CHILD: PROJECT_ROLE_ACTIONS,
    ResourceType.SHARED_DATA_SOURCE: SHARED_SOURCE_ROLE_ACTIONS,
    ResourceType.SHARED_DATA_SOURCE_CHILD: SHARED_SOURCE_ROLE_ACTIONS,
}

DEPLOYMENT_ROLE_ACTIONS: dict[ApplicationRole, frozenset[Action]] = {
    ApplicationRole.PROJECT_CREATOR: frozenset({Action.CREATE_PROJECT}),
    ApplicationRole.OPERATOR: frozenset({Action.READ_ALL_SHARED_SOURCES, Action.MANAGE_SHARED_SOURCES, Action.RUN_INGESTERS}),
    ApplicationRole.PROJECT_MAINTAINER: frozenset({Action.READ, Action.EDIT, Action.EXECUTE}),
    ApplicationRole.ADMIN: frozenset(Action),
}


class AuthorizationPolicy:
    """Evaluate explicit role mappings without implicit allow rules."""

    def allows_resource_role(self, resource_type: ResourceType, role: str, action: Action) -> bool:
        """Return whether a resource role permits an action for its resource type."""
        role_actions = RESOURCE_ROLE_ACTIONS.get(resource_type, {})
        return action in role_actions.get(role, frozenset())

    def allows_deployment_role(self, role: str, action: Action) -> bool:
        """Return whether a deployment role permits an action."""
        try:
            deployment_role = ApplicationRole(role)
        except ValueError:
            return False
        return action in DEPLOYMENT_ROLE_ACTIONS.get(deployment_role, frozenset())
