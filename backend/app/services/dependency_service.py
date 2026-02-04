"""Service for analyzing entity dependencies in projects."""

from pathlib import Path
from typing import Any

from loguru import logger

from backend.app.exceptions import (
    CircularDependencyError,
    DataIntegrityError,
)
from backend.app.models.project import Project
from backend.app.utils.graph import calculate_depths, find_cycles, topological_sort
from backend.app.utils.sql import extract_tables
from src.model import ShapeShiftProject


class DependencyNode(dict):
    """Dependency graph node representation."""

    def __init__(
        self,
        name: str,
        depends_on: list[str],
        depth: int = 0,
        entity_type: str | None = None,
        materialized: bool = False,
    ):
        """Initialize dependency node."""
        super().__init__(name=name, depends_on=depends_on, depth=depth, type=entity_type, materialized=materialized)


class SourceNode(dict):
    """Source node representation (data sources, tables, files)."""

    def __init__(
        self,
        name: str,
        source_type: str,
        node_type: str = "datasource",
        metadata: dict[str, Any] | None = None,
    ):
        """Initialize source node.

        Args:
            name: Unique identifier for the source
            source_type: Type of source (e.g., "postgresql", "csv", "file")
            node_type: Node category ("datasource", "table", "file")
            metadata: Additional metadata (datasource, table name, etc.)
        """
        super().__init__(name=name, source_type=source_type, type=node_type, metadata=metadata or {})


class DependencyGraph(dict):
    """Dependency graph representation."""

    def __init__(
        self,
        nodes: list[DependencyNode],
        edges: list[dict[str, Any]],
        has_cycles: bool,
        cycles: list[list[str]],
        topological_order: list[str] | None,
        source_nodes: list[SourceNode] | None = None,
        source_edges: list[dict[str, Any]] | None = None,
    ):
        """Initialize dependency graph."""
        super().__init__(
            nodes=nodes,
            edges=edges,
            has_cycles=has_cycles,
            cycles=cycles,
            topological_order=topological_order,
            source_nodes=source_nodes or [],
            source_edges=source_edges or [],
        )


class DependencyService:
    """Service for analyzing entity dependencies."""

    def analyze_dependencies(self, api_project: Project, raise_on_cycle: bool = False) -> DependencyGraph:
        """
         Analyze dependencies in project.
        Args:
             api_project: Project to analyze
             raise_on_cycle: If True, raise CircularDependencyError when cycles detected
                           If False, return graph with cycle information (default)

         Returns:
             Dependency graph with nodes, edges, and cycle information

         Raises:
             CircularDependencyError: If raise_on_cycle=True and cycles detected
             DataIntegrityError: If project initialization fails
        """
        try:
            project = ShapeShiftProject(
                cfg={"entities": api_project.entities, "options": api_project.options}, filename=api_project.filename or ""
            )
        except Exception as e:
            raise DataIntegrityError(message=f"Failed to initialize project: {e}") from e

        dependency_map: dict[str, list[str]] = {}
        for entity_name in api_project.entities:
            deps = list(project.get_table(entity_name).depends_on or [])

            # If entity type is "entity", add source as a dependency
            entity_config = api_project.entities.get(entity_name, {})
            if entity_config.get("type") == "entity":
                source = entity_config.get("source")
                if source and source not in deps:
                    deps.append(source)

            dependency_map[entity_name] = deps

        # Detect cycles
        cycles: list[list[str]] = find_cycles(dependency_map)
        has_cycles: bool = len(cycles) > 0

        if raise_on_cycle and has_cycles and cycles:
            raise CircularDependencyError(
                message=f"Circular dependency detected involving {len(cycles[0])} entities",
                cycle=cycles[0]
            )

        # Calculate topological order if no cycles
        topological_order: None | list[str] = None if has_cycles else topological_sort(dependency_map)

        # Calculate depths for visualization
        depths: dict[str, int] = calculate_depths(dependency_map, topological_order)

        allowed_entity_types = {"entity", "sql", "fixed", "csv", "xlsx", "openpyxl"}
        nodes: list[DependencyNode] = []
        for name, deps in dependency_map.items():
            entity_config = api_project.entities.get(name, {})
            entity_type = entity_config.get("type")
            normalized_type = entity_type if entity_type in allowed_entity_types else None

            # Check if entity is materialized
            is_materialized = False
            if hasattr(entity_config, "get"):
                materialized_data = entity_config.get("materialized")
                if isinstance(materialized_data, dict):
                    is_materialized = materialized_data.get("enabled", False)

            nodes.append(
                DependencyNode(
                    name=name,
                    depends_on=deps,
                    depth=depths.get(name, 0),
                    entity_type=normalized_type,
                    materialized=is_materialized,
                )
            )

        # Build edges with foreign key information
        edges: list[dict[str, Any]] = []

        # Add dependency edges from depends_on relationships
        for entity_name, deps in dependency_map.items():
            for dep in deps:
                edges.append(
                    {
                        "source": dep,
                        "target": entity_name,
                        "type": "provides",
                        "label": "provides",
                    }
                )

        # Add foreign key edges
        for entity_name in api_project.entities:
            entity_config = api_project.entities[entity_name]
            foreign_keys = entity_config.get("foreign_keys") or []

            for fk in foreign_keys:
                target_entity = fk.get("entity")
                if target_entity:
                    local_keys = fk.get("local_keys", [])
                    remote_keys = fk.get("remote_keys", [])

                    # Format keys for display
                    if isinstance(local_keys, list) and isinstance(remote_keys, list):
                        keys_label = " → ".join(
                            [", ".join(local_keys) if local_keys else "", ", ".join(remote_keys) if remote_keys else ""]
                        )
                    else:
                        keys_label = f"{local_keys} → {remote_keys}"

                    edges.append(
                        {
                            "source": entity_name,
                            "target": target_entity,
                            "local_keys": local_keys,
                            "remote_keys": remote_keys,
                            "label": keys_label,
                        }
                    )

        logger.debug(f"Analyzed dependencies: {len(nodes)} nodes, {len(edges)} edges, " f"cycles: {has_cycles}")

        # Extract source nodes and edges
        source_nodes, source_edges = SourceNodeService().extract(api_project)

        return DependencyGraph(
            nodes=nodes,
            edges=edges,
            has_cycles=has_cycles,
            cycles=cycles,
            topological_order=topological_order,
            source_nodes=source_nodes,
            source_edges=source_edges,
        )

    def check_circular_dependencies(self, project: Project) -> dict[str, Any]:
        """
        Check for circular dependencies in project.

        Args:
            config: Project to check

        Returns:
            Dictionary with has_cycles flag and list of cycles
        """
        graph: DependencyGraph = self.analyze_dependencies(project)

        return {
            "has_cycles": graph["has_cycles"],
            "cycles": graph["cycles"],
            "cycle_count": len(graph["cycles"]),
        }


class SourceNodeService:
    """Base class for source node extractors."""

    def __init__(self):
        self.source_nodes: list[SourceNode] = []
        self.source_edges: list[dict[str, Any]] = []
        self.seen_sources: set[str] = set()

    def extract(self, api_project: Project) -> tuple[list[SourceNode], list[dict[str, Any]]]:
        """Extract source nodes and edges from project entities."""

        for entity_name, entity_cfg in api_project.entities.items():
            source_nodes, source_edges = self.get_extractor(entity_cfg.get("type", "")).extract(entity_name, entity_cfg)
            self.source_nodes.extend(source_nodes)
            self.source_edges.extend(source_edges)

        return self.source_nodes, self.source_edges

    def get_extractor(self, entity_type: str) -> "BaseSourceNodeExtractor":
        """Factory method to get appropriate extractor based on entity type."""
        if entity_type == "sql":
            return SqlSourceNodeExtractor(self.seen_sources)
        if entity_type in ("csv", "xlsx", "openpyxl"):
            return FileSourceNodeExtractor(self.seen_sources)
        return NullSourceNodeExtractor(self.seen_sources)


class BaseSourceNodeExtractor:
    """Base class for specific source node extractors."""

    def __init__(self, seen_sources: set[str]):
        self.seen_sources: set[str] = seen_sources

    def extract(self, entity_name: str, entity_cfg: dict[str, Any]):
        """Extract source nodes and edges for an entity."""
        raise NotImplementedError("Subclasses must implement extract method.")


class NullSourceNodeExtractor(BaseSourceNodeExtractor):
    """No-op extractor for unsupported entity types."""

    def extract(
        self, entity_name: str, entity_cfg: dict[str, Any]
    ) -> tuple[list[SourceNode], list[dict[str, Any]]]:  # pylint: disable=unused-argument
        """Do nothing for unsupported types."""
        return [], []


class FileSourceNodeExtractor(BaseSourceNodeExtractor):
    """Utility class for extracting file source nodes."""

    def extract(self, entity_name: str, entity_cfg: dict[str, Any]) -> tuple[list[SourceNode], list[dict[str, Any]]]:
        options: dict[str, Any] = entity_cfg.get("options") or {}
        filename: str | None = options.get("filename")
        entity_type: str = entity_cfg.get("type", "csv")

        if not filename:
            return [], []

        source_nodes: list[SourceNode] = []
        source_edges: list[dict[str, Any]] = []

        source_node_id: str = f"file:{Path(filename).stem}"
        if source_node_id not in self.seen_sources:
            metadata: dict[str, Any] = {"filename": filename, "type": entity_type}
            sheet_name: str | None = options.get("sheet_name")  # For Excel files
            if sheet_name:
                metadata["sheet_name"] = sheet_name

            source_nodes.append(SourceNode(name=source_node_id, source_type=entity_type, node_type="file", metadata=metadata))
            self.seen_sources.add(source_node_id)

        # Edge: file -> entity
        source_edges.append(
            {
                "source": source_node_id,
                "target": entity_name,
                "label": "provides",
            }
        )
        return source_nodes, source_edges


class SqlSourceNodeExtractor(BaseSourceNodeExtractor):
    """Utility class for extracting SQL source nodes."""

    def extract(self, entity_name: str, entity_cfg: dict[str, Any]) -> tuple[list[SourceNode], list[dict[str, Any]]]:
        data_source: str | None = entity_cfg.get("data_source")
        sql_query: str | None = entity_cfg.get("query")

        source_nodes: list[SourceNode] = []
        source_edges: list[dict[str, Any]] = []

        # Add data source node
        if data_source and data_source not in self.seen_sources:
            source_node_id = f"source:{data_source}"
            source_nodes.append(
                SourceNode(name=source_node_id, source_type="database", node_type="datasource", metadata={"datasource": data_source})
            )
            self.seen_sources.add(data_source)

            # Extract and add table nodes
        if not (sql_query and data_source):
            return source_nodes, source_edges

        tables: list[str] = extract_tables(sql_query)
        for table in tables:
            table_node_id: str = f"table:{data_source}:{table}"
            # Only add if not already added
            if not any(node["name"] == table_node_id for node in source_nodes):
                source_nodes.append(
                    SourceNode(
                        name=table_node_id,
                        source_type="database_table",
                        node_type="table",
                        metadata={"datasource": data_source, "table": table},
                    )
                )

                # Edge: datasource -> table
                source_edges.append({"source": f"source:{data_source}", "target": table_node_id, "label": "contains"})

                # Edge: table -> entity
            source_edges.append({"source": table_node_id, "target": entity_name, "label": "used_in"})

        return source_nodes, source_edges


# Singleton instance
_dependency_service: DependencyService | None = None  # pylint: disable=invalid-name


def get_dependency_service() -> DependencyService:
    """Get singleton DependencyService instance."""
    global _dependency_service  # pylint: disable=global-statement
    if _dependency_service is None:
        _dependency_service = DependencyService()
    return _dependency_service
