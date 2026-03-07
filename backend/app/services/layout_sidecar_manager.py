"""Service for managing graph layout sidecar files (shapeshifter.layout.yml).

Custom graph layout is presentation state and is stored separately from the main
project configuration to avoid bloating shapeshifter.yml.
"""

from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

from loguru import logger

from backend.app.services.yaml_service import YamlService, get_yaml_service


class LayoutSidecarManager:
    """Manager for graph layout sidecar files (shapeshifter.layout.yml)."""

    SIDECAR_FILENAME = "shapeshifter.layout.yml"

    def __init__(self, yaml_service: YamlService | None = None) -> None:
        """Initialize layout sidecar manager.

        Args:
            yaml_service: YAML service for file operations.
        """
        self.yaml_service = yaml_service or get_yaml_service()

    def get_sidecar_path(self, project_file_path: Path) -> Path:
        """Get sidecar file path for a project file."""
        return project_file_path.parent / self.SIDECAR_FILENAME

    def sidecar_exists(self, project_file_path: Path) -> bool:
        """Check whether layout sidecar exists."""
        return self.get_sidecar_path(project_file_path).exists()

    def load_layout(self, project_file_path: Path) -> dict[str, dict[str, float]]:
        """Load custom layout from sidecar if it exists.

        Supports both:
        - {layout: {entity: {x, y}}} (preferred)
        - {entity: {x, y}} (legacy/root format)

        Returns:
            Entity positions mapping.
        """
        sidecar_path = self.get_sidecar_path(project_file_path)
        if not sidecar_path.exists():
            return {}

        try:
            data = self.yaml_service.load(sidecar_path)
            if not isinstance(data, dict):
                return {}

            raw_layout: dict[str, Any]
            if "layout" in data and isinstance(data.get("layout"), dict):
                raw_layout = data["layout"]
            else:
                raw_layout = data

            layout: dict[str, dict[str, float]] = {}
            for entity_name, pos in raw_layout.items():
                if entity_name.startswith("_"):
                    continue
                if not isinstance(pos, dict) or "x" not in pos or "y" not in pos:
                    logger.warning("Invalid layout position for entity '{}' in {}", entity_name, sidecar_path)
                    continue
                layout[entity_name] = {"x": float(pos["x"]), "y": float(pos["y"])}

            return layout
        except Exception as e:  # noqa: PERF203 ; pylint: disable=broad-exception-caught
            logger.error("Failed to load layout sidecar {}: {}", sidecar_path, e)
            return {}

    def save_layout(self, project_file_path: Path, layout: dict[str, dict[str, float]]) -> None:
        """Save custom layout to sidecar file."""
        sidecar_path = self.get_sidecar_path(project_file_path)
        sidecar_path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "layout": layout,
            "_metadata": {
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "layout_version": 1,
            },
        }
        self.yaml_service.save(payload, sidecar_path)

    def migrate_from_project_options(self, project_file_path: Path, project_options: dict[str, Any]) -> dict[str, dict[str, float]]:
        """Migrate legacy options.layout.custom to sidecar if needed.

        Returns migrated layout (or empty if nothing to migrate).
        """
        if self.sidecar_exists(project_file_path):
            return self.load_layout(project_file_path)

        legacy_layout = (project_options or {}).get("layout", {}).get("custom", {})
        if not isinstance(legacy_layout, dict) or not legacy_layout:
            return {}

        self.save_layout(project_file_path, legacy_layout)
        logger.info("Migrated legacy custom layout to sidecar for {}", project_file_path.name)
        return legacy_layout

    def delete_sidecar(self, project_file_path: Path) -> bool:
        """Delete layout sidecar file if present."""
        sidecar_path = self.get_sidecar_path(project_file_path)
        if not sidecar_path.exists():
            return False

        try:
            sidecar_path.unlink()
            logger.info("Deleted layout sidecar: {}", sidecar_path)
            return True
        except Exception as e:  # noqa: PERF203 ; pylint: disable=broad-exception-caught
            logger.error("Failed to delete layout sidecar {}: {}", sidecar_path, e)
            return False


@lru_cache(maxsize=1)
def get_layout_sidecar_manager() -> LayoutSidecarManager:
    """Get singleton layout sidecar manager."""
    return LayoutSidecarManager()
