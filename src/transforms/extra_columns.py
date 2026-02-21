"""
Extra columns evaluation with support for constants, column copies, and interpolated strings.

This module provides functionality to evaluate extra_columns configurations,
including support for interpolated string patterns like "{first_name} {last_name}".
"""

import re
from typing import Any

import pandas as pd
from loguru import logger


def to_str(val: Any) -> str:
    """Convert value to string, handling numbers and nulls."""
    if isinstance(val, (float, int)):
        if isinstance(val, float) and val == int(val):
            return str(int(val))
        return str(val)
    return str(val)


class ExtraColumnEvaluator:
    """Evaluates extra_columns with support for constants, copies, and interpolated strings.

    The evaluator supports multiple evaluation modes:
    1. Constants: Non-string values or string literals
    2. Column copies: String matching an existing column name
    3. Interpolated strings: String containing {column_name} patterns

    Interpolated strings support:
    - Null-safe evaluation (nulls become empty strings)
    - Type coercion (all values converted to strings)
    - Escaped braces ({{ and }} become { and })
    - Deferred evaluation (for columns not yet available)

    Example:
        >>> evaluator = ExtraColumnEvaluator()
        >>> df = pd.DataFrame({"first": ["John"], "last": ["Doe"]})
        >>> extra_cols = {"fullname": "{first} {last}"}
        >>> result, deferred = evaluator.evaluate_extra_columns(df, extra_cols, "person")
        >>> result["fullname"].iloc[0]
        'John Doe'
    """

    # Regex pattern: match {column_name} but not {{escaped}}
    # Matches: {col}, {first_name}, {col123}
    # Doesn't match: {{literal}}, {123invalid}
    INTERPOLATION_PATTERN = re.compile(r"(?<!\{)\{([a-zA-Z_][\w]*)\}(?!\})")

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
        """
        Evaluate extra_columns configuration, adding columns to DataFrame.

        Processing order:
        1. Constants (non-string values or simple strings)
        2. Column copies (string value matching existing column)
        3. Interpolated strings (string with {column} patterns)

        When defer_missing=True, interpolations with missing columns are deferred
        for later evaluation (e.g., after FK linking adds columns).

        Args:
            df: DataFrame to add columns to
            extra_columns: Dict of {new_column: value/pattern}
            entity_name: For logging and error messages
            defer_missing: If True, defer interpolations with missing columns

        Returns:
            Tuple of (updated_df, deferred_extra_columns)
            - updated_df: DataFrame with new columns added
            - deferred_extra_columns: Dict of items that were deferred

        Examples:
            >>> df = pd.DataFrame({"a": [1, 2]})
            >>> evaluator = ExtraColumnEvaluator()
            >>> result, deferred = evaluator.evaluate_extra_columns(
            ...     df, {"const": 99, "copy": "a", "interp": "{a}"}, "test"
            ... )
            >>> list(result.columns)
            ['a', 'const', 'copy', 'interp']
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
                logger.debug(f"{entity_name}[extra_columns]: Skipping '{new_col}' (already exists)")
                continue

            # Case 1: Non-string constant
            if not isinstance(value, str):
                result[new_col] = value
                added_count += 1
                logger.debug(f"{entity_name}[extra_columns]: Added constant '{new_col}' = {value}")
                continue

            # Case 2: Interpolated string
            if self.is_interpolated_string(value):
                columns: list[str] = self.extract_column_dependencies(value)
                missing: set[str] = set(columns) - set(result.columns)

                if missing:
                    if defer_missing:
                        deferred[new_col] = value
                        logger.debug(
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
                logger.debug(f"{entity_name}[extra_columns]: Added interpolation '{new_col}' = '{value}'")
                continue

            # Case 3: Column copy (string matching existing column, case-insensitive)
            # Convert column names to strings to handle any non-string column names
            col_lower: str = value.lower()
            col_map: dict[str, str] = {str(c).lower(): c for c in result.columns if isinstance(c, str)}

            if col_lower in col_map:
                result[new_col] = result[col_map[col_lower]]
                added_count += 1
                logger.debug(f"{entity_name}[extra_columns]: Copied column '{new_col}' from '{value}'")
                continue

            # Case 4: String constant (doesn't match any column)
            result[new_col] = value
            added_count += 1
            logger.debug(f"{entity_name}[extra_columns]: Added constant '{new_col}' = '{value}'")

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
