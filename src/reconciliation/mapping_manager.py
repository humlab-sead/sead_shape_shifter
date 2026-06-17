"""Mapping sidecar file I/O and in-memory cache (`<project>-mapping.yml`).

``MappingManager`` is the single authority for reading, writing, and
caching the mapping sidecar file.  It provides convenience methods that
delegate to ``MappingCatalog`` for link-level CRUD and adds atomic
file writes plus an in-memory cache keyed by project path.
"""

from __future__ import annotations

import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

import yaml
from loguru import logger

from src.reconciliation.mapping_model import EntityMapping, Link, LinkSource, MappingCatalog, Metadata

if TYPE_CHECKING:
    pass


class MappingManager:
    """CRUD operations and file I/O for ``<project>-mapping.yml`` sidecar files.

    Maintains an in-memory cache of loaded catalogs so that repeated reads
    within a single process lifetime do not re-parse the YAML file.  The
    cache is invalidated on save or can be cleared explicitly.

    Typical usage::

        manager = MappingManager()
        catalog = manager.load("/path/to/project/shapeshifter.yml")
        link = Link(source=LinkSource.MANUAL, created_by="user@example.com", target_id=42)
        manager.set_link(catalog, "taxon", "PLANT001", link)
        manager.save(catalog, "/path/to/project/shapeshifter.yml")
    """

    def __init__(self) -> None:
        self._cache: dict[str, MappingCatalog] = {}

    # ------------------------------------------------------------------
    # Path resolution
    # ------------------------------------------------------------------

    @staticmethod
    def _sidecar_path(project_path: str | Path) -> Path:
        """Resolve the sidecar file path from a project path.

        If *project_path* points to a ``shapeshifter.yml`` (or any regular
        file), the parent directory is used.  The sidecar file is always
        ``<dirname>-mapping.yml``.

        Args:
            project_path: Either a project directory or the path to the
                project's ``shapeshifter.yml`` file.

        Returns:
            The absolute path to ``<project>-mapping.yml``.
        """
        pp = Path(project_path).resolve()
        if pp.is_file():
            pp = pp.parent
        return pp / f"{pp.name}-mapping.yml"

    @staticmethod
    def _cache_key(project_path: str | Path) -> str:
        """Return a stable cache key from a project path."""
        return str(MappingManager._sidecar_path(project_path).resolve())

    # ------------------------------------------------------------------
    # Load / Save
    # ------------------------------------------------------------------

    def load(self, project_path: str | Path) -> MappingCatalog:
        """Load a mapping catalog from the sidecar file.

        Returns an empty ``MappingCatalog`` when no sidecar file exists yet.
        Results are cached; subsequent calls for the same *project_path*
        return the cached instance without re-reading the file.

        Args:
            project_path: Project directory or ``shapeshifter.yml`` path.

        Returns:
            A ``MappingCatalog`` instance (never ``None``).
        """
        cache_key: str = self._cache_key(project_path)

        if cache_key in self._cache:
            logger.debug(f"Mapping catalog cache hit for {cache_key}")
            return self._cache[cache_key]

        sidecar: Path = self._sidecar_path(project_path)

        if not sidecar.exists():
            logger.info(f"No mapping sidecar found at {sidecar}; returning empty catalog")
            project_name: str = sidecar.parent.name
            now: datetime = datetime.now(timezone.utc)
            catalog = MappingCatalog(metadata=Metadata(project=project_name, created_at=now, updated_at=now))
            self._cache[cache_key] = catalog
            return catalog

        logger.debug(f"Loading mapping sidecar from {sidecar}")
        with open(sidecar, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        catalog: MappingCatalog = MappingCatalog.model_validate(data)
        self._cache[cache_key] = catalog
        return catalog

    def save(self, catalog: MappingCatalog, project_path: str | Path) -> None:
        """Persist *catalog* to the sidecar file atomically.

        Writes to a temporary file in the same directory, then renames it
        over the target to avoid partial writes.  Invalidates the in-memory
        cache entry for *project_path* after a successful write.

        Args:
            catalog: The catalog to persist.
            project_path: Project directory or ``shapeshifter.yml`` path.
        """
        sidecar: Path = self._sidecar_path(project_path)
        cache_key: str = self._cache_key(project_path)

        # Refresh updated_at before serialising.
        catalog.metadata.updated_at = datetime.now(timezone.utc)

        sidecar.parent.mkdir(parents=True, exist_ok=True)

        # Write to a temp file in the same directory, then atomic rename.
        with tempfile.NamedTemporaryFile(
            mode="w",
            dir=sidecar.parent,
            prefix=".tmp-mapping-",
            suffix=".yml",
            delete=False,
            encoding="utf-8",
        ) as tmp:
            yaml.dump(
                catalog.model_dump(mode="json", exclude_none=True),
                tmp,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
            )
            tmp_path: str = tmp.name

        try:
            os.replace(tmp_path, sidecar)
        except Exception:
            os.unlink(tmp_path, missing_ok=True)  # type: ignore[attr-defined]
            raise

        # Update cache with the now-persisted catalog.
        self._cache[cache_key] = catalog
        logger.info(f"Saved mapping sidecar to {sidecar}")

    # ------------------------------------------------------------------
    # Cache management
    # ------------------------------------------------------------------

    def invalidate(self, project_path: str | Path) -> None:
        """Remove the cached catalog for *project_path*.

        The next call to :meth:`load` will re-read from disk.
        """
        cache_key = self._cache_key(project_path)
        self._cache.pop(cache_key, None)
        logger.debug(f"Invalidated mapping cache for {cache_key}")

    def clear_cache(self) -> None:
        """Clear all cached catalogs."""
        self._cache.clear()
        logger.debug("Cleared entire mapping cache")

    # ------------------------------------------------------------------
    # Entity-level helpers
    # ------------------------------------------------------------------

    @staticmethod
    def get_entity(catalog: MappingCatalog, entity_name: str) -> EntityMapping | None:
        """Return the ``EntityMapping`` for *entity_name*, or ``None``."""
        return catalog.entities.get(entity_name)

    # ------------------------------------------------------------------
    # Link-level CRUD (convenience over MappingCatalog methods)
    # ------------------------------------------------------------------

    @staticmethod
    def get_link(catalog: MappingCatalog, entity_name: str, local_key_value: str) -> Link | None:
        """Return the link for *entity_name* / *local_key_value*, or ``None``."""
        return catalog.get_link(entity_name, local_key_value)

    @staticmethod
    def set_link(catalog: MappingCatalog, entity_name: str, local_key_value: str, link: Link) -> None:
        """Create or replace a link in *catalog*.

        Raises:
            KeyError: If *entity_name* is not present in the catalog.
        """
        catalog.set_link(entity_name, local_key_value, link)

    @staticmethod
    def delete_link(catalog: MappingCatalog, entity_name: str, local_key_value: str) -> bool:
        """Remove a link for *entity_name* / *local_key_value*.

        Returns:
            ``True`` if the link existed and was removed; ``False`` otherwise.
        """
        entity: EntityMapping | None = catalog.entities.get(entity_name)
        if entity is None or local_key_value not in entity.links:
            return False
        del entity.links[local_key_value]
        catalog.metadata.updated_at = datetime.now(timezone.utc)
        return True

    # ------------------------------------------------------------------
    # Bulk operations
    # ------------------------------------------------------------------

    @staticmethod
    def replace_entity_manual_links(catalog: MappingCatalog, entity_name: str, links: dict[str, Link]) -> int:
        """Replace all ``source="manual"`` links for *entity_name* with *links*.

        Existing links with ``source != "manual"`` (reconciliation, import)
        are preserved.  The *links* dict is merged into the entity's links.

        Args:
            catalog: The mapping catalog to modify in-place.
            entity_name: The entity whose manual links should be replaced.
            links: New manual links keyed by local-key value.

        Returns:
            The number of manual links after replacement.

        Raises:
            KeyError: If *entity_name* is not present in the catalog.
        """
        if entity_name not in catalog.entities:
            raise KeyError(f"Entity '{entity_name}' not found in mapping catalog")

        entity: EntityMapping = catalog.entities[entity_name]

        # Preserve non-manual links.
        preserved: dict[str, Link] = {k: v for k, v in entity.links.items() if v.source != LinkSource.MANUAL}

        # Merge in the new manual links.
        preserved.update(links)
        entity.links = preserved
        catalog.metadata.updated_at = datetime.now(timezone.utc)

        return sum(1 for v in entity.links.values() if v.source == LinkSource.MANUAL)
