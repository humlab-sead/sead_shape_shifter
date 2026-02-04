"""Tests for domain exception hierarchy."""

from backend.app.exceptions import (
    CircularDependencyError,
    ConfigurationError,
    ConstraintViolationError,
    DataIntegrityError,
    DependencyError,
    DomainException,
    ForeignKeyError,
    MissingDependencyError,
    ResourceConflictError,
    ResourceNotFoundError,
    SchemaValidationError,
    ValidationError,
)


class TestDomainExceptionBase:
    """Tests for DomainException base class."""

    def test_domain_exception_structure(self):
        """DomainException creates structured error dict."""
        error = DomainException(
            message="Test error",
            tips=["Tip 1", "Tip 2"],
            recoverable=True,
            context={"key": "value"},
        )

        error_dict = error.to_dict()

        assert error_dict["error_type"] == "DomainException"
        assert error_dict["message"] == "Test error"
        assert error_dict["tips"] == ["Tip 1", "Tip 2"]
        assert error_dict["recoverable"] is True
        assert error_dict["context"] == {"key": "value"}

    def test_domain_exception_defaults(self):
        """DomainException has sensible defaults."""
        error = DomainException(message="Test error")

        error_dict = error.to_dict()

        assert error_dict["tips"] == []
        assert error_dict["recoverable"] is True
        assert error_dict["context"] == {}

    def test_domain_exception_str(self):
        """DomainException str() returns message."""
        error = DomainException(message="Test error")
        assert str(error) == "Test error"


class TestForeignKeyError:
    """Tests for ForeignKeyError."""

    def test_foreign_key_error_with_entity(self):
        """ForeignKeyError includes entity in context."""
        error = ForeignKeyError(
            message="Invalid FK",
            entity="site",
            foreign_key={"local_keys": {}},
        )

        error_dict = error.to_dict()

        assert error_dict["error_type"] == "ForeignKeyError"
        assert error_dict["message"] == "Invalid FK"
        assert error_dict["context"]["entity"] == "site"
        assert error_dict["context"]["foreign_key"] == {"local_keys": {}}
        assert len(error_dict["tips"]) > 0

    def test_foreign_key_error_default_tips(self):
        """ForeignKeyError gets tips from registry."""
        error = ForeignKeyError(message="Invalid FK")

        tips = error.to_dict()["tips"]

        # Tips come from error_tips.py registry for FOREIGN_KEY_INVALID
        assert len(tips) > 0
        assert any("entity" in tip.lower() for tip in tips)
        assert any("column" in tip.lower() for tip in tips)

    def test_foreign_key_error_custom_tips(self):
        """ForeignKeyError allows custom tips."""
        custom_tips = ["Custom tip 1", "Custom tip 2"]
        error = ForeignKeyError(message="Invalid FK", tips=custom_tips)

        assert error.to_dict()["tips"] == custom_tips


class TestCircularDependencyError:
    """Tests for CircularDependencyError."""

    def test_circular_dependency_error_cycle_formatting(self):
        """CircularDependencyError formats cycle in message."""
        cycle = ["A", "B", "C"]
        error = CircularDependencyError(
            message="Cycle detected",
            cycle=cycle,
        )

        assert "A → B → C → A" in error.message
        assert error.to_dict()["context"]["cycle"] == cycle

    def test_circular_dependency_error_without_cycle(self):
        """CircularDependencyError works without cycle parameter."""
        error = CircularDependencyError(message="Generic cycle error")

        error_dict = error.to_dict()

        assert error_dict["message"] == "Generic cycle error"
        assert "cycle" not in error_dict["context"]


class TestMissingDependencyError:
    """Tests for MissingDependencyError."""

    def test_missing_dependency_error_context(self):
        """MissingDependencyError includes both entities in context."""
        error = MissingDependencyError(
            message="Entity not found",
            entity="site",
            missing_entity="location",
        )

        context = error.to_dict()["context"]

        assert context["entity"] == "site"
        assert context["missing_entity"] == "location"

    def test_missing_dependency_error_default_tips(self):
        """MissingDependencyError provides helpful tips."""
        error = MissingDependencyError(
            message="Entity not found",
            missing_entity="location",
        )

        tips = error.to_dict()["tips"]

        assert any("create" in tip.lower() for tip in tips)
        assert any("typo" in tip.lower() for tip in tips)


class TestResourceErrors:
    """Tests for ResourceNotFoundError and ResourceConflictError."""

    def test_resource_not_found_error(self):
        """ResourceNotFoundError includes resource metadata."""
        error = ResourceNotFoundError(
            message="Project not found",
            resource_type="project",
            resource_id="test_project",
        )

        error_dict = error.to_dict()

        assert error_dict["error_type"] == "ResourceNotFoundError"
        assert error_dict["context"]["resource_type"] == "project"
        assert error_dict["context"]["resource_id"] == "test_project"
        assert error_dict["recoverable"] is True

    def test_resource_conflict_error(self):
        """ResourceConflictError includes resource metadata."""
        error = ResourceConflictError(
            message="Project already exists",
            resource_type="project",
            resource_id="duplicate_project",
        )

        error_dict = error.to_dict()

        assert error_dict["error_type"] == "ResourceConflictError"
        assert error_dict["context"]["resource_type"] == "project"
        assert error_dict["context"]["resource_id"] == "duplicate_project"
        assert error_dict["recoverable"] is True


class TestValidationErrors:
    """Tests for validation-related errors."""

    def test_schema_validation_error(self):
        """SchemaValidationError includes entity and field context."""
        error = SchemaValidationError(
            message="Invalid schema",
            entity="site",
            field="system_id",
        )

        context = error.to_dict()["context"]

        assert context["entity"] == "site"
        assert context["field"] == "system_id"

    def test_constraint_violation_error(self):
        """ConstraintViolationError includes constraint type."""
        error = ConstraintViolationError(
            message="Cardinality violation",
            constraint_type="cardinality",
            entity="sample",
        )

        context = error.to_dict()["context"]

        assert context["constraint_type"] == "cardinality"
        assert context["entity"] == "sample"

    def test_configuration_error(self):
        """ConfigurationError includes specification name."""
        error = ConfigurationError(
            message="Invalid config",
            specification="EntitySpecification",
        )

        context = error.to_dict()["context"]

        assert context["specification"] == "EntitySpecification"


class TestExceptionHierarchy:
    """Tests for exception hierarchy relationships."""

    def test_foreign_key_is_data_integrity_error(self):
        """ForeignKeyError is a DataIntegrityError."""
        error = ForeignKeyError(message="Test")
        assert isinstance(error, DataIntegrityError)
        assert isinstance(error, DomainException)

    def test_circular_dependency_is_dependency_error(self):
        """CircularDependencyError is a DependencyError."""
        error = CircularDependencyError(message="Test")
        assert isinstance(error, DependencyError)
        assert isinstance(error, DomainException)

    def test_schema_validation_is_data_integrity_error(self):
        """SchemaValidationError is a DataIntegrityError."""
        error = SchemaValidationError(message="Test")
        assert isinstance(error, DataIntegrityError)
        assert isinstance(error, DomainException)

    def test_constraint_violation_is_validation_error(self):
        """ConstraintViolationError is a ValidationError."""
        error = ConstraintViolationError(message="Test")
        assert isinstance(error, ValidationError)
        assert isinstance(error, DomainException)
