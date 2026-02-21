import json
from os.path import isfile

import pandas as pd
import pytest

from ingesters.sead.metadata import SchemaService, SeadSchema
from ingesters.sead.utility import create_db_uri
from src.configuration.config import Config

# @pytest.mark.skip(reason="sandbox test")
# def test_download_sead_comments():
#     """Stores SEAD comments in a markdown file"""

#     uri: str = create_db_uri(**cfg.get("options:database"))
#     sql = "select * from sead_utility.sead_comments2"
#     df = pd.read_sql(sql, uri)
#     # df.to_excel('sead_comments_20240201.xlsx', index=False)
#     table_template: str = """
# # {{table['table_name']}}
# {{table['comment'] or ''}}
# {% for column in columns -%}
# ## {{table['table_name']}}.{{column['column_name']}} {{'PK' if column['is_pk'] == 'YES' else ''}}
#  {{'FK' if column['is_fk'] == 'YES' else ''}}
# {{column['comment'] or ''}}
# {%- endfor %}"""

#     jinja_env: Environment = Environment()
#     template: Template = jinja_env.from_string(table_template)

#     with open('sead_comments_20240201.md', 'w') as f:
#         for table_name in df.table_name.unique():
#             records: list[dict] = df[df.table_name == table_name].to_dict('records')
#             table: dict = next(x for x in records if x['column_name'] is None)
#             columns: list[dict] = [x for x in records if x['column_name'] is not None]
#             md_str: str = template.render(table=table, columns=columns)
#             f.write(md_str)


@pytest.mark.skipif(isfile("ingesters/sead/tests/test_data/sead_columns.json"), reason="Used for generating test data only")
def test_load_metadata_from_postgres(cfg: Config):
    """Use this test to store SEAD metadata in json files for regression testing"""
    service: SchemaService = SchemaService(create_db_uri(**cfg.get("options:database")))
    schema: SeadSchema = service.load()
    test_tables: list[str] = cfg.get("test:tables")
    with open("ingesters/sead/tests/test_data/sead_tables.json", "w", encoding="utf-8") as outfile:
        data: list[dict] = schema.source_tables[schema.source_tables.table_name.isin(test_tables)].to_dict("records")
        json.dump(data, outfile, indent=4)

    with open("ingesters/sead/tests/test_data/sead_columns.json", "w", encoding="utf-8") as outfile:
        data: list[dict] = schema.source_columns.fillna(0)[schema.source_columns.table_name.isin(test_tables)].to_dict("records")
        json.dump(data, outfile, indent=4)

    assert isinstance(schema, SeadSchema)
    assert isinstance(schema.source_tables, pd.DataFrame)
    assert isinstance(schema.source_columns, pd.DataFrame)
    assert isinstance(schema.source_tables, pd.DataFrame)
    assert isinstance(schema._tables, dict)
