from dataclasses import dataclass, field
from typing import Protocol

from loguru import logger
import pandas as pd

from src.model import ShapeShiftProject


class ProcessState:
    """Helper class to track processing state of entities during normalization."""

    def __init__(self, project: ShapeShiftProject, table_store: dict[str, pd.DataFrame], target_entities: set[str] | None = None) -> None:
        self.project: ShapeShiftProject = project
        self.table_store: dict[str, pd.DataFrame] = table_store
        # Resolve target entities through the project to ensure dependencies are included consistently.
        self.target_entities: set[str] = project.resolve_target_entities(target_entities)

    def get_next_entity_to_process(self) -> str | None:
        """Get the next entity that can be processed based on dependencies."""
        # logger.debug(f"Processed entities so far: {self.processed_entities}")

        for entity_name in self.unprocessed_entities:
            # logger.debug(f"{entity_name}[check]: Checking if entity '{entity_name}' can be processed...")
            unmet_dependencies: set[str] = self.get_unmet_dependencies(entity=entity_name)
            if unmet_dependencies:
                # logger.debug(f"{entity_name}[check]: Entity has unmet dependencies: {unmet_dependencies}")
                continue
            # logger.debug(f"{entity_name}[check]: Entity can be processed next.")
            return entity_name
        return None

    def get_unmet_dependencies(self, entity: str) -> set[str]:
        return self.project.get_table(entity_name=entity).depends_on - self.processed_entities

    def get_all_unmet_dependencies(self) -> dict[str, set[str]]:
        unmet_dependencies: dict[str, set[str]] = {
            entity: self.get_unmet_dependencies(entity=entity) for entity in self.unprocessed_entities
        }
        return {k: v for k, v in unmet_dependencies.items() if v}

    def log_unmet_dependencies(self) -> None:
        for entity, unmet in self.get_all_unmet_dependencies().items():
            logger.error(f"{entity}[check]: Entity has unmet dependencies: {unmet}")

    @property
    def processed_entities(self) -> set[str]:
        """Return the set of processed entities."""
        return set(self.table_store.keys())

    @property
    def unprocessed_entities(self) -> set[str]:
        """Return the set of unprocessed target entities."""
        return self.target_entities - self.processed_entities


@dataclass
class DeferredLinkingTracker:
    """
    Tracks entities whose foreign key linking is deferred and retries linking efficiently.
    """

    deferred: set[str] = field(default_factory=set)

    def track(self, *, entity_name: str, deferred: bool) -> None:
        """Record the deferred status of a just-linked entity."""
        if deferred:
            self.deferred.add(entity_name)
        else:
            self.deferred.discard(entity_name)
