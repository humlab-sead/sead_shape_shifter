"""Reconciliation service module.

This module provides services for entity reconciliation against SEAD database
and external reconciliation services using the OpenRefine protocol.

Classes:
    - ReconciliationService: Main service for reconciliation operations
    - ReconciliationQueryService: Service for building reconciliation queries
    - EntityMappingManager: Manager for entity mapping registry and specification CRUD
    - ReconciliationSourceResolver: Abstract base for source data resolvers
    - TargetEntityReconciliationSourceResolver: Resolver for target entity sources
    - SqlQueryReconciliationSourceResolver: Resolver for SQL query sources
    - AnotherEntityReconciliationSourceResolver: Resolver for another entity sources
"""

from backend.app.services.reconciliation.mapping_manager import EntityMappingManager
from backend.app.services.reconciliation.resolvers import (
    AnotherEntityReconciliationSourceResolver,
    ReconciliationSourceResolver,
    SqlQueryReconciliationSourceResolver,
    TargetEntityReconciliationSourceResolver,
)
from backend.app.services.reconciliation.service import (
    ReconciliationQueryService,
    ReconciliationService,
)

__all__ = [
    "ReconciliationService",
    "ReconciliationQueryService",
    "EntityMappingManager",
    "ReconciliationSourceResolver",
    "TargetEntityReconciliationSourceResolver",
    "SqlQueryReconciliationSourceResolver",
    "AnotherEntityReconciliationSourceResolver",
]
