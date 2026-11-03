import pytest

from backend.app.exceptions import ValidationError
from backend.app.mappers.project_mapper import ProjectMapper


def test_project_mapper_returns_actionable_error_for_invalid_fixed_row_shape() -> None:
    config = {
        "metadata": {"name": "fixed-shape-project", "type": "shapeshifter-project"},
        "entities": {
            "data_provider": {
                "type": "fixed",
                "public_id": "data_provider_id",
                "columns": ["data_provider_code", "data_provider_name", "contact_id"],
                "values": [["arbodat-pilot", "Arbodat Pilot", None, "extra"]],
            }
        },
    }
    project = ProjectMapper.to_api_config(config, "fixed-shape-project")

    with pytest.raises(ValidationError) as exc_info:
        ProjectMapper.to_core(project)

    error = exc_info.value
    assert error.code == "FIXED_ENTITY_SHAPE_INVALID"
    assert "Entity 'data_provider' row 0 has 4 values" in error.message
    assert error.context == {"entity": "data_provider", "validation": "fixed_entity_shape"}
    assert any("full positional form" in tip for tip in error.tips)
