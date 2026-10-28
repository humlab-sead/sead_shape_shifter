"""Contracts and registry for project-load issue collectors."""

from dataclasses import dataclass, field
from typing import Any, Protocol

from backend.app.models.validation import ValidationError as APIValidationError


@dataclass
class ProjectLoadIssues:
    """Warnings and validation errors collected while loading a project."""

    warnings: list[str] = field(default_factory=list)
    errors: list[APIValidationError] = field(default_factory=list)


class ProjectLoadIssueCollector(Protocol):
    """Collect warnings and validation errors from project configuration."""

    def collect(self, cfg_dict: dict[str, Any], project_name: str, filename: str | None = None) -> ProjectLoadIssues:
        """Return load warnings and validation errors for the project configuration."""
        ...


class ProjectLoadIssueCollectorRegistry:
    """Register and run project-load issue collectors."""

    def __init__(self) -> None:
        self._collectors: dict[str, ProjectLoadIssueCollector] = {}

    def register(self, key: str, collector: ProjectLoadIssueCollector) -> None:
        """Register a collector under a unique key."""
        if not key:
            raise ValueError("Project load issue collector key cannot be empty.")
        if key in self._collectors:
            raise ValueError(f"Project load issue collector '{key}' is already registered.")
        self._collectors[key] = collector

    def collect(self, cfg_dict: dict[str, Any], project_name: str, filename: str | None = None) -> ProjectLoadIssues:
        """Aggregate issues from all registered collectors."""
        result = ProjectLoadIssues()
        for collector in self._collectors.values():
            collector_result = collector.collect(cfg_dict, project_name, filename)
            result.warnings.extend(collector_result.warnings)
            result.errors.extend(collector_result.errors)
        return result
