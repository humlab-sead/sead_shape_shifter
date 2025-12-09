from typing import Any

import yaml

from src.utility import dotget

REF_TAG = "@value:"


def _parse_list_expression(expr: str, full_data: dict[str, Any]) -> list[Any] | str:
    """
    Parse and evaluate list expressions with "@value:" directives and list operations.

    Constraints:
    - No nested lists allowed (flat lists only)
    - No brackets in list values

    Supports:
    - Simple value: "@value: path.to.list"
    - Prepend: "['a', 'b'] + @value: path.to.list"
    - Append: "@value: path.to.list + ['c', 'd']"
    - Multiple values: "@value: path1 + @value: path2"
    - Chaining: "['a'] + @value: path1 + @value: path2 + ['b']"

    Args:
        expr: String expression containing @value directives and/or list operations
        full_data: Full configuration data for resolving includes

    Returns:
        Evaluated list or original expression if not a list operation or if parsing fails
    """

    # Quick check: no list operations present
    if REF_TAG not in expr and "[" not in expr:
        return expr

    # Validate bracket balance
    if expr.count("[") != expr.count("]"):
        return expr  # Malformed expression

    # If no + operator found, not a list operation
    if "+" not in expr:
        return expr if not expr.startswith(REF_TAG) else expr

    # Split by '+' while tracking bracket depth (simple state machine)
    tokens: list[str] = []
    current_token: str = ""
    bracket_depth: int = 0

    for char in expr:
        if char == "[":
            bracket_depth += 1
            current_token += char
        elif char == "]":
            bracket_depth -= 1
            current_token += char
            # Check for nested brackets (violation of constraint #1)
            if bracket_depth < 0:
                return expr  # Malformed
        elif char == "+" and bracket_depth == 0:
            if current_token.strip():
                tokens.append(current_token.strip())
            current_token = ""
        else:
            current_token += char

    if current_token.strip():
        tokens.append(current_token.strip())

    # Final validation: bracket depth should be zero
    if bracket_depth != 0:
        return expr

    # If only one token and it's a simple include, return for normal processing
    if len(tokens) == 1 and tokens[0].startswith(REF_TAG):
        return tokens[0]

    # Process each token and build result list
    result: list[Any] = []

    for token in tokens:
        if token.startswith(REF_TAG):
            # Resolve include directive
            ref_path = token[len(REF_TAG) :].strip()
            ref_value = dotget(full_data, ref_path)  # type: ignore

            if ref_value is None:
                continue

            # Recursively resolve references in the value
            ref_value = _replace_references(ref_value, full_data=full_data)

            if isinstance(ref_value, list):
                # Constraint #1: No nested lists
                if any(isinstance(item, list) for item in ref_value):
                    return expr  # Violation: return original
                result.extend(ref_value)
            else:
                result.append(ref_value)

        elif token.startswith("[") and token.endswith("]"):
            # Constraint #4: Check for brackets in string content (excluding outer brackets)
            # Count all brackets in token - should be exactly 2 (opening and closing) for flat list
            inner_content = token[1:-1]  # Remove outer brackets
            if "[" in inner_content or "]" in inner_content:
                return expr  # Violation: nested brackets or brackets in values

            # Parse list literal
            try:
                list_value = yaml.safe_load(token)
                if isinstance(list_value, list):
                    # Constraint #1: No nested lists (double-check after parsing)
                    if any(isinstance(item, list) for item in list_value):
                        return expr  # Violation: return original
                    result.extend(list_value)
                else:
                    result.append(list_value)
            except:  # pylint: disable=bare-except
                return expr  # Parse error: return original

    return result if result else expr


def _replace_references(
    data: dict[str, Any] | list[Any] | str, full_data: dict[str, Any] | list[Any] | str
) -> dict[str, Any] | list[Any] | str:
    """Helper function for replace_references"""
    if isinstance(data, dict):
        return {k: _replace_references(v, full_data=full_data) for k, v in data.items()}
    if isinstance(data, list):
        return [_replace_references(i, full_data=full_data) for i in data]
    if isinstance(data, str):
        # Check for list expressions with operations
        if (REF_TAG in data and "+" in data) or (data.count("[") > 0 and "+" in data):
            parsed = _parse_list_expression(data, full_data)  # type: ignore
            # Only recurse if parsing actually changed the value and it's not a string
            if parsed != data and not isinstance(parsed, str):
                return _replace_references(parsed, full_data=full_data)
            # If still a string or unchanged, continue to simple include check
            if isinstance(parsed, str):
                data = parsed

        # Handle simple include directive
        if data.startswith(REF_TAG):
            ref_path: str = data[len(REF_TAG) :].strip()
            ref_value: Any = dotget(full_data, ref_path)  # type: ignore
            ref_value = _replace_references(ref_value, full_data=full_data)
            return ref_value if ref_value is not None else data
    return data


def replace_references(data: dict[str, Any] | list[Any] | str) -> dict[str, Any] | list[Any] | str:
    """
    Recursively searches dict for values matching @value directives optionally with list operations.

    Supports:
    - Simple value: "@value: some.path.to.value"
    - List concatenation: "['item'] + @value: path.to.list"
    - Multiple operations: "@value: path1 + ['item'] + @value: path2"

    Args:
        data: Configuration data to process

    Returns:
        Processed data with all references and operations resolved
    """
    return _replace_references(data, full_data=data)
