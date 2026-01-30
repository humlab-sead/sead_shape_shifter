"""Tests for YAML utility functions."""

import pytest

from backend.app.utils.yaml_utils import convert_ruamel_types


class TestConvertRuamelTypes:
    """Tests for convert_ruamel_types utility function."""

    def test_plain_string(self):
        """Plain strings are returned as-is."""
        result = convert_ruamel_types("hello")
        assert result == "hello"
        assert isinstance(result, str)

    def test_plain_dict(self):
        """Plain dicts are returned as-is."""
        obj = {"key": "value", "num": 42}
        result = convert_ruamel_types(obj)
        assert result == obj

    def test_plain_list(self):
        """Plain lists are returned as-is."""
        obj = ["a", "b", 42, True]
        result = convert_ruamel_types(obj)
        assert result == obj

    def test_none_value(self):
        """None is preserved."""
        assert convert_ruamel_types(None) is None

    def test_empty_string(self):
        """Empty strings are preserved as-is (not converted to None)."""
        assert convert_ruamel_types("") == ""
        assert convert_ruamel_types("  ") == "  "
        assert convert_ruamel_types("\t\n") == "\t\n"
        # This preserves semantics when empty strings appear in lists/dicts

    def test_nested_dict(self):
        """Nested dicts are recursively converted."""
        obj = {
            "outer": {
                "inner": {
                    "value": "test"
                }
            }
        }
        result = convert_ruamel_types(obj)
        assert result == obj

    def test_nested_list(self):
        """Nested lists are recursively converted."""
        obj = [["a", "b"], ["c", ["d", "e"]]]
        result = convert_ruamel_types(obj)
        assert result == obj

    def test_mixed_nested_structures(self):
        """Mixed nested dicts and lists are handled correctly."""
        obj = {
            "list": [1, 2, {"nested": "value"}],
            "dict": {"key": [3, 4, 5]},
        }
        result = convert_ruamel_types(obj)
        assert result == obj

    def test_ruamel_double_quoted_string(self):
        """ruamel.yaml DoubleQuotedScalarString is converted to plain str."""
        try:
            from ruamel.yaml.scalarstring import DoubleQuotedScalarString
        except ImportError:
            pytest.skip("ruamel.yaml not installed")

        obj = DoubleQuotedScalarString("test")
        result = convert_ruamel_types(obj)
        assert result == "test"
        assert type(result) is str  # Exact type check, not isinstance

    def test_ruamel_single_quoted_string(self):
        """ruamel.yaml SingleQuotedScalarString is converted to plain str."""
        try:
            from ruamel.yaml.scalarstring import SingleQuotedScalarString
        except ImportError:
            pytest.skip("ruamel.yaml not installed")

        obj = SingleQuotedScalarString("test")
        result = convert_ruamel_types(obj)
        assert result == "test"
        assert type(result) is str

    def test_nested_ruamel_types_in_dict(self):
        """Nested ruamel types in dicts are converted."""
        try:
            from ruamel.yaml.scalarstring import DoubleQuotedScalarString
        except ImportError:
            pytest.skip("ruamel.yaml not installed")

        obj = {
            "key1": DoubleQuotedScalarString("value1"),
            "key2": {
                "nested": DoubleQuotedScalarString("value2")
            }
        }
        result = convert_ruamel_types(obj)
        assert result == {"key1": "value1", "key2": {"nested": "value2"}}
        assert type(result["key1"]) is str
        assert type(result["key2"]["nested"]) is str

    def test_nested_ruamel_types_in_list(self):
        """Nested ruamel types in lists are converted."""
        try:
            from ruamel.yaml.scalarstring import DoubleQuotedScalarString
        except ImportError:
            pytest.skip("ruamel.yaml not installed")

        obj = [
            DoubleQuotedScalarString("a"),
            {"key": DoubleQuotedScalarString("b")},
            [DoubleQuotedScalarString("c")]
        ]
        result = convert_ruamel_types(obj)
        assert result == ["a", {"key": "b"}, ["c"]]
        assert type(result[0]) is str
        assert type(result[1]["key"]) is str
        assert type(result[2][0]) is str

    def test_preserves_other_types(self):
        """Other Python types (bool, int, float) are preserved."""
        obj = {
            "bool": True,
            "int": 42,
            "float": 3.14,
            "none": None,
        }
        result = convert_ruamel_types(obj)
        assert result == obj
        assert isinstance(result["bool"], bool)
        assert isinstance(result["int"], int)
        assert isinstance(result["float"], float)
        assert result["none"] is None
