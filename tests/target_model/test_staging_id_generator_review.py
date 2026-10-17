"""Tests for scripts/review_staging_id_generators.py.

The tests exercise the pure derivation and classification functions with
controlled catalog facts. No database connection is opened.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

from src.target_model.models import TargetModel

MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "review_staging_id_generators.py"


def load_audit_module() -> ModuleType:
    """Load the audit script as a module for unit testing."""
    module_name = "tests.review_staging_id_generators_module"
    spec = importlib.util.spec_from_file_location(module_name, MODULE_PATH)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    sys.modules.pop(module_name, None)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _model(entities: dict) -> TargetModel:
    return TargetModel.model_validate({"model": {"name": "Test Model", "version": "1.0.0"}, "entities": entities})


def _candidate(module: ModuleType, **overrides) -> object:
    values = {
        "entity": "abundance_modification",
        "root_entity": "dataset",
        "root_identity_tracking": "tracked",
        "target_table": "tbl_abundance_modifications",
        "public_id": "abundance_modification_id",
        "chain_issues": (),
    }
    values.update(overrides)
    return module.CandidateChild(**values)


def _catalog(
    module: ModuleType,
    *,
    relations: int = 1,
    column: object | None = None,
    sequence: object | None = None,
    triggers: tuple = (),
) -> object:
    matches = tuple(
        module.RelationMatch(
            schema="public",
            name="tbl_abundance_modifications" if relations == 1 else f"tbl_abundance_modifications_{index}",
            oid=index + 1,
        )
        for index in range(relations)
    )
    if column is None and relations == 1:
        column = module.IdColumnInfo(
            name="abundance_modification_id",
            data_type="integer",
            identity_mode="",
            default_expression="nextval('public.tbl_abundance_modifications_abundance_modification_id_seq'::regclass)",
        )
    if sequence is None and relations == 1:
        sequence = module.SequenceInfo(
            name="public.tbl_abundance_modifications_abundance_modification_id_seq",
            increment=1,
            cycles=False,
            cache=1,
        )
    return module.RelationCatalog(matches=matches, column=column, sequence=sequence, insert_triggers=triggers)


class TestCandidateChildren:
    """Derivation of candidates from effective identity."""

    def test_only_aggregate_children_are_candidates(self) -> None:
        module = load_audit_module()
        model = _model(
            {
                "dataset": {"role": "lookup", "identity_tracking": "tracked", "reconciliation": "allocate", "public_id": "dataset_id"},
                "analysis_entity": {
                    "role": "fact",
                    "aggregate_parent": "dataset",
                    "target_table": "tbl_analysis_entities",
                    "public_id": "analysis_entity_id",
                },
                "sample": {"role": "fact", "target_table": "tbl_physical_samples", "public_id": "physical_sample_id"},
            }
        )

        candidates = module.candidate_children(model)

        assert [candidate.entity for candidate in candidates] == ["analysis_entity"]
        assert candidates[0].root_entity == "dataset"
        assert candidates[0].root_identity_tracking == "tracked"
        assert candidates[0].chain_issues == ()

    def test_invalid_chain_is_recorded_on_the_candidate(self) -> None:
        module = load_audit_module()
        model = _model(
            {
                "alpha": {"role": "fact", "aggregate_parent": "beta", "public_id": "alpha_id"},
                "beta": {"role": "fact", "aggregate_parent": "alpha", "public_id": "beta_id"},
            }
        )

        candidates = module.candidate_children(model)

        assert {candidate.entity for candidate in candidates} == {"alpha", "beta"}
        assert all("AGGREGATE_PARENT_CYCLE" in candidate.chain_issues for candidate in candidates)


class TestClassifyGenerator:
    """Generator support classification from catalog facts."""

    def test_serial_sequence_with_cache_one_is_supported(self) -> None:
        module = load_audit_module()

        report = module.classify_generator(_candidate(module), _catalog(module))

        assert report.status == module.SUPPORTED_STATUS
        assert report.reasons == ()
        assert report.cache == 1

    def test_identity_always_without_default_is_supported(self) -> None:
        module = load_audit_module()
        column = module.IdColumnInfo(name="abundance_modification_id", data_type="bigint", identity_mode="a", default_expression=None)

        report = module.classify_generator(_candidate(module), _catalog(module, column=column))

        assert report.status == module.SUPPORTED_STATUS
        assert report.identity_mode == "a"

    def test_sequence_cache_above_one_is_unsupported(self) -> None:
        module = load_audit_module()
        sequence = module.SequenceInfo(name="public.seq", increment=1, cycles=False, cache=10)

        report = module.classify_generator(_candidate(module), _catalog(module, sequence=sequence))

        assert report.status == module.UNSUPPORTED_STATUS
        assert report.reasons == ("sequence_cache_above_one:10",)

    def test_cycling_sequence_is_unsupported(self) -> None:
        module = load_audit_module()
        sequence = module.SequenceInfo(name="public.seq", increment=1, cycles=True, cache=1)

        report = module.classify_generator(_candidate(module), _catalog(module, sequence=sequence))

        assert report.reasons == ("cycling_sequence",)

    def test_non_positive_increment_is_unsupported(self) -> None:
        module = load_audit_module()
        sequence = module.SequenceInfo(name="public.seq", increment=-1, cycles=False, cache=1)

        report = module.classify_generator(_candidate(module), _catalog(module, sequence=sequence))

        assert report.reasons == ("non_positive_increment:-1",)

    def test_missing_relation_is_unsupported(self) -> None:
        module = load_audit_module()

        report = module.classify_generator(_candidate(module), _catalog(module, relations=0))

        assert report.status == module.UNSUPPORTED_STATUS
        assert report.reasons == ("relation_not_found",)

    def test_ambiguous_relation_is_unsupported(self) -> None:
        module = load_audit_module()

        report = module.classify_generator(_candidate(module), _catalog(module, relations=2))

        assert report.reasons == ("ambiguous_relation:public.tbl_abundance_modifications_0, public.tbl_abundance_modifications_1",)

    def test_missing_id_column_is_unsupported(self) -> None:
        module = load_audit_module()
        catalog = module.RelationCatalog(
            matches=(module.RelationMatch(schema="public", name="tbl_abundance_modifications", oid=1),),
            column=None,
        )

        report = module.classify_generator(_candidate(module), catalog)

        assert report.reasons == ("missing_id_column:abundance_modification_id",)

    def test_non_integer_id_column_is_unsupported(self) -> None:
        module = load_audit_module()
        column = module.IdColumnInfo(name="abundance_modification_id", data_type="text", identity_mode="", default_expression=None)

        report = module.classify_generator(_candidate(module), _catalog(module, column=column))

        assert report.reasons == ("unsupported_id_column_type:text",)

    def test_column_without_identity_or_default_has_no_generator(self) -> None:
        module = load_audit_module()
        column = module.IdColumnInfo(name="abundance_modification_id", data_type="integer", identity_mode="", default_expression=None)
        catalog = module.RelationCatalog(
            matches=(module.RelationMatch(schema="public", name="tbl_abundance_modifications", oid=1),),
            column=column,
            sequence=None,
        )

        report = module.classify_generator(_candidate(module), catalog)

        assert report.reasons == ("missing_id_generator",)

    def test_default_without_owned_sequence_is_unsupported(self) -> None:
        module = load_audit_module()
        column = module.IdColumnInfo(
            name="abundance_modification_id",
            data_type="integer",
            identity_mode="",
            default_expression="nextval('elsewhere.seq'::regclass)",
        )
        catalog = module.RelationCatalog(
            matches=(module.RelationMatch(schema="public", name="tbl_abundance_modifications", oid=1),),
            column=column,
            sequence=None,
        )

        report = module.classify_generator(_candidate(module), catalog)

        assert report.reasons == ("sequence_not_owned",)

    def test_enabled_insert_trigger_requires_manual_review(self) -> None:
        module = load_audit_module()
        triggers = (module.TriggerInfo(name="set_identifier", enabled=True),)

        report = module.classify_generator(_candidate(module), _catalog(module, triggers=triggers))

        assert report.status == module.MANUAL_REVIEW_STATUS
        assert report.reasons == ("enabled_insert_trigger:set_identifier",)
        assert not report.is_supported

    def test_disabled_insert_trigger_keeps_the_candidate_supported(self) -> None:
        module = load_audit_module()
        triggers = (module.TriggerInfo(name="set_identifier", enabled=False),)

        report = module.classify_generator(_candidate(module), _catalog(module, triggers=triggers))

        assert report.status == module.SUPPORTED_STATUS
        assert report.reasons == ()

    def test_invalid_chain_is_unsupported_before_catalog_checks(self) -> None:
        module = load_audit_module()
        candidate = _candidate(module, chain_issues=("INVALID_AGGREGATE_ROOT_IDENTITY",))

        report = module.classify_generator(candidate, _catalog(module))

        assert report.status == module.UNSUPPORTED_STATUS
        assert report.reasons == ("invalid_aggregate_chain:INVALID_AGGREGATE_ROOT_IDENTITY",)

    def test_missing_target_table_is_unsupported(self) -> None:
        module = load_audit_module()
        candidate = _candidate(module, target_table="")

        report = module.classify_generator(candidate, module.RelationCatalog())

        assert report.reasons == ("missing_target_table",)


class TestReporting:
    """Report shaping for table and JSON output."""

    def test_generator_labels(self) -> None:
        module = load_audit_module()
        catalog = _catalog(module)

        serial_report = module.classify_generator(_candidate(module), catalog)
        always_report = module.classify_generator(
            _candidate(module),
            _catalog(
                module,
                column=module.IdColumnInfo(name="id", data_type="integer", identity_mode="a", default_expression=None),
            ),
        )

        assert module.generator_label(serial_report) == "serial"
        assert module.generator_label(always_report) == "identity-always"

    def test_report_rows_include_generator_and_facts(self) -> None:
        module = load_audit_module()

        rows = module.report_rows([module.classify_generator(_candidate(module), _catalog(module))])

        assert rows[0]["entity"] == "abundance_modification"
        assert rows[0]["status"] == module.SUPPORTED_STATUS
        assert rows[0]["generator"] == "serial"
        assert rows[0]["relation"] == "public.tbl_abundance_modifications"

    @pytest.mark.parametrize(
        ("target_table", "expected"),
        [
            ("tbl_abundance_modifications", (None, "tbl_abundance_modifications")),
            ("public.tbl_abundance_modifications", ("public", "tbl_abundance_modifications")),
        ],
    )
    def test_split_target_table(self, target_table: str, expected: tuple[str | None, str]) -> None:
        module = load_audit_module()

        assert module._split_target_table(target_table) == expected
