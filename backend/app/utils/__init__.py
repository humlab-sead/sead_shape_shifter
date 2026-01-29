"""Utility modules for the backend application.

This package contains reusable utilities for graph algorithms and SQL parsing.
Modules were refactored from dependency_service.py for improved testability.
"""

from backend.app.utils.graph import calculate_depths, find_cycles, topological_sort
from backend.app.utils.sql import extract_tables

__all__ = [
    # Graph algorithms
    "find_cycles",
    "topological_sort",
    "calculate_depths",
    # SQL utilities
    "extract_tables",
]
