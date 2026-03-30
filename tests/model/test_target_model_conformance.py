from collections import Counter
from pathlib import Path

import yaml

from src.model import ShapeShiftProject, TableConfig
from src.target_model.conformance import TargetModelConformanceValidator
from src.target_model.models import TargetModel

ROOT_DIR = Path(__file__).resolve().parents[2]
SPEC_PATH = ROOT_DIR / "target_models" / "specs" / "sead_v2.yml"
EXAMPLES_DIR = ROOT_DIR / "target_models" / "examples"
REAL_PROJECTS_DIR = ROOT_DIR / "tests" / "test_data" / "projects"


def load_target_model() -> TargetModel:
    return TargetModel.model_validate(yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8")))


def load_project(name: str) -> ShapeShiftProject:
    project_path = EXAMPLES_DIR / name
    return ShapeShiftProject(cfg=yaml.safe_load(project_path.read_text(encoding="utf-8")))


def load_real_project(project_name: str) -> ShapeShiftProject:
    project_path = REAL_PROJECTS_DIR / project_name / "shapeshifter.yml"
    return ShapeShiftProject(cfg=yaml.safe_load(project_path.read_text(encoding="utf-8")))


def issue_pairs(target_model: TargetModel, project: ShapeShiftProject) -> list[tuple[str, str | None]]:
    issues = TargetModelConformanceValidator().validate(target_model, project)
    return [(issue.code, issue.entity) for issue in issues]


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
    target_model = TargetModel.model_validate(
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

    issues = TargetModelConformanceValidator().validate(target_model, project)

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


def test_core_legacy_mode_matches_existing_fixture() -> None:
    target_model = load_target_model()
    project = load_project("sead_arbodat_core.yml")

    assert sorted(issue_pairs(target_model, project)) == sorted(
        [
            ("MISSING_REQUIRED_FOREIGN_KEY_TARGET", "analysis_entity"),
            ("MISSING_REQUIRED_COLUMN", "analysis_entity"),
            ("MISSING_REQUIRED_COLUMN", "method"),
            ("MISSING_REQUIRED_COLUMN", "sample_type"),
        ]
    )


def test_core_conformance_reports_missing_entity_and_wrong_public_id() -> None:
    target_model = load_target_model()
    project = load_project("sead_missing_sample_group.yml")

    issues = set(issue_pairs(target_model, project))

    assert ("MISSING_REQUIRED_ENTITY", "sample_group") in issues
    assert ("UNEXPECTED_PUBLIC_ID", "sample") in issues


def test_core_conformance_keeps_alias_like_names_strict() -> None:
    target_model = load_target_model()
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
    target_model = load_target_model()
    project = load_real_project("arbodat")

    assert sorted(issue_pairs(target_model, project)) == sorted(
        [
            ("MISSING_REQUIRED_FOREIGN_KEY_TARGET", "site"),
            ("MISSING_REQUIRED_FOREIGN_KEY_TARGET", "sample_group"),
            ("MISSING_REQUIRED_FOREIGN_KEY_TARGET", "sample_group"),
            ("MISSING_REQUIRED_COLUMN", "sample_type"),
            ("MISSING_REQUIRED_FOREIGN_KEY_TARGET", "analysis_entity"),
            ("MISSING_REQUIRED_COLUMN", "analysis_entity"),
            ("MISSING_REQUIRED_FOREIGN_KEY_TARGET", "abundance"),
            ("MISSING_INDUCED_REQUIRED_ENTITY", "taxa_tree_master"),
        ]
    )


def test_core_conformance_current_corpus_issue_families_are_stable() -> None:
    target_model = load_target_model()
    corpus = {
        "sead_arbodat_core": load_project("sead_arbodat_core.yml"),
        "sead_missing_sample_group": load_project("sead_missing_sample_group.yml"),
        "arbodat_full": load_real_project("arbodat"),
    }

    issue_summary = {name: Counter(code for code, _entity in issue_pairs(target_model, project)) for name, project in corpus.items()}

    assert issue_summary == {
        "sead_arbodat_core": Counter({"MISSING_REQUIRED_COLUMN": 3, "MISSING_REQUIRED_FOREIGN_KEY_TARGET": 1}),
        "sead_missing_sample_group": Counter(
            {
                "MISSING_REQUIRED_COLUMN": 5,
                "MISSING_REQUIRED_FOREIGN_KEY_TARGET": 3,
                "MISSING_REQUIRED_ENTITY": 1,
                "UNEXPECTED_PUBLIC_ID": 1,
            }
        ),
        "arbodat_full": Counter(
            {"MISSING_REQUIRED_FOREIGN_KEY_TARGET": 5, "MISSING_REQUIRED_COLUMN": 2, "MISSING_INDUCED_REQUIRED_ENTITY": 1}
        ),
    }


def _minimal_target_model(entities: dict) -> TargetModel:
    return TargetModel.model_validate({"model": {"name": "test", "version": "1.0"}, "entities": entities})


def _minimal_project(entities: dict) -> ShapeShiftProject:
    return ShapeShiftProject(cfg={"metadata": {"name": "test", "type": "shapeshifter-project"}, "entities": entities})


def test_public_id_validator_produces_missing_public_id_when_project_entity_has_none() -> None:
    """PublicIdConformanceValidator reports MISSING_PUBLIC_ID when the spec declares a public_id
    but the project entity omits it entirely."""
    target_model = _minimal_target_model({"location": {"public_id": "location_id", "required": True}})
    project = _minimal_project({"location": {"columns": ["location_name"]}})  # no public_id

    codes = [issue.code for issue in TargetModelConformanceValidator().validate(target_model, project)]

    assert "MISSING_PUBLIC_ID" in codes


def test_public_id_validator_is_silent_when_spec_declares_no_public_id() -> None:
    """PublicIdConformanceValidator produces no issue when the target spec does not declare a public_id,
    regardless of what the project entity carries."""
    target_model = _minimal_target_model({"location": {"required": True}})  # no public_id in spec
    project = _minimal_project({"location": {"public_id": "location_id", "columns": ["location_name"]}})

    issues = TargetModelConformanceValidator().validate(target_model, project)

    assert not any(issue.code.startswith("MISSING_PUBLIC_ID") or issue.code.startswith("UNEXPECTED_PUBLIC_ID") for issue in issues)


# ---------------------------------------------------------------------------
# InducedRequirementConformanceValidator
# ---------------------------------------------------------------------------


def test_induced_requirement_emits_issue_when_optional_entity_present_but_required_fk_target_absent() -> None:
    """If non-required entity X is in the project and has a required FK to Y,
    then Y must also be present even though Y is not globally required."""
    target_model = _minimal_target_model(
        {
            "site": {
                "required": False,
                "foreign_keys": [{"entity": "location", "required": True}],
            },
            "location": {"required": False},
        }
    )
    # project has site but NOT location
    project = _minimal_project({"site": {"columns": ["site_name"]}})

    codes_entities = [(i.code, i.entity) for i in TargetModelConformanceValidator().validate(target_model, project)]

    assert ("MISSING_INDUCED_REQUIRED_ENTITY", "location") in codes_entities


def test_induced_requirement_is_silent_when_required_fk_target_is_present() -> None:
    """No issue when the induced-required entity Y is already present in the project."""
    target_model = _minimal_target_model(
        {
            "site": {
                "required": False,
                "foreign_keys": [{"entity": "location", "required": True}],
            },
            "location": {"required": False},
        }
    )
    project = _minimal_project(
        {
            "site": {"columns": ["site_name"]},
            "location": {"columns": ["location_name"]},
        }
    )

    codes = [i.code for i in TargetModelConformanceValidator().validate(target_model, project)]

    assert "MISSING_INDUCED_REQUIRED_ENTITY" not in codes


def test_induced_requirement_is_silent_when_optional_entity_is_absent_from_project() -> None:
    """If X is not present in the project, its FK requirements are not induced."""
    target_model = _minimal_target_model(
        {
            "site": {
                "required": False,
                "foreign_keys": [{"entity": "location", "required": True}],
            },
            "location": {"required": False},
        }
    )
    # project has neither site nor location — no rule triggered
    project = _minimal_project({"sample": {"columns": ["sample_name"]}})

    codes = [i.code for i in TargetModelConformanceValidator().validate(target_model, project)]

    assert "MISSING_INDUCED_REQUIRED_ENTITY" not in codes


def test_induced_requirement_does_not_double_report_when_entity_is_globally_required() -> None:
    """If X is globally required (required=True), the induced_requirements validator skips it;
    required_entity validator handles it. No MISSING_INDUCED_REQUIRED_ENTITY is emitted for X."""
    target_model = _minimal_target_model(
        {
            "site": {
                "required": True,  # globally required — handled by required_entity validator
                "foreign_keys": [{"entity": "location", "required": True}],
            },
            "location": {"required": False},
        }
    )
    # project has neither — required_entity will fire for site, not induced_requirements
    project = _minimal_project({"sample": {"columns": ["sample_name"]}})

    issues = TargetModelConformanceValidator().validate(target_model, project)
    codes = [i.code for i in issues]

    assert "MISSING_REQUIRED_ENTITY" in codes  # site is globally required
    assert "MISSING_INDUCED_REQUIRED_ENTITY" not in codes  # induced validator skips globally-required entities


def test_induced_requirement_is_transitive() -> None:
    """If X (present) → Y (absent, required FK) → Z (absent, required FK), both Y and Z are reported."""
    target_model = _minimal_target_model(
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
    project = _minimal_project({"abundance": {"columns": ["count"]}})

    codes_entities = set((i.code, i.entity) for i in TargetModelConformanceValidator().validate(target_model, project))

    assert ("MISSING_INDUCED_REQUIRED_ENTITY", "taxon") in codes_entities
    assert ("MISSING_INDUCED_REQUIRED_ENTITY", "taxon_group") in codes_entities


# ---------------------------------------------------------------------------
# SourceTypeAppropriatenessConformanceValidator
# ---------------------------------------------------------------------------


def test_source_type_appropriateness_emits_issue_for_classifier_with_entity_type() -> None:
    """A classifier using type: entity should produce CLASSIFIER_WRONG_SOURCE_TYPE."""
    target_model = _minimal_target_model({"sample_type": {"role": "classifier"}})
    project = _minimal_project({"sample_type": {"type": "entity", "columns": ["sample_type_name"]}})

    codes_entities = [(i.code, i.entity) for i in TargetModelConformanceValidator().validate(target_model, project)]

    assert ("CLASSIFIER_WRONG_SOURCE_TYPE", "sample_type") in codes_entities


def test_source_type_appropriateness_is_silent_for_classifier_with_fixed_type() -> None:
    """A classifier using type: fixed is correct — no issue."""
    target_model = _minimal_target_model({"sample_type": {"role": "classifier"}})
    project = _minimal_project({"sample_type": {"type": "fixed", "columns": ["system_id", "sample_type_id"]}})

    codes = [i.code for i in TargetModelConformanceValidator().validate(target_model, project)]

    assert "CLASSIFIER_WRONG_SOURCE_TYPE" not in codes


def test_source_type_appropriateness_is_silent_for_classifier_with_sql_type() -> None:
    """A classifier using type: sql is correct — no issue."""
    target_model = _minimal_target_model({"sample_type": {"role": "classifier"}})
    project = _minimal_project({"sample_type": {"type": "sql", "source": "SELECT * FROM sample_types"}})

    codes = [i.code for i in TargetModelConformanceValidator().validate(target_model, project)]

    assert "CLASSIFIER_WRONG_SOURCE_TYPE" not in codes


def test_source_type_appropriateness_is_silent_for_non_classifier_entity_type() -> None:
    """A non-classifier entity may use any source type — rule does not apply."""
    target_model = _minimal_target_model({"sample": {"role": "fact"}})
    project = _minimal_project({"sample": {"type": "entity", "columns": ["sample_name"]}})

    codes = [i.code for i in TargetModelConformanceValidator().validate(target_model, project)]

    assert "CLASSIFIER_WRONG_SOURCE_TYPE" not in codes


def test_source_type_appropriateness_is_silent_when_classifier_has_no_type() -> None:
    """If the project entity omits type entirely, emit no issue (cannot determine intent)."""
    target_model = _minimal_target_model({"sample_type": {"role": "classifier"}})
    project = _minimal_project({"sample_type": {"columns": ["sample_type_name"]}})  # no type key

    codes = [i.code for i in TargetModelConformanceValidator().validate(target_model, project)]

    assert "CLASSIFIER_WRONG_SOURCE_TYPE" not in codes


def test_induced_requirement_transitive_stops_at_present_intermediate() -> None:
    """If X (present) → Y (present) → Z (absent), Z is still reported because Y is present."""
    target_model = _minimal_target_model(
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
    project = _minimal_project(
        {
            "abundance": {"columns": ["count"]},
            "taxon": {"columns": ["taxon_name"]},
        }
    )

    codes_entities = set((i.code, i.entity) for i in TargetModelConformanceValidator().validate(target_model, project))

    assert ("MISSING_INDUCED_REQUIRED_ENTITY", "taxon_group") in codes_entities
    assert ("MISSING_INDUCED_REQUIRED_ENTITY", "taxon") not in codes_entities  # taxon is present
