"""Business logic services.

This module provides centralized access to all service classes used throughout
the backend application. Services handle business logic, data processing,
and interactions with external systems.

Service Classes:
    - AutoFixService: Automated configuration fix suggestions and application
    - ProjectService: Project file management (CRUD operations)
    - DataSourceService: Global data source file management
    - DependencyService: Entity dependency analysis and topological sorting
    - ShapeShiftService: Project change preview generation
    - QueryService: SQL query execution against configured data sources
    - SchemaIntrospectionService: Database schema introspection
    - SuggestionService: Entity and configuration suggestions
    - TestRunService: Test run execution and result handling
    - TypeMappingService: Type mapping between database and Python types
    - ValidationService: Multi-level configuration validation
    - YamlService: YAML file reading and writing with error handling


Data Classes:
    - DependencyNode: Represents a node in the dependency graph
    - DependencyGraph: Represents the complete dependency graph
    - PreviewCache: Cache for preview results
    - SchemaCache: Cache for database schema information
    - TypeMapping: Type mapping definition
"""

from backend.app.services.auto_fix_service import AutoFixService
from backend.app.services.data_source_service import DataSourceService
from backend.app.services.dependency_service import DependencyGraph, DependencyNode, DependencyService, SourceNode
from backend.app.services.project import ProjectServiceError
from backend.app.services.project_service import ProjectService
from backend.app.services.query_service import QueryService
from backend.app.services.schema_service import SchemaCache, SchemaIntrospectionService

# Preview service
from backend.app.services.shapeshift_service import ShapeShiftCache, ShapeShiftService

# Suggestion service
from backend.app.services.suggestion_service import SuggestionService

# Type mapping service
from backend.app.services.type_mapping_service import TypeMapping, TypeMappingService

# Validation service
from backend.app.services.validation_service import ValidationService

# YAML service
from backend.app.services.yaml_service import (
    YamlLoadError,
    YamlSaveError,
    YamlService,
    YamlServiceError,
)

__all__ = [
    # Services
    "AutoFixService",
    "ProjectService",
    "DataSourceService",
    "DependencyService",
    "ShapeShiftService",
    "QueryService",
    "SchemaIntrospectionService",
    "SuggestionService",
    "TypeMappingService",
    "ValidationService",
    "YamlService",
    # Generic service exception
    "ProjectServiceError",
    # Dependency classes
    "DependencyNode",
    "DependencyGraph",
    "SourceNode",
    # YAML exceptions
    "YamlServiceError",
    "YamlLoadError",
    "YamlSaveError",
    # Data classes
    "SchemaCache",
    "ShapeShiftCache",
    "TypeMapping",
]
