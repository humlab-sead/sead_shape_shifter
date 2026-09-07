"""Central authorization decision service."""

from datetime import UTC, datetime
from uuid import uuid4

from backend.app.authorization.models import Action, AuthorizedResource, Grant, Principal, ResourceRecord, ResourceType
from backend.app.authorization.policy import AuthorizationPolicy
from backend.app.authorization.repository import AuthorizationRepository


class AuthorizationService:
    """Evaluate resource and application access using one policy and repository."""

    def __init__(self, repository: AuthorizationRepository, policy: AuthorizationPolicy | None = None) -> None:
        self.repository = repository
        self.policy = policy or AuthorizationPolicy()

    def is_allowed(self, principal: Principal, action: Action, resource: ResourceRecord) -> bool:
        """Return whether the principal may perform an action on a resource."""
        if resource.lifecycle_state != "active":
            return False

        if any(
            self.policy.allows_application_role(role, action) for role in self.repository.list_application_roles(principal.principal_id)
        ):
            return True

        resource_ids = self._resource_and_ancestors(resource)
        return any(
            grant.resource_id in resource_ids and self.policy.allows_resource_role(resource.resource_type, grant.role, action)
            for grant in self.repository.list_matching_grants(principal.principal_id, tuple(principal.group_ids))
        )

    def authorize(self, principal: Principal, action: Action, resource: ResourceRecord) -> AuthorizedResource | None:
        """Return an authorized resource or None when access is denied."""
        if not self.is_allowed(principal, action, resource):
            return None
        return AuthorizedResource(principal=principal, action=action, resource=resource)

    def register_project(self, principal: Principal, locator: str) -> ResourceRecord:
        """Create a project resource and assign its initial owner."""
        if self.repository.get_resource_by_locator(ResourceType.PROJECT, locator) is not None:
            raise ValueError(f"Authorization resource already exists for project: {locator}")

        resource = ResourceRecord(uuid4(), ResourceType.PROJECT, locator)
        self.repository.create_resource(resource)
        self.repository.add_grant(Grant(principal.principal_id, resource.resource_id, "owner", datetime.now(UTC), principal.principal_id))
        return resource

    def register_shared_data_source(self, principal: Principal, locator: str) -> ResourceRecord:
        """Create a shared data source resource and assign the creator read access."""
        if self.repository.get_resource_by_locator(ResourceType.SHARED_DATA_SOURCE, locator) is not None:
            raise ValueError(f"Authorization resource already exists for shared data source: {locator}")

        resource = ResourceRecord(uuid4(), ResourceType.SHARED_DATA_SOURCE, locator)
        self.repository.create_resource(resource)
        self.repository.add_grant(Grant(principal.principal_id, resource.resource_id, "reader", datetime.now(UTC), principal.principal_id))
        return resource

    def transition_resource(self, resource: ResourceRecord, lifecycle_state: str) -> None:
        """Set the lifecycle state of a server-owned resource."""
        self.repository.update_resource_lifecycle(resource.resource_id, lifecycle_state)

    def _resource_and_ancestors(self, resource: ResourceRecord) -> set:
        resource_ids = {resource.resource_id}
        parent_id = resource.parent_resource_id
        while parent_id is not None:
            resource_ids.add(parent_id)
            parent = self.repository.get_resource(parent_id)
            parent_id = parent.parent_resource_id if parent else None
        return resource_ids
