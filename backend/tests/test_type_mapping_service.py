"""
Tests for Type Mapping Service
"""

import pytest
from app.services.type_mapping_service import TypeMapping, TypeMappingService


class TestTypeMappingService:
    """Test cases for TypeMappingService."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = TypeMappingService()

    def test_integer_type_mapping(self):
        """Should map integer types correctly."""
        mapping = self.service.get_type_mapping("integer")
        assert mapping.suggested_type == "integer"
        assert mapping.confidence == 1.0
        assert "integer" in mapping.reason

    def test_varchar_type_mapping(self):
        """Should map varchar to string."""
        mapping = self.service.get_type_mapping("character varying")
        assert mapping.suggested_type == "string"
        assert mapping.confidence == 1.0

    def test_text_type_mapping(self):
        """Should map text types."""
        mapping = self.service.get_type_mapping("text")
        assert mapping.suggested_type == "text"
        assert mapping.confidence == 1.0

    def test_boolean_type_mapping(self):
        """Should map boolean types."""
        mapping = self.service.get_type_mapping("boolean")
        assert mapping.suggested_type == "boolean"
        assert mapping.confidence == 1.0

    def test_date_type_mapping(self):
        """Should map date types."""
        mapping = self.service.get_type_mapping("date")
        assert mapping.suggested_type == "date"
        assert mapping.confidence == 1.0

    def test_timestamp_type_mapping(self):
        """Should map timestamp to datetime."""
        mapping = self.service.get_type_mapping("timestamp without time zone")
        assert mapping.suggested_type == "datetime"
        assert mapping.confidence == 1.0

    def test_uuid_type_mapping(self):
        """Should map UUID types."""
        mapping = self.service.get_type_mapping("uuid")
        assert mapping.suggested_type == "uuid"
        assert mapping.confidence == 1.0

    def test_json_type_mapping(self):
        """Should map JSON types."""
        mapping = self.service.get_type_mapping("jsonb")
        assert mapping.suggested_type == "json"
        assert mapping.confidence == 1.0

    def test_numeric_type_mapping(self):
        """Should map numeric to float."""
        mapping = self.service.get_type_mapping("numeric")
        assert mapping.suggested_type == "float"
        assert mapping.confidence == 0.9

    def test_id_column_heuristic(self):
        """Should recognize ID columns."""
        mapping = self.service.get_type_mapping("integer", column_name="user_id")
        assert mapping.suggested_type == "integer"
        assert mapping.confidence >= 0.9
        assert "ID column" in mapping.reason

    def test_uuid_id_column_heuristic(self):
        """Should recognize UUID ID columns."""
        mapping = self.service.get_type_mapping("uuid", column_name="id")
        assert mapping.suggested_type == "uuid"
        assert mapping.confidence >= 0.95

    def test_boolean_flag_heuristic(self):
        """Should recognize boolean flag columns."""
        mapping = self.service.get_type_mapping("smallint", column_name="is_active")
        assert mapping.suggested_type == "boolean"
        assert mapping.confidence >= 0.85

    def test_date_column_heuristic(self):
        """Should recognize date columns by name."""
        mapping = self.service.get_type_mapping("character varying", column_name="created_at")
        assert mapping.suggested_type == "datetime"
        assert mapping.confidence >= 0.85

    def test_count_column_heuristic(self):
        """Should recognize count columns."""
        mapping = self.service.get_type_mapping("bigint", column_name="view_count")
        assert mapping.suggested_type == "integer"
        assert mapping.confidence >= 0.9

    def test_email_column_heuristic(self):
        """Should recognize email columns."""
        mapping = self.service.get_type_mapping("character varying", column_name="email")
        assert mapping.suggested_type == "string"
        assert mapping.confidence >= 0.9

    def test_unknown_type_fallback(self):
        """Should fallback to string for unknown types."""
        mapping = self.service.get_type_mapping("custom_type")
        assert mapping.suggested_type == "string"
        assert mapping.confidence == 0.5
        assert "Unknown type" in mapping.reason

    def test_partial_match(self):
        """Should match type patterns like 'character varying(255)'."""
        mapping = self.service.get_type_mapping("character varying(255)")
        assert mapping.suggested_type == "string"
        assert mapping.confidence == 1.0

    def test_alternatives_provided(self):
        """Should provide alternative type suggestions."""
        mapping = self.service.get_type_mapping("integer")
        assert len(mapping.alternatives) > 0
        assert "string" in mapping.alternatives or "float" in mapping.alternatives

    def test_get_mappings_for_table(self):
        """Should generate mappings for all columns in a table."""
        columns = [
            {"name": "id", "data_type": "integer", "is_primary_key": True, "max_length": None},
            {"name": "name", "data_type": "character varying", "is_primary_key": False, "max_length": 255},
            {"name": "created_at", "data_type": "timestamp", "is_primary_key": False, "max_length": None},
            {"name": "is_active", "data_type": "boolean", "is_primary_key": False, "max_length": None},
        ]

        mappings = self.service.get_mappings_for_table(columns)

        assert len(mappings) == 4
        assert "id" in mappings
        assert "name" in mappings
        assert "created_at" in mappings
        assert "is_active" in mappings

        assert mappings["id"].suggested_type == "integer"
        assert mappings["name"].suggested_type == "string"
        assert mappings["created_at"].suggested_type == "datetime"
        assert mappings["is_active"].suggested_type == "boolean"

    def test_confidence_levels(self):
        """Should assign appropriate confidence levels."""
        # High confidence - exact match
        high = self.service.get_type_mapping("integer")
        assert high.confidence == 1.0

        # Medium-high confidence - heuristic
        medium_high = self.service.get_type_mapping("character varying", column_name="user_id")
        assert 0.85 <= medium_high.confidence < 1.0

        # Medium confidence - fuzzy match
        medium = self.service.get_type_mapping("numeric")
        assert 0.7 <= medium.confidence < 1.0

        # Low confidence - unknown
        low = self.service.get_type_mapping("unknown_type")
        assert low.confidence <= 0.5
