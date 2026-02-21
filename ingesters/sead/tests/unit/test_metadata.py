import pytest

from ingesters.sead.tests.builders import build_column, build_schema, build_table

# pylint: disable=redefined-outer-name,no-member


def test_metadata_load_metadata():
    """Test that schema structure has expected attributes."""
    schema = build_schema([build_table("tbl_test", "test_id")])

    assert schema.source_tables is not None
    assert schema.source_columns is not None
    assert isinstance(schema._tables, dict)
    assert schema._foreign_keys is not None


def test_tables_specifications():
    """Test table and column metadata structure."""
    schema = build_schema(
        [
            build_table(
                "tbl_sites",
                "site_id",
                columns={
                    "site_id": build_column("tbl_sites", "site_id", is_pk=True),
                    "site_name": build_column("tbl_sites", "site_name", data_type="varchar"),
                },
            ),
            build_table(
                "tbl_locations",
                "location_id",
                columns={
                    "location_id": build_column("tbl_locations", "location_id", is_pk=True),
                    "location_type_id": build_column("tbl_locations", "location_type_id", is_fk=True, fk_table_name="tbl_location_types"),
                },
            ),
        ]
    )

    assert isinstance(schema._tables, dict)
    assert len(schema.source_tables) == len(schema)

    # Check table structure
    assert "columns" in schema["tbl_sites"].keys()
    assert "site_id" in schema["tbl_sites"].columns.keys()
    assert len(schema["tbl_sites"].columns) == 2

    # Check PK/FK flags
    assert schema["tbl_sites"].columns["site_id"].is_pk is True
    assert schema["tbl_sites"].columns["site_name"].is_pk is False
    assert schema["tbl_locations"].columns["location_type_id"].is_fk is True
    assert schema["tbl_locations"].columns["location_id"].is_fk is False
    assert schema["tbl_locations"].columns["location_id"].is_pk is True


def test_is_pk():
    """Test primary key identification."""
    schema = build_schema(
        [
            build_table(
                "tbl_sites",
                "site_id",
                columns={
                    "site_id": build_column("tbl_sites", "site_id", is_pk=True),
                    "site_name": build_column("tbl_sites", "site_name", data_type="varchar"),
                },
            ),
            build_table(
                "tbl_locations",
                "location_id",
                columns={
                    "location_id": build_column("tbl_locations", "location_id", is_pk=True),
                    "location_type_id": build_column("tbl_locations", "location_type_id", is_fk=True),
                },
            ),
        ]
    )

    assert schema.is_pk("tbl_sites", "site_id") is True
    assert schema.is_pk("tbl_sites", "site_name") is False
    assert schema.is_pk("tbl_locations", "location_type_id") is False
    assert schema.is_pk("tbl_locations", "location_id") is True


def test_is_fk():
    """Test foreign key identification."""
    schema = build_schema(
        [
            build_table(
                "tbl_sites",
                "site_id",
                columns={
                    "site_id": build_column("tbl_sites", "site_id", is_pk=True),
                    "site_name": build_column("tbl_sites", "site_name", data_type="varchar"),
                },
            ),
            build_table(
                "tbl_locations",
                "location_id",
                columns={
                    "location_id": build_column("tbl_locations", "location_id", is_pk=True),
                    "location_type_id": build_column("tbl_locations", "location_type_id", is_fk=True, fk_table_name="tbl_location_types"),
                },
            ),
        ]
    )

    assert schema.is_fk("tbl_sites", "site_id") is False
    assert schema.is_fk("tbl_sites", "site_name") is False
    assert schema.is_fk("tbl_locations", "location_type_id") is True
    assert schema.is_fk("tbl_locations", "location_id") is False


def test_get_tablenames_referencing():
    """Test finding tables that reference a given table."""
    schema = build_schema(
        [
            build_table("tbl_sites", "site_id", columns={"site_id": build_column("tbl_sites", "site_id", is_pk=True)}),
            build_table(
                "tbl_sample_groups",
                "sample_group_id",
                columns={
                    "sample_group_id": build_column("tbl_sample_groups", "sample_group_id", is_pk=True),
                    "site_id": build_column("tbl_sample_groups", "site_id", is_fk=True, fk_table_name="tbl_sites"),
                },
            ),
            build_table(
                "tbl_site_images",
                "site_image_id",
                columns={
                    "site_image_id": build_column("tbl_site_images", "site_image_id", is_pk=True),
                    "site_id": build_column("tbl_site_images", "site_id", is_fk=True, fk_table_name="tbl_sites"),
                },
            ),
        ]
    )

    referencing_tables = set(schema.get_tablenames_referencing("tbl_sites"))
    assert referencing_tables == {"tbl_sample_groups", "tbl_site_images"}


@pytest.mark.parametrize(
    "table_name,fk_column,fk_table,fk_class",
    [
        ("tbl_abundances", "abundance_element_id", "tbl_abundance_elements", "TblAbundanceElements"),
        ("tbl_analysis_entities", "physical_sample_id", "tbl_physical_samples", "TblPhysicalSamples"),
        ("tbl_datasets", "master_set_id", "tbl_dataset_masters", "TblDatasetMasters"),
        ("tbl_datasets", "project_id", "tbl_projects", "TblProjects"),
    ],
)
def test_foreign_keys(table_name: str, fk_column: str, fk_table: str, fk_class: str):
    """Test foreign key metadata is correctly stored."""
    schema = build_schema(
        [
            build_table(
                fk_table,
                f"{fk_table.replace('tbl_', '')}_id",
                columns={f"{fk_table.replace('tbl_', '')}_id": build_column(fk_table, f"{fk_table.replace('tbl_', '')}_id", is_pk=True)},
            ),
            build_table(
                table_name,
                f"{table_name.replace('tbl_', '')}_id",
                columns={
                    f"{table_name.replace('tbl_', '')}_id": build_column(table_name, f"{table_name.replace('tbl_', '')}_id", is_pk=True),
                    fk_column: build_column(
                        table_name,
                        fk_column,
                        is_fk=True,
                        fk_table_name=fk_table,
                        fk_column_name=fk_column,
                        class_name=fk_class,
                    ),
                },
            ),
        ]
    )

    # Verify FK metadata exists
    assert schema._foreign_keys is not None
    assert len(schema._foreign_keys) > 0

    # Verify this specific FK relationship exists
    fk_row = schema._foreign_keys[(schema._foreign_keys["table_name"] == table_name) & (schema._foreign_keys["column_name"] == fk_column)]
    assert len(fk_row) > 0
    assert fk_row.iloc[0]["fk_table_name"] == fk_table
    assert fk_row.iloc[0]["class_name"] == fk_class
