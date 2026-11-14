"""
Extra columns evaluation with support for constants, column copies, interpolated strings, and DSL formulas.
This module provides functionality to evaluate extra_columns configurations,
including support for:
- Interpolated string patterns like "{first_name} {last_name}"
- DSL formulas like "=concat(first_name, ' ', last_name)"
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Protocol

import pandas as pd
from loguru import logger

from src.transforms.dsl import Expr, FormulaEngine, extract_column_references
from src.utility import Registry


class ExtraColumnStrategyRegistry(Registry):
    """Registry for extra-column strategies."""

    items: dict[str, type[ExtraColumnStrategy]] = {}

    @classmethod
    def registered_class_hook(cls, fn_or_class: Any, **options: Any) -> Any:
        setattr(fn_or_class, "priority", options.get("priority", 0))
        return fn_or_class

    @property
    def instances(self) -> list[ExtraColumnStrategy]:
        strategy_classes = sorted(self.items.values(), key=lambda strategy: getattr(strategy, "priority", 0))
        return [strategy_class() for strategy_class in strategy_classes]


EXTRA_COLUMN_STRATEGIES = ExtraColumnStrategyRegistry()


def to_str(val: Any) -> str:
    """Convert value to string, handling numbers and nulls."""
    if isinstance(val, (float, int)):
        if isinstance(val, float) and val == int(val):
            return str(int(val))
        return str(val)
    return str(val)


@dataclass(frozen=True)
class EvaluationContext:
    """State shared by strategies for one evaluation pass.

    Strategies are stateless and reusable. Only this pass's DataFrame is mutated.
    """

    df: pd.DataFrame
    formula_engine: FormulaEngine
    entity_name: str
    defer_missing: bool
    extra_column_keys: frozenset[str]
    case_sensitive: bool = False

    def resolve_column(self, reference: str) -> str | None:
        """Resolve a string column name under this operation's case policy."""
        lookup = {column if self.case_sensitive else column.lower(): column for column in self.df.columns if isinstance(column, str)}
        key = reference if self.case_sensitive else reference.lower()
        return lookup.get(key)

    def require_columns(self, name: str, value: str, columns: Sequence[str], kind: str) -> bool:
        """Return False for deferred dependencies; otherwise require all columns."""
        missing = set(columns) - set(self.df.columns)
        if not missing:
            return True
        if self.defer_missing:
            logger.trace(f"{self.entity_name}[extra_columns]: Deferred {kind} '{name}' " f"(missing columns: {sorted(missing)})")
            return False
        raise ValueError(
            f"{self.entity_name}[extra_columns]: Cannot evaluate '{name}' = '{value}': " f"columns not found: {sorted(missing)}"
        )


class ExtraColumnStrategy(Protocol):
    """An evaluation algorithm selected by an ordered matching policy."""

    def matches(self, value: Any, context: EvaluationContext) -> bool:
        """Whether this strategy handles the expression in this context."""
        ...

    def apply(self, name: str, value: Any, context: EvaluationContext) -> bool:
        """Assign the column and return True, or return False to defer it.

        Returning False must leave the DataFrame unchanged. Errors propagate;
        a failed strategy never falls through to the next strategy.
        """
        ...

    def dependencies(self, value: Any, context: EvaluationContext) -> Sequence[str]:
        """Report references, including missing ones, without changing the frame.

        Malformed formulas may return no inferred references during inspection;
        apply must still report their errors.
        """
        ...

    def source_column(self, value: Any, context: EvaluationContext) -> str | None:
        """Return a direct copy source, or None for other expressions."""
        ...


class BaseExtraColumnStrategy:
    """Default analysis for strategies with no dependencies or direct copy source.

    Subclasses provide matches/apply and override dependency analysis as needed.
    """

    def dependencies(self, value: Any, context: EvaluationContext) -> Sequence[str]:
        _ = value, context
        return ()

    def source_column(self, value: Any, context: EvaluationContext) -> str | None:  # pylint: disable=useless-return
        _ = value, context
        return None


@EXTRA_COLUMN_STRATEGIES.register(key="constant", priority=1)
class ConstantStrategy(BaseExtraColumnStrategy):
    """Assign non-string values with pandas' existing assignment semantics."""

    def matches(self, value: Any, context: EvaluationContext) -> bool:
        _ = context
        return not isinstance(value, str)

    def apply(self, name: str, value: Any, context: EvaluationContext) -> bool:
        context.df[name] = value
        logger.trace(f"{context.entity_name}[extra_columns]: Added constant '{name}' = {value}")
        return True


@EXTRA_COLUMN_STRATEGIES.register(key="escaped_equals", priority=2)
class EscapedEqualsStrategy(BaseExtraColumnStrategy):
    """Treat '==...' as a literal '=...' before formula detection."""

    def matches(self, value: Any, context: EvaluationContext) -> bool:
        _ = context
        return self.is_escaped_equals_literal(value)

    def apply(self, name: str, value: Any, context: EvaluationContext) -> bool:
        literal = self.unescape_equals_literal(value)
        context.df[name] = literal
        logger.trace(f"{context.entity_name}[extra_columns]: Added escaped literal '{name}' " f"= '{value}' -> '{literal}'")
        return True

    @staticmethod
    def is_escaped_equals_literal(value: Any) -> bool:
        """Detect if value is an escaped equals literal (starts with '==').
        Strings starting with '==' are treated as literal constants where
        the first '=' is an escape character, and the result is a string
        starting with '=' (not a DSL formula).
        Args:
            value: Value to check
        Returns:
            True if value is a string starting with '=='
        Examples:
            >>> EscapedEqualsStrategy.is_escaped_equals_literal("==literal")
            True
            >>> EscapedEqualsStrategy.is_escaped_equals_literal("=formula")
            False
            >>> EscapedEqualsStrategy.is_escaped_equals_literal("regular")
            False
        """
        return isinstance(value, str) and value.startswith("==")

    @staticmethod
    def unescape_equals_literal(value: str) -> str:
        """Remove the escape character from an escaped equals literal.
        Converts '==...' to '=...' by removing the first '=' character.
        Args:
            value: String starting with '=='
        Returns:
            String with first '=' removed
        Examples:
            >>> EscapedEqualsStrategy.unescape_equals_literal("==not_a_formula")
            '=not_a_formula'
            >>> EscapedEqualsStrategy.unescape_equals_literal("==value")
            '=value'
        """
        if value.startswith("=="):
            return value[1:]  # Remove first '='
        return value


@EXTRA_COLUMN_STRATEGIES.register(key="formula", priority=3)
class FormulaStrategy(BaseExtraColumnStrategy):
    """Parse, check dependencies, compile, and evaluate a DSL formula."""

    def dependencies(self, value: Any, context: EvaluationContext) -> Sequence[str]:
        try:
            return list(extract_column_references(context.formula_engine.parse(value)))
        except Exception:  # pylint: disable=broad-except
            # Analysis is best-effort; apply reports the error.
            return ()

    def matches(self, value: Any, context: EvaluationContext) -> bool:
        _ = context
        return self.is_dsl_formula(value)

    def apply(self, name: str, value: Any, context: EvaluationContext) -> bool:
        engine: FormulaEngine = context.formula_engine
        try:
            ast: Expr = engine.parse(value)
            columns: list[str] = list(extract_column_references(ast))
            if not context.require_columns(name, value, columns, "formula"):
                return False
            compiled_ast: Expr = engine.compile(value, context.df.columns)
            context.df[name] = engine.evaluate(compiled_ast, context.df)
            logger.trace(f"{context.entity_name}[extra_columns]: Added formula '{name}' = '{value}'")
            return True
        except Exception as exc:
            raise ValueError(f"{context.entity_name}[extra_columns]: Error evaluating formula '{name}' = '{value}': {exc}") from exc

    @staticmethod
    def is_dsl_formula(value: Any) -> bool:
        """Detect if value is a DSL formula (starts with '=' but not '==').
        DSL formulas are strings that start with '=' and contain
        function calls like concat(), upper(), etc. Strings starting
        with '==' are escaped literals, not formulas.
        Args:
            value: Value to check
        Returns:
            True if value is a string starting with '=' but not '=='
        Examples:
            >>> FormulaStrategy.is_dsl_formula("=concat(first, last)")
            True
            >>> FormulaStrategy.is_dsl_formula("{first} {last}")
            False
            >>> FormulaStrategy.is_dsl_formula("==literal")
            False
            >>> FormulaStrategy.is_dsl_formula(123)
            False
        """
        return isinstance(value, str) and value.startswith("=") and not value.startswith("==")


@EXTRA_COLUMN_STRATEGIES.register(key="interpolation", priority=4)
class InterpolationStrategy(BaseExtraColumnStrategy):
    """Evaluate brace templates with null handling and escaped braces."""

    INTERPOLATION_PATTERN: re.Pattern[str] = re.compile(r"(?<!\{)\{([^\W\d][\w]*)\}(?!\})")

    def dependencies(self, value: Any, context: EvaluationContext) -> Sequence[str]:
        return self.extract_column_dependencies(value)

    def matches(self, value: Any, context: EvaluationContext) -> bool:
        _ = context
        return self.is_interpolated_string(value)

    def apply(self, name: str, value: Any, context: EvaluationContext) -> bool:
        columns = self.dependencies(value, context)
        if not context.require_columns(name, value, columns, "interpolation"):
            return False
        context.df[name] = self.evaluate_interpolation(context.df, value, context.entity_name)
        logger.trace(f"{context.entity_name}[extra_columns]: Added interpolation '{name}' = '{value}'")
        return True

    @staticmethod
    def is_interpolated_string(value: Any) -> bool:
        """
        Detect if value is an interpolated string pattern.
        An interpolated string contains {column_name} patterns where:
        - Column names must start with letter or underscore
        - Can contain letters, numbers, underscores
        - Escaped braces {{}} are not considered interpolation
        Args:
            value: Value to check
        Returns:
            True if value contains unescaped {column} patterns
        Examples:
            >>> InterpolationStrategy.is_interpolated_string("{first_name} {last_name}")
            True
            >>> InterpolationStrategy.is_interpolated_string("{{literal}}")
            False
            >>> InterpolationStrategy.is_interpolated_string("constant")
            False
            >>> InterpolationStrategy.is_interpolated_string(123)
            False
        """
        if not isinstance(value, str):
            return False
        # Check for unescaped {column} patterns
        return bool(InterpolationStrategy.INTERPOLATION_PATTERN.search(value))

    @staticmethod
    def extract_column_dependencies(pattern: str) -> list[str]:
        """
        Extract column names from interpolated string pattern.
        Args:
            pattern: String containing {column} patterns
        Returns:
            List of unique column names in order of appearance
        Examples:
            >>> InterpolationStrategy.extract_column_dependencies("{first} {last}")
            ['first', 'last']
            >>> InterpolationStrategy.extract_column_dependencies("{a} {a}")
            ['a']
            >>> InterpolationStrategy.extract_column_dependencies("{{literal}}")
            []
        """
        matches = InterpolationStrategy.INTERPOLATION_PATTERN.findall(pattern)
        # Preserve order, remove duplicates using dict (maintains insertion order in Python 3.7+)
        return list(dict.fromkeys(matches))

    @staticmethod
    def unescape_braces(text: str) -> str:
        """
        Convert escaped braces to literal braces.
        Args:
            text: String potentially containing {{ or }}
        Returns:
            String with {{ replaced by { and }} replaced by }
        Examples:
            >>> InterpolationStrategy.unescape_braces("{{literal}}")
            '{literal}'
            >>> InterpolationStrategy.unescape_braces("{normal}")
            '{normal}'
        """
        return text.replace("{{", "{").replace("}}", "}")

    @staticmethod
    def evaluate_interpolation(df: pd.DataFrame, pattern: str, entity_name: str = "") -> pd.Series:
        """
        Evaluate interpolated string pattern against DataFrame.
        The evaluation process:
        1. Extract column dependencies from pattern
        2. Verify all columns exist in DataFrame
        3. Convert referenced values to strings and nulls to empty strings
        4. Concatenate literal text and column values in template order
        5. Unescape any {{}} to {}
        Args:
            df: DataFrame with columns to interpolate
            pattern: String like "{col1} {col2}"
            entity_name: Entity name for error messages
        Returns:
            pd.Series with interpolated values
        Raises:
            ValueError: If required columns are missing from DataFrame
        Examples:
            >>> df = pd.DataFrame({"a": [1, None], "b": ["x", "y"]})
            >>> result = InterpolationStrategy.evaluate_interpolation(df, "{a}-{b}", "test")
            >>> result.tolist()
            ['1-x', '-y']
        """
        columns: list[str] = InterpolationStrategy.extract_column_dependencies(pattern)
        # Check all columns exist
        missing: set[str] = set(columns) - set(df.columns)
        if missing:
            entity_suffix: str = f" for entity '{entity_name}'" if entity_name else ""
            raise ValueError(f"Cannot interpolate '{pattern}'{entity_suffix}: " f"columns not found: {sorted(missing)}")
        if len(df) == 0:
            return pd.Series(index=df.index, dtype="float64")
        left_brace: str = "\x00LEFTBRACE\x00"
        right_brace: str = "\x00RIGHTBRACE\x00"
        template: str = pattern.replace("{{", left_brace).replace("}}", right_brace)
        values: dict[str, pd.Series] = {}
        for column in columns:
            converted: pd.Series = df[column].map(to_str, na_action="ignore")
            if converted.dtype != object:
                converted = converted.astype(object)
            values[column] = converted.fillna("").rename(None)

        def unescape_literal(text: str) -> str:
            return text.replace(left_brace, "{").replace(right_brace, "}")

        result: pd.Series | str = ""
        offset: int = 0
        for match in InterpolationStrategy.INTERPOLATION_PATTERN.finditer(template):
            if match.start() > offset:
                result = result + unescape_literal(template[offset : match.start()])
            result = result + values[match.group(1)]
            offset = match.end()
        if offset < len(template):
            result = result + unescape_literal(template[offset:])
        if isinstance(result, str):
            result = pd.Series(result, index=df.index, dtype=object)
        return result.rename(None)


@EXTRA_COLUMN_STRATEGIES.register(key="copy", priority=5)
class ColumnCopyStrategy(BaseExtraColumnStrategy):
    """Copy available source columns, excluding configured extra-column names."""

    def source_column(self, value: Any, context: EvaluationContext) -> str | None:
        if not isinstance(value, str) or value.lower() in context.extra_column_keys:
            return None
        return context.resolve_column(value)

    def matches(self, value: Any, context: EvaluationContext) -> bool:
        return self.source_column(value, context) is not None

    def dependencies(self, value: Any, context: EvaluationContext) -> Sequence[str]:
        column = self.source_column(value, context)
        return () if column is None else (column,)

    def apply(self, name: str, value: Any, context: EvaluationContext) -> bool:
        column = self.source_column(value, context)
        if column is None:
            raise ValueError(f"Column-copy strategy has no source for {value!r}")
        context.df[name] = context.df[column]
        logger.trace(f"{context.entity_name}[extra_columns]: Copied column '{name}' from '{value}'")
        return True


@EXTRA_COLUMN_STRATEGIES.register(key="string_constant", priority=6)
class StringConstantStrategy(BaseExtraColumnStrategy):
    """Fallback for strings, including the existing numeric literal coercion."""

    INTEGER_LITERAL_PATTERN = re.compile(r"[+-]?\d+")
    FLOAT_LITERAL_PATTERN = re.compile(r"[+-]?(?:\d+\.\d*|\.\d+)")

    def matches(self, value: Any, context: EvaluationContext) -> bool:
        _ = context
        return isinstance(value, str)

    def apply(self, name: str, value: Any, context: EvaluationContext) -> bool:
        context.df[name] = self.coerce_string_constant_literal(value)
        logger.trace(
            f"{context.entity_name}[extra_columns]: Added constant '{name}' = "
            f"'{context.df[name].iloc[0] if len(context.df) > 0 else context.df[name]}'"
        )
        return True

    @staticmethod
    def coerce_string_constant_literal(value: str) -> str | int | float:
        """Coerce plain numeric string literals used as extra-column constants.
        This applies only after formula, interpolation, and column-copy detection,
        so it affects only literal string constants such as "53" or "53.5".
        """
        text = value.strip()
        if StringConstantStrategy.INTEGER_LITERAL_PATTERN.fullmatch(text):
            return int(text)
        if StringConstantStrategy.FLOAT_LITERAL_PATTERN.fullmatch(text):
            return float(text)
        return value


class ExtraColumnEvaluator:
    """Evaluates extra_columns with support for constants, copies, interpolated strings, and DSL formulas.
    The evaluator supports multiple evaluation modes:
    1. Constants: Non-string values or string literals
    2. DSL formulas: Strings starting with '=' containing function calls
    3. Column copies: String matching an existing column name
    4. Interpolated strings: String containing {column_name} patterns
    DSL formulas support:
    - Safe function calls: concat, upper, lower, trim, substr, coalesce, map_value
    - Column references and literals (strings, numbers, null, true, false)
    - Nested function calls
    - Deferred evaluation (for columns not yet available)
    Interpolated strings support:
    - Null-safe evaluation (nulls become empty strings)
    - Type coercion (all values converted to strings)
    - Escaped braces ({{ and }} become { and })
    - Deferred evaluation (for columns not yet available)
    Examples:
        >>> evaluator = ExtraColumnEvaluator()
        >>> df = pd.DataFrame({"first": ["John"], "last": ["Doe"]})
        >>>
        >>> # Interpolated string
        >>> extra_cols = {"fullname": "{first} {last}"}
        >>> result, deferred = evaluator.evaluate_extra_columns(df, extra_cols, "person")
        >>> result["fullname"].iloc[0]
        'John Doe'
        >>>
        >>> # DSL formula
        >>> extra_cols = {"initials": "=concat(upper(substr(first, 0, 1)), upper(substr(last, 0, 1)))"}
        >>> result, deferred = evaluator.evaluate_extra_columns(df, extra_cols, "person")
        >>> result["initials"].iloc[0]
        'JD'
    """

    def __init__(self, strategies: Sequence[ExtraColumnStrategy] | None = None):
        """Use the default ordered strategies, or an explicitly supplied sequence.

        Custom sequences must include a fallback (normally StringConstantStrategy).
        The first matching strategy handles each expression.
        """
        self.formula_engine = FormulaEngine()
        self.strategies: list[ExtraColumnStrategy] = list(strategies) if strategies is not None else EXTRA_COLUMN_STRATEGIES.instances

    def select_strategy(self, value: Any, context: EvaluationContext) -> ExtraColumnStrategy:
        for strategy in self.strategies:
            if strategy.matches(value, context):
                return strategy
        raise ValueError(f"No extra-column strategy matches {value!r}")

    def collect_source_dependencies(
        self,
        source: pd.DataFrame | list[str],
        extra_columns: dict[str, Any],
        case_sensitive: bool = True,
    ) -> set[str]:
        """Collect existing source references declared by the selected strategies.

        Constants have no dependencies. Formula parse failures are left for
        evaluation to report. Only references present in source are returned.
        """
        frame: pd.DataFrame = source if isinstance(source, pd.DataFrame) else pd.DataFrame(columns=source)
        context: EvaluationContext = self._make_context(frame, extra_columns, case_sensitive=case_sensitive)
        dependencies: set[str] = set()
        for value in extra_columns.values():
            strategy: ExtraColumnStrategy = self.select_strategy(value, context)
            for reference in strategy.dependencies(value, context):
                column: str | None = context.resolve_column(reference)
                if column is not None:
                    dependencies.add(column)
        return dependencies

    def get_unresolved_extra_columns(
        self,
        df: pd.DataFrame,
        extra_columns: dict[str, Any],
    ) -> dict[str, dict[str, Any]]:
        """Describe absent outputs using the selected strategies' dependencies.

        An absent constant output is unresolved but has no missing dependencies.
        Malformed formulas report no inferred dependencies; evaluation raises the
        parse error. Formula and interpolation references remain case-sensitive.
        """
        context: EvaluationContext = self._make_context(df, extra_columns)
        available_columns: set[str] = set(df.columns)
        unresolved: dict[str, dict[str, Any]] = {}
        for name, value in extra_columns.items():
            if name in available_columns:
                continue
            strategy: ExtraColumnStrategy = self.select_strategy(value, context)
            unresolved[name] = {
                "expression": value,
                "missing_dependencies": sorted(set(strategy.dependencies(value, context)) - available_columns),
            }
        return unresolved

    def evaluate_extra_columns(
        self,
        df: pd.DataFrame,
        extra_columns: dict[str, Any],
        entity_name: str,
        defer_missing: bool = False,
    ) -> tuple[pd.DataFrame, dict[str, Any]]:
        """Evaluate in configuration order using the first matching strategy.

        Existing columns are skipped. Formulas and interpolations can be deferred
        until their dependencies exist. The input DataFrame is never modified.
        """
        if not extra_columns:
            return df, {}

        result: pd.DataFrame = df.copy()
        context: EvaluationContext = self._make_context(result, extra_columns, entity_name, defer_missing)
        deferred: dict[str, Any] = {}
        added_count = 0
        skipped_count = 0

        for new_col, value in extra_columns.items():
            if new_col in result.columns:
                skipped_count += 1
                logger.trace(f"{entity_name}[extra_columns]: Skipping '{new_col}' (already exists)")
                continue

            strategy: ExtraColumnStrategy = self.select_strategy(value, context)
            if strategy.apply(new_col, value, context):
                added_count += 1
            else:
                deferred[new_col] = value

        msg_parts = []
        if added_count:
            msg_parts.append(f"Added {added_count} column(s)")
        if deferred:
            msg_parts.append(f"deferred {len(deferred)}")
        if skipped_count:
            msg_parts.append(f"skipped {skipped_count} (already exist)")
        if msg_parts:
            logger.info(f"{entity_name}[extra_columns]: {', '.join(msg_parts)}")

        return result, deferred

    def _make_context(
        self,
        df: pd.DataFrame,
        extra_columns: dict[str, Any],
        entity_name: str = "",
        defer_missing: bool = False,
        case_sensitive: bool = False,
    ) -> EvaluationContext:
        return EvaluationContext(
            df=df,
            formula_engine=self.formula_engine,
            entity_name=entity_name,
            defer_missing=defer_missing,
            extra_column_keys=frozenset(str(key).lower() for key in extra_columns),
            case_sensitive=case_sensitive,
        )

    def verify_extra_columns(self, df: pd.DataFrame, extra_columns: dict[str, Any], entity_name: str) -> bool:
        """Verify all configured extra_columns have been evaluated.
        Logs a warning if any configured extra_columns are not in the DataFrame.
        Args:
            df: DataFrame to check
            extra_columns: Configured extra_columns dict
            entity_name: Name of entity (for logging)
        Returns:
            True if all extra_columns evaluated, False otherwise
        """
        if not extra_columns:
            return True
        missing_columns: list[str] = [col for col in extra_columns.keys() if col not in df.columns]
        if missing_columns:
            logger.warning(f"{entity_name}[extra_columns]: Unresolved columns after normalization: {missing_columns}")
            return False
        return True

    @staticmethod
    def split_extra_columns(
        source: pd.DataFrame, extra_columns: dict[str, Any], case_sensitive: bool = False
    ) -> tuple[dict[str, str], dict[str, Any]]:
        """Legacy static helper using the default strategies.

        Returns source copies and all remaining expressions (not just constants).
        Use instance.partition_extra_columns to include custom strategies.
        """
        return ExtraColumnEvaluator().partition_extra_columns(source, extra_columns, case_sensitive)

    def partition_extra_columns(
        self,
        source: pd.DataFrame,
        extra_columns: dict[str, Any],
        case_sensitive: bool = False,
    ) -> tuple[dict[str, str], dict[str, Any]]:
        """Partition source copies and other expressions using this instance's strategies."""
        context: EvaluationContext = self._make_context(source, extra_columns, case_sensitive=case_sensitive)
        copies: dict[str, str] = {}
        expressions: dict[str, Any] = {}
        for name, value in extra_columns.items():
            strategy: ExtraColumnStrategy = self.select_strategy(value, context)
            column: str | None = strategy.source_column(value, context)
            if column is None:
                expressions[name] = value
            else:
                copies[name] = column
        return copies, expressions
