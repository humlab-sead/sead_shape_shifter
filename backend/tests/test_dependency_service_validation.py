"""Tests for DependencyService - focus on graph analysis.

NOTE: Foreign key validation is handled by specifications in src/specifications.py
and tested in tests/test_specifications.py. These tests focus on dependency graph
construction, cycle detection, and graph analysis logic.
"""

import pytest

from backend.app.exceptions import CircularDependencyError, DataIntegrityError
from backend.app.models.project import Project
from backend.app.services.dependency_service import DependencyService


class TestDependencyGraphAnalysis:
    """Tests for dependency graph analysis (not FK validation)."""

    def test_analyze_dependencies_success(self):
        """Test successful dependency analysis with valid project."""
        project = Project(
            entities={
                "grandparent": {
                    "type": "fixed",
                    "values": [{"id": 1}],
                },
                "parent": {
                    "type": "entity",
                    "source": "grandparent",
                },
                "child": {
                    "type": "entity",
                    "source": "parent",
                    "foreign_keys": [
                        {
                            "entity": "parent",
                            "local_keys": ["parent_id"],
                            "remote_keys": ["id"],
                        }
                    ],
                },
            },
            options={},
        )

        service = DependencyService()
        graph = service.analyze_dependencies(project)

        assert not graph["has_cycles"]
        assert len(graph["nodes"]) == 3
        assert graph["topological_order"] is not None
        assert len(graph["edges"]) > 0

    def test_dependency_graph_includes_source_dependencies(self):
        """Test that entity source fields create dependency edges."""
        project = Project(
            entities={
                "base": {"type": "fixed", "values": []},
                "derived": {"type": "entity", "source": "base"},
            },
            options={},
        )

        service = DependencyService()
        graph = service.analyze_dependencies(project)

        # derived should depend on base
        derived_node = next(n for n in graph["nodes"] if n["name"] == "derived")
        assert "base" in derived_node["depends_on"]

    def test_dependency_graph_includes_foreign_key_edges(self):
        """Test that foreign keys create edges in the dependency graph."""
        project = Project(
            entities={
                "parent": {"type": "fixed", "values": []},
                "child": {
                    "type": "fixed",
                    "values": [],
                    "foreign_keys": [
                        {
                            "entity": "parent",
                            "local_keys": ["parent_id"],
                            "remote_keys": ["id"],
                        }
                    ],
                },
            },
            options={},
        )

        service = DependencyService()
        graph = service.analyze_dependencies(project)

        # FK edges have local_keys and remote_keys fields (not 'type' field)
        fk_edges = [e for e in graph["edges"] if "local_keys" in e and "remote_keys" in e]
        assert len(fk_edges) > 0
        # FK edges go from child to parent (child references parent)
        assert any(e["source"] == "child" and e["target"] == "parent" for e in fk_edges)


class TestCircularDependencyDetection:
    """Tests for circular dependency detection."""

    def test_circular_dependency_raises_error_when_requested(self):
        """Circular dependency raises CircularDependencyError when raise_on_cycle=True."""
        project = Project(
            entities={
                "A": {
                    "type": "entity",
                    "source": "B",
                },
                "B": {
                    "type": "entity",
                    "source": "C",
                },
                "C": {
                    "type": "entity",
                    "source": "A",
                },
            },
            options={},
        )

        service = DependencyService()

        # Validation mode: raise_on_cycle=True
        with pytest.raises(CircularDependencyError) as exc_info:
            service.analyze_dependencies(project, raise_on_cycle=True)

        error_dict = exc_info.value.to_dict()
        assert error_dict["error_type"] == "CircularDependencyError"
        assert "cycle" in error_dict["context"]
        # Cycle should contain the entities
        assert len(error_dict["context"]["cycle"]) >= 3
        # Cycle should have arrow formatting in message
        assert "→" in error_dict["message"]

    def test_circular_dependency_returns_graph_by_default(self):
        """Circular dependency returns graph with cycle info when raise_on_cycle=False."""
        project = Project(
            entities={
                "A": {"type": "entity", "source": "B"},
                "B": {"type": "entity", "source": "A"},
            },
            options={},
        )

        service = DependencyService()

        # Default behavior: return graph with cycle info (no raise)
        graph = service.analyze_dependencies(project, raise_on_cycle=False)

        assert graph["has_cycles"]
        assert len(graph["cycles"]) > 0
        assert graph["topological_order"] is None  # Can't sort with cycles

    def test_no_cycles_provides_topological_order(self):
        """Graph without cycles includes valid topological ordering."""
        project = Project(
            entities={
                "base": {"type": "fixed", "values": []},
                "middle": {"type": "entity", "source": "base"},
                "top": {"type": "entity", "source": "middle"},
            },
            options={},
        )

        service = DependencyService()
        graph = service.analyze_dependencies(project)

        assert not graph["has_cycles"]
        assert graph["topological_order"] is not None
        assert len(graph["topological_order"]) == 3
        # Topological order is reversed: leaves first, roots last
        # So: top, middle, base (dependencies processed from bottom up)
        order = graph["topological_order"]
        assert order.index("base") > order.index("middle")
        assert order.index("middle") > order.index("top")
