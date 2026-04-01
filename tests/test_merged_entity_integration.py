"""Integration test for merged entity processing."""

import pytest

from src.model import ShapeShiftProject
from src.normalizer import ShapeShifter
from src.specifications.entity import MergedEntityFieldsSpecification
from tests.decorators import with_test_config


@pytest.mark.asyncio
async def test_merged_entity_basic_processing():
    """Test that merged entity can be loaded and processed through the pipeline."""
    config = {
        "metadata": {"name": "test_merged", "version": "1.0.0"},
        "entities": {
            # Branch source 1
            "abundance": {
                "type": "fixed",
                "public_id": "abundance_id",
                "columns": ["sample_id", "taxon_id", "abundance_value"],
                "values": [
                    [1, "sample_001", "taxon_a", 10.5],
                    [2, "sample_002", "taxon_b", 20.3],
                ],
            },
            # Branch source 2
            "_analysis_entity_relative_dating": {
                "type": "fixed",
                "public_id": "analysis_entity_relative_dating_id",
                "columns": ["dating_id", "dating_method"],
                "values": [
                    [101, "dating_001", "C14"],
                    [102, "dating_002", "OSL"],
                ],
            },
            # Merged entity
            "analysis_entity": {
                "type": "merged",
                "public_id": "analysis_entity_id",
                "columns": ["sample_id", "taxon_id", "dating_id"],
                "branches": [
                    {"name": "abundance", "source": "abundance", "keys": ["sample_id"]},
                    {"name": "relative_dating", "source": "_analysis_entity_relative_dating", "keys": ["dating_id"]},
                ],
            },
        },
    }

    # Create project
    project = ShapeShiftProject(cfg=config)

    # Verify TableConfig recognizes merged type
    analysis_entity = project.get_table("analysis_entity")
    assert analysis_entity.type == "merged"
    assert len(analysis_entity.branches) == 2

    # Verify dependencies include branch sources
    assert "abundance" in analysis_entity.depends_on
    assert "_analysis_entity_relative_dating" in analysis_entity.depends_on

    # Verify get_sub_table_configs yields branch configs
    sub_configs = list(analysis_entity.get_sub_table_configs())
    assert len(sub_configs) == 2  # Two branches, no base config

    # Check that branch configs have correct metadata
    branch_names = {cfg.entity_cfg.get("_branch_name") for cfg in sub_configs}
    assert "abundance" in branch_names
    assert "relative_dating" in branch_names


@pytest.mark.asyncio
@with_test_config
async def test_merged_entity_branch_fk_columns_use_source_public_ids(test_provider):
    """Merged lineage columns should use source public_id names while storing source system_id values."""
    config = {
        "metadata": {"name": "test_merged_lineage", "version": "1.0.0"},
        "entities": {
            "abundance_source": {
                "type": "fixed",
                "public_id": "abundance_id",
                "keys": ["sample_code", "taxon_name"],
                "columns": ["sample_code", "taxon_name", "abundance"],
                "values": [
                    ["S1", "Oak", 12],
                    ["S2", "Pine", 8],
                ],
            },
            "relative_dating_source": {
                "type": "fixed",
                "public_id": "relative_dating_id",
                "keys": ["sample_code", "dating_label"],
                "columns": ["sample_code", "dating_label"],
                "values": [
                    ["S1", "Early Iron Age"],
                    ["S3", "Roman Period"],
                ],
            },
            "analysis_entity": {
                "type": "merged",
                "public_id": "analysis_entity_id",
                "branches": [
                    {"name": "abundance", "source": "abundance_source", "keys": ["sample_code"]},
                    {"name": "relative_dating", "source": "relative_dating_source", "keys": ["sample_code"]},
                ],
            },
        },
    }

    project = ShapeShiftProject(cfg=config)
    normalizer = ShapeShifter(project=project)

    await normalizer.normalize()

    merged = normalizer.table_store["analysis_entity"]

    assert "abundance_id" in merged.columns
    assert "relative_dating_id" in merged.columns
    assert "abundance_source_id" not in merged.columns
    assert "relative_dating_source_id" not in merged.columns

    abundance_rows = merged[merged["analysis_entity_branch"] == "abundance"].reset_index(drop=True)
    relative_rows = merged[merged["analysis_entity_branch"] == "relative_dating"].reset_index(drop=True)

    assert abundance_rows["abundance_id"].tolist() == [1, 2]
    assert abundance_rows["relative_dating_id"].isna().all()
    assert relative_rows["relative_dating_id"].tolist() == [1, 2]
    assert relative_rows["abundance_id"].isna().all()


@pytest.mark.asyncio
async def test_merged_entity_validation():
    """Test that merged entity validation catches configuration errors."""

    # Invalid: missing public_id
    config_missing_public_id = {
        "entities": {
            "source1": {"type": "fixed", "public_id": "source1_id", "values": [[1, "a"]]},
            "merged": {
                "type": "merged",
                # Missing public_id
                "columns": ["id"],
                "branches": [{"name": "branch1", "source": "source1"}],
            },
        }
    }

    spec = MergedEntityFieldsSpecification(config_missing_public_id)
    assert not spec.is_satisfied_by(entity_name="merged")
    assert any("public_id" in str(err).lower() for err in spec.errors)

    # Invalid: missing branches
    config_missing_branches = {
        "entities": {
            "merged": {
                "type": "merged",
                "public_id": "merged_id",
                "columns": ["id"],
                # Missing branches field
            },
        }
    }

    spec = MergedEntityFieldsSpecification(config_missing_branches)
    assert not spec.is_satisfied_by(entity_name="merged")
    assert any("branches" in str(err).lower() for err in spec.errors)

    # Invalid: branch source doesn't exist
    config_bad_source = {
        "entities": {
            "merged": {
                "type": "merged",
                "public_id": "merged_id",
                "columns": ["id"],
                "branches": [{"name": "branch1", "source": "nonexistent"}],
            },
        }
    }

    spec = MergedEntityFieldsSpecification(config_bad_source)
    assert not spec.is_satisfied_by(entity_name="merged")
    assert any("does not exist" in str(err) for err in spec.errors)


def test_merged_entity_dependency_tracking():
    """Test that merged entity dependencies are correctly tracked."""
    config = {
        "metadata": {"name": "test_deps", "version": "1.0.0"},
        "entities": {
            "location": {"type": "fixed", "public_id": "location_id", "values": [[1, "Norway"]]},
            "source1": {"type": "fixed", "public_id": "source1_id", "values": [[1, "a"]]},
            "source2": {"type": "fixed", "public_id": "source2_id", "values": [[1, "b"]]},
            "merged": {
                "type": "merged",
                "public_id": "merged_id",
                "columns": ["id", "location_name"],
                "foreign_keys": [{"entity": "location", "local_keys": ["location_name"], "remote_keys": ["location_name"]}],
                "branches": [
                    {"name": "branch1", "source": "source1"},
                    {"name": "branch2", "source": "source2"},
                ],
            },
        },
    }

    project = ShapeShiftProject(cfg=config)
    merged_cfg = project.get_table("merged")

    # Should include both branch sources and FK dependency
    depends_on = merged_cfg.depends_on
    assert "source1" in depends_on
    assert "source2" in depends_on
    assert "location" in depends_on
    assert len(depends_on) == 3


def test_merged_entity_not_in_dependent_entities():
    """Test that merged entities don't have dependent entities via depends_on.

    Note: Merged entities can still be FK targets for other entities, but they
    don't appear in dependent_entities of their branch sources because they
    don't have a depends_on reference - they have branches references instead.
    """
    config = {
        "metadata": {"name": "test_no_deps", "version": "1.0.0"},
        "entities": {
            "source1": {"type": "fixed", "public_id": "source1_id", "values": [[1, "a"]]},
            "merged": {
                "type": "merged",
                "public_id": "merged_id",
                "columns": ["id"],
                "branches": [{"name": "branch1", "source": "source1"}],
            },
        },
    }

    project = ShapeShiftProject(cfg=config)
    source1_cfg = project.get_table("source1")

    # source1 should see merged as a dependent (merged depends on source1 via branches)
    dependents = set(source1_cfg.dependent_entities())
    assert "merged" in dependents
