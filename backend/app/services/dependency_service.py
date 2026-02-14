"""Service for analyzing entity dependencies in projects."""

from pathlib import Path
from typing import Any, Generic, TypeVar

from loguru import logger

from backend.app.exceptions import (
    CircularDependencyError,
    DataIntegrityError,
)
from backend.app.models.project import Project
from backend.app.utils.graph import calculate_depths, find_cycles, topological_sort
from backend.app.utils.sql import extract_tables
from src.model import ShapeShiftProject

# Type variable for registry
T = TypeVar("T")


class SourceNodeExtractorRegistry(Generic[T]):
    """Registry for SourceNodeExtractor classes indexed by entity type."""

    items: dict[str, type["BaseSourceNodeExtractor"]] = {}

    @classmethod
    def register(cls, entity_types: str | list[str]):
        """Decorator to register a SourceNodeExtractor for specific entity types.

        Args:
            entity_types: Single entity type or list of entity types this extractor handles

        Example:
            @SourceNodeExtractors.register(["csv", "tsv"])
            class CsvFileSourceNodeExtractor(BaseSourceNodeExtractor):
                ...
        """

        def decorator(extractor_class: type["BaseSourceNodeExtractor"]):
            types = [entity_types] if isinstance(entity_types, str) else entity_types
            for entity_type in types:
                cls.items[entity_type] = extractor_class
            return extractor_class

        return decorator

    @classmethod
    def get(cls, entity_type: str, seen_sources: set[str]) -> "BaseSourceNodeExtractor":
        """Get extractor instance for entity type.

        Args:
            entity_type: Entity type to get extractor for
            seen_sources: Set of already-seen source node IDs

        Returns:
            Extractor instance, or NullSourceNodeExtractor if type not registered
        """
        extractor_class = cls.items.get(entity_type, NullSourceNodeExtractor)
        return extractor_class(seen_sources)


# Global registry instance
SourceNodeExtractors = SourceNodeExtractorRegistry()


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
            raise CircularDependencyError(message=f"Circular dependency detected involving {len(cycles[0])} entities", cycle=cycles[0])

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
            # Pass full entity_cfg for materialized fixed entities to access source_state
            source_nodes, source_edges = self.get_extractor(entity_cfg.get("type", "")).extract(entity_name, entity_cfg)
            self.source_nodes.extend(source_nodes)
            self.source_edges.extend(source_edges)

        return self.source_nodes, self.source_edges

    def get_extractor(self, entity_type: str) -> "BaseSourceNodeExtractor":
        """Factory method to get appropriate extractor based on entity type."""
        return SourceNodeExtractors.get(entity_type, self.seen_sources)


class BaseSourceNodeExtractor:
    """Base class for specific source node extractors."""

    def __init__(self, seen_sources: set[str]):
        self.seen_sources: set[str] = seen_sources

    def extract(self, entity_name: str, entity_cfg: dict[str, Any]):
        """Extract source nodes and edges for an entity."""
        raise NotImplementedError("Subclasses must implement extract method.")


class NullSourceNodeExtractor(BaseSourceNodeExtractor):
    """No-op extractor for unsupported entity types (default fallback)."""

    def extract(
        self, entity_name: str, entity_cfg: dict[str, Any]
    ) -> tuple[list[SourceNode], list[dict[str, Any]]]:  # pylint: disable=unused-argument
        """Do nothing for unsupported types."""
        return [], []


class BaseFileSourceNodeExtractor(BaseSourceNodeExtractor):
    """Base class for file-based source node extractors."""

    def extract(self, entity_name: str, entity_cfg: dict[str, Any]) -> tuple[list[SourceNode], list[dict[str, Any]]]:
        """Extract source nodes and edges for a file entity.

        Subclasses must implement this method.
        """
        raise NotImplementedError("Subclasses must implement extract method.")

    def _create_file_node(self, filename: str, entity_type: str) -> tuple[str, SourceNode | None]:
        """Create file node if it doesn't exist.

        Args:
            filename: Path to the file
            entity_type: Type of entity (csv, xlsx, openpyxl)

        Returns:
            Tuple of (file_node_id, SourceNode or None if already exists)
        """
        file_node_id: str = f"file:{Path(filename).stem}"

        if file_node_id in self.seen_sources:
            return file_node_id, None

        file_metadata: dict[str, Any] = {"filename": filename, "type": entity_type}
        node = SourceNode(name=file_node_id, source_type=entity_type, node_type="file", metadata=file_metadata)
        self.seen_sources.add(file_node_id)

        return file_node_id, node

    def _get_filename_from_options(self, entity_cfg: dict[str, Any]) -> str | None:
        """Extract filename from entity configuration."""
        options: dict[str, Any] = entity_cfg.get("options") or {}
        return options.get("filename")


@SourceNodeExtractors.register("csv")
class CsvFileSourceNodeExtractor(BaseFileSourceNodeExtractor):
    """Extractor for CSV file entities (simple file -> entity)."""

    def extract(self, entity_name: str, entity_cfg: dict[str, Any]) -> tuple[list[SourceNode], list[dict[str, Any]]]:
        """Extract source nodes for CSV entities.

        Creates simple file -> entity dependency chain.
        """
        filename = self._get_filename_from_options(entity_cfg)
        if not filename:
            return [], []

        entity_type: str = entity_cfg.get("type", "csv")
        source_nodes: list[SourceNode] = []
        source_edges: list[dict[str, Any]] = []

        # Create file node
        file_node_id, file_node = self._create_file_node(filename, entity_type)
        if file_node:
            source_nodes.append(file_node)

        # Edge: file -> entity
        source_edges.append(
            {
                "source": file_node_id,
                "target": entity_name,
                "label": "provides",
                "via_source_entity": False,  # CSV has no intermediate entity
            }
        )

        return source_nodes, source_edges


@SourceNodeExtractors.register(["xlsx", "openpyxl"])
class ExcelFileSourceNodeExtractor(BaseFileSourceNodeExtractor):
    """Extractor for Excel file entities (file -> sheet -> entity when sheet specified)."""

    def extract(self, entity_name: str, entity_cfg: dict[str, Any]) -> tuple[list[SourceNode], list[dict[str, Any]]]:
        """Extract source nodes for Excel entities.

        Creates file -> sheet -> entity chain when sheet_name is specified,
        otherwise creates simple file -> entity chain.
        """
        filename = self._get_filename_from_options(entity_cfg)
        if not filename:
            return [], []

        options: dict[str, Any] = entity_cfg.get("options") or {}
        sheet_name: str | None = options.get("sheet_name")
        entity_type: str = entity_cfg.get("type", "xlsx")

        source_nodes: list[SourceNode] = []
        source_edges: list[dict[str, Any]] = []

        # Create file node
        file_node_id, file_node = self._create_file_node(filename, entity_type)
        if file_node:
            source_nodes.append(file_node)

        # If sheet_name is specified, create sheet node
        if sheet_name:
            sheet_node_id: str = f"sheet:{Path(filename).stem}:{sheet_name}"
            sheet_node_created: bool = sheet_node_id not in self.seen_sources

            if sheet_node_created:
                sheet_metadata: dict[str, Any] = {
                    "filename": filename,
                    "sheet_name": sheet_name,
                    "type": entity_type,
                }
                sheet_node = SourceNode(name=sheet_node_id, source_type=f"{entity_type}_sheet", node_type="sheet", metadata=sheet_metadata)
                source_nodes.append(sheet_node)
                self.seen_sources.add(sheet_node_id)

                # Edge: file -> sheet (only when sheet node is first created)
                source_edges.append(
                    {
                        "source": file_node_id,
                        "target": sheet_node_id,
                        "label": "contains",
                        "via_source_entity": True,
                    }
                )

            # Edge: sheet -> entity (via intermediate)
            source_edges.append(
                {
                    "source": sheet_node_id,
                    "target": entity_name,
                    "label": "provides",
                    "via_source_entity": True,
                }
            )

            # Direct edge: file -> entity (for when source entities hidden)
            source_edges.append(
                {
                    "source": file_node_id,
                    "target": entity_name,
                    "label": "provides",
                    "via_source_entity": False,
                }
            )
        else:
            # No sheet_name specified: file -> entity (direct, no intermediate)
            source_edges.append(
                {
                    "source": file_node_id,
                    "target": entity_name,
                    "label": "provides",
                    "via_source_entity": False,
                }
            )

        return source_nodes, source_edges


@SourceNodeExtractors.register("fixed")
class MaterializedFixedSourceNodeExtractor(BaseSourceNodeExtractor):
    """Extractor for materialized fixed entities - shows frozen source dependencies."""

    def extract(self, entity_name: str, entity_cfg: dict[str, Any]) -> tuple[list[SourceNode], list[dict[str, Any]]]:
        """Extract source nodes from materialized.source_state.

        For materialized entities, we show the dependencies that existed
        when the entity was frozen. These are marked as 'frozen' edges
        to distinguish them from active dependencies.
        """
        # Check if entity is materialized
        materialized_data = entity_cfg.get("materialized")
        if not isinstance(materialized_data, dict):
            return [], []

        if not materialized_data.get("enabled", False):
            return [], []

        # Get saved source configuration
        source_state = materialized_data.get("source_state")
        if not isinstance(source_state, dict):
            return [], []

        # Determine original entity type and delegate to appropriate extractor
        source_type = source_state.get("type")
        if not source_type:
            return [], []

        # Get appropriate extractor for the source type from registry
        extractor = SourceNodeExtractors.get(source_type, self.seen_sources)

        # If we got the null extractor, there's nothing to extract
        if isinstance(extractor, NullSourceNodeExtractor):
            return [], []

        # Extract nodes and edges from source_state
        source_nodes, source_edges = extractor.extract(entity_name, source_state)

        # Mark all edges as frozen
        for edge in source_edges:
            edge["frozen"] = True
            # Add frozen indicator to label
            original_label = edge.get("label", "")
            edge["label"] = f"{original_label} (frozen)" if original_label else "frozen"

        return source_nodes, source_edges


@SourceNodeExtractors.register("sql")
class SqlSourceNodeExtractor(BaseSourceNodeExtractor):
    """Extractor for SQL entities - shows database and table dependencies."""

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
                source_edges.append(
                    {"source": f"source:{data_source}", "target": table_node_id, "label": "contains", "via_source_entity": True}
                )

            # Edge: table -> entity (via intermediate)
            source_edges.append({"source": table_node_id, "target": entity_name, "label": "used_in", "via_source_entity": True})

            # Direct edge: datasource -> entity (for when source entities hidden)
            source_edges.append({"source": f"source:{data_source}", "target": entity_name, "label": "provides", "via_source_entity": False})

        return source_nodes, source_edges


# Singleton instance
_dependency_service: DependencyService | None = None  # pylint: disable=invalid-name


def get_dependency_service() -> DependencyService:
    """Get singleton DependencyService instance."""
    global _dependency_service  # pylint: disable=global-statement
    if _dependency_service is None:
        _dependency_service = DependencyService()
    return _dependency_service
