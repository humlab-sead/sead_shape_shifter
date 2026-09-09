from typing import Any

from loguru import logger


class LayoutPosition:
    """Position of a node in custom graph layout."""

    def __init__(self, data: dict[str, Any]) -> None:
        """Initialize layout position from configuration data.

        Args:
            data: Dictionary containing 'x' and 'y' coordinates

        Raises:
            ValueError: If x or y coordinates are missing
        """
        if "x" not in data or "y" not in data:
            raise ValueError("Layout position must have x and y coordinates")
        self.x: float = float(data["x"])
        self.y: float = float(data["y"])

    def to_dict(self) -> dict[str, float]:
        """Convert position to dictionary for serialization."""
        return {"x": self.x, "y": self.y}


class CustomLayoutConfig:
    """Custom graph layout configuration."""

    def __init__(self, data: dict[str, Any]) -> None:
        """Initialize custom layout from configuration data.

        Args:
            data: Dictionary mapping entity names to position dictionaries
        """
        self.positions: dict[str, LayoutPosition] = {}
        for entity_name, pos_data in data.items():
            if entity_name.startswith("_"):  # Skip metadata keys
                continue
            try:
                self.positions[entity_name] = LayoutPosition(pos_data)
            except ValueError as e:
                logger.warning(f"Invalid position for entity '{entity_name}': {e}, skipping")

    def get_position(self, entity_name: str) -> tuple[float, float] | None:
        """Get (x, y) position for entity, or None if not set.

        Args:
            entity_name: Name of the entity

        Returns:
            Tuple of (x, y) coordinates, or None if entity has no saved position
        """
        pos = self.positions.get(entity_name)
        return (pos.x, pos.y) if pos else None

    def set_position(self, entity_name: str, x: float, y: float) -> None:
        """Set position for entity.

        Args:
            entity_name: Name of the entity
            x: X coordinate
            y: Y coordinate
        """
        self.positions[entity_name] = LayoutPosition({"x": x, "y": y})

    def remove_position(self, entity_name: str) -> None:
        """Remove position for entity.

        Args:
            entity_name: Name of the entity to remove
        """
        self.positions.pop(entity_name, None)

    def to_dict(self) -> dict[str, dict[str, float]]:
        """Convert to dictionary for serialization."""
        return {name: pos.to_dict() for name, pos in self.positions.items()}

    @property
    def is_empty(self) -> bool:
        """Check if no positions are configured."""
        return len(self.positions) == 0


class LayoutOptions:
    """Layout options for dependency graph visualization."""

    def __init__(self, data: dict[str, Any]) -> None:
        """Initialize layout options from configuration data.

        Args:
            data: Dictionary containing layout configuration
        """
        self.data = data
        self._custom: CustomLayoutConfig | None = None

    @property
    def custom(self) -> CustomLayoutConfig:
        """Get custom layout configuration."""
        if self._custom is None:
            custom_data = self.data.get("custom", {})
            self._custom = CustomLayoutConfig(custom_data)
        return self._custom

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {}
        if self._custom and not self._custom.is_empty:
            result["custom"] = self._custom.to_dict()
        return result
