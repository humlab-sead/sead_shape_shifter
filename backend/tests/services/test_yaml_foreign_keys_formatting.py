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


if __name__ == "__main__":
    test_foreign_keys_block_style()
