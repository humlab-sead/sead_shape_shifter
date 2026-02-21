import base64
import os
import pickle
import struct
from typing import Any

import pandas as pd

from ingesters.sead.metadata import SchemaService, SeadSchema
from ingesters.sead.submission import Submission
from ingesters.sead.utility import create_db_uri
from src.configuration import ConfigValue

# @deprecated('table_name_index data sheet has been removed')
# def load_excel_by_regression(filename: str) -> dict[str, pd.DataFrame]:
#     def recode_excel_sheet_name(row):
#         value = row['excel_sheet']
#         if pd.notnull(value) and len(value) > 0 and value != 'nan':
#             return value
#         return row['table_name']

#     tables: pd.DataFrame = pd.read_excel(
#         filename,
#         'Tables',
#         dtype={'table_name': 'str', 'java_class': 'str', 'pk_name': 'str', 'excel_sheet': 'str', 'notes': 'str'},
#     )

#     columns: pd.DataFrame = pd.read_excel(
#         filename,
#         'Columns',
#         dtype={
#             'table_name': 'str',
#             'column_name': 'str',
#             'nullable': 'str',
#             'type': 'str',
#             'type2': 'str',
#             'class': 'str',
#         },
#     )

#     tables['table_name_index'] = tables['table_name']
#     tables = tables.set_index('table_name_index')

#     tables['excel_sheet'] = tables.apply(recode_excel_sheet_name, axis=1)

#     primary_keys: pd.DataFrame = pd.merge(
#         tables,
#         columns,
#         how='inner',
#         left_on=['table_name', 'pk_name'],
#         right_on=['table_name', 'column_name'],
#     )[['table_name', 'column_name', 'java_class']]
#     primary_keys.columns = ['table_name', 'column_name', 'class_name']

#     foreign_keys: pd.DataFrame = pd.merge(
#         columns,
#         primary_keys,
#         how='inner',
#         left_on=['column_name', 'class'],
#         right_on=['column_name', 'class_name'],
#     )[['table_name_x', 'column_name', 'table_name_y', 'class_name']]
#     foreign_keys = foreign_keys[foreign_keys.table_name_x != foreign_keys.table_name_y]

#     foreign_keys_lookup: dict[str, bool] = {
#         x: True for x in list(foreign_keys.table_name_x + '#' + foreign_keys.column_name)
#     }

#     primary_keys_lookup: dict[str, bool] = {x: True for x in tables.table_name + '#' + tables.pk_name}

#     classname_cache: dict[str, dict] = tables.set_index('java_class')['table_name'].to_dict()

#     return {
#         'tables': tables,
#         'columns': columns,
#         'primary_keys': primary_keys,
#         'foreign_keys': foreign_keys,
#         'foreign_keys_lookup': foreign_keys_lookup,
#         'primary_keys_lookup': primary_keys_lookup,
#         'classname_cache': classname_cache,
#     }


def generate_test_excel(
    excel_filename: str,
    test_sites: list[int],
    filename: str,
    force: bool = False,
):
    def filter_table(submission: Submission, table_name: str, column_name: str, values: pd.Series, flip: bool = False) -> pd.DataFrame:
        table: pd.DataFrame = submission[table_name]
        data: pd.DataFrame = table[table["system_id" if flip else column_name].isin(values)]
        print(f"{table_name}: {len(data)}")
        return data

    submission: Submission = load_test_submission(excel_filename, test_sites, filename, force)

    assert submission is not None
    number_of_physical_samples: int = 2

    sites: pd.DataFrame = filter_table(submission, "tbl_sites", "system_id", pd.Series(test_sites))
    site_locations: pd.DataFrame = filter_table(submission, "tbl_site_locations", "site_id", sites.system_id)
    site_references: pd.DataFrame = filter_table(submission, "tbl_site_references", "site_id", sites.system_id)
    sample_groups: pd.DataFrame = filter_table(submission, "tbl_sample_groups", "site_id", sites.system_id)
    sample_group_descriptions: pd.DataFrame = filter_table(
        submission, "tbl_sample_group_descriptions", "sample_group_id", sample_groups.system_id
    )
    sample_group_coordinates: pd.DataFrame = filter_table(
        submission, "tbl_sample_group_coordinates", "sample_group_id", sample_groups.system_id
    )
    sample_group_notes: pd.DataFrame = filter_table(submission, "tbl_sample_group_notes", "sample_group_id", sample_groups.system_id)
    physical_samples: pd.DataFrame = filter_table(submission, "tbl_physical_samples", "sample_group_id", sample_groups.system_id).head(
        number_of_physical_samples
    )
    sample_descriptions: pd.DataFrame = filter_table(
        submission, "tbl_sample_descriptions", "physical_sample_id", physical_samples.system_id
    )
    sample_locations: pd.DataFrame = filter_table(submission, "tbl_sample_locations", "physical_sample_id", physical_samples.system_id)
    sample_notes: pd.DataFrame = filter_table(submission, "tbl_sample_notes", "physical_sample_id", physical_samples.system_id)
    sample_alt_refs: pd.DataFrame = filter_table(submission, "tbl_sample_alt_refs", "physical_sample_id", physical_samples.system_id)
    analysis_entities: pd.DataFrame = filter_table(submission, "tbl_analysis_entities", "physical_sample_id", physical_samples.system_id)
    dendro: pd.DataFrame = filter_table(submission, "tbl_dendro", "analysis_entity_id", analysis_entities.system_id)
    dendro_dates: pd.DataFrame = filter_table(submission, "tbl_dendro_dates", "analysis_entity_id", analysis_entities.system_id)
    dendro_date_notes: pd.DataFrame = filter_table(submission, "tbl_dendro_date_notes", "dendro_date_note_id", dendro_dates.system_id)
    datasets: pd.DataFrame = filter_table(
        submission, "tbl_datasets", "dataset_id", pd.Series(list(set(analysis_entities.dataset_id))), flip=True
    )
    dataset_contacts: pd.DataFrame = filter_table(submission, "tbl_dataset_contacts", "dataset_id", datasets.system_id)
    dataset_submissions: pd.DataFrame = filter_table(submission, "tbl_dataset_submissions", "dataset_id", datasets.system_id)
    projects: pd.DataFrame = filter_table(submission, "tbl_projects", "project_id", pd.Series(list(set(datasets.project_id))), flip=True)
    abundances: pd.DataFrame = filter_table(submission, "tbl_abundances", "analysis_entity_id", analysis_entities.system_id)

    # add_dummy_row(sample_notes, [1, physical_samples.iloc[0]['system_id'], 1, 'Dummy note', np.nan, np.nan])
    # add_dummy_row(dendro_date_notes, [1, 'A dummy note', dendro_dates.iloc[0]['system_id'], np.nan])

    reduced_submission: dict[str, pd.DataFrame] = {
        "tbl_sites": sites,
        "tbl_site_locations": site_locations,
        "tbl_site_references": site_references,
        "tbl_sample_groups": sample_groups,
        "tbl_sample_group_descriptions": sample_group_descriptions,
        "tbl_sample_group_coordinates": sample_group_coordinates,
        "tbl_sample_group_notes": sample_group_notes,
        "tbl_physical_samples": physical_samples,
        "tbl_sample_descriptions": sample_descriptions,
        "tbl_sample_locations": sample_locations,
        "tbl_sample_notes": sample_notes,
        "tbl_sample_alt_refs": sample_alt_refs,
        "tbl_analysis_entities": analysis_entities,
        "tbl_dendro": dendro,
        "tbl_dendro_dates": dendro_dates,
        "tbl_dendro_date_notes": dendro_date_notes,
        "tbl_datasets": datasets,
        "tbl_dataset_contacts": dataset_contacts,
        "tbl_dataset_submissions": dataset_submissions,
        "tbl_projects": projects,
        "tbl_abundances": abundances,
    }

    with pd.ExcelWriter(filename, engine="xlsxwriter") as writer:  # pylint: disable=abstract-class-instantiated
        for table_name, table in reduced_submission.items():
            table.to_excel(writer, sheet_name=table_name, index=False)


def encode_sites(sites: list[int]) -> str:
    return base64.urlsafe_b64encode(struct.pack(f"{len(sites)}I", *sites)).decode().rstrip("=")


def load_test_submission(excel_filename: str, test_sites: list[int], filename: str, force: bool) -> Submission:
    """Load test data from Excel file, stores and loads pickled data if exists for better performance."""
    basename: str = os.path.splitext(os.path.basename(filename))[0]
    pickled_filename: str = f"{basename}_{encode_sites(test_sites)}.pkl"
    if not os.path.isfile(pickled_filename) or force:
        opts: dict[str, Any] = ConfigValue("options:database").resolve() or {}
        service: SchemaService = SchemaService(create_db_uri(**opts))
        schema: SeadSchema = service.load()
        submission: Submission = Submission.load(schema=schema, source=excel_filename, service=service)
        with open(pickled_filename, "wb") as fp:
            pickle.dump(submission, fp)
    else:
        with open(pickled_filename, "rb") as fp:
            submission = pickle.load(fp)
    return submission
