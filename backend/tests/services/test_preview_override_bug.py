"""Test case to reproduce preview override config bug."""

import pytest

from backend.app.services.project_service import ProjectService
from backend.app.services.shapeshift_service import ShapeShiftService


class TestPreviewOverrideBug:
    """Reproduce the preview override config error."""

    @pytest.mark.asyncio
    async def test_preview_with_minimal_override_config(self):
        """
        Test preview with override config matching the frontend payload.

        This reproduces the error:
        "RuntimeError: ShapeShift failed for land_use: Unable to resolve source for entity 'land_use'"

        The override config comes from the frontend's buildEntityConfigFromFormData() function.
        """
        project_service = ProjectService()
        shapeshift_service = ShapeShiftService(project_service=project_service)

        # The exact payload sent from the frontend
        override_config = {
            "type": "sql",
            "keys": [],
            "columns": [],
            "public_id": "land_use_id",
            "data_source": "digidiggie-options",
            "query": "select *\r\nfrom land_use;",
        }

        # This should work but currently fails with "Unable to resolve source for entity"
        result = await shapeshift_service.preview_entity(
            project_name="digidiggie-dev", entity_name="land_use", limit=50, override_config=override_config
        )

        assert result is not None
        assert result.entity_name == "land_use"
        print(f"Preview succeeded: {result.total_rows_in_preview} rows")

    @pytest.mark.asyncio
    async def test_preview_entries_with_exact_error_payload(self):
        """
        Test with the EXACT payload from the user's error message.

        Original error payload:
        {"entity_config":{"name":"entries","type":"sql","system_id":"system_id",
        "public_id":"public_id","surrogate_id":"","keys":[],"columns":["actor_id","year"],
        "values":[],"source":null,"data_source":"digidiggie-options",
        "query":"select actor_is, year from entries","options":{...},"foreign_keys":[],
        "depends_on":[],"drop_duplicates":{"enabled":true,"columns":[]},
        "drop_empty_rows":{"enabled":false,"columns":[]},"check_functional_dependency":false,
        "advanced":{"filters":[],"unnest":null,"append":[]}}}
        """
        project_service = ProjectService()
        shapeshift_service = ShapeShiftService(project_service=project_service)

        # The OLD payload (before fix) - this is what was being sent and causing errors
        old_payload = {
            "name": "entries",
            "type": "sql",
            "system_id": "system_id",  # ← UI field, not needed by backend
            "public_id": "public_id",
            "surrogate_id": "",  # ← UI field
            "keys": [],
            "columns": ["actor_id", "year"],
            "values": [],  # ← UI field (for fixed type only)
            "source": None,
            "data_source": "digidiggie-options",
            "query": "select actor_id, year from entries",  # Fixed typo: actor_is → actor_id
            "options": {"filename": "", "sep": ",", "encoding": "utf-8", "sheet_name": "", "range": ""},  # ← UI nested object
            "foreign_keys": [],
            "depends_on": [],
            "drop_duplicates": {"enabled": True, "columns": []},  # ← UI nested object
            "drop_empty_rows": {"enabled": False, "columns": []},  # ← UI nested object
            "check_functional_dependency": False,
            "advanced": {"filters": [], "unnest": None, "append": []},  # ← UI wrapper object
        }

        # This SHOULD fail because it has UI-specific structure
        try:
            result = await shapeshift_service.preview_entity(
                project_name="digidiggie-dev", entity_name="entries", limit=50, override_config=old_payload
            )
            print(f"Old payload succeeded unexpectedly: {result.total_rows_in_preview} rows")
        except Exception as e:
            print(f"Old payload failed as expected: {type(e).__name__}: {e}")

        # The NEW payload (after fix) - what buildEntityConfigFromFormData() produces
        new_payload = {
            "type": "sql",
            "keys": [],
            "columns": ["actor_id", "year"],
            "public_id": "public_id",
            "data_source": "digidiggie-options",
            "query": "select actor_id, year from entries",
            "drop_duplicates": True,  # ← Flattened from nested structure
        }

        # This SHOULD succeed
        result = await shapeshift_service.preview_entity(
            project_name="digidiggie-dev", entity_name="entries", limit=50, override_config=new_payload
        )

        assert result is not None
        assert result.entity_name == "entries"
        print(f"New payload succeeded: {result.total_rows_in_preview} rows")
