# type: ignore
from pathlib import Path

from .base import ProjectSpecification, SpecificationIssue
from .entity import EntitySpecification
from .foreign_key import ForeignKeyConfigSpecification, ForeignKeyDataSpecification
from .project import (
    CircularDependencySpecification,
    CompositeProjectSpecification,
    DataSourceExistsSpecification,
    EntitiesSpecification,
)
from .base import FIELD_VALIDATORS
FIELD_VALIDATORS.scan(__name__, Path(__file__).parent)