"""
Extra columns evaluation with support for constants, column copies, interpolated strings, and DSL formulas.

This module provides functionality to evaluate extra_columns configurations,
including support for:
- Interpolated string patterns like "{first_name} {last_name}"
- DSL formulas like "=concat(first_name, ' ', last_name)"
"""

import re
from typing import Any

import pandas as pd
from loguru import logger

from src.transforms.dsl import FormulaEngine, extract_column_references


def to_str(val: Any) -> str:
    """Convert value to string, handling numbers and nulls."""
    if isinstance(val, (float, int)):
        if isinstance(val, float) and val == int(val):
            return str(int(val))
        return str(val)
    return str(val)


class ExtraColumnEvaluator:
    """Evaluates extra_columns with support for constants, copies, interpolated strings, and DSL formulas.

    The evaluator supports multiple evaluation modes:
    1. Constants: Non-string values or string literals
    2. DSL formulas: Strings starting with '=' containing function calls
    3. Column copies: String matching an existing column name
    4. Interpolated strings: String containing {column_name} patterns

    DSL formulas support:
    - Safe function calls: concat, upper, lower, trim, substr, coalesce
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

    # Regex pattern: match {column_name} but not {{escaped}}
    # Matches: {col}, {first_name}, {col123}
    # Doesn't match: {{literal}}, {123invalid}
    INTERPOLATION_PATTERN = re.compile(r"(?<!\{)\{([a-zA-Z_][\w]*)\}(?!\})")

    def __init__(self):
        """Initialize evaluator with FormulaEngine for DSL formula support."""
        self.formula_engine = FormulaEngine()

    def collect_source_dependencies(
        self,
        source: pd.DataFrame | list[str],
        extra_columns: dict[str, Any],
        case_sensitive: bool = True,
    ) -> set[str]:
        """Collect all source column dependencies required to evaluate extra_columns.

        This method analyzes the extra_columns configuration and determines which
        source columns are needed to evaluate all the extra column expressions.
        It handles DSL formulas, interpolated strings, and column copies.

        Args:
            source: DataFrame or list of available source column names
            extra_columns: Dict of {new_column: value/pattern/formula}
            case_sensitive: Whether column name matching is case-sensitive

        Returns:
            Set of source column names required to evaluate extra_columns

        Examples:
            >>> df = pd.DataFrame({"first": [1], "last": [2], "age": [30]})
            >>> evaluator = ExtraColumnEvaluator()
            >>> extra_cols = {"fullname": "{first} {last}", "status": "active"}
            >>> deps = evaluator.collect_source_dependencies(df, extra_cols)
            >>> sorted(deps)
            ['first', 'last']
        """
        if not extra_columns:
            return set()

        # Get available source columns
        if isinstance(source, pd.DataFrame):
            source_columns: set[str] = set(source.columns)
        else:
            source_columns = set(source)

        # Build case-insensitive column lookup if needed
        if not case_sensitive:
            col_map: dict[str, str] = {str(c).lower(): c for c in source_columns}
        else:
            col_map = {c: c for c in source_columns}

        dependencies: set[str] = set()

        for _, value in extra_columns.items():
            # Skip non-string constants (no dependencies)
            if not isinstance(value, str):
                continue

            # Case 1: DSL formula (starts with '=')
            if self.is_dsl_formula(value):
                try:
                    # Parse formula and extract column references
                    ast = self.formula_engine.parse(value)
                    formula_deps = extract_column_references(ast)

                    # Match against source columns (case-insensitive if needed)
                    for dep in formula_deps:
                        dep_key = dep.lower() if not case_sensitive else dep
                        if dep_key in col_map:
                            dependencies.add(col_map[dep_key])
                except Exception:  # pylint: disable=broad-except
                    # If formula parsing fails, skip it
                    # The actual evaluation will report the error
                    pass
                continue

            # Case 2: Interpolated string (contains {column})
            if self.is_interpolated_string(value):
                interp_deps = self.extract_column_dependencies(value)

                # Match against source columns (case-insensitive if needed)
                for dep in interp_deps:
                    dep_key = dep.lower() if not case_sensitive else dep
                    if dep_key in col_map:
                        dependencies.add(col_map[dep_key])
                continue

            # Case 3: Potential column copy (string value)
            # Check if value matches an existing source column
            value_key = value.lower() if not case_sensitive else value
            if value_key in col_map:
                dependencies.add(col_map[value_key])

        return dependencies

    def get_unresolved_extra_columns(
        self,
        df: pd.DataFrame,
        extra_columns: dict[str, Any],
    ) -> dict[str, dict[str, Any]]:
        """Identify extra_columns that could not be evaluated and their missing dependencies.

        This method checks which configured extra_columns are not present in the
        DataFrame and determines which dependencies are missing for each unresolved column.

        Args:
            df: DataFrame to check for evaluated extra_columns
            extra_columns: Configured extra_columns dict

        Returns:
            Dict mapping unresolved column names to metadata:
            {
                "column_name": {
                    "expression": original_value,
                    "missing_dependencies": [list of missing column names]
                }
            }

        Examples:
            >>> df = pd.DataFrame({"a": [1], "b": [2]})
            >>> evaluator = ExtraColumnEvaluator()
            >>> extra_cols = {"result": "=concat(a, c)", "constant": 99}
            >>> unresolved = evaluator.get_unresolved_extra_columns(df, extra_cols)
            >>> unresolved
            {'result': {'expression': '=concat(a, c)', 'missing_dependencies': ['c']}}
        """
        if not extra_columns:
            return {}

        unresolved: dict[str, dict[str, Any]] = {}
        available_columns = set(df.columns)

        for column_name, value in extra_columns.items():
            # Skip if column was successfully evaluated
            if column_name in available_columns:
                continue

            # Column is missing - determine why
            missing_dependencies: list[str] = []

            # Check what dependencies this column needs
            if isinstance(value, str):
                # Case 1: DSL formula
                if self.is_dsl_formula(value):
                    try:
                        ast = self.formula_engine.parse(value)
                        formula_deps = extract_column_references(ast)
                        missing_dependencies = sorted(set(formula_deps) - available_columns)
                    except Exception:  # pylint: disable=broad-except
                        # Parsing failed - can't determine dependencies
                        missing_dependencies = []

                # Case 2: Interpolated string
                elif self.is_interpolated_string(value):
                    interp_deps = self.extract_column_dependencies(value)
                    missing_dependencies = sorted(set(interp_deps) - available_columns)

                # Case 3: Column copy (string matching column name)
                else:
                    # Check if it's trying to copy a column that doesn't exist
                    col_lower = value.lower()
                    col_map = {str(c).lower(): c for c in available_columns if isinstance(c, str)}
                    if col_lower not in col_map:
                        missing_dependencies = [value]

            # Record the unresolved column
            unresolved[column_name] = {
                "expression": value,
                "missing_dependencies": missing_dependencies,
            }

        return unresolved

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
            >>> ExtraColumnEvaluator.is_escaped_equals_literal("==literal")
            True
            >>> ExtraColumnEvaluator.is_escaped_equals_literal("=formula")
            False
            >>> ExtraColumnEvaluator.is_escaped_equals_literal("regular")
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
            >>> ExtraColumnEvaluator.unescape_equals_literal("==not_a_formula")
            '=not_a_formula'
            >>> ExtraColumnEvaluator.unescape_equals_literal("==value")
            '=value'
        """
        if value.startswith("=="):
            return value[1:]  # Remove first '='
        return value

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
            >>> ExtraColumnEvaluator.is_dsl_formula("=concat(first, last)")
            True
            >>> ExtraColumnEvaluator.is_dsl_formula("{first} {last}")
            False
            >>> ExtraColumnEvaluator.is_dsl_formula("==literal")
            False
            >>> ExtraColumnEvaluator.is_dsl_formula(123)
            False
        """
        return isinstance(value, str) and value.startswith("=") and not value.startswith("==")

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
            >>> ExtraColumnEvaluator.is_interpolated_string("{first_name} {last_name}")
            True
            >>> ExtraColumnEvaluator.is_interpolated_string("{{literal}}")
            False
            >>> ExtraColumnEvaluator.is_interpolated_string("constant")
            False
            >>> ExtraColumnEvaluator.is_interpolated_string(123)
            False
        """
        if not isinstance(value, str):
            return False

        # Check for unescaped {column} patterns
        return bool(ExtraColumnEvaluator.INTERPOLATION_PATTERN.search(value))

    @staticmethod
    def extract_column_dependencies(pattern: str) -> list[str]:
        """
        Extract column names from interpolated string pattern.

        Args:
            pattern: String containing {column} patterns

        Returns:
            List of unique column names in order of appearance

        Examples:
            >>> ExtraColumnEvaluator.extract_column_dependencies("{first} {last}")
            ['first', 'last']
            >>> ExtraColumnEvaluator.extract_column_dependencies("{a} {a}")
            ['a']
            >>> ExtraColumnEvaluator.extract_column_dependencies("{{literal}}")
            []
        """
        matches = ExtraColumnEvaluator.INTERPOLATION_PATTERN.findall(pattern)
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
            >>> ExtraColumnEvaluator.unescape_braces("{{literal}}")
            '{literal}'
            >>> ExtraColumnEvaluator.unescape_braces("{normal}")
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
        3. For each row, substitute {column} with value
        4. Handle nulls (convert to empty strings)
        5. Coerce all values to strings
        6. Unescape any {{}} to {}

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
            >>> result = ExtraColumnEvaluator.evaluate_interpolation(df, "{a}-{b}", "test")
            >>> result.tolist()
            ['1-x', '-y']
        """
        columns: list[str] = ExtraColumnEvaluator.extract_column_dependencies(pattern)

        # Check all columns exist
        missing: set[str] = set(columns) - set(df.columns)
        if missing:
            entity_suffix: str = f" for entity '{entity_name}'" if entity_name else ""
            raise ValueError(f"Cannot interpolate '{pattern}'{entity_suffix}: " f"columns not found: {sorted(missing)}")

        # Create a row-wise function that handles nulls and types
        def interpolate_row(row: pd.Series) -> str:
            """Interpolate a single row, substituting {column} with values."""
            values: dict[str, str] = {col: "" if pd.isna(row[col]) else to_str(row[col]) for col in columns}

            # First unescape {{}} to a temporary placeholder to protect them
            # Use a placeholder that won't appear in normal text
            temp: str = pattern.replace("{{", "\x00LEFTBRACE\x00").replace("}}", "\x00RIGHTBRACE\x00")

            # Replace each {column} with its value
            for col in columns:
                temp = temp.replace(f"{{{col}}}", values[col])

            # Now restore the escaped braces as literal braces
            return temp.replace("\x00LEFTBRACE\x00", "{").replace("\x00RIGHTBRACE\x00", "}")

        return df[columns].apply(interpolate_row, axis=1)

    def evaluate_extra_columns(
        self,
        df: pd.DataFrame,
        extra_columns: dict[str, Any],
        entity_name: str,
        defer_missing: bool = False,
    ) -> tuple[pd.DataFrame, dict[str, Any]]:
        """Evaluate extra_columns configuration, adding columns to DataFrame.

        Processing order:
        1. Constants (non-string values)
        2. Escaped equals literals (strings starting with '==')
        3. DSL formulas (strings starting with '=' but not '==')
        4. Interpolated strings (strings with {column} patterns)
        5. Column copies (string value matching existing column)
        6. String constants

        When defer_missing=True, formulas and interpolations with missing columns
        are deferred for later evaluation (e.g., after FK linking adds columns).

        Args:
            df: DataFrame to add columns to
            extra_columns: Dict of {new_column: value/pattern/formula}
            entity_name: For logging and error messages
            defer_missing: If True, defer formulas/interpolations with missing columns

        Returns:
            Tuple of (updated_df, deferred_extra_columns)
            - updated_df: DataFrame with new columns added
            - deferred_extra_columns: Dict of items that were deferred

        Examples:
            >>> df = pd.DataFrame({"a": [1, 2]})
            >>> evaluator = ExtraColumnEvaluator()
            >>> result, deferred = evaluator.evaluate_extra_columns(
            ...     df, {"const": 99, "copy": "a", "interp": "{a}", "formula": "=upper(a)"}, "test"
            ... )
            >>> list(result.columns)
            ['a', 'const', 'copy', 'interp', 'formula']
        """
        if not extra_columns:
            return df, {}

        result: pd.DataFrame = df.copy()
        deferred: dict[str, Any] = {}
        added_count = 0
        skipped_count = 0

        for new_col, value in extra_columns.items():

            # Skip if column already exists in DataFrame (idempotent evaluation)
            # This allows passing the full extra_columns dict multiple times
            if new_col in result.columns:
                skipped_count += 1
                logger.trace(f"{entity_name}[extra_columns]: Skipping '{new_col}' (already exists)")
                continue

            # Case 1: Non-string constant
            if not isinstance(value, str):
                result[new_col] = value
                added_count += 1
                logger.trace(f"{entity_name}[extra_columns]: Added constant '{new_col}' = {value}")
                continue

            # Case 2: Escaped equals literal (starts with '==')
            if self.is_escaped_equals_literal(value):
                result[new_col] = self.unescape_equals_literal(value)
                added_count += 1
                logger.trace(
                    f"{entity_name}[extra_columns]: Added escaped literal '{new_col}' = '{value}' -> "
                    f"'{result[new_col].iloc[0] if len(result) > 0 else self.unescape_equals_literal(value)}'"
                )
                continue

            # Case 3: DSL formula (starts with '=' but not '==')
            if self.is_dsl_formula(value):
                try:
                    # Parse formula and extract dependencies
                    ast = self.formula_engine.parse(value)
                    columns = list(extract_column_references(ast))
                    missing: set[str] = set(columns) - set(result.columns)

                    if missing:
                        if defer_missing:
                            deferred[new_col] = value
                            logger.trace(
                                f"{entity_name}[extra_columns]: Deferred formula '{new_col}' " f"(missing columns: {sorted(missing)})"
                            )
                        else:
                            raise ValueError(
                                f"{entity_name}[extra_columns]: Cannot evaluate '{new_col}' = '{value}': "
                                f"columns not found: {sorted(missing)}"
                            )
                        continue

                    # All columns available - compile (parse + validate) and evaluate
                    compiled_ast = self.formula_engine.compile(value, result.columns)
                    result[new_col] = self.formula_engine.evaluate(compiled_ast, result)
                    added_count += 1
                    logger.trace(f"{entity_name}[extra_columns]: Added formula '{new_col}' = '{value}'")

                except Exception as e:
                    raise ValueError(f"{entity_name}[extra_columns]: Error evaluating formula '{new_col}' = '{value}': {e}") from e

                continue

            # Case 4: Interpolated string
            if self.is_interpolated_string(value):
                columns: list[str] = self.extract_column_dependencies(value)
                missing: set[str] = set(columns) - set(result.columns)

                if missing:
                    if defer_missing:
                        deferred[new_col] = value
                        logger.trace(
                            f"{entity_name}[extra_columns]: Deferred interpolation '{new_col}' " f"(missing columns: {sorted(missing)})"
                        )
                    else:
                        raise ValueError(
                            f"{entity_name}[extra_columns]: Cannot evaluate '{new_col}' = '{value}': "
                            f"columns not found: {sorted(missing)}"
                        )
                    continue

                # All columns available - evaluate
                result[new_col] = self.evaluate_interpolation(result, value, entity_name)
                added_count += 1
                logger.trace(f"{entity_name}[extra_columns]: Added interpolation '{new_col}' = '{value}'")
                continue

            # Case 5: Column copy (string matching existing column, case-insensitive)
            # BUT: If value matches another extra_column key, treat as literal constant to avoid ambiguity
            # (e.g., extra_columns: {abundance: FAnzahl, analysis_entity_type: abundance})
            # Convert column names to strings to handle any non-string column names
            col_lower: str = value.lower()
            col_map: dict[str, str] = {str(c).lower(): c for c in result.columns if isinstance(c, str)}

            # Check if value matches an extra_column key (case-insensitive)
            extra_col_keys_lower = {str(k).lower() for k in extra_columns.keys()}
            is_extra_col_ref = col_lower in extra_col_keys_lower

            if col_lower in col_map and not is_extra_col_ref:
                result[new_col] = result[col_map[col_lower]]
                added_count += 1
                logger.trace(f"{entity_name}[extra_columns]: Copied column '{new_col}' from '{value}'")
                continue

            # Case 6: String constant (doesn't match any column, or matches extra_column key)
            result[new_col] = value
            added_count += 1
            logger.trace(f"{entity_name}[extra_columns]: Added constant '{new_col}' = '{value}'")

        if added_count > 0 or deferred or skipped_count > 0:
            msg_parts = []
            if added_count > 0:
                msg_parts.append(f"Added {added_count} column(s)")
            if deferred:
                msg_parts.append(f"deferred {len(deferred)}")
            if skipped_count > 0:
                msg_parts.append(f"skipped {skipped_count} (already exist)")
            logger.info(f"{entity_name}[extra_columns]: {', '.join(msg_parts)}")

        return result, deferred

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

        missing_columns = [col for col in extra_columns.keys() if col not in df.columns]

        if missing_columns:
            logger.warning(f"{entity_name}[extra_columns]: Unresolved columns after normalization: {missing_columns}")
            return False

        return True

    @staticmethod
    def split_extra_columns(
        source: pd.DataFrame, extra_columns: dict[str, Any], case_sensitive: bool = False
    ) -> tuple[dict[str, str], dict[str, Any]]:
        """Split extra columns into those that copy existing source columns and those that are constants."""
        source_columns: dict[str, str]
        if not case_sensitive:
            # Convert column names to strings to handle NaN/float columns from Excel
            source_columns_lower: dict[str, str] = {str(col).lower(): col for col in source.columns if isinstance(col, str)}
            source_columns = {
                k: source_columns_lower[v.lower()]
                for k, v in extra_columns.items()
                if isinstance(v, str) and v.lower() in source_columns_lower
            }
        else:
            source_columns = {k: v for k, v in extra_columns.items() if isinstance(v, str) and v in source.columns}

        constant_columns: dict[str, Any] = {new_name: value for new_name, value in extra_columns.items() if new_name not in source_columns}

        return source_columns, constant_columns
