import hashlib
import time
from dataclasses import dataclass

import pandas as pd
from loguru import logger

from backend.app.core.state_manager import get_app_state
from backend.app.mappers.project_mapper import ProjectMapper
from backend.app.models.project import Project
from backend.app.services.project_service import ProjectService
from src.model import ShapeShiftProject, TableConfig


@dataclass
class CacheMetadata:
    """Metadata for cached entity DataFrame."""

    timestamp: float
    project_name: str
    entity_name: str
    project_version: int
    entity_hash: str  # Hash of entity configuration


class ShapeShiftCache:
    """Cache for ShapeShifter results with individual entity storage.

    Caches individual DataFrames per entity, enabling better cache efficiency
    and granular invalidation. Dependencies are stored separately and reused
    across multiple entities.

    Uses 3-tier cache validation:
    1. TTL (time-to-live) - Expire after fixed duration
    2. Project version - Invalidate on configuration file changes
    3. Entity hash - Invalidate on entity-specific configuration changes
    """

    def __init__(self, ttl_seconds: int = 300):
        """Initialize cache with TTL in seconds (default 5 minutes)."""
        # Store individual DataFrames: key -> DataFrame
        self._dataframes: dict[str, pd.DataFrame] = {}
        # Store metadata: key -> CacheMetadata
        self._metadata: dict[str, CacheMetadata] = {}
        self._ttl: int = ttl_seconds

    def _generate_key(self, project_name: str, entity_name: str) -> str:
        """Generate cache key from config and entity name."""
        key_str = f"{project_name}:{entity_name}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def get_dataframe(
        self,
        project_name: str,
        entity_name: str,
        project_version: int | None = None,
        entity_config: TableConfig | None = None,
    ) -> pd.DataFrame | None:
        """Get cached DataFrame for entity with 3-tier validation.

        Validation order:
        1. TTL - Check if cache entry has expired
        2. Project version - Validate against ApplicationState version
        3. Entity hash - Validate against entity configuration hash

        Args:
            project_name: Configuration name
            entity_name: Entity name
            config_version: Optional config version for validation (from ApplicationState)
            entity_config: Optional entity configuration for hash validation

        Returns:
            DataFrame if cached and valid, None otherwise
        """
        key = self._generate_key(project_name, entity_name)
        if key not in self._dataframes or key not in self._metadata:
            return None

        metadata = self._metadata[key]

        # Tier 1: Check TTL
        if time.time() - metadata.timestamp >= self._ttl:
            del self._dataframes[key]
            del self._metadata[key]
            logger.debug(f"Cache expired for {entity_name} (TTL)")
            return None

        # Tier 2: Check project version if provided
        if project_version is not None and metadata.project_version != project_version:
            del self._dataframes[key]
            del self._metadata[key]
            logger.debug(f"Cache invalidated for {entity_name} (version mismatch: {metadata.project_version} != {project_version})")
            return None

        # Tier 3: Check entity hash if entity_config provided
        if entity_config is not None:
            current_hash = entity_config.hash()
            if metadata.entity_hash != current_hash:
                del self._dataframes[key]
                del self._metadata[key]
                logger.debug(
                    f"Cache invalidated for {entity_name} (entity config changed: {metadata.entity_hash[:8]} != {current_hash[:8]})"
                )
                return None

        logger.debug(f"Cache hit for {entity_name} (valid: TTL + version + hash)")
        return self._dataframes[key].copy()  # Return copy to prevent modifications

    def set_dataframe(
        self,
        project_name: str,
        entity_name: str,
        dataframe: pd.DataFrame,
        project_version: int = 0,
        entity_config: TableConfig | None = None,
    ) -> None:
        """Cache DataFrame for entity with metadata including entity hash.

        Args:
            project_name: Configuration name
            entity_name: Entity name
            dataframe: DataFrame to cache
            project_version: Project version from ApplicationState
            entity_config: Entity configuration for hash computation
        """
        key: str = self._generate_key(project_name, entity_name)
        self._dataframes[key] = dataframe.copy()  # Store copy to prevent external modifications

        # Compute entity hash if config provided, otherwise use empty hash
        entity_hash = entity_config.hash() if entity_config else ""

        self._metadata[key] = CacheMetadata(
            timestamp=time.time(),
            project_name=project_name,
            entity_name=entity_name,
            project_version=project_version,
            entity_hash=entity_hash,
        )
        logger.debug(f"Cached DataFrame for {entity_name} (version {project_version}, hash {entity_hash[:8]}, {len(dataframe)} rows)")

    def set_table_store(
        self,
        project_name: str,
        table_store: dict[str, pd.DataFrame],
        target_entity: str,
        project_version: int = 0,
        entity_configs: dict[str, TableConfig] | None = None,
    ) -> None:
        """Cache all entities from table_store individually with entity hashes.

        Args:
            project_name: Configuration name
            table_store: Dict of entity_name -> DataFrame
            target_entity: Target entity name (for logging)
            project_version: Project version from ApplicationState
            entity_configs: Optional dict of entity_name -> TableConfig for hash computation
        """
        for entity_name, df in table_store.items():
            entity_config: TableConfig | None = entity_configs.get(entity_name) if entity_configs else None
            self.set_dataframe(project_name, entity_name, df, project_version, entity_config)
        logger.debug(f"Cached {len(table_store)} entities from {target_entity} execution")

    def get_dependencies(
        self,
        project_name: str,
        entity_config: TableConfig,
        project_version: int | None = None,
        shapeshift_config: ShapeShiftProject | None = None,
    ) -> dict[str, pd.DataFrame]:
        """Gather all cached dependencies for an entity with hash validation.

        Args:
            project_name: Configuration name
            entity_config: Target entity configuration
            project_version: Optional project version for validation
            shapeshift_config: Optional ShapeShiftProject for dependency hash validation

        Returns:
            Dict of cached entity DataFrames
        """
        cached_deps: dict[str, pd.DataFrame] = {}
        for dep_name in entity_config.depends_on:
            # Get dependency config for hash validation if available
            dep_config: TableConfig | None = shapeshift_config.get_table(dep_name) if shapeshift_config else None
            cached_df: pd.DataFrame | None = self.get_dataframe(project_name, dep_name, project_version, dep_config)
            if cached_df is not None:
                cached_deps[dep_name] = cached_df

        if cached_deps:
            logger.debug(f"Found {len(cached_deps)} cached dependencies for {entity_config.entity_name}: {list(cached_deps.keys())}")

        return cached_deps

    @dataclass
    class CacheCheckResult:
        found: bool
        data: pd.DataFrame | None
        dependencies: dict[str, pd.DataFrame]

    def fetch_cached_entity_data(
        self, project_name: str, entity_name: str, project_version: int, entity_config: TableConfig, shapeshift_config: ShapeShiftProject
    ) -> CacheCheckResult:
        data: pd.DataFrame | None = self.get_dataframe(project_name, entity_name, project_version, entity_config)
        found: bool = data is not None
        dependencies: dict[str, pd.DataFrame] = self.get_dependencies(project_name, entity_config, project_version, shapeshift_config)
        return self.CacheCheckResult(found=found, data=data, dependencies=dependencies)

    def get_available_entities(self, project_name: str) -> set[str]:
        """Get all entity names available in cache for a configuration."""
        available = set()
        current_time = time.time()
        for key, metadata in list(self._metadata.items()):
            if metadata.project_name == project_name and (current_time - metadata.timestamp) < self._ttl:
                if key in self._dataframes:
                    available.add(metadata.entity_name)
        return available

    def invalidate(self, project_name: str, entity_name: str | None = None) -> None:
        """Invalidate cache entries for a configuration or specific entity.

        Args:
            project_name: Configuration name
            entity_name: Optional entity name to invalidate specific entity,
                        None to invalidate all entities for config
        """
        keys_to_remove = []
        for key, metadata in list(self._metadata.items()):
            if metadata.project_name == project_name:
                if entity_name is None or metadata.entity_name == entity_name:
                    keys_to_remove.append(key)

        for key in keys_to_remove:
            if key in self._dataframes:
                del self._dataframes[key]
            if key in self._metadata:
                del self._metadata[key]
        logger.debug(f"Invalidated {len(keys_to_remove)} cache entries for {project_name}:{entity_name or 'all'}")


class ShapeShiftProjectCache:
    """Cache for ShapeShiftProject instances with version tracking."""

    def __init__(self, project_service: ProjectService):
        """Initialize ShapeShiftProject cache."""
        self.project_service: ProjectService = project_service
        self._cache: dict[str, ShapeShiftProject] = {}
        self._versions: dict[str, int] = {}

    async def get_project(self, project_name: str) -> ShapeShiftProject:
        """
        Get ShapeShiftProject with caching and version tracking.

        Uses ApplicationState version tracking to invalidate cache when
        configuration is edited.

        Args:
            project_name: Configuration name

        Returns:
            ShapeShiftProject instance
        """
        # Get current version from ApplicationState
        try:
            current_version: int = get_app_state().get_version(project_name)
            cached_version: int = self._versions.get(project_name, -1)

            # Check if cached version is still valid
            if project_name in self._cache and cached_version == current_version:
                logger.debug(f"ShapeShiftProject cache hit for '{project_name}' (version {current_version})")
                return self._cache[project_name]

            # Version mismatch or no cache - reload
            logger.debug(
                f"ShapeShiftProject cache miss/invalid for '{project_name}' (cached: {cached_version}, current: {current_version})"
            )
            api_project: Project | None = get_app_state().get_project(project_name)

            if api_project:
                # Convert from active API Project
                shapeshift: ShapeShiftProject = ProjectMapper.to_core(api_project)
                self._cache[project_name] = shapeshift
                self._versions[project_name] = current_version
                logger.debug(f"Loaded ShapeShiftProject from ApplicationState for '{project_name}'")
                return shapeshift

        except RuntimeError:
            # ApplicationState not initialized
            pass

        # Fallback: Load from disk
        logger.debug(f"Loading ShapeShiftProject from disk for '{project_name}'")
        api_project = self.project_service.load_project(project_name)
        shapeshift: ShapeShiftProject = ProjectMapper.to_core(api_project)

        # Cache it (version 0 since not in active editing)
        self._cache[project_name] = shapeshift
        self._versions[project_name] = 0

        return shapeshift
