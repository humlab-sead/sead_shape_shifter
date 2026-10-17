"""Tests for insert dependency planning."""

from __future__ import annotations

import pytest

from src.target_model.insert_dependencies import (
    AGGREGATE_PARENT_EDGE,
    PRESENT_OPTIONAL_FOREIGN_KEY_EDGE,
    REQUIRED_FOREIGN_KEY_EDGE,
    InsertDependencyEdge,
    build_insert_plan,
)
from src.target_model.models import TargetModel


def _model(entities: dict) -> TargetModel:
    return TargetModel.model_validate({"model": {"name": "Test Model", "version": "1.0.0"}, "entities": entities})


def _chain_model() -> TargetModel:
    return _model(
        {
            "sample": {"role": "fact", "public_id": "physical_sample_id"},
            "sample_note": {
                "role": "fact",
                "public_id": "sample_note_id",
                "aggregate_parent": "sample",
                "foreign_keys": [{"entity": "sample", "required": True}],
            },
        }
    )


def test_aggregate_child_is_ordered_after_its_parent() -> None:
    plan = build_insert_plan(_chain_model(), ["sample_note", "sample"])

    assert plan.is_acyclic
    assert plan.order == ("sample", "sample_note")
    assert plan.cycles == ()


def test_aggregate_parent_and_required_foreign_key_are_both_recorded() -> None:
    plan = build_insert_plan(_chain_model(), ["sample", "sample_note"])

    reasons = {(edge.entity, edge.requires, edge.reason) for edge in plan.edges}

    assert reasons == {
        ("sample_note", "sample", AGGREGATE_PARENT_EDGE),
        ("sample_note", "sample", REQUIRED_FOREIGN_KEY_EDGE),
    }


def test_reference_only_parent_creates_no_edge() -> None:
    plan = build_insert_plan(_chain_model(), ["sample_note"])

    assert plan.is_acyclic
    assert plan.order == ("sample_note",)
    assert plan.edges == ()


def test_optional_foreign_key_is_ignored_until_the_caller_reports_it_present() -> None:
    model = _model(
        {
            "alpha": {"role": "fact", "public_id": "alpha_id"},
            "beta": {
                "role": "fact",
                "public_id": "beta_id",
                "foreign_keys": [{"entity": "alpha", "required": False}],
            },
        }
    )

    without_optional = build_insert_plan(model, ["alpha", "beta"])
    with_optional = build_insert_plan(model, ["alpha", "beta"], present_optional_foreign_keys=[("beta", "alpha")])

    assert without_optional.order == ("alpha", "beta")
    assert without_optional.edges == ()
    assert with_optional.order == ("alpha", "beta")
    assert with_optional.edges == (InsertDependencyEdge(entity="beta", requires="alpha", reason=PRESENT_OPTIONAL_FOREIGN_KEY_EDGE),)


def test_conditional_optional_foreign_key_cycle_is_reported_only_when_present() -> None:
    model = _model(
        {
            "alpha": {
                "role": "fact",
                "public_id": "alpha_id",
                "foreign_keys": [{"entity": "beta", "required": False}],
            },
            "beta": {
                "role": "fact",
                "public_id": "beta_id",
                "foreign_keys": [{"entity": "alpha", "required": True}],
            },
        }
    )

    acyclic = build_insert_plan(model, ["alpha", "beta"])
    cyclic = build_insert_plan(model, ["alpha", "beta"], present_optional_foreign_keys=[("alpha", "beta")])

    assert acyclic.is_acyclic
    assert acyclic.order == ("alpha", "beta")
    assert cyclic.cycles == (("alpha", "beta"),)


def test_conditional_foreign_key_is_required_when_its_owner_is_inserted() -> None:
    model = _model(
        {
            "alpha": {"role": "fact", "public_id": "alpha_id"},
            "beta": {
                "role": "fact",
                "public_id": "beta_id",
                "foreign_keys": [{"entity": "alpha", "required_when": {"has_new_rows": "beta"}}],
            },
        }
    )

    plan = build_insert_plan(model, ["alpha", "beta"])

    assert plan.order == ("alpha", "beta")
    assert plan.edges == (InsertDependencyEdge(entity="beta", requires="alpha", reason=REQUIRED_FOREIGN_KEY_EDGE),)


def test_required_foreign_key_cycle_names_both_entities_and_keeps_a_partial_order() -> None:
    model = _model(
        {
            "alpha": {"role": "fact", "public_id": "alpha_id", "foreign_keys": [{"entity": "beta", "required": True}]},
            "beta": {"role": "fact", "public_id": "beta_id", "foreign_keys": [{"entity": "alpha", "required": True}]},
            "gamma": {"role": "lookup", "public_id": "gamma_id"},
        }
    )

    plan = build_insert_plan(model, ["alpha", "beta", "gamma"])

    assert not plan.is_acyclic
    assert plan.cycles == (("alpha", "beta"),)
    assert plan.order == ("gamma",)


def test_unrelated_cycle_outside_the_insert_set_is_not_reported() -> None:
    model = _model(
        {
            "alpha": {"role": "fact", "public_id": "alpha_id", "foreign_keys": [{"entity": "beta", "required": True}]},
            "beta": {"role": "fact", "public_id": "beta_id", "foreign_keys": [{"entity": "alpha", "required": True}]},
            "gamma": {"role": "lookup", "public_id": "gamma_id"},
        }
    )

    plan = build_insert_plan(model, ["gamma"])

    assert plan.is_acyclic
    assert plan.order == ("gamma",)
    assert plan.edges == ()


def test_multi_level_dependency_order_is_deterministic() -> None:
    model = _model(
        {
            "root": {"role": "fact", "public_id": "root_id"},
            "middle": {
                "role": "fact",
                "public_id": "middle_id",
                "aggregate_parent": "root",
                "foreign_keys": [{"entity": "root", "required": True}],
            },
            "leaf": {
                "role": "fact",
                "public_id": "leaf_id",
                "aggregate_parent": "middle",
                "foreign_keys": [{"entity": "middle", "required": True}],
            },
            "sibling": {"role": "lookup", "public_id": "sibling_id"},
        }
    )

    first = build_insert_plan(model, ["sibling", "leaf", "middle", "root"])
    second = build_insert_plan(model, ["root", "middle", "leaf", "sibling"])

    assert first.order == ("root", "middle", "leaf", "sibling")
    assert first.order == second.order


def test_bridge_foreign_keys_do_not_create_direct_edges() -> None:
    model = _model(
        {
            "site": {"role": "lookup", "public_id": "site_id"},
            "location": {"role": "lookup", "public_id": "location_id"},
            "site_location": {"role": "bridge", "public_id": "site_location_id"},
            "site_detail": {
                "role": "fact",
                "public_id": "site_detail_id",
                "foreign_keys": [{"entity": "location", "required": True, "via": "site_location"}],
            },
        }
    )

    plan = build_insert_plan(model, ["site", "location", "site_location", "site_detail"])

    assert plan.is_acyclic
    assert ("site_detail", "location") not in {(edge.entity, edge.requires) for edge in plan.edges}


def test_self_referencing_optional_foreign_key_is_reported_only_when_present() -> None:
    model = _model(
        {
            "value_class": {
                "role": "classifier",
                "public_id": "value_class_id",
                "foreign_keys": [{"entity": "value_class", "required": False}],
            }
        }
    )

    without_self = build_insert_plan(model, ["value_class"])
    with_self = build_insert_plan(model, ["value_class"], present_optional_foreign_keys=[("value_class", "value_class")])

    assert without_self.is_acyclic
    assert with_self.cycles == (("value_class",),)


@pytest.mark.parametrize(
    ("insert_entities", "present_optional", "message"),
    [
        (["missing"], [], "Unknown insert entities: missing"),
        (["alpha"], [("missing", "alpha")], "Unknown entity 'missing' in present optional foreign keys"),
        (["alpha"], [("alpha", "missing")], "Unknown target entity 'missing' in present optional foreign keys"),
    ],
)
def test_unknown_entities_are_rejected(insert_entities: list[str], present_optional: list[tuple[str, str]], message: str) -> None:
    model = _model({"alpha": {"role": "fact", "public_id": "alpha_id"}})

    with pytest.raises(ValueError, match=message):
        build_insert_plan(model, insert_entities, present_optional_foreign_keys=present_optional)


def test_optional_pair_without_a_matching_foreign_key_is_rejected() -> None:
    model = _model(
        {
            "alpha": {"role": "fact", "public_id": "alpha_id"},
            "beta": {"role": "fact", "public_id": "beta_id", "foreign_keys": [{"entity": "alpha", "required": True}]},
        }
    )

    with pytest.raises(ValueError, match="has no optional foreign key"):
        build_insert_plan(model, ["alpha", "beta"], present_optional_foreign_keys=[("beta", "alpha")])


def test_empty_selection_returns_an_empty_plan() -> None:
    plan = build_insert_plan(_chain_model(), [])

    assert plan.order == ()
    assert plan.edges == ()
    assert plan.cycles == ()
    assert plan.is_acyclic
