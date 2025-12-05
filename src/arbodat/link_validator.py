from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Literal, Self

import pandas as pd
from loguru import logger

from src.arbodat.config_model import ForeignKeyConfig, ForeignKeyConstraints
from src.utility import Registry


class ForeignKeyConstraintViolation(Exception):
    """Raised when a foreign key constraint is violated."""

    pass


@dataclass
class ValidationContext:
    """Encapsulates all data needed for constraint validation."""

    local_df: pd.DataFrame
    remote_df: pd.DataFrame | None = None
    linked_df: pd.DataFrame | None = None
    merge_indicator_col: str | None = None


class ConstraintValidator(ABC):
    """Base class for constraint validators."""

    def __init__(self, entity_name: str, fk: ForeignKeyConfig, constraints: ForeignKeyConstraints) -> None:
        self.entity_name: str = entity_name
        self.fk: ForeignKeyConfig = fk
        self.constraints: ForeignKeyConstraints = constraints

    def raise_if_violated(self, message: str) -> None:
        """Raise a constraint violation exception with context."""
        raise ForeignKeyConstraintViolation(f"{self.entity_name} -> {self.fk.remote_entity}: {message}")

    @abstractmethod
    def is_applicable(self) -> bool:
        """Return True if this validator should be applied."""
        pass

    @abstractmethod
    def validate(self, context: ValidationContext) -> None:
        """Execute the validation logic."""
        pass


class ValidatorRegistry(Registry):

    items: dict[str, type[ConstraintValidator]] = {}

    @classmethod
    def registered_class_hook(cls, fn_or_class: Any, **args) -> Any:
        if args.get("type") != "function":
            if args.get("stage"):
                if not hasattr(fn_or_class, "stage"):
                    setattr(fn_or_class, "stage", args["stage"])
            if not hasattr(fn_or_class, "is_match_validator"):
                setattr(fn_or_class, "is_match_validator", args.get("is_match_validator", False))
        return fn_or_class

    def get_validators_for_stage(self, stage: str) -> list[type[ConstraintValidator]]:
        """Retrieve all registered validators for a given stage."""
        return [v for v in self.items.values() if getattr(v, "stage", None) == stage]


Validators: ValidatorRegistry = ValidatorRegistry()

# Pre-merge validators


@Validators.register(key="allow_null_keys", stage="pre-merge")
class NullKeyValidator(ConstraintValidator):
    """Validates that keys don't contain null values if not allowed."""

    def is_applicable(self) -> bool:
        return not self.constraints.allow_null_keys

    def validate(self, context: ValidationContext) -> None:
        for col in self.fk.local_keys:
            if context.local_df[col].isnull().any():
                self.raise_if_violated(f"Null values found in local key '{col}' (allow_null_keys=False)")
        if context.remote_df is not None:
            for col in self.fk.remote_keys:
                if context.remote_df[col].isnull().any():
                    self.raise_if_violated(f"Null values found in remote key '{col}' (allow_null_keys=False)")


@Validators.register(key="require_unique_left", stage="pre-merge")
class UniqueLeftKeyValidator(ConstraintValidator):
    """Validates that left keys are unique."""

    def is_applicable(self) -> bool:
        return self.constraints.require_unique_left

    def validate(self, context: ValidationContext) -> None:
        duplicates = context.local_df[self.fk.local_keys].duplicated().sum()
        if duplicates > 0:
            self.raise_if_violated(f"{duplicates} duplicate left key(s) found (require_unique_left=True)")


@Validators.register(key="require_unique_right", stage="pre-merge")
class UniqueRightKeyValidator(ConstraintValidator):
    """Validates that right keys are unique."""

    def is_applicable(self) -> bool:
        return self.constraints.require_unique_right

    def validate(self, context: ValidationContext) -> None:
        assert context.remote_df is not None
        duplicates = context.remote_df[self.fk.remote_keys].duplicated().sum()
        if duplicates > 0:
            self.raise_if_violated(f"{duplicates} duplicate right key(s) found (require_unique_right=True)")


# Post-merge validators


@Validators.register(key="cardinality", stage="post-merge")
class OneToOneCardinalityValidator(ConstraintValidator):
    """Validates one-to-one cardinality (row count stays the same)."""

    def is_applicable(self) -> bool:
        return self.constraints.cardinality == "one_to_one"

    def validate(self, context: ValidationContext) -> None:
        assert context.linked_df is not None
        rows_before: int = len(context.local_df)
        rows_after: int = len(context.linked_df)
        if rows_after != rows_before:
            self.raise_if_violated(f"one_to_one cardinality violated (rows: {rows_before} -> {rows_after})")


@Validators.register(key="cardinality", stage="post-merge")
class ManyToOneCardinalityValidator(ConstraintValidator):
    """Validates many-to-one cardinality (row count cannot increase)."""

    def is_applicable(self) -> bool:
        return self.constraints.cardinality == "many_to_one"

    def validate(self, context: ValidationContext) -> None:
        assert context.linked_df is not None
        rows_before: int = len(context.local_df)
        rows_after: int = len(context.linked_df)
        if rows_after > rows_before:
            self.raise_if_violated(f"many_to_one cardinality violated (rows increased: {rows_before} -> {rows_after})")


@Validators.register(key="cardinality", stage="post-merge")
class OneToManyCardinalityValidator(ConstraintValidator):
    """Validates one-to-many cardinality (row count cannot decrease)."""

    def is_applicable(self) -> bool:
        return self.constraints.cardinality == "one_to_many"

    def validate(self, context: ValidationContext) -> None:
        assert context.linked_df is not None
        rows_before: int = len(context.local_df)
        rows_after: int = len(context.linked_df)
        if rows_after < rows_before:
            self.raise_if_violated(f"one_to_many cardinality violated (rows decreased: {rows_before} -> {rows_after})")


@Validators.register(key="max_row_increase_abs", stage="post-merge")
class MaxRowIncreaseAbsoluteValidator(ConstraintValidator):
    """Validates maximum absolute row increase."""

    def is_applicable(self) -> bool:
        return self.constraints.max_row_increase_abs is not None

    def validate(self, context: ValidationContext) -> None:
        assert context.linked_df is not None
        rows_before: int = len(context.local_df)
        rows_after: int = len(context.linked_df)
        rows_change: int = rows_after - rows_before
        max_increase: int | None = self.constraints.max_row_increase_abs
        assert max_increase is not None  # Guaranteed by is_applicable
        if rows_change > max_increase:
            self.raise_if_violated(f"Row increase {rows_change} exceeds max_row_increase_abs={max_increase}")


@Validators.register(key="max_row_increase_pct", stage="post-merge")
class MaxRowIncreasePercentValidator(ConstraintValidator):
    """Validates maximum percentage row increase."""

    def is_applicable(self) -> bool:
        return self.constraints.max_row_increase_pct is not None

    def validate(self, context: ValidationContext) -> None:
        assert context.linked_df is not None
        rows_before: int = len(context.local_df)
        rows_after: int = len(context.linked_df)
        rows_change: int = rows_after - rows_before
        pct_increase: float | Literal[0] = (rows_change / rows_before * 100) if rows_before > 0 else 0
        max_pct: float | None = self.constraints.max_row_increase_pct
        assert max_pct is not None  # Guaranteed by is_applicable
        if pct_increase > max_pct:
            self.raise_if_violated(f"Row increase {pct_increase:.1f}% exceeds max_row_increase_pct={max_pct}%")


@Validators.register(key="allow_row_decrease", stage="post-merge")
class AllowRowDecreaseValidator(ConstraintValidator):
    """Validates that row decrease is allowed if it occurs."""

    def is_applicable(self) -> bool:
        return self.constraints.allow_row_decrease is False

    def validate(self, context: ValidationContext) -> None:
        assert context.linked_df is not None
        rows_before: int = len(context.local_df)
        rows_after: int = len(context.linked_df)
        if rows_after < rows_before:
            self.raise_if_violated(f"Row decrease not allowed (rows: {rows_before} -> {rows_after})")


@Validators.register(key="allow_unmatched_left", stage="post-merge-match", is_match_validator=True)
class UnmatchedLeftValidator(ConstraintValidator):
    """Validates that unmatched left rows are allowed."""

    def is_applicable(self) -> bool:
        return self.constraints.allow_unmatched_left is False

    def validate(self, context: ValidationContext) -> None:
        assert context.linked_df is not None and context.merge_indicator_col is not None
        left_only: int = (context.linked_df[context.merge_indicator_col] == "left_only").sum()
        if left_only > 0:
            self.raise_if_violated(f"{left_only} unmatched left rows (allow_unmatched_left=False)")


@Validators.register(key="require_all_left_matched", stage="post-merge-match", is_match_validator=True)
class RequireAllLeftMatchedValidator(
    ConstraintValidator,
):
    """Validates that all left rows are matched."""

    def is_applicable(self) -> bool:
        return self.constraints.require_all_left_matched

    def validate(self, context: ValidationContext) -> None:
        assert context.linked_df is not None and context.merge_indicator_col is not None
        left_only: int = (context.linked_df[context.merge_indicator_col] == "left_only").sum()
        if left_only > 0:
            self.raise_if_violated(f"{left_only} unmatched left rows (require_all_left_matched=True)")


@Validators.register(key="allow_unmatched_right", stage="post-merge-match", is_match_validator=True)
class UnmatchedRightValidator(ConstraintValidator):
    """Validates that unmatched right rows are allowed."""

    def is_applicable(self) -> bool:
        return self.constraints.allow_unmatched_right is False

    def validate(self, context: ValidationContext) -> None:
        assert context.linked_df is not None and context.merge_indicator_col is not None
        right_only: int = (context.linked_df[context.merge_indicator_col] == "right_only").sum()
        if right_only > 0:
            self.raise_if_violated(f"{right_only} unmatched right rows (allow_unmatched_right=False)")


@Validators.register(key="require_all_right_matched", stage="post-merge-match", is_match_validator=True)
class RequireAllRightMatchedValidator(ConstraintValidator):
    """Validates that all right rows are matched."""

    def is_applicable(self) -> bool:
        return self.constraints.require_all_right_matched

    def validate(self, context: ValidationContext) -> None:
        assert context.linked_df is not None and context.merge_indicator_col is not None
        right_only: int = (context.linked_df[context.merge_indicator_col] == "right_only").sum()
        if right_only > 0:
            self.raise_if_violated(f"{right_only} unmatched right rows (require_all_right_matched=True)")


@Validators.register(key="min_match_rate", stage="post-merge-match", is_match_validator=True)
class MinMatchRateValidator(ConstraintValidator):
    """Validates minimum match rate."""

    def is_applicable(self) -> bool:
        return self.constraints.min_match_rate is not None

    def validate(self, context: ValidationContext) -> None:
        assert context.linked_df is not None and context.merge_indicator_col is not None
        rows_before: int = len(context.local_df)
        both: int = (context.linked_df[context.merge_indicator_col] == "both").sum()
        match_rate: float | Literal[0] = both / rows_before if rows_before > 0 else 0
        min_rate: float | None = self.constraints.min_match_rate
        assert min_rate is not None  # Guaranteed by is_applicable
        if match_rate < min_rate:
            self.raise_if_violated(f"Match rate {match_rate:.2%} below minimum {min_rate:.2%}")


class ForeignKeyConstraintValidator:
    """Orchestrates validation of foreign key constraints during and after merging."""

    def __init__(self, entity_name: str, fk: ForeignKeyConfig) -> None:
        self.entity_name: str = entity_name
        self.fk: ForeignKeyConfig = fk
        self.constraints: ForeignKeyConstraints = fk.constraints
        self.merge_indicator_col: str | None = None
        self.size_before_merge: tuple[int, int] = (0, 0)
        self.size_after_merge: tuple[int, int] = (0, 0)

    def validate_before_merge(self, local_df: pd.DataFrame, remote_df: pd.DataFrame) -> Self:
        """Validate constraints before performing the merge."""
        if not self.fk.has_constraints:
            return self

        context = ValidationContext(local_df=local_df, remote_df=remote_df)
        for validator_cls in Validators.get_validators_for_stage("pre-merge"):
            validator: ConstraintValidator = validator_cls(self.entity_name, self.fk, self.constraints)
            if validator.is_applicable():
                validator.validate(context)

        if self.constraints.has_match_constraints:
            self.merge_indicator_col = f"_merge_indicator_{self.fk.remote_entity}"

        self.size_before_merge = local_df.shape
        self.size_after_merge = (0, 0)
        return self

    def validate_merge_opts(self) -> dict[str, Any]:
        """Return opts required for merge validation."""
        return {"indicator": self.merge_indicator_col} if self.merge_indicator_col else {}

    def validate_after_merge(
        self, local_df: pd.DataFrame, remote_df: pd.DataFrame, linked_df: pd.DataFrame, merge_indicator_col: str | None = None
    ) -> Self:
        """Validate constraints after performing the merge."""
        if not self.fk.has_constraints:
            return self

        self.size_after_merge = linked_df.shape

        logger.debug(f"{self.entity_name}[linking]: merge size: before={self.size_before_merge}, after={self.size_after_merge}")

        context = ValidationContext(local_df=local_df, remote_df=remote_df, linked_df=linked_df)
        for validator_cls in Validators.get_validators_for_stage("post-merge"):
            validator: ConstraintValidator = validator_cls(self.entity_name, self.fk, self.constraints)
            if validator.is_applicable():
                validator.validate(context)

        match_context = ValidationContext(
            local_df=local_df, remote_df=remote_df, linked_df=linked_df, merge_indicator_col=merge_indicator_col
        )
        for validator_cls in Validators.get_validators_for_stage("post-merge-match"):
            validator: ConstraintValidator = validator_cls(self.entity_name, self.fk, self.constraints)
            if validator.is_applicable():
                if merge_indicator_col and merge_indicator_col in linked_df.columns:
                    validator.validate(match_context)
                else:
                    logger.warning(
                        f"{self.entity_name} -> {self.fk.remote_entity}: Merge indicator column '{merge_indicator_col}' not found in linked DataFrame for match validation"
                    )

        if self.fk.how != "cross":
            if self.size_before_merge[0] != self.size_after_merge[0]:
                logger.warning(
                    f"{self.fk.local_entity}[linking]: join resulted in change in row count for '{self.fk.remote_entity}': before={self.size_before_merge[0]}, after={self.size_after_merge[0]}"
                )

        if self.size_after_merge[1] != self.size_before_merge[1] + len(self.fk.remote_extra_columns):
            logger.warning(
                f"{self.entity_name}[linking]: join resulted in unexpected number of columns for '{self.fk.remote_entity}': before={self.size_before_merge[1]}, after={self.size_after_merge[1]}, expected increase={len(self.fk.remote_extra_columns)}"
            )
        return self
