"""Shared target-model domain types and validators."""

from src.target_model.conformance import ConformanceIssue, TargetModelConformanceValidator
from src.target_model.documentation import DocumentFormat, TargetModelDocumentGenerator
from src.target_model.models import ColumnSpec, EntitySpec, ForeignKeySpec, GlobalConstraint, ModelMetadata, NamingConventions, TargetModel
from src.target_model.spec_validator import SpecValidationIssue, TargetModelSpecValidator
from src.target_model.template_generator import generate_project_template, render_project_template_yaml

__all__ = [
    "ColumnSpec",
    "ConformanceIssue",
    "DocumentFormat",
    "EntitySpec",
    "ForeignKeySpec",
    "GlobalConstraint",
    "ModelMetadata",
    "NamingConventions",
    "SpecValidationIssue",
    "TargetModel",
    "TargetModelConformanceValidator",
    "TargetModelDocumentGenerator",
    "TargetModelSpecValidator",
    "generate_project_template",
    "render_project_template_yaml",
]
