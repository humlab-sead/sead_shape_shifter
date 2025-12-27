"""Tests for constraint validators and orchestration."""

import pandas as pd
import pytest

from src.constraints import ForeignKeyConstraintViolation, ForeignKeyConstraintValidator, Validators
from src.model import ForeignKeyConfig, ShapeShiftConfig


def build_fk(
    *, local_entity: str = "orders", remote_entity: str = "customers", constraints: dict | None = None
) -> ForeignKeyConfig:
    cfg = {
        "entities": {
            local_entity: {
                "columns": ["order_id", "customer_id"],
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
    return ShapeShiftConfig(cfg=cfg).get_table(local_entity).foreign_keys[0]


def test_validator_registry_lookup():
    """Registry returns stage-filtered and sub-key lookups."""
    validators = Validators.get_validators_for_stage("post-merge")
    assert validators, "expected post-merge validators"

    one_to_one_validator = Validators.get_validator_by_constraint("cardinality", "one_to_one")
    assert one_to_one_validator is not None


def test_pre_merge_null_and_uniqueness_checks():
    """Pre-merge validators should raise when constraints violated."""
    fk = build_fk(constraints={"allow_null_keys": False, "require_unique_left": True, "require_unique_right": True})
    validator = ForeignKeyConstraintValidator(entity_name="orders", fk=fk)

    local_df = pd.DataFrame({"order_id": [1, 2, 3], "customer_id": [1, 1, None]})
    remote_df = pd.DataFrame({"id": [1, 1]})

    with pytest.raises(ForeignKeyConstraintViolation, match="Null values"):
        validator.validate_before_merge(local_df=local_df, remote_df=remote_df)

    # Fix nulls but keep duplicate right keys to trigger unique right
    local_df["customer_id"] = [1, 1, 2]
    with pytest.raises(ForeignKeyConstraintViolation, match="duplicate left"):
        validator.validate_before_merge(local_df=local_df, remote_df=remote_df)


def test_post_merge_cardinality_and_unmatched_checks():
    """Post-merge validators enforce cardinality and unmatched rules."""
    fk = build_fk(
        constraints={
            "cardinality": "one_to_one",
            "allow_unmatched_left": False,
            "allow_unmatched_right": False,
        }
    )
    validator = ForeignKeyConstraintValidator(entity_name="orders", fk=fk)

    local_df = pd.DataFrame({"order_id": [1, 2], "customer_id": [1, 2]})
    remote_df = pd.DataFrame({"id": [1]})

    # Simulate a merge with unmatched rows and row count change
    linked_df = pd.DataFrame(
        {"order_id": [1, 2], "customer_id": [1, 2], "_merge_indicator_customers": ["both", "left_only"]}
    )

    validator.validate_before_merge(local_df=local_df, remote_df=remote_df)

    with pytest.raises(ForeignKeyConstraintViolation, match="unmatched left"):
        validator.validate_after_merge(
            local_df=local_df,
            remote_df=remote_df,
            linked_df=linked_df,
            merge_indicator_col="_merge_indicator_customers",
        )
