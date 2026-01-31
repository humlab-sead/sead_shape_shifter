from itertools import chain
from pyexpat import errors
from src.model import TableConfig
from src.model import ShapeShiftProject
from src.specifications.base import Specification


class CanMaterializeSpecification(Specification):

    def __init__(self, project: "ShapeShiftProject"):
        super().__init__()
        self.project: ShapeShiftProject = project

    def is_satisfied_by(self, *, entity: TableConfig, **kwargs) -> bool:
        """
        Check if entity can be materialized.

        Returns:
            True if entity can be materialized, False otherwise.
        """

        # Rule 1: Cannot be fixed
        if entity.type == "fixed":
            self.add_error("Entity is already type 'fixed'", entity.entity_name)

        # Rule 2: Cannot already be materialized
        if entity.is_materialized:
            self.add_error("Entity is already materialized", entity.entity_name)
        # Rule 3: Cannot depend on non-materialized dynamic entities
        dependencies: chain[str] = chain((fk.remote_entity for fk in entity.foreign_keys), entity.depends_on)
        for entity_name in dependencies:
            try:
                dep_entity: TableConfig = self.project.get_table(entity_name)
                if dep_entity.type != "fixed" and not dep_entity.is_materialized:
                    self.add_error(f"Depends on non-materialized entity '{entity_name}'", entity_name)
            except KeyError:
                self.add_error(f"Depends on non-existent entity '{entity_name}'", entity_name)

        return not self.has_errors()
