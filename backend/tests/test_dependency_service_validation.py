"""Tests for DependencyService - focus on graph analysis.

NOTE: Foreign key validation is handled by specifications in src/specifications.py
and tested in tests/test_specifications.py. These tests focus on dependency graph
construction, cycle detection, and graph analysis logic.
"""

import pytest

from backend.app.exceptions import CircularDependencyError
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


class TestSourceNodeExtraction:
    """Tests for source node extraction from file and SQL entities."""

    def test_excel_entity_with_sheet_creates_file_and_sheet_nodes(self):
        """Excel entity with sheet_name creates file->sheet->entity chain."""
        project = Project(
            entities={
                "my_data": {
                    "type": "xlsx",
                    "options": {
                        "filename": "projects/data.xlsx",
                        "sheet_name": "Sheet1",
                    },
                },
            },
            options={},
        )

        service = DependencyService()
        graph = service.analyze_dependencies(project)

        # Should have 2 source nodes: file and sheet
        assert len(graph["source_nodes"]) == 2

        # Find file and sheet nodes
        file_node = next((n for n in graph["source_nodes"] if n["type"] == "file"), None)
        sheet_node = next((n for n in graph["source_nodes"] if n["type"] == "sheet"), None)

        assert file_node is not None
        assert file_node["name"] == "file:data"
        assert file_node["metadata"]["filename"] == "projects/data.xlsx"

        assert sheet_node is not None
        assert sheet_node["name"] == "sheet:data:Sheet1"
        assert sheet_node["metadata"]["sheet_name"] == "Sheet1"

        # Should have 2 source edges: file->sheet and sheet->entity
        assert len(graph["source_edges"]) == 2

        # Verify file->sheet edge
        file_to_sheet = next(
            (e for e in graph["source_edges"] if e["source"] == "file:data" and e["target"] == "sheet:data:Sheet1"), None
        )
        assert file_to_sheet is not None
        assert file_to_sheet["label"] == "contains"

        # Verify sheet->entity edge
        sheet_to_entity = next(
            (e for e in graph["source_edges"] if e["source"] == "sheet:data:Sheet1" and e["target"] == "my_data"), None
        )
        assert sheet_to_entity is not None
        assert sheet_to_entity["label"] == "provides"

    def test_excel_entity_without_sheet_creates_file_node_only(self):
        """Excel entity without sheet_name creates direct file->entity edge."""
        project = Project(
            entities={
                "my_data": {
                    "type": "xlsx",
                    "options": {
                        "filename": "projects/data.xlsx",
                    },
                },
            },
            options={},
        )

        service = DependencyService()
        graph = service.analyze_dependencies(project)

        # Should have 1 source node: file only
        assert len(graph["source_nodes"]) == 1
        file_node = graph["source_nodes"][0]
        assert file_node["type"] == "file"
        assert file_node["name"] == "file:data"

        # Should have 1 source edge: file->entity
        assert len(graph["source_edges"]) == 1
        assert graph["source_edges"][0]["source"] == "file:data"
        assert graph["source_edges"][0]["target"] == "my_data"
        assert graph["source_edges"][0]["label"] == "provides"

    def test_csv_entity_creates_file_node_only(self):
        """CSV entity creates direct file->entity edge (no sheet)."""
        project = Project(
            entities={
                "my_csv": {
                    "type": "csv",
                    "options": {
                        "filename": "projects/data.csv",
                        "sep": ",",
                    },
                },
            },
            options={},
        )

        service = DependencyService()
        graph = service.analyze_dependencies(project)

        # Should have 1 source node: file only
        assert len(graph["source_nodes"]) == 1
        file_node = graph["source_nodes"][0]
        assert file_node["type"] == "file"
        assert file_node["name"] == "file:data"

        # Should have 1 source edge: file->entity
        assert len(graph["source_edges"]) == 1
        assert graph["source_edges"][0]["source"] == "file:data"
        assert graph["source_edges"][0]["target"] == "my_csv"

    def test_multiple_entities_from_same_excel_sheet_reuse_nodes(self):
        """Multiple entities from same Excel sheet reuse file and sheet nodes."""
        project = Project(
            entities={
                "entity1": {
                    "type": "xlsx",
                    "options": {
                        "filename": "projects/data.xlsx",
                        "sheet_name": "Sheet1",
                    },
                },
                "entity2": {
                    "type": "xlsx",
                    "options": {
                        "filename": "projects/data.xlsx",
                        "sheet_name": "Sheet1",
                    },
                },
            },
            options={},
        )

        service = DependencyService()
        graph = service.analyze_dependencies(project)

        # Should have 2 source nodes (file and sheet), not 4
        assert len(graph["source_nodes"]) == 2

        # Should have 3 edges: file->sheet, sheet->entity1, sheet->entity2
        assert len(graph["source_edges"]) == 3

        # Verify both entities share the same sheet
        entity1_edge = next((e for e in graph["source_edges"] if e["target"] == "entity1"), None)
        entity2_edge = next((e for e in graph["source_edges"] if e["target"] == "entity2"), None)
        assert entity1_edge["source"] == entity2_edge["source"] == "sheet:data:Sheet1"

    def test_multiple_sheets_from_same_file_create_separate_sheet_nodes(self):
        """Multiple entities from different sheets of same file create separate sheet nodes."""
        project = Project(
            entities={
                "sheet1_data": {
                    "type": "openpyxl",
                    "options": {
                        "filename": "projects/data.xlsx",
                        "sheet_name": "Sheet1",
                    },
                },
                "sheet2_data": {
                    "type": "openpyxl",
                    "options": {
                        "filename": "projects/data.xlsx",
                        "sheet_name": "Sheet2",
                    },
                },
            },
            options={},
        )

        service = DependencyService()
        graph = service.analyze_dependencies(project)

        # Should have 3 source nodes: 1 file + 2 sheets
        assert len(graph["source_nodes"]) == 3

        file_nodes = [n for n in graph["source_nodes"] if n["type"] == "file"]
        sheet_nodes = [n for n in graph["source_nodes"] if n["type"] == "sheet"]

        assert len(file_nodes) == 1
        assert len(sheet_nodes) == 2
        assert file_nodes[0]["name"] == "file:data"

        # Verify sheet names
        sheet_names = sorted([n["name"] for n in sheet_nodes])
        assert sheet_names == ["sheet:data:Sheet1", "sheet:data:Sheet2"]

        # Should have 4 edges: file->sheet1, file->sheet2, sheet1->entity1, sheet2->entity2
        assert len(graph["source_edges"]) == 4


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
