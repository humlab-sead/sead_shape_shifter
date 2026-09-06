from __future__ import annotations

from pathlib import Path

from pylint.lint import Run

from src.target_model.schema_reference import generate_target_model_schema_reference

REFERENCE_PATH = Path("docs/TARGET_MODEL_SCHEMA_REFERENCE.md")


def test_generated_reference_lists_expected_yaml_paths():
    rendered = generate_target_model_schema_reference()

    assert "# Target Model Schema Reference" in rendered
    assert "- `model`: ModelMetadata (required)" in rendered
    assert "- `entities.<entity_name>.columns.<column_name>.required`: boolean (optional)" in rendered
    assert "- `entities.<entity_name>.foreign_keys[].via`: string | null (optional)" in rendered


def test_generated_reference_lists_allowed_enum_values():
    rendered = generate_target_model_schema_reference()

    assert (
        r'| role | enum[string] \\| null | No | null | "fact", "lookup", "classifier", "bridge", null |'.replace("\\\\|", "\\|") in rendered
    )
    assert r'| identity_tracking | enum[string] \| null | No | null | "tracked", "reconciled", "derived", "child", null |' in rendered


def test_committed_reference_is_in_sync():
    committed = REFERENCE_PATH.read_text(encoding="utf-8")

    # Ensure the committed reference matches the generated reference
    # Run `make generate-target-model-schema-reference` to update the reference if it has changed

    assert committed == generate_target_model_schema_reference(), (
        "The committed reference is out of sync with the generated reference. "
        "Run `make generate-target-model-schema-reference` to update the reference if it has changed."
    )
