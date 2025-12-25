"""Business logic services.

This module provides centralized access to all service classes used throughout
the backend application. Services handle business logic, data processing,
and interactions with external systems.

Service Classes:
    - AutoFixService: Automated configuration fix suggestions and application
    - ConfigurationService: Configuration file management (CRUD operations)
    - DataSourceService: Global data source file management
    - DependencyService: Entity dependency analysis and topological sorting
    - PreviewService: Configuration change preview generation
    - QueryService: SQL query execution against configured data sources
    - SchemaIntrospectionService: Database schema introspection
    - SuggestionService: Entity and configuration suggestions
    - TestRunService: Test run execution and result handling
    - TypeMappingService: Type mapping between database and Python types
    - ValidationService: Multi-level configuration validation
    - YamlService: YAML file reading and writing with error handling

Exception Classes:
    Configuration Service:
        - ConfigurationServiceError: Base exception for configuration operations
        - ConfigurationNotFoundError: Configuration file not found
        - EntityNotFoundError: Entity not found in configuration
        - EntityAlreadyExistsError: Entity already exists in configuration
        - InvalidConfigurationError: Invalid configuration structure

    Dependency Service:
        - DependencyServiceError: Base exception for dependency operations
        - CircularDependencyError: Circular dependency detected

    Query Service:
        - QueryExecutionError: Query execution failed
        - QuerySecurityError: Query rejected for security reasons

    Schema Service:
        - SchemaServiceError: Schema introspection failed

    YAML Service:
        - YamlServiceError: Base exception for YAML operations
        - YamlLoadError: Failed to load YAML file
        - YamlSaveError: Failed to save YAML file

Data Classes:
    - DependencyNode: Represents a node in the dependency graph
    - DependencyGraph: Represents the complete dependency graph
    - PreviewCache: Cache for preview results
    - SchemaCache: Cache for database schema information
    - TypeMapping: Type mapping definition
"""

# Auto-fix service
from backend.app.services.auto_fix_service import AutoFixService

# Configuration service
from backend.app.services.config_service import (
    ConfigurationNotFoundError,
    ConfigurationService,
    ConfigurationServiceError,
    EntityAlreadyExistsError,
    EntityNotFoundError,
    InvalidConfigurationError,
)

# Data source service
from backend.app.services.data_source_service import DataSourceService

# Dependency service
from backend.app.services.dependency_service import (
    CircularDependencyError,
    DependencyGraph,
    DependencyNode,
    DependencyService,
    DependencyServiceError,
)

# Preview service
from backend.app.services.shapeshift_service import PreviewCache, PreviewService

# Query service
from backend.app.services.query_service import (
    QueryExecutionError,
    QuerySecurityError,
    QueryService,
)

# Schema service
from backend.app.services.schema_service import (
    SchemaCache,
    SchemaIntrospectionService,
    SchemaServiceError,
)

# Suggestion service
from backend.app.services.suggestion_service import SuggestionService

# Test run service
from backend.app.services.test_run_service import TestRunService

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
    "ConfigurationService",
    "DataSourceService",
    "DependencyService",
    "PreviewService",
    "QueryService",
    "SchemaIntrospectionService",
    "SuggestionService",
    "TestRunService",
    "TypeMappingService",
    "ValidationService",
    "YamlService",
    # Configuration exceptions
    "ConfigurationServiceError",
    "ConfigurationNotFoundError",
    "EntityNotFoundError",
    "EntityAlreadyExistsError",
    "InvalidConfigurationError",
    # Dependency exceptions and classes
    "DependencyServiceError",
    "CircularDependencyError",
    "DependencyNode",
    "DependencyGraph",
    # Query exceptions
    "QueryExecutionError",
    "QuerySecurityError",
    # Schema exceptions and classes
    "SchemaServiceError",
    "SchemaCache",
    # YAML exceptions
    "YamlServiceError",
    "YamlLoadError",
    "YamlSaveError",
    # Data classes
    "PreviewCache",
    "TypeMapping",
]
