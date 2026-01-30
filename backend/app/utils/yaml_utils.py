"""Utilities for YAML processing and type conversion."""

from typing import Any


def convert_ruamel_types(obj: Any) -> Any:
    """
    Recursively convert ruamel.yaml types to plain Python types.
    
    This is necessary because ruamel.yaml uses special string subclasses
    like DoubleQuotedScalarString, SingleQuotedScalarString, etc. that can
    cause issues during serialization and when code expects plain Python types.
    
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
    elif isinstance(obj, dict):
        # Recursively convert dict values
        return {k: convert_ruamel_types(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        # Recursively convert list/tuple items
        return [convert_ruamel_types(item) for item in obj]
    else:
        # Return other types as-is (bool, int, float, None, etc.)
        return obj
