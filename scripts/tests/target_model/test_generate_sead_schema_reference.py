from __future__ import annotations

from pathlib import Path

import pytest

from scripts.target_model import generate_sead_schema_reference as reference

HEADER = (
    "table_schema,table_name,column_name,ordinal_position,data_type,numeric_precision,numeric_scale,"
    "character_maximum_length,is_nullable,is_pk,is_fk,fk_table_name,fk_column_name\n"
)
ROWS = (
    "public,tbl_sites,site_id,1,integer,32,0,NULL,NO,YES,NO,NULL,NULL\n"
    "public,tbl_sites,site_name,2,character varying,NULL,NULL,60,YES,NO,NO,NULL,NULL\n"
    "public,tbl_sites,altitude,3,numeric(18,10),18,10,NULL,YES,NO,NO,NULL,NULL\n"
    "public,tbl_samples,sample_id,1,integer,32,0,NULL,NO,YES,NO,NULL,NULL\n"
    "public,tbl_samples,site_id,2,integer,32,0,NULL,NO,NO,YES,tbl_sites,site_id\n"
    "public,tbl_samples,weight,3,numeric,10,2,NULL,YES,NO,NO,,\n"
)


def write_csv(tmp_path: Path, content: str = HEADER + ROWS) -> Path:
    path = tmp_path / "columns.csv"
    path.write_text(content, encoding="utf-8")
    return path


def test_load_columns_reads_keys_and_treats_null_text_and_empty_as_missing(tmp_path: Path) -> None:
    columns = reference.load_columns(write_csv(tmp_path))

    by_name = {(column.table, column.name): column for column in columns}
    assert by_name[("tbl_sites", "site_id")].primary_key
    assert by_name[("tbl_samples", "site_id")].fk_table == "tbl_sites"
    assert by_name[("tbl_samples", "weight")].fk_table is None
    assert by_name[("tbl_sites", "site_name")].max_length == "60"
    assert [column.table for column in columns] == sorted(column.table for column in columns)


def test_type_text_adds_length_and_numeric_precision(tmp_path: Path) -> None:
    by_name = {column.name: column for column in reference.load_columns(write_csv(tmp_path))}

    assert by_name["site_name"].type_text == "character varying(60)"
    assert by_name["weight"].type_text == "numeric(10,2)"
    assert by_name["site_id"].type_text == "integer"


def test_render_markdown_lists_references_in_both_directions(tmp_path: Path) -> None:
    markdown = reference.render_markdown(reference.load_columns(write_csv(tmp_path)))

    assert "2 tables, 6 columns, 1 foreign keys." in markdown
    assert "## tbl_samples" in markdown and "## tbl_sites" in markdown
    assert "References: `tbl_sites`." in markdown
    assert "Referenced by: `tbl_samples` (`site_id`)." in markdown
    assert "| `site_id` | integer | no | FK | `tbl_sites.site_id` |" in markdown
    assert "| `site_id` | integer | no | PK |  |" in markdown


def test_load_columns_rejects_missing_header_field(tmp_path: Path) -> None:
    path = write_csv(tmp_path, "table_name,column_name\ntbl_sites,site_id\n")

    with pytest.raises(ValueError, match="missing columns in header"):
        reference.load_columns(path)


def test_check_reports_out_of_date_file_without_writing(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    csv_path = write_csv(tmp_path)
    output = tmp_path / "SCHEMA.md"
    output.write_text("old\n", encoding="utf-8")

    assert reference.main(["--csv", str(csv_path), "--output", str(output), "--check"]) == 1
    assert output.read_text(encoding="utf-8") == "old\n"
    assert "out of date" in capsys.readouterr().err

    assert reference.main(["--csv", str(csv_path), "--output", str(output)]) == 0
    assert reference.main(["--csv", str(csv_path), "--output", str(output), "--check"]) == 0
