from unittest.mock import Mock

import pytest

from backend.app.exceptions import ValidationError
from backend.app.mappers.entity_config_mapper import EntityMapperContext
from backend.app.services.shapeshift_service import ShapeShiftService


def test_preview_override_reports_fixed_entity_shape_as_validation_error() -> None:
    service = ShapeShiftService(project_service=Mock())
    entity_config = {
        "type": "fixed",
        "public_id": "data_provider_id",
        "columns": ["data_provider_code", "data_provider_name", "contact_id"],
        "values": [["arbodat-pilot", "Arbodat Pilot", None, "extra"]],
    }

    with pytest.raises(ValidationError) as exc_info:
        service._resolve_entity_config(
            entity_config,
            EntityMapperContext(project_name="test_project"),
            "data_provider",
        )

    assert exc_info.value.code == "FIXED_ENTITY_SHAPE_INVALID"
    assert exc_info.value.context["entity"] == "data_provider"
