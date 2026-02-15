import os
from tempfile import TemporaryDirectory
from typing import Any

import pandas as pd
import pytest

from ingesters.sead import policies
from ingesters.sead.metadata import SchemaService, SeadSchema
from ingesters.sead.process import ImportService, Options
from ingesters.sead.specification import (
    ForeignKeyColumnsHasValuesSpecification,
    SpecificationMessages,
    SubmissionSpecification,
)
from ingesters.sead.submission import Submission
from ingesters.sead.utility import create_db_uri
from src.configuration.config import Config


@pytest.mark.integration
@pytest.mark.skip(reason="Requires living tree data and live database connection")
class TestLivingTreeSubmission:

    @pytest.fixture(scope="module")
    def schema_service(self, cfg: Config) -> SchemaService:
        db_opts: dict[str, Any] = cfg.get("options:database") | cfg.get("test:dendrochronology:database")
        uri: str = create_db_uri(**db_opts)
        return SchemaService(uri)

    @pytest.fixture(scope="module")
    def schema(self, schema_service: SchemaService) -> SeadSchema:
        return schema_service.load()

    @pytest.fixture(scope="module")
    def submission(self, cfg: Config, schema: SeadSchema, service: SchemaService) -> Submission:
        source: str = cfg.get("test:dendrochronology:living_tree:source:filename")
        return Submission.load(schema=schema, source=source, apply_policies=True, service=service)

    def test_pk_set(self, schema_service: SchemaService):
        keys: set[int] = schema_service.get_primary_key_values("tbl_sites", "site_id")
        assert keys

    def test_load_living_tree(self, submission: Submission):
        assert submission is not None
        assert submission.schema is not None
        assert submission.data_tables is not None
        assert len(submission.data_tables) > 0

    def test_living_tree_tables_specifications(self, submission: Submission, cfg: Config):
        specification: SubmissionSpecification = SubmissionSpecification(
            schema=submission.schema, ignore_columns=cfg.get("options:ignore_columns"), raise_errors=False
        )
        specification.is_satisfied_by(submission)
        assert specification.messages.errors == []

    def test_living_tree_tables_specifications_bugg(self, submission: Submission, cfg: Config):
        specification: ForeignKeyColumnsHasValuesSpecification = ForeignKeyColumnsHasValuesSpecification(
            schema=submission.schema,
            messages=SpecificationMessages(),
            ignore_columns=cfg.get("options:ignore_columns"),
        )
        specification.is_satisfied_by(submission, "tbl_dataset_submissions")
        assert specification.messages.errors == []
        assert specification.messages.warnings == []

    def test_to_lookups_sql(self, submission: Submission):

        filename: str = "tests/output/lookups.sql"

        os.makedirs(os.path.dirname(filename), exist_ok=True)
        if os.path.isfile(filename):
            os.unlink(filename)

        submission.to_lookups_sql(filename)

        assert os.path.isfile(filename)

    def test_loaded_living_tree_source(self, submission: Submission, cfg: Config):
        source: str = cfg.get("test:dendrochronology:submission:source:filename")

        assert submission.data_tables is not None

        empty_tables: list[str] = [n for n, df in submission.data_tables.items() if len(df) == 0]

        assert len(empty_tables) == 0, f"Empty tables found: {empty_tables}"

        # Verify that no table in the submission is keyed by excel sheet name for aliased tables
        assert all(n.excel_sheet not in submission.data_tables for n in submission.schema.aliased_tables)

        with pd.ExcelFile(source) as reader:
            # Verify that all excel sheet names are in the submission data tables
            excel_sheet_names: set[int | str] = set(reader.sheet_names)
            excel_table_names: set[str] = {n for n, t in submission.schema.items() if t.excel_sheet in excel_sheet_names}

            assert all(table_name in submission.data_tables for table_name in excel_table_names)

    def test_import_living_tree_submission(self, submission: Submission, cfg: Config, schema_service: SchemaService):

        with TemporaryDirectory() as output_folder:

            opts: Options = Options(
                **{
                    "filename": cfg.get("test:dendrochronology:submission:source:filename"),
                    "data_types": "submission",
                    "database": cfg.get("options:database"),
                    "output_folder": output_folder,
                    "skip": False,
                    "submission_id": None,
                    "table_names": None,
                    "check_only": False,
                    "register": False,
                    "explode": False,
                    "timestamp": False,
                    "transfer_format": "csv",
                }
            )

            service: ImportService = ImportService(schema=submission.schema, opts=opts, service=schema_service)

            service.process(process_target=submission)
            assert not service.specification.messages.errors

            for table_name in ["tables", "columns", "records", "recordvalues"]:
                filename: str = os.path.join(output_folder, f"{table_name}.csv")
                assert os.path.isfile(filename)

    # Policy tests in living tree data

    @pytest.fixture(scope="module")
    def unprocessed_submission(self, cfg: Config, schema: SeadSchema, service: SchemaService) -> Submission:
        return Submission.load(
            schema=schema,
            source=cfg.get("test:dendrochronology:living_tree:source:filename"),
            apply_policies=False,
            service=service,
        )

    def test_add_primary_key_column_if_missing_policy(self, unprocessed_submission: Submission):
        policy: policies.AddPrimaryKeyColumnIfMissingPolicy = policies.AddPrimaryKeyColumnIfMissingPolicy(
            schema=unprocessed_submission.schema, submission=unprocessed_submission
        )
        policy.apply()
        assert not policy.logs

    def test_add_default_foreign_key_policy(self, unprocessed_submission: Submission):
        policy: policies.UpdateMissingForeignKeyPolicy = policies.UpdateMissingForeignKeyPolicy(
            schema=unprocessed_submission.schema, submission=unprocessed_submission
        )
        policy.apply()
        assert not policy.logs

    def test_if_table_is_missing_add_table_using_system_id_as_public_id(self, unprocessed_submission: Submission):
        policy: policies.AddIdentityMappingSystemIdToPublicIdPolicy = policies.AddIdentityMappingSystemIdToPublicIdPolicy(
            schema=unprocessed_submission.schema, submission=unprocessed_submission
        )
        policy.apply()
        assert len(policy.logs) > 0

    def test_statistics(self, unprocessed_submission: Submission):

        statistics = []

        for table_name in unprocessed_submission.data_table_names:
            # data: pd.DataFrame = unprocessed_submission.data_tables[table_name]
            table: policies.Table = unprocessed_submission.schema[table_name]

            for column in table.columns.values():

                if column.is_fk:
                    fk_table_name: str | None = column.fk_table_name
                    fk_column_name: str | None = column.fk_column_name
                    fk_table_exists: bool = fk_table_name in unprocessed_submission.data_tables

                    statistics.append((fk_table_name, fk_column_name, fk_table_exists, table_name, column.column_name))

        df = pd.DataFrame(statistics, columns=["fk_table_name", "fk_column_name", "fk_table_exists", "table_name", "column_name"])
        df.to_csv("living_tree_statistics.csv", index=False)

        assert True

        # schema = MagicMock(spec=SeadSchema)
        # submission = MagicMock(spec=Submission)
        # table = MagicMock(spec=Table)
        # table.columns = {
        #     "col1": MagicMock(data_type="smallint"),
        #     "col2": MagicMock(data_type="integer"),
        #     "col3": MagicMock(data_type="bigint"),
        # }

    #     schema.__getitem__.return_value = table
    #     submission.data_tables = {
    #         "table1": pd.DataFrame(
    #             {
    #                 "col1": [1, 2, 3],
    #                 "col2": [4, 5, 6],
    #                 "col3": [7, 8, 9],
    #             }
    #         )
    #     }

    #     policy = UpdateTypesBasedOnSeadSchema(schema=schema, submission=submission)
    #     policy.apply()

    #     assert submission.data_tables["table1"]["col1"].dtype == "Int16"
    #     assert submission.data_tables["table1"]["col2"].dtype == "Int32"
    #     assert submission.data_tables["table1"]["col3"].dtype == "Int64"

    # def test_if_system_id_is_missing_set_system_id_to_public_id(self, ):
    #     schema = MagicMock(spec=SeadSchema)
    #     submission = MagicMock(spec=Submission)
    #     table = MagicMock(spec=Table)
    #     table.pk_name = "id"
    #     schema.__getitem__.return_value = table
    #     submission.data_tables = {
    #         "table1": pd.DataFrame(
    #             {
    #                 "id": [1, 2, 3],
    #                 "system_id": [np.nan, np.nan, np.nan],
    #             }
    #         )
    #     }

    #     policy = IfSystemIdIsMissingSetSystemIdToPublicId(schema=schema, submission=submission)
    #     policy.apply()

    #     assert list(submission.data_tables["table1"]["system_id"]) == [1, 2, 3]

    # def test_if_foreign_key_value_is_missing_add_identity_mapping_to_foreign_key_table(self, ):
    #     schema = MagicMock(spec=SeadSchema)
    #     submission = MagicMock(spec=Submission)
    #     sead_schema = MagicMock(spec=SeadSchema)
    #     table = MagicMock(spec=Table)
    #     table.pk_name = "public_id"
    #     table.table_name = "tbl_table"
    #     sead_schema.lookup_tables = [table]
    #     schema.sead_schema = sead_schema
    #     sead_schema.__getitem__.side_effect = lambda x: table
    #     submission.get_referenced_keyset.return_value = [1, 2, 3]
    #     submission.data_tables = {table.table_name: pd.DataFrame({"system_id": [1], table.pk_name: [1]})}
    #     submission.__contains__.side_effect = lambda x: x in submission.data_tables

    #     policy = IfForeignKeyValueIsMissingAddIdentityMappingToForeignKeyTable(schema=schema, submission=submission)
    #     policy.apply()

    #     assert list(submission.data_tables[table.table_name]["system_id"]) == [1, 2, 3]
    #     assert list(submission.data_tables[table.table_name][table.pk_name]) == [1, 2, 3]

    # def test_if_lookup_with_no_new_data_then_keep_only_system_id_public_id__not_lookup(self, ):
    #     schema = MagicMock(spec=SeadSchema)
    #     submission = MagicMock(spec=Submission)
    #     table = MagicMock(spec=Table)
    #     table.is_lookup = False
    #     schema.__getitem__.return_value = table
    #     submission.data_tables = {"table1": pd.DataFrame(columns=["system_id", "public_id", "col1", "col2"])}
    #     policy: PolicyBase = IfLookupWithNoNewDataThenKeepOnlySystemIdPublicId(schema=schema, submission=submission)
    #     policy.update()

    #     assert "col1" in submission.data_tables["table1"].columns
    #     assert "col2" in submission.data_tables["table1"].columns

    # def test_if_lookup_with_no_new_data_then_keep_only_system_id_public_id__pk_not_in_data_table(self, ):
    #     schema = MagicMock(spec=SeadSchema)
    #     submission = MagicMock(spec=Submission)
    #     table = MagicMock(spec=Table)
    #     table.is_lookup = True
    #     table.pk_name = "public_id"
    #     schema.__getitem__.return_value = table
    #     submission.data_tables = {"table1": pd.DataFrame(columns=["system_id", "col1", "col2"])}

    #     policy: PolicyBase = IfLookupWithNoNewDataThenKeepOnlySystemIdPublicId(schema=schema, submission=submission)
    #     policy.update()

    #     assert "col1" in submission.data_tables["table1"].columns
    #     assert "col2" in submission.data_tables["table1"].columns

    # def test_if_lookup_with_no_new_data_then_keep_only_system_id_public_id__all_pk_values_null(self, ):
    #     schema = MagicMock(spec=SeadSchema)
    #     submission = MagicMock(spec=Submission)
    #     table = MagicMock(spec=Table)
    #     table.is_lookup = True
    #     table.pk_name = "public_id"
    #     schema.__getitem__.return_value = table
    #     submission.data_tables = {
    #         "table1": pd.DataFrame(
    #             {"system_id": [1, 2, 3], "public_id": [None, None, None], "col1": [4, 5, 6], "col2": [7, 8, 9]}
    #         )
    #     }

    #     policy: PolicyBase = IfLookupWithNoNewDataThenKeepOnlySystemIdPublicId(schema=schema, submission=submission)
    #     policy.update()

    #     assert "col1" in submission.data_tables["table1"].columns
    #     assert "col2" in submission.data_tables["table1"].columns

    # def test_not_all_pk_values_null(self, ):
    #     schema = MagicMock(spec=SeadSchema)
    #     submission = MagicMock(spec=Submission)
    #     table = MagicMock(spec=Table)
    #     table.is_lookup = True
    #     table.pk_name = "public_id"
    #     schema.__getitem__.return_value = table
    #     submission.data_tables = {
    #         "table1": pd.DataFrame(
    #             {"system_id": [1, 2, 3], "public_id": [None, 2, None], "col1": [4, 5, 6], "col2": [7, 8, 9]}
    #         )
    #     }

    #     policy: PolicyBase = IfLookupWithNoNewDataThenKeepOnlySystemIdPublicId(schema=schema, submission=submission)
    #     policy.update()

    #     assert "col1" in submission.data_tables["table1"].columns
    #     assert "col2" in submission.data_tables["table1"].columns
