from datetime import datetime, timezone

import pytest
import yaml
from loguru import logger

from src.model import TableConfig
from src.reconciliation.mapping_manager import MappingManager
from src.reconciliation.mapping_model import (
    EntityMapping,
    EntityType,
    Link,
    LinkSource,
    MappingCatalog,
    Metadata,
    decode_local_key,
    encode_local_key,
)
from src.reconciliation.mapping_validator import SidecarValidationError, validate_entity_mapping, validate_local_key


def make_table_config(
    *,
    entity_name: str = "samples",
    public_id: str = "sample_id",
    keys: list[str] | None = None,
    extra_columns: dict[str, str] | None = None,
) -> TableConfig:
    entities_cfg = {
        entity_name: {
            "public_id": public_id,
            "keys": keys or ["sample_code"],
            "columns": ["sample_name"],
            "extra_columns": extra_columns or {},
        }
    }
    return TableConfig(entities_cfg=entities_cfg, entity_name=entity_name)


def make_link(
    *,
    target_id: int,
    source: LinkSource,
    created_by: str = "tester",
    committed: bool = True,
) -> Link:
    committed_at = datetime(2026, 1, 1, tzinfo=timezone.utc) if committed else None
    return Link(
        target_id=target_id,
        source=source,
        created_by=created_by,
        committed_at=committed_at,
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


def make_catalog() -> MappingCatalog:
    return MappingCatalog(
        metadata=Metadata(
            project="demo-project",
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        ),
        entities={
            "samples": EntityMapping(
                local_key=["site_code", "sample_code"],
                public_id="sample_id",
                entity_type=EntityType.PRIMARY,
                description="Sample mappings",
                links={
                    encode_local_key(["site_code", "sample_code"], ["SEAD", "S1"]): make_link(
                        target_id=100,
                        source=LinkSource.MANUAL,
                    ),
                    encode_local_key(["site_code", "sample_code"], ["SEAD", "S2"]): make_link(
                        target_id=200,
                        source=LinkSource.RECONCILIATION,
                    ),
                },
            )
        },
    )


def test_mapping_catalog_parses_valid_yaml_fixture() -> None:
    fixture = yaml.safe_load(
        """
version: "2.0"
metadata:
  project: demo-project
  created_at: 2026-01-01T00:00:00Z
  updated_at: 2026-01-02T00:00:00Z
entities:
  samples:
    local_key:
      - site_code
      - sample_code
    public_id: sample_id
    entity_type: primary
    description: Sample mappings
    links:
      SEAD|S1:
        target_id: 100
        source: manual
        confidence: 0.99
        created_at: 2026-01-01T00:00:00Z
        committed_at: 2026-01-02T00:00:00Z
        notes: curated
        created_by: tester
        reviewed_by: reviewer
"""
    )

    catalog = MappingCatalog.model_validate(fixture)

    assert catalog.version == "2.0"
    assert catalog.metadata.project == "demo-project"
    assert catalog.metadata.created_at == datetime(2026, 1, 1, tzinfo=timezone.utc)
    entity = catalog.entities["samples"]
    assert entity.local_key == ["site_code", "sample_code"]
    assert entity.public_id == "sample_id"
    assert entity.entity_type == EntityType.PRIMARY
    assert entity.description == "Sample mappings"
    link = entity.links["SEAD|S1"]
    assert link.target_id == 100
    assert link.source == LinkSource.MANUAL
    assert link.confidence == pytest.approx(0.99)
    assert link.notes == "curated"
    assert link.created_by == "tester"
    assert link.reviewed_by == "reviewer"


def test_mapping_manager_load_returns_empty_catalog_when_file_is_absent(tmp_path) -> None:
    project_dir = tmp_path / "demo-project"
    project_dir.mkdir()

    manager = MappingManager()

    catalog = manager.load(project_dir)

    assert catalog.version == "2.0"
    assert catalog.metadata.project == "demo-project"
    assert catalog.entities == {}


def test_mapping_manager_load_save_round_trip_preserves_catalog_fields(tmp_path) -> None:
    project_dir = tmp_path / "demo-project"
    project_dir.mkdir()
    catalog = make_catalog()
    manager = MappingManager()

    manager.save(catalog, project_dir)

    reloaded = MappingManager().load(project_dir)

    assert reloaded.model_dump(mode="json") == catalog.model_dump(mode="json")


@pytest.mark.parametrize(
    ("local_key", "values", "expected_encoded", "expected_decoded"),
    [
        ("sample_code", "S1", "S1", ["S1"]),
        (["site_code", "sample_code"], ["SEAD", "S1"], "SEAD|S1", ["SEAD", "S1"]),
        (["site_code", "sample_code"], ["SE|AD", "S1"], r"SE\|AD|S1", ["SE|AD", "S1"]),
        (["site_code", "sample_code"], [None, "S1"], "<NULL>|S1", ["", "S1"]),
    ],
)
def test_compound_key_encoding_cases(local_key, values, expected_encoded, expected_decoded) -> None:
    encoded = encode_local_key(local_key, values)

    assert encoded == expected_encoded
    assert decode_local_key(local_key, encoded) == expected_decoded


def test_validate_entity_mapping_raises_on_public_id_mismatch() -> None:
    entity_mapping = EntityMapping(local_key="sample_code", public_id="wrong_id")
    entity_config = make_table_config(public_id="sample_id")

    with pytest.raises(SidecarValidationError, match="specifies public_id 'wrong_id'.*entity public_id is 'sample_id'"):
        validate_entity_mapping(entity_mapping, entity_config)


def test_validate_entity_mapping_accepts_matching_public_id() -> None:
    entity_mapping = EntityMapping(local_key="sample_code", public_id="sample_id")
    entity_config = make_table_config(public_id="sample_id")

    validate_entity_mapping(entity_mapping, entity_config)


@pytest.mark.parametrize("local_key", ["system_id", "sample_id", "derived_label"])
def test_validate_local_key_raises_for_forbidden_columns(local_key: str) -> None:
    entity_mapping = EntityMapping(local_key=local_key, public_id="sample_id")
    entity_config = make_table_config(extra_columns={"derived_label": "@value:Derived"})

    with pytest.raises(SidecarValidationError):
        validate_local_key(entity_mapping, entity_config)


def test_validate_local_key_warns_when_key_not_in_entity_keys() -> None:
    entity_mapping = EntityMapping(local_key="alternate_code", public_id="sample_id")
    entity_config = make_table_config(keys=["sample_code"])
    messages: list[str] = []

    sink_id = logger.add(lambda message: messages.append(str(message)), level="WARNING")
    try:
        validate_local_key(entity_mapping, entity_config)
    finally:
        logger.remove(sink_id)

    assert any("alternate_code" in message and "is not in entity.keys" in message for message in messages)


def test_replace_entity_manual_links_replaces_only_manual_links() -> None:
    catalog = make_catalog()
    new_links = {
        encode_local_key(["site_code", "sample_code"], ["SEAD", "S3"]): make_link(
            target_id=300,
            source=LinkSource.MANUAL,
        )
    }

    manual_count = MappingManager.replace_entity_manual_links(catalog, "samples", new_links)

    entity_links = catalog.entities["samples"].links
    assert manual_count == 1
    assert encode_local_key(["site_code", "sample_code"], ["SEAD", "S1"]) not in entity_links
    assert encode_local_key(["site_code", "sample_code"], ["SEAD", "S2"]) in entity_links
    assert entity_links[encode_local_key(["site_code", "sample_code"], ["SEAD", "S2"])].source == LinkSource.RECONCILIATION
    assert entity_links[encode_local_key(["site_code", "sample_code"], ["SEAD", "S3"])].target_id == 300
