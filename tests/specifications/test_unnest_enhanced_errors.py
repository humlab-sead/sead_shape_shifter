"""Test that demonstrates improved error messages in UnnestColumnsSpecification."""

from src.specifications.entity import UnnestColumnsSpecification


def test_unnest_columns_spec_includes_available_columns():
    """Verify that config-time validation now lists available columns like runtime does."""
    project_cfg = {
        "entities": {
            "site_property": {
                "type": "entity",
                "columns": ["site_id", "socken", "raanr"],
                "extra_columns": {
                    "raa_number": "{socken} {raanr}",  # This IS available
                },
                "unnest": {
                    "id_vars": ["site_id"],
                    "value_vars": ["raa_number", "lamningsnummer"],  # lamningsnummer is NOT
                    "var_name": "property_type",
                    "value_name": "property_value",
                },
            }
        }
    }

    spec = UnnestColumnsSpecification(project_cfg)
    result = spec.is_satisfied_by(entity_name="site_property")

    assert result is False
    assert len(spec.errors) == 1

    error_msg = spec.errors[0].message

    # Verify error includes missing column
    assert "lamningsnummer" in error_msg

    # Verify error lists available columns for debugging
    assert "Available columns:" in error_msg
    assert "site_id" in error_msg
    assert "socken" in error_msg
    assert "raanr" in error_msg
    assert "raa_number" in error_msg  # extra_columns should be included

    # Verify error provides helpful guidance
    assert "'columns'" in error_msg
    assert "'keys'" in error_msg
    assert "'extra_columns'" in error_msg
    assert "foreign keys" in error_msg

    print("\n" + "=" * 80)
    print("Enhanced config-time error message:")
    print("=" * 80)
    print(error_msg)
    print("=" * 80)


if __name__ == "__main__":
    test_unnest_columns_spec_includes_available_columns()
    print("\n✅ Config-time validation now provides detailed, actionable error messages!")
