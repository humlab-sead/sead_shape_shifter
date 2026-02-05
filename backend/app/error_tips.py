"""
Centralized error tips registry.

Maps error codes to actionable recovery tips for users.
Keeps tips out of business logic while maintaining discoverability.

Tips can use template variables that will be replaced with context values:
- {entity} - Entity name from context
- {target_entity} - Referenced entity name
- {missing_entity} - Missing dependency
- {resource_id} - Resource identifier
- {resource_type} - Type of resource (project, entity, file)
- {field_type} - Expected field type
- {actual_type} - Actual field type
- {count_local} - Local key count
- {count_remote} - Remote key count
- {data_source} - Data source name
"""

# ============================================================================
# Error Tips Registry
# ============================================================================

from typing import Any

ERROR_TIPS: dict[str, list[str]] = {
    # Resource errors
    "RESOURCE_NOT_FOUND": [
        "Check resource name for typos",
        "Verify resource exists in the system",
        "Refresh resource list",
    ],
    "RESOURCE_CONFLICT": [
        "Choose a different name",
        "Delete existing resource if you want to replace it",
        "Check for concurrent modifications",
    ],
    "RESOURCE_ERROR": [
        "Check resource availability",
        "Verify permissions to access resource",
        "Review resource configuration",
    ],
    # Configuration Errors (CONFIG_*)
    "CONFIG_INVALID": [
        "Check configuration syntax",
        "Verify all required fields are present",
        "Restore from backup if corrupted",
    ],
    "CONFIG_YAML_ERROR": [
        "Check YAML syntax for errors",
        "Validate indentation and special characters",
        "Restore from backup if syntax is corrupted",
    ],
    # Validation errors
    "VALIDATION_FAILED": [
        "Review validation error details",
        "Check data types and formats",
        "Ensure required fields are present",
    ],
    "FOREIGN_KEY_INVALID": [
        "Verify referenced entity exists",
        "Check foreign key column names match",
        "Ensure data types are compatible",
    ],
    "FK_NOT_LIST": [
        "Change foreign_keys to a list: foreign_keys: [...]",
        "Each foreign key should be a separate list item",
        "Check YAML syntax - use '- entity: ...' for list items",
    ],
    "FK_NOT_DICT": [
        "Foreign key definition should have keys: entity, local_keys, remote_keys",
        "Example: - entity: {target_entity}\n  local_keys: [column]\n  remote_keys: [column]",
    ],
    "FK_MISSING_ENTITY": [
        "Add 'entity' field specifying the referenced entity",
        "Example: entity: {target_entity}",
    ],
    "FK_MISSING_LOCAL_KEYS": [
        "Add local_keys as a list of column names",
        "Example: local_keys: [column_name]",
    ],
    "FK_LOCAL_KEYS_NOT_LIST": [
        "Change local_keys from {actual_type} to list: local_keys: [key1, key2]",
        "Ensure YAML uses sequence syntax with '- item'",
        "Do not use dict format like {{key: value}}",
    ],
    "FK_LOCAL_KEY_NOT_STRING": [
        "Change key from {actual_type} to string",
        "Remove nested structures or dicts from key list",
        "Each key should be a simple column name string",
    ],
    "FK_MISSING_REMOTE_KEYS": [
        "Add remote_keys as a list of column names from referenced entity",
        "Example: remote_keys: [column_name]",
    ],
    "FK_REMOTE_KEYS_NOT_LIST": [
        "Change remote_keys from {actual_type} to list: remote_keys: [key1, key2]",
        "Ensure YAML uses sequence syntax with '- item'",
        "Do not use dict format like {{key: value}}",
    ],
    "FK_REMOTE_KEY_NOT_STRING": [
        "Change key from {actual_type} to string",
        "Remove nested structures or dicts from key list",
        "Each key should be a simple column name string",
    ],
    "FK_KEY_COUNT_MISMATCH": [
        "Ensure local_keys and remote_keys have same number of items ({count_local} vs {count_remote})",
        "Each local key should map to exactly one remote key",
        "For composite keys, both lists must have same length",
    ],
    # Dependency Errors (DEPENDENCY_*, CIRCULAR_*)
    "DEPENDENCY_ERROR": [
        "Review entity dependencies",
        "Check for circular references",
        "Ensure required entities are defined",
    ],
    "MISSING_DEPENDENCY": [
        "Create the missing entity '{missing_entity}' first",
        "Check for typos in entity name (case-sensitive)",
        "Verify entity hasn't been renamed or deleted",
        "Review all entity names in project overview",
    ],
    "CIRCULAR_DEPENDENCY": [
        "Review entity dependency graph",
        "Remove circular references",
        "Reorganize entity relationships",
    ],
    # Data integrity errors
    "DATA_INTEGRITY_VIOLATION": [
        "Check for duplicate values in unique columns",
        "Verify foreign key relationships",
        "Review data constraints",
    ],
    # Query errors
    "QUERY_EXEC_FAILED": [
        "Check data source connection is active",
        "Verify SQL syntax is valid for the database type",
        "Check if query timeout needs to be increased",
        "Ensure proper database permissions are granted",
    ],
    "QUERY_EXEC_TIMEOUT": [
        "Simplify query or add WHERE clause to reduce result set",
        "Increase timeout value if query is expected to be slow",
        "Check database server performance",
        "Consider adding indexes to improve query speed",
    ],
    "QUERY_EXEC_CONNECTION": [
        "Verify data source connection settings",
        "Check network connectivity to database",
        "Ensure database server is running",
        "Review connection timeout settings",
    ],
    "QUERY_SECURITY_VIOLATION": [
        "Only SELECT queries are allowed",
        "Remove DELETE, DROP, UPDATE, INSERT operations",
        "Use read-only database connections",
        "Contact administrator for write access",
    ],
    # Schema introspection errors
    "SCHEMA_INTROSPECT_FAILED": [
        "Verify data source connection is active",
        "Check driver supports schema introspection",
        "Ensure proper database permissions for metadata access",
        "Confirm table/database exists",
    ],
    "SCHEMA_NOT_SUPPORTED": [
        "Use a database driver that supports schema introspection",
        "Check driver compatibility",
        "Consider using a different data source type",
    ],
    # Dependency errors
    "DEPENDENCY_ERROR": [
        "Review entity dependencies",
        "Check for circular references",
        "Ensure required entities are defined",
    ],
}


def get_tips(error_code: str, context: dict[str, Any] | None = None) -> list[str]:
    """
    Get tips for an error code with optional template formatting.

    Args:
        error_code: Error code to look up
        context: Optional context dict for template variable substitution

    Returns:
        List of actionable tips (formatted if context provided), or empty list if code not found
    """
    tips = ERROR_TIPS.get(error_code, [])

    if not context:
        return tips

    # Format tips with context values
    formatted_tips = []
    for tip in tips:
        try:
            formatted_tips.append(tip.format(**context))
        except (KeyError, ValueError):
            # If template variable missing, use unformatted tip
            formatted_tips.append(tip)

    return formatted_tips


def register_tips(error_code: str, tips: list[str]) -> None:
    """
    Register or update tips for an error code.

    Args:
        error_code: Error code to register
        tips: List of actionable tips
    """
    ERROR_TIPS[error_code] = tips
