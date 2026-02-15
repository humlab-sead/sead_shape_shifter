import pytest
from src.configuration.config import Config
from ingesters.sead.metadata import SchemaService, SeadSchema
from ingesters.sead.process import ImportService, Options
from ingesters.sead.submission import Submission


def test_create_options(cfg: Config):
    opts: Options = Options(
        **{
            "submission_name": "42",
            "filename": "data/projects/dummy.xlsx",
            "data_types": "dendrochronology",
            "database": cfg.get("options:database"),
            "output_folder": "data/output",
            "skip": False,
            "submission_id": None,
            "table_names": None,
            "check_only": True,
            "timestamp": True,
        }
    )
    assert opts.basename == "dummy"
    assert opts.timestamp
    assert opts.target is not None
    assert opts.ignore_columns is not None
    assert opts.db_uri().startswith("postgresql+psycopg://")


@pytest.mark.integration
@pytest.mark.skip(reason="Requires live database connection")
class TestImportService:
    def test_import_reduced_submission(self, cfg: Config):

        opts: Options = Options(
            **{
                "filename": "tests/test_data/building_dendro_reduced.xlsx",
                "data_types": "dendrochronology",
                "database": cfg.get("options:database"),
                "output_folder": "data/output",
                "skip": False,
                "submission_id": None,
                "table_names": None,
                "check_only": False,
                "register": False,
                "explode": False,
                "timestamp": False,
            }
        )
        assert opts.filename is not None

        schema_service: SchemaService = SchemaService(opts.db_uri())
        schema: SeadSchema = schema_service.load()
        submission: Submission = Submission.load(schema=schema, source=opts.filename, service=schema_service)

        service: ImportService = ImportService(schema=schema, opts=opts, service=schema_service)
        service.process(process_target=submission)
        assert len(service.specification.errors) == 0
