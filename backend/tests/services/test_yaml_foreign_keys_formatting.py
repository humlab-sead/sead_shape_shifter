"""Test foreign_keys block formatting."""

import tempfile
from pathlib import Path

from backend.app.services.yaml_service import YamlService


def test_foreign_keys_block_style():
    """Verify foreign_keys are formatted in readable block style, not compact flow style."""
    yaml_service = YamlService()

    # Test data with foreign_keys (complex nested structure)
    data = {
        "entities": {
            "test_entity": {
                "type": "entity",
                "columns": [],
                "keys": ["col1", "col2"],  # Should use flow style (short list)
                "foreign_keys": [  # Should use block style (complex structure)
                    {"entity": "parent1", "local_keys": ["col1"], "remote_keys": ["id"], "extra_columns": {"name": "parent_name"}},
                    {"entity": "parent2", "local_keys": ["col2"], "remote_keys": ["id"]},
                ],
                "depends_on": ["parent1", "parent2"],  # Should use flow style
            }
        }
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        temp_path = Path(f.name)

    try:
        yaml_service.save(data, temp_path, create_backup=False)
        content: str = temp_path.read_text(encoding="utf-8")

        print("\n=== Saved YAML ===")
        print(content)

        # Verify foreign_keys use block style
        assert "foreign_keys:" in content, "Missing foreign_keys key"
        assert "- entity: parent1" in content, "Foreign keys should use block style with '- entity:'"
        assert "extra_columns:" in content, "Extra columns should be on separate line"
        assert "name: parent_name" in content, "Extra columns dict should use block style"

        # Verify short lists still use flow style
        assert "keys: [col1, col2]" in content, "Short lists like 'keys' should use flow style"
        assert "depends_on: [parent1, parent2]" in content, "Short lists like 'depends_on' should use flow style"

        print("\n✅ Foreign keys formatted in readable block style")
        print("✅ Short lists still use compact flow style")

    finally:
        temp_path.unlink()


def test_append_uses_block_style_but_preserves_compact_columns():
    """Verify append entries use block style while nested columns stay flow style."""
    yaml_service = YamlService()

    data = {
        "entities": {
            "analysis_entity": {
                "type": "fixed",
                "append": [
                    {
                        "source": "abundance",
                        "columns": [
                            "PCODE",
                            "Fraktion",
                            "cf",
                            "RTyp",
                            "Zust",
                            "ArchDat",
                            "analysis_entity_type",
                            "analysis_entity_value",
                        ],
                    },
                    {
                        "source": "_analysis_entity_relative_dating",
                        "columns": [
                            "PCODE",
                            "Fraktion",
                            "cf",
                            "RTyp",
                            "Zust",
                            "ArchDat",
                            "analysis_entity_type",
                            "analysis_entity_value",
                        ],
                    },
                ],
            }
        }
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        temp_path = Path(f.name)

    try:
        yaml_service.save(data, temp_path, create_backup=False)
        content: str = temp_path.read_text(encoding="utf-8")

        assert "append:" in content, "Missing append key"
        assert "append: [{source:" not in content, "Append should not be serialized as a flow-style JSON-like list"
        assert "append:\n    - source: abundance" in content, "Append entries should use block style"
        assert "    - source: _analysis_entity_relative_dating" in content, "Second append entry should use block style"
        assert (
            "columns: [PCODE, Fraktion, cf, RTyp, Zust, ArchDat, analysis_entity_type, analysis_entity_value]" in content
        ), "Nested columns list should remain compact flow style"

    finally:
        temp_path.unlink()


if __name__ == "__main__":
    test_foreign_keys_block_style()
