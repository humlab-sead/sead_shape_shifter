import pytest

from backend.app.models.reconciliation import EntityResolutionCatalog, EntityResolutionSet, ReconciliationSource
from scripts.generate_schemas import generate_schemas

RECONCILIATION_SCHEMA = generate_schemas()["reconciliationSchema.json"]
ENTITY_SCHEMA = generate_schemas()["entitySchema.json"]


def test_entity_schema_describes_direct_foreign_key_value_sources() -> None:
    value_sources_schema = ENTITY_SCHEMA["properties"]["foreign_key_value_sources"]

    assert value_sources_schema["default"] == {}
    assert value_sources_schema["additionalProperties"]["enum"] == ["system_id", "public_id"]
    assert "existing target ID" in value_sources_schema["description"]
    assert "without creating a Core link" in value_sources_schema["description"]
    assert "Omitted entries use system_id" in value_sources_schema["description"]


@pytest.mark.parametrize(
    ("source", "expected_schema"),
    [
        pytest.param(None, {"type": "null"}, id="null-source"),
        pytest.param("site", {"type": "string"}, id="entity-name-source"),
        pytest.param(
            {"data_source": "sead", "type": "sql", "query": "SELECT site_name FROM site"},
            {"$ref": "#/$defs/ReconciliationSource"},
            id="custom-query-source",
        ),
    ],
)
def test_reconciliation_schema_covers_source_variants(source: object, expected_schema: dict[str, str]) -> None:
    specification_schema = RECONCILIATION_SCHEMA["$defs"]["EntityResolutionSet"]
    source_schema = specification_schema["properties"]["source"]

    assert expected_schema in source_schema["anyOf"]
    EntityResolutionSet.model_validate({"source": source, "remote": {"service_type": "site"}})


def test_reconciliation_schema_covers_nested_catalog_specifications() -> None:
    catalog_schema = RECONCILIATION_SCHEMA["$defs"]["EntityResolutionCatalog"]
    nested_specification_schema = catalog_schema["properties"]["entities"]["additionalProperties"]["additionalProperties"]

    assert nested_specification_schema == {"$ref": "#/$defs/EntityResolutionSet"}

    catalog = EntityResolutionCatalog.model_validate(
        {
            "service_url": "http://localhost:8000",
            "entities": {
                "site": {
                    "site_code": {
                        "source": {
                            "data_source": "sead",
                            "type": "sql",
                            "query": "SELECT site_name FROM site",
                        },
                        "property_mappings": {"name": "site_name"},
                        "remote": {"service_type": "site", "columns": ["name"]},
                        "auto_accept_threshold": 0.95,
                        "review_threshold": 0.7,
                        "mapping": [{"source_value": "Example", "target_id": 1, "confidence": 0.9}],
                    }
                }
            },
        }
    )

    source = catalog.entities["site"]["site_code"].source
    assert isinstance(source, ReconciliationSource)
    assert source.model_dump() == {
        "data_source": "sead",
        "type": "sql",
        "query": "SELECT site_name FROM site",
    }
