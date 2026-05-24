"""Tests for constraint validators and orchestration."""

import pandas as pd
import pytest

from src.model import ForeignKeyConfig, ShapeShiftProject, TableConfig
from src.specifications.constraints import (
    ForeignKeyConstraintValidator,
    ForeignKeyConstraintViolation,
    ForeignKeyRuntimeOptions,
    Validators,
)


def build_project(*, local_entity: str = "orders", remote_entity: str = "customers", constraints: dict | None = None) -> ShapeShiftProject:
    cfg = {
        "entities": {
            local_entity: {
                "public_id": "order_public_id",
                "columns": ["order_id", "order_public_id", "customer_id"],
                "foreign_keys": [
                    {
                        "entity": remote_entity,
                        "local_keys": ["customer_id"],
                        "remote_keys": ["id"],
                        "constraints": constraints or {},
                    }
                ],
            },
            remote_entity: {"columns": ["id"]},
        }
    }
    return ShapeShiftProject(cfg=cfg)


def build_fk(*, local_entity: str = "orders", remote_entity: str = "customers", constraints: dict | None = None) -> ForeignKeyConfig:
    return (
        build_project(local_entity=local_entity, remote_entity=remote_entity, constraints=constraints)
        .get_table(local_entity)
        .foreign_keys[0]
    )


def test_validator_registry_lookup():
    """Registry returns stage-filtered and sub-key lookups."""
    validators = Validators.get_validators_for_stage("post-merge")
    assert validators, "expected post-merge validators"

    one_to_one_validator = Validators.get_validator_by_constraint("cardinality", "one_to_one")
    assert one_to_one_validator is not None


def test_pre_merge_null_and_uniqueness_checks():
    """Pre-merge validators should raise when constraints violated."""
    project = build_project(constraints={"allow_null_keys": False, "require_unique_left": True, "require_unique_right": True})
    fk: ForeignKeyConfig = project.get_table("orders").foreign_keys[0]
    entity: TableConfig = project.get_table("orders")
    validator = ForeignKeyConstraintValidator(local_entity=entity, fk=fk)

    local_df = pd.DataFrame({"order_id": [1, 2, 3], "order_public_id": [None, None, None], "customer_id": [1, 1, None]})
    remote_df = pd.DataFrame({"id": [1, 1]})

    with pytest.raises(ForeignKeyConstraintViolation, match="Null values"):
        validator.validate_before_merge(local_df=local_df, remote_df=remote_df)

    # Fix nulls but keep duplicate right keys to trigger unique right
    local_df["customer_id"] = [1, 1, 2]
    with pytest.raises(ForeignKeyConstraintViolation, match="duplicate left"):
        validator.validate_before_merge(local_df=local_df, remote_df=remote_df)


def test_post_merge_cardinality_and_unmatched_checks():
    """Post-merge validators enforce cardinality and unmatched rules."""
    project = build_project(
        constraints={
            "cardinality": "one_to_one",
            "allow_unmatched_left": False,
            "allow_unmatched_right": False,
        }
    )
    fk: ForeignKeyConfig = project.get_table("orders").foreign_keys[0]
    entity: TableConfig = project.get_table("orders")
    validator = ForeignKeyConstraintValidator(local_entity=entity, fk=fk)

    local_df = pd.DataFrame({"order_id": [1, 2], "order_public_id": [None, None], "customer_id": [1, 2]})
    remote_df = pd.DataFrame({"id": [1]})

    # Simulate a merge with unmatched rows and row count change
    linked_df = pd.DataFrame({"order_id": [1, 2], "customer_id": [1, 2], "_merge_indicator_customers": ["both", "left_only"]})

    validator.validate_before_merge(local_df=local_df, remote_df=remote_df)

    with pytest.raises(ForeignKeyConstraintViolation, match="unmatched left"):
        validator.validate_after_merge(
            local_df=local_df,
            remote_df=remote_df,
            linked_df=linked_df,
            merge_indicator_col="_merge_indicator_customers",
        )


def test_lookup_runtime_options_skip_strict_null_validation_for_targeted_case():
    """Lookup-style runtime options should bypass strict null-key validation."""
    cfg = {
        "entities": {
            "orders": {
                "columns": ["order_id", "customer_code"],
                "foreign_keys": [
                    {
                        "entity": "customers",
                        "local_keys": ["customer_code"],
                        "remote_keys": ["customer_code"],
                        "how": "left",
                        "constraints": {"cardinality": "many_to_one"},
                    }
                ],
            },
            "customers": {
                "columns": ["customer_code"],
                "public_id": "customer_id",
            },
        }
    }
    entity: TableConfig = ShapeShiftProject(cfg=cfg).get_table("orders")
    fk = entity.foreign_keys[0]
    validator = ForeignKeyConstraintValidator(
        local_entity=entity,
        fk=fk,
        runtime_options=ForeignKeyRuntimeOptions(enforce_strict_null_keys=False, use_null_safe_merge=True),
    )

    local_df = pd.DataFrame({"order_id": [1, 2], "customer_code": ["A", None]})
    remote_df = pd.DataFrame({"customer_code": ["A", None]})

    validator.validate_before_merge(local_df=local_df, remote_df=remote_df)


def test_pre_merge_null_check_exempts_rows_with_existing_public_id():
    """Rows with an existing public_id are treated as simple mappings and are exempt from strict null-key checks."""
    cfg = {
        "entities": {
            "orders": {
                "public_id": "order_public_id",
                "columns": ["order_id", "order_public_id", "customer_id"],
                "foreign_keys": [
                    {
                        "entity": "customers",
                        "local_keys": ["customer_id"],
                        "remote_keys": ["id"],
                        "constraints": {"allow_null_keys": False},
                    }
                ],
            },
            "customers": {"columns": ["id"]},
        }
    }
    project = ShapeShiftProject(cfg=cfg)
    entity = project.get_table("orders")
    fk = entity.foreign_keys[0]
    validator = ForeignKeyConstraintValidator(local_entity=entity, fk=fk)

    local_df = pd.DataFrame(
        {
            "order_id": [1, 2],
            "order_public_id": [1001, 1002],
            "customer_id": [None, None],
        }
    )
    remote_df = pd.DataFrame({"id": [1, 2]})

    validator.validate_before_merge(local_df=local_df, remote_df=remote_df)


def test_pre_merge_null_check_still_applies_to_new_rows_without_public_id():
    """Strict null-key validation still applies to rows whose public_id is not populated yet."""
    cfg = {
        "entities": {
            "orders": {
                "public_id": "order_public_id",
                "columns": ["order_id", "order_public_id", "customer_id"],
                "foreign_keys": [
                    {
                        "entity": "customers",
                        "local_keys": ["customer_id"],
                        "remote_keys": ["id"],
                        "constraints": {"allow_null_keys": False},
                    }
                ],
            },
            "customers": {"columns": ["id"]},
        }
    }
    project = ShapeShiftProject(cfg=cfg)
    entity = project.get_table("orders")
    fk = entity.foreign_keys[0]
    validator = ForeignKeyConstraintValidator(local_entity=entity, fk=fk)

    local_df = pd.DataFrame(
        {
            "order_id": [1, 2],
            "order_public_id": [1001, None],
            "customer_id": [None, None],
        }
    )
    remote_df = pd.DataFrame({"id": [1, 2]})

    with pytest.raises(ForeignKeyConstraintViolation, match="customer_id"):
        validator.validate_before_merge(local_df=local_df, remote_df=remote_df)
