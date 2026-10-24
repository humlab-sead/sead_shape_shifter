from collections import Counter
from pathlib import Path

import pytest
import yaml

from src.model import ShapeShiftProject, TableConfig
from src.target_model.conformance import (
    CONFORMANCE_VALIDATORS,
    ConformanceIssue,
    EntityConformanceValidator,
    GlobalConformanceValidator,
    TargetModelConformanceValidator,
)
from src.target_model.models import TargetModel

TEST_DATA_DIR: Path = Path(__file__).resolve().parent.parent / "test_data"
TARGET_MODEL_PATH: Path = TEST_DATA_DIR / "target_models" / "sead_standard_model.yml"
EXAMPLES_DIR: Path = TEST_DATA_DIR / "examples"
REAL_PROJECTS_DIR: Path = TEST_DATA_DIR / "projects"


def load_target_model() -> TargetModel:
    return TargetModel.model_validate(yaml.safe_load(TARGET_MODEL_PATH.read_text(encoding="utf-8")))


def load_project(name: str) -> ShapeShiftProject:
    project_path: Path = EXAMPLES_DIR / name
    return ShapeShiftProject(cfg=yaml.safe_load(project_path.read_text(encoding="utf-8")))


def load_real_project(project_name: str) -> ShapeShiftProject:
    project_path: Path = REAL_PROJECTS_DIR / project_name / "shapeshifter.yml"
    return ShapeShiftProject(cfg=yaml.safe_load(project_path.read_text(encoding="utf-8")))


def issue_pairs(target_model: TargetModel, project: ShapeShiftProject) -> list[tuple[str | None, str | None]]:
    issues: list[ConformanceIssue] = TargetModelConformanceValidator().validate(target_model, project)
    return [(issue.code, issue.entity) for issue in issues]


def test_conformance_registry_runs_global_and_entity_validator_base_types() -> None:
    """The registry should execute both global and entity validator subclasses."""

    @CONFORMANCE_VALIDATORS.register(key="test_global_conformance_validator")
    class TestGlobalConformanceValidator(GlobalConformanceValidator):  # pylint: disable=unused-variable
        def validate_global(self, target_model: TargetModel, project: ShapeShiftProject) -> list[ConformanceIssue]:
            return [ConformanceIssue(code="TEST_GLOBAL_CONFORMANCE_RULE", entity="sample", message="global validator executed")]

    @CONFORMANCE_VALIDATORS.register(key="test_entity_conformance_validator")
    class TestEntityConformanceValidator(EntityConformanceValidator):  # pylint: disable=unused-variable
        def validate_entity(self, entity_name: str, entity_spec, table_cfg) -> list[ConformanceIssue]:
            return [ConformanceIssue(code="TEST_ENTITY_CONFORMANCE_RULE", entity=entity_name, message="entity validator executed")]

    target_model: TargetModel = TargetModel.model_validate(
        {
            "model": {"name": "test", "version": "1.0"},
            "entities": {"sample": {"required": True, "public_id": "sample_id"}},
        }
    )
    project = ShapeShiftProject(
        cfg={
            "metadata": {"name": "registry-base-types", "type": "shapeshifter-project"},
            "entities": {"sample": {"public_id": "sample_id", "columns": ["sample_name"]}},
        }
    )

    try:
        issues = TargetModelConformanceValidator().validate(target_model, project)
    finally:
        CONFORMANCE_VALIDATORS.items.pop("test_global_conformance_validator", None)
        CONFORMANCE_VALIDATORS.items.pop("test_entity_conformance_validator", None)

    issue_codes = {issue.code for issue in issues}

    assert "TEST_GLOBAL_CONFORMANCE_RULE" in issue_codes
    assert "TEST_ENTITY_CONFORMANCE_RULE" in issue_codes


def test_table_config_target_facing_columns_treat_materialized_entity_as_fixed_view() -> None:
    entities = {
        "method_group": {
            "public_id": "method_group_id",
            "columns": ["group_code", "group_name"],
        },
        "method": {
            "type": "fixed",
            "public_id": "method_id",
            "columns": ["system_id", "method_id"],
            "materialized": {
                "enabled": True,
                "source_state": {
                    "public_id": "method_id",
                    "keys": ["arbodat_code"],
                    "columns": ["method_name"],
                    "extra_columns": {"description": "method_description"},
                    "foreign_keys": [
                        {
                            "entity": "method_group",
                            "local_keys": ["group_code"],
                            "remote_keys": ["group_code"],
                            "extra_columns": {"method_group_name": "group_name"},
                        }
                    ],
                    "append": [
                        {
                            "source": "method_group",
                            "columns": ["method_name", "append_only_column"],
                        }
                    ],
                },
            },
        },
    }

    table_cfg = TableConfig(entities_cfg=entities, entity_name="method")

    assert set(table_cfg.get_target_facing_columns()) == {"method_id"}


def test_core_conformance_validator_treats_materialized_entity_as_fixed_view() -> None:
    target_model: TargetModel = TargetModel.model_validate(
        {
            "model": {"name": "SEAD Clearinghouse", "version": "2.0.0"},
            "entities": {
                "method_group": {
                    "public_id": "method_group_id",
                    "columns": {"group_name": {"required": True}},
                },
                "method": {
                    "required": True,
                    "public_id": "method_id",
                    "columns": {
                        "method_name": {"required": True},
                        "description": {"required": True},
                        "method_group_id": {"required": True},
                    },
                    "foreign_keys": [{"entity": "method_group", "required": True}],
                },
            },
        }
    )
    project = ShapeShiftProject(
        cfg={
            "metadata": {"name": "materialized-example", "type": "shapeshifter-project"},
            "entities": {
                "method_group": {
                    "public_id": "method_group_id",
                    "columns": ["group_name"],
                },
                "method": {
                    "type": "fixed",
                    "public_id": "method_id",
                    "columns": ["system_id", "method_id"],
                    "materialized": {
                        "enabled": True,
                        "source_state": {
                            "public_id": "method_id",
                            "columns": ["method_name"],
                            "extra_columns": {"description": "method_description"},
                            "foreign_keys": [
                                {
                                    "entity": "method_group",
                                    "local_keys": ["group_code"],
                                    "remote_keys": ["group_code"],
                                }
                            ],
                        },
                    },
                },
            },
        }
    )

    issues: list[ConformanceIssue] = TargetModelConformanceValidator().validate(target_model, project)

    assert [(issue.code, issue.entity) for issue in issues] == [
        ("MISSING_REQUIRED_FOREIGN_KEY_TARGET", "method"),
        ("MISSING_REQUIRED_COLUMN", "method"),
        ("MISSING_REQUIRED_COLUMN", "method"),
        ("MISSING_REQUIRED_COLUMN", "method"),
    ]


def test_table_config_target_facing_columns_collapse_at_unnest_boundary() -> None:
    entities = {
        "location_type": {
            "public_id": "location_type_id",
            "columns": ["kind", "kind_name"],
        },
        "dropped_lookup": {
            "public_id": "dropped_lookup_id",
            "columns": ["x_coord", "label"],
        },
        "location": {
            "public_id": "location_id",
            "keys": ["record_key"],
            "columns": ["x_coord", "y_coord"],
            "extra_columns": {"extra_before_unnest": 1},
            "foreign_keys": [
                {
                    "entity": "location_type",
                    "local_keys": ["kind"],
                    "remote_keys": ["kind"],
                },
                {
                    "entity": "dropped_lookup",
                    "local_keys": ["x_coord"],
                    "remote_keys": ["x_coord"],
                },
            ],
            "unnest": {
                "id_vars": ["record_key"],
                "value_vars": ["x_coord", "y_coord"],
                "var_name": "kind",
                "value_name": "location_name",
            },
        },
    }

    table_cfg = TableConfig(entities_cfg=entities, entity_name="location")

    assert set(table_cfg.get_target_facing_columns()) == {
        "kind",
        "location_id",
        "location_name",
        "location_type_id",
        "record_key",
    }
    assert table_cfg.get_target_facing_foreign_key_targets() == {"location_type"}


def test_core_conformance_reports_local_foreign_key_keys_dropped_by_unnest() -> None:
    target_model = _minimal_target_model(
        {
            "abundance_property": {
                "foreign_keys": [{"entity": "property_type", "required": True}],
            },
            "property_type": {"public_id": "property_type_id"},
        }
    )
    project = _minimal_project(
        {
            "abundance_property": {
                "columns": ["record_key", "property_group", "property_type_a", "property_type_b"],
                "foreign_keys": [
                    {
                        "entity": "property_type",
                        "local_keys": ["property_group", "property_type"],
                        "remote_keys": ["property_group", "property_type"],
                    }
                ],
                "unnest": {
                    "id_vars": ["record_key"],
                    "value_vars": ["property_type_a", "property_type_b"],
                    "var_name": "property_type",
                    "value_name": "count",
                },
            },
            "property_type": {"public_id": "property_type_id", "columns": ["property_group", "property_type"]},
        }
    )

    issues = TargetModelConformanceValidator().validate(target_model, project)
    fk_issue = next(issue for issue in issues if issue.code == "MISSING_REQUIRED_FOREIGN_KEY_TARGET")

    assert fk_issue.message == (
        "Entity 'abundance_property' is missing required foreign key target 'property_type' because local key "
        "column(s) 'property_group' do not survive unnest. Preserve them in 'id_vars' or otherwise make them "
        "available after unnest."
    )


def test_core_conformance_keeps_generic_missing_foreign_key_message_without_matching_project_fk() -> None:
    target_model = _minimal_target_model(
        {
            "abundance_property": {
                "foreign_keys": [{"entity": "property_type", "required": True}],
            },
            "property_type": {"public_id": "property_type_id"},
        }
    )
    project = _minimal_project(
        {
            "abundance_property": {
                "columns": ["record_key", "property_type_a", "property_type_b"],
                "unnest": {
                    "id_vars": ["record_key"],
                    "value_vars": ["property_type_a", "property_type_b"],
                    "var_name": "property_type",
                    "value_name": "count",
                },
            },
            "property_type": {"public_id": "property_type_id"},
        }
    )

    issues = TargetModelConformanceValidator().validate(target_model, project)
    fk_issue = next(issue for issue in issues if issue.code == "MISSING_REQUIRED_FOREIGN_KEY_TARGET")

    assert fk_issue.message == ("Entity 'abundance_property' is missing required foreign key target 'property_type'")


def test_table_config_target_facing_columns_allow_chained_fk_extra_columns_after_unnest() -> None:
    entities = {
        "location_type": {
            "public_id": "location_type_id",
            "columns": ["kind", "kind_name", "group_code"],
        },
        "location_group": {
            "public_id": "location_group_id",
            "columns": ["group_code", "group_name"],
        },
        "location": {
            "public_id": "location_id",
            "keys": ["record_key"],
            "columns": ["x_coord", "y_coord"],
            "foreign_keys": [
                {
                    "entity": "location_type",
                    "local_keys": ["kind"],
                    "remote_keys": ["kind"],
                    "extra_columns": {"group_code": "group_code"},
                },
                {
                    "entity": "location_group",
                    "local_keys": ["group_code"],
                    "remote_keys": ["group_code"],
                },
            ],
            "unnest": {
                "id_vars": ["record_key"],
                "value_vars": ["x_coord", "y_coord"],
                "var_name": "kind",
                "value_name": "location_name",
            },
        },
    }

    table_cfg = TableConfig(entities_cfg=entities, entity_name="location")

    assert set(table_cfg.get_target_facing_columns()) == {
        "group_code",
        "kind",
        "location_group_id",
        "location_id",
        "location_name",
        "location_type_id",
        "record_key",
    }
    assert table_cfg.get_target_facing_foreign_key_targets() == {"location_group", "location_type"}


def test_core_conformance_reports_missing_entity_and_wrong_public_id() -> None:
    target_model: TargetModel = load_target_model()
    project: ShapeShiftProject = load_project("sead_missing_sample_group.yml")

    issues: set[tuple[str | None, str | None]] = set(issue_pairs(target_model, project))

    assert ("MISSING_REQUIRED_ENTITY", "sample_group") in issues
    assert ("UNEXPECTED_PUBLIC_ID", "sample") in issues


def test_core_conformance_accepts_sample_note_example_fixture() -> None:
    target_model: TargetModel = _minimal_target_model(
        {
            "sample": {
                "required": True,
                "public_id": "physical_sample_id",
                "columns": {
                    "sample_name": {"required": True},
                },
            },
            "sample_note": {
                "required": False,
                "public_id": "sample_note_id",
                "columns": {
                    "physical_sample_id": {"required": True},
                    "note_type": {"required": False},
                    "note": {"required": True},
                },
                "foreign_keys": [{"entity": "sample", "required": True}],
            },
        }
    )
    project: ShapeShiftProject = load_project("sead_sample_note_context.yml")

    assert issue_pairs(target_model, project) == []


def test_core_conformance_accepts_sample_group_note_example_fixture() -> None:
    target_model: TargetModel = _minimal_target_model(
        {
            "sample_group": {
                "required": True,
                "public_id": "sample_group_id",
                "columns": {
                    "sample_group_name": {"required": True},
                },
            },
            "sample_group_note": {
                "required": False,
                "public_id": "sample_group_note_id",
                "columns": {
                    "sample_group_id": {"required": True},
                    "note": {"required": True},
                },
                "foreign_keys": [{"entity": "sample_group", "required": True}],
            },
        }
    )
    project: ShapeShiftProject = load_project("sead_sample_group_note_context.yml")

    assert issue_pairs(target_model, project) == []


def test_core_conformance_accepts_transitive_foreign_key_path() -> None:
    target_model: TargetModel = _minimal_target_model(
        {
            "site": {
                "required": True,
                "public_id": "site_id",
            },
            "sample_group": {
                "required": True,
                "public_id": "sample_group_id",
                "foreign_keys": [{"entity": "site", "required": True}],
            },
            "sample": {
                "required": True,
                "public_id": "sample_id",
                "foreign_keys": [{"entity": "site", "required": True}],
            },
        }
    )
    project = ShapeShiftProject(
        cfg={
            "metadata": {
                "name": "transitive-fk-example",
                "type": "shapeshifter-project",
            },
            "entities": {
                "site": {
                    "public_id": "site_id",
                    "columns": ["site_name"],
                },
                "sample_group": {
                    "public_id": "sample_group_id",
                    "columns": ["sample_group_name"],
                    "foreign_keys": [{"entity": "site", "local_keys": ["site_id"], "remote_keys": ["site_id"]}],
                },
                "sample": {
                    "public_id": "sample_id",
                    "columns": ["sample_name"],
                    "foreign_keys": [{"entity": "sample_group", "local_keys": ["sample_group_id"], "remote_keys": ["sample_group_id"]}],
                },
            },
        }
    )

    issues = set(issue_pairs(target_model, project))

    assert ("MISSING_REQUIRED_FOREIGN_KEY_TARGET", "sample") not in issues


def test_schema_aware_append_emits_issue_when_append_branch_misses_required_column() -> None:
    target_model: TargetModel = _minimal_target_model(
        {
            "site": {
                "required": True,
                "public_id": "site_id",
                "columns": {
                    "site_name": {"required": True},
                    "site_type": {"required": True},
                },
            }
        }
    )
    project = ShapeShiftProject(
        cfg={
            "metadata": {"name": "append-missing-required", "type": "shapeshifter-project"},
            "entities": {
                "site": {
                    "public_id": "site_id",
                    "columns": ["site_name", "site_type"],
                    "append": [
                        {
                            "type": "fixed",
                            "columns": ["site_name"],
                            "values": [["Append Site"]],
                        }
                    ],
                }
            },
        }
    )

    issues = set(issue_pairs(target_model, project))

    assert ("APPEND_MISSING_REQUIRED_COLUMN", "site") in issues


def test_schema_aware_append_respects_align_by_position() -> None:
    target_model: TargetModel = _minimal_target_model(
        {
            "site": {
                "required": True,
                "public_id": "site_id",
                "columns": {
                    "site_name": {"required": True},
                    "site_type": {"required": True},
                },
            }
        }
    )
    project = ShapeShiftProject(
        cfg={
            "metadata": {"name": "append-align-by-position", "type": "shapeshifter-project"},
            "entities": {
                "legacy_site": {
                    "public_id": "legacy_site_id",
                    "columns": ["legacy_name", "legacy_kind"],
                },
                "site": {
                    "public_id": "site_id",
                    "columns": ["site_name", "site_type"],
                    "append": [
                        {
                            "source": "legacy_site",
                            "align_by_position": True,
                        }
                    ],
                },
            },
        }
    )

    codes = [issue.code for issue in TargetModelConformanceValidator().validate(target_model, project)]

    assert "APPEND_MISSING_REQUIRED_COLUMN" not in codes


def test_required_columns_ignores_required_generated_columns() -> None:
    target_model: TargetModel = _minimal_target_model(
        {
            "site": {
                "required": True,
                "public_id": "site_id",
                "columns": {
                    "site_name": {"required": True},
                    "site_slug": {"required": True, "generated": True},
                },
            }
        }
    )
    project = _minimal_project({"site": {"public_id": "site_id", "columns": ["site_name"]}})

    issues = issue_pairs(target_model, project)

    assert ("MISSING_REQUIRED_COLUMN", "site") not in issues


def test_schema_aware_append_ignores_required_generated_columns() -> None:
    target_model: TargetModel = _minimal_target_model(
        {
            "site": {
                "required": True,
                "public_id": "site_id",
                "columns": {
                    "site_name": {"required": True},
                    "site_slug": {"required": True, "generated": True},
                },
            }
        }
    )
    project = ShapeShiftProject(
        cfg={
            "metadata": {"name": "append-generated-column", "type": "shapeshifter-project"},
            "entities": {
                "site": {
                    "public_id": "site_id",
                    "columns": ["site_name", "site_slug"],
                    "append": [
                        {
                            "type": "fixed",
                            "columns": ["site_name"],
                            "values": [["Append Site"]],
                        }
                    ],
                }
            },
        }
    )

    codes = [issue.code for issue in TargetModelConformanceValidator().validate(target_model, project)]

    assert "APPEND_MISSING_REQUIRED_COLUMN" not in codes


def test_core_conformance_keeps_alias_like_names_strict() -> None:
    target_model: TargetModel = load_target_model()
    project = ShapeShiftProject(
        cfg={
            "metadata": {
                "name": "sead:alias-like-columns",
                "type": "shapeshifter-project",
                "version": "1.0.0",
            },
            "entities": {
                "location": {
                    "public_id": "location_id",
                    "columns": ["location_name"],
                    "foreign_keys": [{"entity": "location_type"}],
                },
                "location_type": {
                    "public_id": "location_type_id",
                    "columns": ["location_type"],
                },
                "site": {
                    "public_id": "site_id",
                    "columns": ["site_name"],
                    "foreign_keys": [{"entity": "location"}],
                },
                "sample_group": {
                    "public_id": "sample_group_id",
                    "keys": ["site_id"],
                    "extra_columns": {"method_id": None, "sample_group_name": None},
                    "foreign_keys": [{"entity": "site"}, {"entity": "method"}],
                },
                "sample": {
                    "public_id": "physical_sample_id",
                    "extra_columns": {"sample_name": None},
                    "foreign_keys": [{"entity": "sample_group"}, {"entity": "sample_type"}],
                },
                "sample_type": {
                    "public_id": "sample_type_id",
                    "extra_columns": {"sample_type_name": None},
                },
                "method": {
                    "public_id": "method_id",
                    "columns": ["method_name", "description", "sead_method_group_id"],
                },
                "dataset": {
                    "public_id": "dataset_id",
                    "extra_columns": {"dataset_name": None, "data_type_id": None},
                    "foreign_keys": [{"entity": "method"}],
                },
                "analysis_entity": {
                    "public_id": "analysis_entity_id",
                    "foreign_keys": [{"entity": "sample"}, {"entity": "dataset"}],
                },
            },
        }
    )

    issues = set(issue_pairs(target_model, project))

    assert ("MISSING_REQUIRED_COLUMN", "sample_type") in issues
    assert ("MISSING_REQUIRED_COLUMN", "method") in issues


def test_core_conformance_reports_known_gaps_for_full_arbodat_project() -> None:
    target_model: TargetModel = load_target_model()
    project: ShapeShiftProject = load_real_project("arbodat")

    expected_errors: list[tuple[str, str]] = [
        ("CONDITIONAL_FK_AWAITING_RECONCILIATION", "location"),
        ("MISSING_REQUIRED_COLUMN", "relative_dating"),
        ("MISSING_REQUIRED_FOREIGN_KEY_TARGET", "abundance_modification"),
        ("MISSING_REQUIRED_FOREIGN_KEY_TARGET", "abundance_property"),
        ("MISSING_REQUIRED_FOREIGN_KEY_TARGET", "relative_dating"),
        ("UNEXPECTED_PUBLIC_ID", "relative_dating"),
    ]

    issues: list[ConformanceIssue] = TargetModelConformanceValidator().validate(target_model, project)
    actual_issues = [(issue.code, issue.entity) for issue in issues]
    # print('\n'.join(f'{x.code};{x.entity};{x.message}' for x in issues))
    assert sorted(actual_issues) == sorted(expected_errors)


def test_core_conformance_current_corpus_issue_families_are_stable() -> None:
    target_model: TargetModel = load_target_model()
    corpus: dict[str, ShapeShiftProject] = {
        "sead_arbodat_core": load_project("sead_arbodat_core.yml"),
        "sead_missing_sample_group": load_project("sead_missing_sample_group.yml"),
        "arbodat_full": load_real_project("arbodat"),
    }

    issue_summary: dict[str, Counter[str | None]] = {
        name: Counter(code for code, _entity in issue_pairs(target_model, project)) for name, project in corpus.items()
    }
    expected_summary: dict[str, Counter[str]] = {
        "sead_arbodat_core": Counter(
            {
                "MISSING_REQUIRED_FOREIGN_KEY_TARGET": 5,
                "MISSING_REQUIRED_COLUMN": 5,
                "MISSING_REQUIRED_ENTITY": 5,
                "MISSING_BRIDGE_ENTITY": 1,
                "CONDITIONAL_FK_AWAITING_RECONCILIATION": 1,
            }
        ),
        "sead_missing_sample_group": Counter(
            {
                "MISSING_REQUIRED_COLUMN": 8,
                "MISSING_REQUIRED_FOREIGN_KEY_TARGET": 6,
                "MISSING_REQUIRED_ENTITY": 6,
                "UNEXPECTED_PUBLIC_ID": 1,
                "MISSING_BRIDGE_ENTITY": 1,
                "CONDITIONAL_FK_AWAITING_RECONCILIATION": 1,
            }
        ),
        "arbodat_full": Counter(
            {
                "MISSING_REQUIRED_COLUMN": 15,
                "MISSING_REQUIRED_FOREIGN_KEY_TARGET": 13,
                "ORPHAN_FACT_ENTITY": 3,
                "MISSING_REQUIRED_ENTITY": 2,
                "UNEXPECTED_PUBLIC_ID": 1,
                "CONDITIONAL_FK_AWAITING_RECONCILIATION": 1,
                "MISSING_INDUCED_REQUIRED_ENTITY": 1,
            }
        ),
    }
    assert issue_summary == expected_summary


def _minimal_target_model(entities: dict) -> TargetModel:
    return TargetModel.model_validate({"model": {"name": "test", "version": "1.0"}, "entities": entities})


def _minimal_project(entities: dict, options: dict | None = None) -> ShapeShiftProject:
    return ShapeShiftProject(
        cfg={"metadata": {"name": "test", "type": "shapeshifter-project"}, "entities": entities, "options": options or {}}
    )


def test_conditional_foreign_key_awaits_reconciliation_without_project_only_errors() -> None:
    target_model = _minimal_target_model(
        {
            "location": {
                "public_id": "location_id",
                "foreign_keys": [{"entity": "location_type", "required_when": {"has_new_rows": "location"}}],
            },
            "location_type": {"public_id": "location_type_id"},
        }
    )
    project = _minimal_project({"location": {"public_id": "location_id", "columns": ["location_name"]}})

    issues = TargetModelConformanceValidator().validate(target_model, project)

    assert [(issue.code, issue.severity, issue.entity) for issue in issues] == [
        ("CONDITIONAL_FK_AWAITING_RECONCILIATION", "info", "location")
    ]


def test_conditional_foreign_key_status_is_not_promoted_by_severity_override() -> None:
    target_model = _minimal_target_model(
        {
            "location": {
                "public_id": "location_id",
                "foreign_keys": [{"entity": "location_type", "required_when": {"has_new_rows": "location"}}],
            },
            "location_type": {"public_id": "location_type_id"},
        }
    )
    project = _minimal_project(
        {"location": {"public_id": "location_id", "columns": ["location_name"]}},
        options={"validation": {"severity_overrides": {"conditional_foreign_key": "error"}}},
    )

    issues = TargetModelConformanceValidator().validate(target_model, project)

    assert [(issue.code, issue.severity) for issue in issues] == [("CONDITIONAL_FK_AWAITING_RECONCILIATION", "info")]


def test_conditional_foreign_key_status_is_omitted_when_source_is_absent() -> None:
    target_model = _minimal_target_model(
        {
            "location": {
                "foreign_keys": [{"entity": "location_type", "required_when": {"has_new_rows": "location"}}],
            },
            "location_type": {"public_id": "location_type_id"},
        }
    )

    issues = TargetModelConformanceValidator().validate(target_model, _minimal_project({}))

    assert issues == []


def test_conditional_foreign_key_does_not_change_static_requirements() -> None:
    target_model = _minimal_target_model(
        {
            "location": {
                "public_id": "location_id",
                "columns": {"location_name": {"required": True}},
                "foreign_keys": [
                    {"entity": "location_type", "required_when": {"has_new_rows": "location"}},
                    {"entity": "site", "required": True},
                ],
            },
            "location_type": {"public_id": "location_type_id"},
            "site": {"required": True, "public_id": "site_id"},
        }
    )
    project = _minimal_project({"location": {"public_id": "location_id", "columns": ["location_id"]}})

    issues = TargetModelConformanceValidator().validate(target_model, project)
    issue_pairs_with_severity = {(issue.code, issue.entity, issue.severity) for issue in issues}

    assert ("CONDITIONAL_FK_AWAITING_RECONCILIATION", "location", "info") in issue_pairs_with_severity
    assert ("MISSING_REQUIRED_COLUMN", "location", "error") in issue_pairs_with_severity
    assert ("MISSING_REQUIRED_ENTITY", "site", "error") in issue_pairs_with_severity
    assert ("MISSING_REQUIRED_FOREIGN_KEY_TARGET", "location", "error") in issue_pairs_with_severity


def test_public_id_validator_produces_missing_public_id_when_project_entity_has_none() -> None:
    """PublicIdConformanceValidator reports MISSING_PUBLIC_ID when the spec declares a public_id
    but the project entity omits it entirely."""
    target_model: TargetModel = _minimal_target_model({"location": {"public_id": "location_id", "required": True}})
    project: ShapeShiftProject = _minimal_project({"location": {"columns": ["location_name"]}})  # no public_id

    codes: list[str | None] = [issue.code for issue in TargetModelConformanceValidator().validate(target_model, project)]

    assert "MISSING_PUBLIC_ID" in codes


def test_public_id_validator_is_silent_when_spec_declares_no_public_id() -> None:
    """PublicIdConformanceValidator produces no issue when the target spec does not declare a public_id,
    regardless of what the project entity carries."""
    target_model: TargetModel = _minimal_target_model({"location": {"required": True}})  # no public_id in spec
    project: ShapeShiftProject = _minimal_project({"location": {"public_id": "location_id", "columns": ["location_name"]}})

    issues: list[ConformanceIssue] = TargetModelConformanceValidator().validate(target_model, project)

    assert not any(
        (issue.code or "").startswith("MISSING_PUBLIC_ID") or (issue.code or "").startswith("UNEXPECTED_PUBLIC_ID") for issue in issues
    )


def test_disabled_rules_skip_named_conformance_validator() -> None:
    """Disabled conformance rules should be skipped by registry key."""
    target_model: TargetModel = TargetModel.model_validate(
        {
            "model": {"name": "test", "version": "1.0"},
            "naming": {"public_id_suffix": "_id"},
            "entities": {"location": {}},
        }
    )
    project: ShapeShiftProject = _minimal_project(
        {"location": {"public_id": "location_identifier", "columns": ["location_name"]}},
        options={"validation": {"disabled_rules": ["naming_convention"]}},
    )

    codes: list[str | None] = [issue.code for issue in TargetModelConformanceValidator().validate(target_model, project)]

    assert "PUBLIC_ID_NAMING_VIOLATION" not in codes


# ---------------------------------------------------------------------------
# InducedRequirementConformanceValidator
# ---------------------------------------------------------------------------


def test_induced_requirement_emits_issue_when_optional_entity_present_but_required_fk_target_absent() -> None:
    """If non-required entity X is in the project and has a required FK to Y,
    then Y must also be present even though Y is not globally required."""
    target_model: TargetModel = _minimal_target_model(
        {
            "site": {
                "required": False,
                "foreign_keys": [{"entity": "location", "required": True}],
            },
            "location": {"required": False},
        }
    )
    # project has site but NOT location
    project: ShapeShiftProject = _minimal_project({"site": {"columns": ["site_name"]}})

    codes_entities: list[tuple[str | None, str | None]] = [
        (i.code, i.entity) for i in TargetModelConformanceValidator().validate(target_model, project)
    ]

    assert ("MISSING_INDUCED_REQUIRED_ENTITY", "location") in codes_entities


def test_induced_requirement_is_silent_when_required_fk_target_is_present() -> None:
    """No issue when the induced-required entity Y is already present in the project."""
    target_model: TargetModel = _minimal_target_model(
        {
            "site": {
                "required": False,
                "foreign_keys": [{"entity": "location", "required": True}],
            },
            "location": {"required": False},
        }
    )
    project: ShapeShiftProject = _minimal_project(
        {
            "site": {"columns": ["site_name"]},
            "location": {"columns": ["location_name"]},
        }
    )

    codes = [i.code for i in TargetModelConformanceValidator().validate(target_model, project)]

    assert "MISSING_INDUCED_REQUIRED_ENTITY" not in codes


def test_induced_requirement_is_silent_when_optional_entity_is_absent_from_project() -> None:
    """If X is not present in the project, its FK requirements are not induced."""
    target_model: TargetModel = _minimal_target_model(
        {
            "site": {
                "required": False,
                "foreign_keys": [{"entity": "location", "required": True}],
            },
            "location": {"required": False},
        }
    )
    # project has neither site nor location — no rule triggered
    project: ShapeShiftProject = _minimal_project({"sample": {"columns": ["sample_name"]}})

    codes: list[str | None] = [i.code for i in TargetModelConformanceValidator().validate(target_model, project)]

    assert "MISSING_INDUCED_REQUIRED_ENTITY" not in codes


def test_induced_requirement_does_not_double_report_when_entity_is_globally_required() -> None:
    """If X is globally required (required=True), the induced_requirements validator skips it;
    required_entity validator handles it. No MISSING_INDUCED_REQUIRED_ENTITY is emitted for X."""
    target_model: TargetModel = _minimal_target_model(
        {
            "site": {
                "required": True,  # globally required — handled by required_entity validator
                "foreign_keys": [{"entity": "location", "required": True}],
            },
            "location": {"required": False},
        }
    )
    # project has neither — required_entity will fire for site, not induced_requirements
    project: ShapeShiftProject = _minimal_project({"sample": {"columns": ["sample_name"]}})

    issues: list[ConformanceIssue] = TargetModelConformanceValidator().validate(target_model, project)
    codes: list[str | None] = [i.code for i in issues]

    assert "MISSING_REQUIRED_ENTITY" in codes  # site is globally required
    assert "MISSING_INDUCED_REQUIRED_ENTITY" not in codes  # induced validator skips globally-required entities


def test_induced_requirement_is_transitive() -> None:
    """If X (present) → Y (absent, required FK) → Z (absent, required FK), both Y and Z are reported."""
    target_model: TargetModel = _minimal_target_model(
        {
            "abundance": {
                "required": False,
                "foreign_keys": [{"entity": "taxon", "required": True}],
            },
            "taxon": {
                "required": False,
                "foreign_keys": [{"entity": "taxon_group", "required": True}],
            },
            "taxon_group": {"required": False},
        }
    )
    # only abundance is present — taxon and taxon_group must both be induced
    project: ShapeShiftProject = _minimal_project({"abundance": {"columns": ["count"]}})

    codes_entities: set[tuple[str | None, str | None]] = set(
        (i.code, i.entity) for i in TargetModelConformanceValidator().validate(target_model, project)
    )

    assert ("MISSING_INDUCED_REQUIRED_ENTITY", "taxon") in codes_entities
    assert ("MISSING_INDUCED_REQUIRED_ENTITY", "taxon_group") in codes_entities


# ---------------------------------------------------------------------------
# SourceTypeAppropriatenessConformanceValidator
# ---------------------------------------------------------------------------


def test_source_type_appropriateness_emits_issue_for_classifier_with_entity_type() -> None:
    """A classifier using type: entity should produce CLASSIFIER_WRONG_SOURCE_TYPE."""
    target_model: TargetModel = _minimal_target_model({"sample_type": {"role": "classifier"}})
    project: ShapeShiftProject = _minimal_project({"sample_type": {"type": "entity", "columns": ["sample_type_name"]}})

    codes_entities: list[tuple[str | None, str | None]] = [
        (i.code, i.entity) for i in TargetModelConformanceValidator().validate(target_model, project)
    ]

    assert ("CLASSIFIER_WRONG_SOURCE_TYPE", "sample_type") in codes_entities


def test_source_type_appropriateness_is_silent_for_classifier_with_fixed_type() -> None:
    """A classifier using type: fixed is correct — no issue."""
    target_model: TargetModel = _minimal_target_model({"sample_type": {"role": "classifier"}})
    project: ShapeShiftProject = _minimal_project({"sample_type": {"type": "fixed", "columns": ["system_id", "sample_type_id"]}})

    codes: list[str | None] = [i.code for i in TargetModelConformanceValidator().validate(target_model, project)]

    assert "CLASSIFIER_WRONG_SOURCE_TYPE" not in codes


def test_source_type_appropriateness_is_silent_for_classifier_with_sql_type() -> None:
    """A classifier using type: sql is correct — no issue."""
    target_model: TargetModel = _minimal_target_model({"sample_type": {"role": "classifier"}})
    project: ShapeShiftProject = _minimal_project({"sample_type": {"type": "sql", "source": "SELECT * FROM sample_types"}})

    codes: list[str | None] = [i.code for i in TargetModelConformanceValidator().validate(target_model, project)]

    assert "CLASSIFIER_WRONG_SOURCE_TYPE" not in codes


def test_source_type_appropriateness_is_silent_for_non_classifier_entity_type() -> None:
    """A non-classifier entity may use any source type — rule does not apply."""
    target_model: TargetModel = _minimal_target_model({"sample": {"role": "fact"}})
    project: ShapeShiftProject = _minimal_project({"sample": {"type": "entity", "columns": ["sample_name"]}})

    codes: list[str | None] = [i.code for i in TargetModelConformanceValidator().validate(target_model, project)]

    assert "CLASSIFIER_WRONG_SOURCE_TYPE" not in codes


def test_source_type_appropriateness_is_silent_when_classifier_has_no_type() -> None:
    """If the project entity omits type entirely, emit no issue (cannot determine intent)."""
    target_model: TargetModel = _minimal_target_model({"sample_type": {"role": "classifier"}})
    project: ShapeShiftProject = _minimal_project({"sample_type": {"columns": ["sample_type_name"]}})  # no type key

    codes: list[str | None] = [i.code for i in TargetModelConformanceValidator().validate(target_model, project)]

    assert "CLASSIFIER_WRONG_SOURCE_TYPE" not in codes


def test_induced_requirement_transitive_stops_at_present_intermediate() -> None:
    """If X (present) → Y (present) → Z (absent), Z is still reported because Y is present."""
    target_model: TargetModel = _minimal_target_model(
        {
            "abundance": {
                "required": False,
                "foreign_keys": [{"entity": "taxon", "required": True}],
            },
            "taxon": {
                "required": False,
                "foreign_keys": [{"entity": "taxon_group", "required": True}],
            },
            "taxon_group": {"required": False},
        }
    )
    # both abundance and taxon are present; taxon_group is missing
    project: ShapeShiftProject = _minimal_project(
        {
            "abundance": {"columns": ["count"]},
            "taxon": {"columns": ["taxon_name"]},
        }
    )

    codes_entities: set[tuple[str | None, str | None]] = set(
        (i.code, i.entity) for i in TargetModelConformanceValidator().validate(target_model, project)
    )

    assert ("MISSING_INDUCED_REQUIRED_ENTITY", "taxon_group") in codes_entities
    assert ("MISSING_INDUCED_REQUIRED_ENTITY", "taxon") not in codes_entities  # taxon is present


def test_direct_public_id_fks_allow_missing_targets_and_report_pending_checks() -> None:
    target_model = _minimal_target_model(
        {
            "sample": {
                "foreign_keys": [
                    {"entity": "optional_dataset"},
                    {"entity": "required_dataset", "required": True},
                    {"entity": "conditional_dataset", "required_when": {"has_new_rows": "sample"}},
                ],
            },
            "optional_dataset": {"public_id": "optional_dataset_id", "target_table": "public.optional_dataset"},
            "required_dataset": {"public_id": "required_dataset_id", "target_table": "public.required_dataset"},
            "conditional_dataset": {"public_id": "conditional_dataset_id", "target_table": "public.conditional_dataset"},
        }
    )
    project = _minimal_project(
        {
            "sample": {
                "columns": ["optional_dataset_id", "required_dataset_id", "conditional_dataset_id"],
                "foreign_key_value_sources": {
                    "optional_dataset": "public_id",
                    "required_dataset": "public_id",
                    "conditional_dataset": "public_id",
                },
            }
        },
        options={"validation": {"severity_overrides": {"direct_fk_pending_check": "error"}}},
    )

    issues = TargetModelConformanceValidator().validate(target_model, project)
    codes = [issue.code for issue in issues]

    pending = [issue for issue in issues if issue.code == "DIRECT_FK_TARGET_CHECK_PENDING"]
    assert len(pending) == 3
    assert {issue.severity for issue in pending} == {"info"}
    assert "MISSING_REQUIRED_FOREIGN_KEY_TARGET" not in codes
    assert "MISSING_INDUCED_REQUIRED_ENTITY" not in codes
    assert "CONDITIONAL_FK_AWAITING_RECONCILIATION" in codes


def test_system_id_value_source_keeps_local_link_check_and_has_no_pending_check() -> None:
    target_model = _minimal_target_model(
        {
            "sample": {"foreign_keys": [{"entity": "dataset", "required": True}]},
            "dataset": {"public_id": "dataset_id"},
        }
    )
    project = _minimal_project(
        {
            "sample": {
                "columns": ["dataset_id"],
                "foreign_keys": [{"entity": "dataset", "local_keys": ["dataset_id"], "remote_keys": ["dataset_id"]}],
                "foreign_key_value_sources": {"dataset": "system_id"},
            },
            "dataset": {"public_id": "dataset_id", "columns": ["dataset_name"]},
        }
    )

    issues = TargetModelConformanceValidator().validate(target_model, project)

    assert not any(issue.code == "DIRECT_FK_TARGET_CHECK_PENDING" for issue in issues)
    assert not any(issue.code == "MISSING_REQUIRED_FOREIGN_KEY_TARGET" for issue in issues)


def test_direct_public_id_fk_does_not_satisfy_globally_required_entity() -> None:
    target_model = _minimal_target_model(
        {
            "sample": {"foreign_keys": [{"entity": "dataset", "required": True}]},
            "dataset": {"required": True, "public_id": "dataset_id", "target_table": "public.dataset"},
        }
    )
    project = _minimal_project({"sample": {"columns": ["dataset_id"], "foreign_key_value_sources": {"dataset": "public_id"}}})

    issues = TargetModelConformanceValidator().validate(target_model, project)

    assert any(issue.code == "MISSING_REQUIRED_ENTITY" and issue.entity == "dataset" for issue in issues)
    assert not any(issue.code == "MISSING_REQUIRED_FOREIGN_KEY_TARGET" for issue in issues)
    assert not any(issue.code == "MISSING_INDUCED_REQUIRED_ENTITY" for issue in issues)


@pytest.mark.parametrize(
    ("target_entities", "source_entity", "expected_code"),
    [
        ({}, {"foreign_key_value_sources": {"dataset": "public_id"}}, "DIRECT_FK_RELATIONSHIP_UNKNOWN"),
        (
            {
                "sample": {"foreign_keys": [{"entity": "dataset", "via": "sample_dataset"}]},
                "dataset": {"public_id": "dataset_id", "target_table": "public.dataset"},
            },
            {"columns": ["dataset_id"], "foreign_key_value_sources": {"dataset": "public_id"}},
            "DIRECT_FK_VIA_UNSUPPORTED",
        ),
        (
            {
                "sample": {"foreign_keys": [{"entity": "dataset"}]},
                "dataset": {"target_table": "public.dataset"},
            },
            {"columns": ["dataset_id"], "foreign_key_value_sources": {"dataset": "public_id"}},
            "DIRECT_FK_TARGET_PUBLIC_ID_MISSING",
        ),
        (
            {
                "sample": {"foreign_keys": [{"entity": "dataset"}]},
                "dataset": {"public_id": "dataset_id"},
            },
            {"columns": ["dataset_id"], "foreign_key_value_sources": {"dataset": "public_id"}},
            "DIRECT_FK_TARGET_TABLE_MISSING",
        ),
        (
            {
                "sample": {"foreign_keys": [{"entity": "dataset"}]},
                "dataset": {"public_id": "dataset_id", "target_table": "public.dataset"},
            },
            {
                "columns": ["dataset_id"],
                "foreign_keys": [{"entity": "dataset", "local_keys": ["dataset_id"], "remote_keys": ["dataset_id"]}],
                "foreign_key_value_sources": {"dataset": "public_id"},
            },
            "DIRECT_FK_CORE_LINK_CONFLICT",
        ),
        (
            {
                "sample": {"foreign_keys": [{"entity": "dataset"}]},
                "dataset": {"public_id": "dataset_id", "target_table": "public.dataset"},
            },
            {"columns": ["sample_name"], "foreign_key_value_sources": {"dataset": "public_id"}},
            "DIRECT_FK_OUTPUT_COLUMN_MISSING",
        ),
    ],
)
def test_invalid_direct_public_id_fk_reports_specific_code(target_entities: dict, source_entity: dict, expected_code: str) -> None:
    if "sample" not in target_entities and expected_code == "DIRECT_FK_RELATIONSHIP_UNKNOWN":
        target_entities = {"sample": {"foreign_keys": [{"entity": "dataset", "required": True}]}}
    target_model = _minimal_target_model(target_entities)
    project_entities = {"sample": source_entity}
    if expected_code == "DIRECT_FK_CORE_LINK_CONFLICT":
        project_entities["dataset"] = {"public_id": "dataset_id", "columns": ["dataset_name"]}
    project = _minimal_project(project_entities)

    codes = [issue.code for issue in TargetModelConformanceValidator().validate(target_model, project)]

    assert expected_code in codes
    if expected_code == "DIRECT_FK_RELATIONSHIP_UNKNOWN":
        assert "MISSING_REQUIRED_FOREIGN_KEY_TARGET" in codes


def test_direct_public_id_column_dropped_by_unnest_is_rejected() -> None:
    target_model = _minimal_target_model(
        {
            "sample": {"foreign_keys": [{"entity": "dataset"}]},
            "dataset": {"public_id": "dataset_id", "target_table": "public.dataset"},
        }
    )
    project = _minimal_project(
        {
            "sample": {
                "columns": ["record_key", "dataset_id"],
                "foreign_key_value_sources": {"dataset": "public_id"},
                "unnest": {
                    "id_vars": ["record_key"],
                    "value_vars": ["dataset_id"],
                    "var_name": "attribute",
                    "value_name": "value",
                },
            }
        }
    )

    codes = [issue.code for issue in TargetModelConformanceValidator().validate(target_model, project)]

    assert "DIRECT_FK_OUTPUT_COLUMN_MISSING" in codes


def test_direct_public_id_fk_counts_as_fact_path_to_lookup() -> None:
    target_model = TargetModel.model_validate(
        {
            "model": {"name": "test", "version": "1.0"},
            "constraints": [{"type": "no_orphan_facts"}],
            "entities": {
                "dataset": {"role": "lookup", "public_id": "dataset_id", "target_table": "public.dataset"},
                "sample": {
                    "role": "fact",
                    "foreign_keys": [{"entity": "dataset", "required": True}],
                },
            },
        }
    )
    project = _minimal_project({"sample": {"columns": ["dataset_id"], "foreign_key_value_sources": {"dataset": "public_id"}}})

    issues = TargetModelConformanceValidator().validate(target_model, project)

    assert not any(issue.code == "ORPHAN_FACT_ENTITY" for issue in issues)


def test_no_orphan_facts_is_silent_when_constraint_is_not_declared() -> None:
    """The orphan-fact rule should only run when the target model declares that global constraint."""
    target_model: TargetModel = _minimal_target_model(
        {
            "dataset": {"role": "lookup", "required": True},
            "analysis_entity": {"role": "fact", "required": True},
        }
    )
    project: ShapeShiftProject = _minimal_project(
        {"analysis_entity": {"columns": ["analysis_name"]}, "dataset": {"columns": ["dataset_name"]}}
    )

    codes: list[str | None] = [i.code for i in TargetModelConformanceValidator().validate(target_model, project)]

    assert "ORPHAN_FACT_ENTITY" not in codes


def test_no_orphan_facts_emits_issue_for_fact_without_required_lookup_path() -> None:
    """A fact with no path to any required lookup or classifier should be reported when the constraint is enabled."""
    target_model: TargetModel = TargetModel.model_validate(
        {
            "model": {"name": "test", "version": "1.0"},
            "constraints": [{"type": "no_orphan_facts"}],
            "entities": {
                "dataset": {"role": "lookup", "required": True},
                "analysis_entity": {"role": "fact", "required": True},
            },
        }
    )
    project: ShapeShiftProject = _minimal_project(
        {"analysis_entity": {"columns": ["analysis_name"]}, "dataset": {"columns": ["dataset_name"]}}
    )

    issues = TargetModelConformanceValidator().validate(target_model, project)

    assert any(issue.code == "ORPHAN_FACT_ENTITY" and issue.entity == "analysis_entity" for issue in issues)
    assert next(issue for issue in issues if issue.code == "ORPHAN_FACT_ENTITY").severity == "warning"


def test_no_orphan_facts_uses_error_severity_when_constraint_is_strict() -> None:
    """Strict orphan-fact constraints should be promoted from warning to error."""
    target_model: TargetModel = TargetModel.model_validate(
        {
            "model": {"name": "test", "version": "1.0"},
            "constraints": [{"type": "no_orphan_facts", "required": "strict"}],
            "entities": {
                "dataset": {"role": "lookup", "required": True},
                "analysis_entity": {"role": "fact", "required": True},
            },
        }
    )
    project: ShapeShiftProject = _minimal_project(
        {"analysis_entity": {"columns": ["analysis_name"]}, "dataset": {"columns": ["dataset_name"]}}
    )

    issues: list[ConformanceIssue] = TargetModelConformanceValidator().validate(target_model, project)

    assert any(issue.code == "ORPHAN_FACT_ENTITY" and issue.severity == "error" for issue in issues)


def test_no_orphan_facts_accepts_transitive_required_lookup_path() -> None:
    """A fact linked transitively to a required lookup should satisfy the orphan-fact rule."""
    target_model: TargetModel = TargetModel.model_validate(
        {
            "model": {"name": "test", "version": "1.0"},
            "constraints": [{"type": "no_orphan_facts"}],
            "entities": {
                "site": {"role": "lookup", "required": True},
                "sample_group": {"role": "bridge", "required": True},
                "sample": {"role": "fact", "required": True},
            },
        }
    )
    project: ShapeShiftProject = _minimal_project(
        {
            "site": {"public_id": "site_id", "columns": ["site_name"]},
            "sample_group": {
                "public_id": "sample_group_id",
                "columns": ["sample_group_name"],
                "foreign_keys": [{"entity": "site", "local_keys": ["site_id"], "remote_keys": ["site_id"]}],
            },
            "sample": {
                "public_id": "sample_id",
                "columns": ["sample_name"],
                "foreign_keys": [{"entity": "sample_group", "local_keys": ["sample_group_id"], "remote_keys": ["sample_group_id"]}],
            },
        }
    )

    codes: list[str | None] = [i.code for i in TargetModelConformanceValidator().validate(target_model, project)]

    assert "ORPHAN_FACT_ENTITY" not in codes


def test_source_type_appropriateness_emits_warning_by_default() -> None:
    """Classifier source-type mismatches should stay advisory unless overridden."""
    target_model: TargetModel = _minimal_target_model(
        {
            "taxon": {
                "role": "classifier",
                "required": True,
            }
        }
    )
    project: ShapeShiftProject = _minimal_project({"taxon": {"type": "entity", "columns": ["taxon_name"]}})

    issues: list[ConformanceIssue] = TargetModelConformanceValidator().validate(target_model, project)

    assert any(issue.code == "CLASSIFIER_WRONG_SOURCE_TYPE" and issue.severity == "warning" for issue in issues)


def test_rule_severity_override_promotes_phase_four_rule_to_error() -> None:
    """Project severity overrides should replace the default severity for a conformance rule."""
    target_model: TargetModel = _minimal_target_model(
        {
            "taxon": {
                "role": "classifier",
                "required": True,
            }
        }
    )
    project: ShapeShiftProject = ShapeShiftProject(
        cfg={
            "metadata": {"name": "severity-override-example", "type": "shapeshifter-project"},
            "entities": {
                "taxon": {
                    "type": "entity",
                    "columns": ["taxon_name"],
                }
            },
            "options": {"validation": {"severity_overrides": {"source_type_appropriateness": "error"}}},
        }
    )

    issues: list[ConformanceIssue] = TargetModelConformanceValidator().validate(target_model, project)

    assert any(issue.code == "CLASSIFIER_WRONG_SOURCE_TYPE" and issue.severity == "error" for issue in issues)
