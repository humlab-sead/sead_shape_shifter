"""Utilities for YAML processing and type conversion.

DEPRECATION NOTE: convert_ruamel_types() is no longer needed.
YamlService.load() now converts ruamel.yaml wrapper types to plain Python types
at the I/O boundary, preventing type pollution in service layer code.

FUTURE: Consider migrating to ryaml (https://pypi.org/project/ryaml/) which is an
actively maintained community fork of ruamel.yaml. ryaml is API-compatible and can
be swapped in as a drop-in replacement if needed.
"""

from typing import Any


def convert_ruamel_types(obj: Any) -> Any:
    """
    DEPRECATED: No longer needed. Kept for backward compatibility.

    Recursively convert ruamel.yaml types to plain Python types.

    This is necessary because ruamel.yaml uses special string subclasses
    like DoubleQuotedScalarString, SingleQuotedScalarString, etc. that can
    cause issues during serialization and when code expects plain Python types.

    YamlService.load() now handles this conversion automatically at the I/O boundary,
    so this function should not be needed in new code.

    Args:
        obj: Any Python object, potentially containing ruamel.yaml types

    Returns:
        The same object structure with all ruamel.yaml types converted to
        plain Python equivalents (str, dict, list, etc.). Empty/whitespace-only
        strings are preserved (not converted to None) to maintain semantics.

    Examples:
        >>> from ruamel.yaml.scalarstring import DoubleQuotedScalarString
        >>> obj = {"key": DoubleQuotedScalarString("value")}
        >>> convert_ruamel_types(obj)
        {'key': 'value'}

        >>> nested = {"outer": [DoubleQuotedScalarString("a"), {"inner": DoubleQuotedScalarString("b")}]}
        >>> convert_ruamel_types(nested)
        {'outer': ['a', {'inner': 'b'}]}
    """
    if isinstance(obj, str):
        # Convert any string subclass (including ruamel types) to plain str
        return str(obj)
    if isinstance(obj, dict):
        # Recursively convert dict values
        return {k: convert_ruamel_types(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        # Recursively convert list/tuple items
        return [convert_ruamel_types(item) for item in obj]
    # Return other types as-is (bool, int, float, None, etc.)
    return obj
