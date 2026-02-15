import os
from tempfile import TemporaryDirectory

import pandas as pd
import pytest
from src.configuration.config import Config
from ingesters.sead.metadata import SchemaService, SeadSchema
from ingesters.sead.process import ImportService, Options
from ingesters.sead.specification import SubmissionSpecification
from ingesters.sead.submission import Submission
from ingesters.sead.utility import create_db_uri


@pytest.mark.integration
@pytest.mark.skip(reason="Requires ancient DNA data and live database connection")
class TestAdnaSubmission:

    @pytest.fixture(scope="module")
    def adna(self, cfg: Config) -> Submission:
        uri: str = create_db_uri(**cfg.get("options:database"))
        source: str = cfg.get("test:adna:source:filename")
        service: SchemaService = SchemaService(uri)
        schema: SeadSchema = service.load()
        submission: Submission = Submission.load(schema=schema, source=source, service=service)
        return submission

    def test_to_lookups_sql(self, adna: Submission):

        filename: str = "tests/output/lookups.sql"

        os.makedirs(os.path.dirname(filename), exist_ok=True)
        if os.path.isfile(filename):
            os.unlink(filename)

        adna.to_lookups_sql(filename)

        assert os.path.isfile(filename)

    def test_loaded_adna_source(self, adna: Submission, cfg: Config):
        source: str = cfg.get("test:adna:source:filename")

        assert adna.data_tables is not None

        assert all(len(df) > 0 for df in adna.data_tables.values())

        # Verify that no table in the submission is keyed by excel sheet name for aliased tables
        assert all(n.excel_sheet not in adna.data_tables for n in adna.schema.aliased_tables)

        with pd.ExcelFile(source) as reader:
            # Verify that all excel sheet names are in the submission data tables
            excel_sheet_names: set[int | str] = set(reader.sheet_names)
            excel_table_names: set[str] = {n for n, t in adna.schema.items() if t.excel_sheet in excel_sheet_names}

            assert all(table_name in adna.data_tables for table_name in excel_table_names)

    def test_adna_tables_specifications(self, adna: Submission, cfg: Config):
        specification: SubmissionSpecification = SubmissionSpecification(
            schema=adna.schema, ignore_columns=cfg.get("options:ignore_columns"), raise_errors=False
        )
        specification.is_satisfied_by(adna)
        assert specification.messages.errors == []

    def test_dispatch_a_dna_submission_to_csv_files(self, adna: Submission, cfg: Config, schema_service: SchemaService):

        # create a unique tmp folder using mktemp for output of CSV files
        with TemporaryDirectory() as output_folder:
            opts: Options = Options(
                **{
                    "filename": cfg.get("test:adna:source:filename"),
                    "data_types": "adna",
                    "database": cfg.get("options:database"),
                    "output_folder": output_folder,
                    "skip": False,
                    "submission_id": None,
                    "table_names": None,
                    "check_only": False,
                    "register": True,
                    "explode": False,
                    "timestamp": False,
                    "transfer_format": "csv",
                }
            )

            if os.path.isfile(opts.target):
                os.remove(opts.target)

            service: ImportService = ImportService(schema=adna.schema, opts=opts, service=schema_service)

            service.process(process_target=adna)
            assert not service.specification.messages.errors

            for table_name in ["tables", "columns", "records", "recordvalues"]:
                filename: str = os.path.join(output_folder, f"{table_name}.csv")
                assert os.path.isfile(filename)

    def test_dispatch_a_dna_submission_to_database(self, adna: Submission, cfg: Config, schema_service: SchemaService):
        """Test dispatching an ancient DNA submission to the database via CSV uploader."""

        # create a unique tmp folder using mktemp for output of CSV files
        with TemporaryDirectory() as output_folder:
            opts: Options = Options(
                **{
                    "filename": cfg.get("test:adna:source:filename"),
                    "data_types": "adna",
                    "database": cfg.get("options:database"),
                    "output_folder": output_folder,
                    "skip": False,
                    "submission_id": None,
                    "table_names": None,
                    "check_only": False,
                    "register": True,
                    "explode": False,
                    "timestamp": False,
                    "transfer_format": "csv",
                }
            )

            if os.path.isfile(opts.target):
                os.remove(opts.target)

            service: ImportService = ImportService(schema=adna.schema, opts=opts, service=schema_service)

            service.process(process_target=adna)
            assert not service.specification.messages.errors
