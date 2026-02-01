"""@value directive validation service.

Validates @value directive paths against project structure to catch
invalid references before runtime.
"""

from typing import Any

from loguru import logger
from pydantic import BaseModel

from backend.app.models.project import Project


class DirectiveValidationResult(BaseModel):
    """Result of validating a @value directive."""

    is_valid: bool
    path: str
    resolved_value: Any | None = None
    error: str | None = None
    suggestions: list[str] = []


class DirectiveValidator:
    """Service for validating @value directive paths."""

    def __init__(self, project: Project):
        self.project = project

    def validate_directive(self, directive: str) -> DirectiveValidationResult:
        """
        Validate a @value directive path.

        Args:
            directive: The @value directive string (e.g., "@value:entities.site.keys")

        Returns:
            DirectiveValidationResult with validation status and details
        """
        # Strip @value: prefix
        if not directive.startswith("@value:"):
            return DirectiveValidationResult(
                is_valid=False,
                path=directive,
                error="Directive must start with '@value:'",
            )

        path = directive[7:]  # Remove "@value:" prefix
        
        # Split path into parts
        parts = path.split(".")
        
        if len(parts) < 2:
            return DirectiveValidationResult(
                is_valid=False,
                path=path,
                error="Path must have at least 2 parts (e.g., 'entities.site')",
                suggestions=self._get_root_suggestions(),
            )

        # Validate path
        try:
            resolved_value = self._resolve_path(parts)
            return DirectiveValidationResult(
                is_valid=True,
                path=path,
                resolved_value=resolved_value,
            )
        except KeyError as e:
            suggestions = self._get_suggestions_for_path(parts)
            return DirectiveValidationResult(
                is_valid=False,
                path=path,
                error=str(e),
                suggestions=suggestions,
            )

    def _resolve_path(self, parts: list[str]) -> Any:
        """
        Resolve a path through the project structure.

        Args:
            parts: Path parts (e.g., ["entities", "site", "keys"])

        Returns:
            The resolved value at the path

        Raises:
            KeyError: If path is invalid
        """
        # Start at project root
        current = {"entities": self.project.entities, "options": self.project.options}

        for i, part in enumerate(parts):
            if isinstance(current, dict):
                if part not in current:
                    available = list(current.keys())
                    raise KeyError(f"'{part}' not found at {'.'.join(parts[:i])}. Available: {available}")
                current = current[part]
            else:
                raise KeyError(f"Cannot navigate into non-dict value at {'.'.join(parts[:i])}")

        return current

    def _get_root_suggestions(self) -> list[str]:
        """Get suggestions for root-level paths."""
        suggestions = ["entities", "options"]
        
        # Add common entity paths
        for entity_name in self.project.entity_names[:5]:  # First 5 entities
            suggestions.append(f"entities.{entity_name}.keys")
            suggestions.append(f"entities.{entity_name}.columns")
            
        return suggestions

    def _get_suggestions_for_path(self, parts: list[str]) -> list[str]:
        """
        Get suggestions for completing an invalid path.

        Args:
            parts: Path parts that failed to resolve

        Returns:
            List of suggested valid paths
        """
        suggestions = []
        
        # Try to navigate as far as possible
        try:
            current = {"entities": self.project.entities, "options": self.project.options}
            valid_parts = []
            
            for part in parts[:-1]:  # All parts except the last
                if isinstance(current, dict) and part in current:
                    current = current[part]
                    valid_parts.append(part)
                else:
                    break
            
            # If we're at a dict, suggest its keys
            if isinstance(current, dict):
                base_path = ".".join(valid_parts) if valid_parts else ""
                keys = list(current.keys())[:10]  # Max 10 suggestions
                
                if keys:
                    for key in keys:
                        suggestion = f"{base_path}.{key}" if base_path else key
                        suggestions.append(suggestion)
                else:
                    # No keys available, suggest root paths
                    suggestions = self._get_root_suggestions()
                    
        except Exception as e:
            logger.debug(f"Error generating suggestions: {e}")
            # Fallback to root suggestions on error
            suggestions = self._get_root_suggestions()
        
        return suggestions

    def validate_foreign_key_directive(
        self, local_entity: str, remote_entity: str, directive: str, is_local: bool
    ) -> DirectiveValidationResult:
        """
        Validate a @value directive in FK context.

        Args:
            local_entity: Local entity name
            remote_entity: Remote entity name
            directive: The @value directive string
            is_local: True if directive is for local keys, False for remote keys

        Returns:
            DirectiveValidationResult with context-aware validation
        """
        result = self.validate_directive(directive)
        
        # Add context-specific validation
        if result.is_valid:
            # Check if resolved value is a list (appropriate for FK keys)
            if not isinstance(result.resolved_value, list):
                result.is_valid = False
                result.error = f"FK keys must resolve to a list, got {type(result.resolved_value).__name__}"
                
        # Add context-specific suggestions
        if not result.is_valid:
            entity_name = local_entity if is_local else remote_entity
            if entity_name in self.project.entities:
                result.suggestions = [
                    f"@value:entities.{entity_name}.keys",
                    f"@value:entities.{entity_name}.columns",
                ]
                
        return result

    def get_all_valid_paths(self, max_depth: int = 3) -> list[str]:
        """
        Get all valid @value paths in the project.

        Args:
            max_depth: Maximum path depth to traverse

        Returns:
            List of valid @value directive paths
        """
        paths = []
        
        # Traverse entities
        for entity_name in self.project.entity_names:
            entity = self.project.entities[entity_name]
            paths.append(f"@value:entities.{entity_name}.keys")
            paths.append(f"@value:entities.{entity_name}.columns")
            
            if isinstance(entity, dict):
                # Add paths for common fields
                for field in ["public_id", "system_id", "extra_columns"]:
                    if field in entity:
                        paths.append(f"@value:entities.{entity_name}.{field}")
                        
        return paths
