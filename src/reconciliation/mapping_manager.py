"""Mapping sidecar file I/O and in-memory cache (`<project>-mapping.yml`).

``MappingManager`` is the single authority for reading, writing, and
caching the mapping sidecar file.  It provides convenience methods that
delegate to ``MappingCatalog`` for link-level CRUD and adds atomic
file writes plus an in-memory cache keyed by project path.
"""

from __future__ import annotations

import hashlib
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

import yaml
from loguru import logger

from src.reconciliation.mapping_model import EntityMapping, Link, LinkSource, MappingCatalog, Metadata

MISSING_CONTENT_VERSION = "missing"


@dataclass(frozen=True)
class MappingSnapshot:
    """A catalog parsed from one exact sidecar file version."""

    catalog: MappingCatalog
    content_version: str


class MappingVersionConflictError(RuntimeError):
    """Raised when the sidecar changed after a writer read it."""


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
        self._cache_versions: dict[str, str] = {}

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

    @staticmethod
    def _content_version(content: bytes | None) -> str:
        """Return the content hash, or a distinct token for a missing file."""
        if content is None:
            return MISSING_CONTENT_VERSION
        return hashlib.sha256(content).hexdigest()

    @staticmethod
    def _read_content(sidecar: Path) -> bytes | None:
        """Read sidecar bytes, returning ``None`` when the file is absent."""
        try:
            return sidecar.read_bytes()
        except FileNotFoundError:
            return None

    @staticmethod
    def _parse_catalog(sidecar: Path, content: bytes | None) -> MappingCatalog:
        """Parse one disk snapshot into a new catalog instance."""
        if content is None:
            project_name = sidecar.parent.name
            now = datetime.now(timezone.utc)
            return MappingCatalog(metadata=Metadata(project=project_name, created_at=now, updated_at=now))

        data = yaml.safe_load(content.decode("utf-8")) or {}
        return MappingCatalog.model_validate(data)

    def load_snapshot(self, project_path: str | Path) -> MappingSnapshot:
        """Read and parse the current sidecar without consulting the catalog cache."""
        sidecar = self._sidecar_path(project_path)
        content = self._read_content(sidecar)
        catalog = self._parse_catalog(sidecar, content)
        return MappingSnapshot(catalog=catalog, content_version=self._content_version(content))

    def load(self, project_path: str | Path) -> MappingCatalog:
        """Load a mapping catalog from the sidecar file.

        Returns an empty ``MappingCatalog`` when no sidecar file exists yet.
        Cached catalogs are reused only while the exact sidecar bytes are unchanged.

        Args:
            project_path: Project directory or ``shapeshifter.yml`` path.

        Returns:
            A ``MappingCatalog`` instance (never ``None``).
        """
        cache_key: str = self._cache_key(project_path)
        sidecar = self._sidecar_path(project_path)
        content = self._read_content(sidecar)
        content_version = self._content_version(content)
        if cache_key in self._cache and self._cache_versions.get(cache_key) == content_version:
            logger.debug(f"Mapping catalog cache hit for {cache_key}")
            return self._cache[cache_key]

        if content_version == MISSING_CONTENT_VERSION:
            logger.info(f"No mapping sidecar found at {sidecar}; returning empty catalog")
        catalog = self._parse_catalog(sidecar, content)
        self._cache[cache_key] = catalog
        self._cache_versions[cache_key] = content_version
        return catalog

    def save(
        self,
        catalog: MappingCatalog,
        project_path: str | Path,
        expected_version: str | None = None,
    ) -> str:
        """Persist *catalog* to the sidecar file atomically.

        Writes to a temporary file in the same directory, then renames it
        over the target to avoid partial writes. When *expected_version* is
        supplied, the write fails if the exact disk bytes have changed.

        Args:
            catalog: The catalog to persist.
            project_path: Project directory or ``shapeshifter.yml`` path.

        Returns:
            The SHA-256 content version of the written sidecar.

        Raises:
            MappingVersionConflictError: If the current sidecar version differs
                from *expected_version*.
        """
        sidecar: Path = self._sidecar_path(project_path)
        cache_key: str = self._cache_key(project_path)

        updated_at = datetime.now(timezone.utc)
        catalog_to_save = catalog.model_copy(deep=True)
        catalog_to_save.metadata.updated_at = updated_at
        content = yaml.dump(
            catalog_to_save.model_dump(mode="json", exclude_none=True),
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        ).encode("utf-8")
        written_version = self._content_version(content)

        sidecar.parent.mkdir(parents=True, exist_ok=True)

        tmp_path: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=sidecar.parent,
                prefix=".tmp-mapping-",
                suffix=".yml",
                delete=False,
            ) as tmp:
                tmp.write(content)
                tmp_path = tmp.name

            if expected_version is not None:
                try:
                    current_content = sidecar.read_bytes()
                except FileNotFoundError:
                    current_content = None
                current_version = self._content_version(current_content)
                if current_version != expected_version:
                    raise MappingVersionConflictError(
                        f"Mapping sidecar changed: expected version '{expected_version}', current '{current_version}'"
                    )

            os.replace(tmp_path, sidecar)
        except Exception:
            if tmp_path is not None:
                Path(tmp_path).unlink(missing_ok=True)
            raise

        catalog.metadata.updated_at = updated_at
        self._cache[cache_key] = catalog
        self._cache_versions[cache_key] = written_version
        logger.info(f"Saved mapping sidecar to {sidecar}")
        return written_version

    # ------------------------------------------------------------------
    # Cache management
    # ------------------------------------------------------------------

    def invalidate(self, project_path: str | Path) -> None:
        """Remove the cached catalog for *project_path*.

        The next call to :meth:`load` will re-read from disk.
        """
        cache_key = self._cache_key(project_path)
        self._cache.pop(cache_key, None)
        self._cache_versions.pop(cache_key, None)
        logger.debug(f"Invalidated mapping cache for {cache_key}")

    def clear_cache(self) -> None:
        """Clear all cached catalogs."""
        self._cache.clear()
        self._cache_versions.clear()
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
