import time
from dataclasses import dataclass, field
from os.path import basename, join, splitext

from loguru import logger

from src.configuration.resolve import ConfigValue

from . import utility
from .dispatchers import Dispatchers, IDispatcher
from .metadata import SchemaService, SeadSchema
from .repository import SubmissionRepository
from .specification import SpecificationError, SubmissionSpecification
from .submission import Submission

# pylint: disable=too-many-instance-attributes


@dataclass
class Options:
    """
    Options for the importer
    """

    filename: str | None
    skip: bool
    submission_id: int | None
    submission_name: str
    data_types: str
    table_names: list[str] = field(default_factory=list)
    check_only: bool = False
    register: bool = False
    explode: bool = False
    timestamp: bool = True
    ignore_columns: list[str] | None = None  # type: ignore[assignment]
    basename: str | None = field(init=False, default=None)  # type: ignore[assignment]
    target: str | None = field(init=False, default=None)  # type: ignore[assignment]

    output_folder: str = field(default="data/output")
    database: dict[str, str] = field(default_factory=dict)
    transfer_format: str | None = field(default="csv")
    dump_to_csv: bool = field(default=False)

    def __post_init__(self) -> None:

        if self.filename:
            self.basename: str = splitext(basename(self.filename))[0]
            self.target: str = (
                join(self.output_folder, f"{self.basename}_{time.strftime('%Y%m%d-%H%M%S')}")
                if self.timestamp
                else join(self.output_folder, f"{self.basename}")
            )
        default_ignore_patterns: list[str] = ConfigValue("options:ignore_columns").resolve() or []
        self.ignore_columns: list[str] = (
            self.ignore_columns if self.ignore_columns is not None else default_ignore_patterns
        )

    def db_uri(self) -> str:
        return utility.create_db_uri(**self.database)

    @property
    def use_existing_submission(self) -> bool:
        return self.submission_id is not None and self.submission_id > 0

    @property
    def source_name(self) -> str:
        """Name of the source file"""
        return basename(self.filename) if self.filename else self.submission_name


class ImportService:
    def __init__(
        self,
        *,
        opts: Options,
        schema: SeadSchema,
        service: SchemaService,
        repository: SubmissionRepository | None = None,
    ) -> None:
        self.opts: Options = opts
        self.repository: SubmissionRepository = repository or SubmissionRepository(
            opts.database, uploader=opts.transfer_format or "unknown"
        )
        self.schema: SeadSchema = schema
        self.service: SchemaService = service

        # Select dispatcher based on transfer_format
        self.dispatcher_cls: type[IDispatcher] = Dispatchers.get(key=opts.transfer_format or "csv")

        self.specification: SubmissionSpecification = SubmissionSpecification(
            schema=self.schema, ignore_columns=self.opts.ignore_columns, raise_errors=False
        )

    @utility.log_decorator(
        enter_message=" ---> generating target file(s)...", exit_message=" ---> target file(s) created", level="DEBUG"
    )
    def dispatch(self, submission: Submission) -> str:
        """Reads Excel files and convert content to an dispatch format."""

        self.dispatcher_cls().dispatch(
            target=self.opts.target, schema=self.schema, submission=submission, table_names=self.opts.table_names
        )

        logger.debug(f" ---> target file created: {self.opts.target}")

        return self.opts.target

    @utility.log_decorator(enter_message="Processing started...", exit_message="Processing done", level="DEBUG")
    def process(self, process_target: int | str | Submission) -> None:
        """Process a submission. The submission can be either
        - an Excel file,
        - a SubmissionData object (parsed Excel file, see importer/submission.py)
        - a submission id (int) already stored in the database
        """
        opts: Options = self.opts
        try:
            if opts.skip is True:
                logger.debug("Skipping: %s", opts.basename)
                return

            if isinstance(process_target, int):
                # When existing submission id is given, just explode (requires --explode option)
                self.explode_submission(opts)
                return

            submission: Submission = (
                Submission.load(schema=self.schema, source=process_target, service=self.service, apply_policies=True)
                if isinstance(process_target, str)
                else process_target
            )

            if not self.specification.is_satisfied_by(submission):
                logger.error(f" ---> {opts.basename} does not satisfy the specification")
                raise SpecificationError(str(self.specification.messages))

            if opts.dump_to_csv:
                submission.to_csv(self.opts.output_folder)

            if self.opts.check_only:
                logger.debug(f" ---> {opts.basename} satisfies the specification")
                return

            if opts.register:
                opts.submission_id = self.repository.register(
                    name=opts.submission_name,
                    source_name=opts.source_name,
                    data_types=opts.data_types,
                )

            assert isinstance(opts.submission_id, int), "Submission id falsy is unexpected after registration"

            self.dispatch(submission)

            if opts.explode:
                if not opts.register:
                    logger.error(" ---> cannot explode without registration")
                    raise ValueError("Cannot explode without registration")
                self.explode_submission(opts)

        except SpecificationError:
            logger.error(f"Specification(s) not satisfied {opts.basename}")

        except Exception:  # pylint: disable=broad-except
            logger.exception(f"aborted critical error {opts.basename}")

    def explode_submission(self, opts):

        if not opts.submission_id:
            raise ValueError("Submission id is required for exploding submission")

        if not opts.explode:
            raise ValueError("Submission id must be set with --explode option")

        self.repository.remove(opts.submission_id, clear_header=False, clear_exploded=False)

        # Extract to staging tables "clearing_house.tbl_clearinghouse_submission_[xml,csv]_content_[tables|columns|records|recordvalues]"
        self.repository.extract_to_staging_tables(opts.submission_id)
        self.repository.explode_to_public_tables(opts.submission_id, p_dry_run=False, p_add_missing_columns=False)
        self.repository.set_pending(opts.submission_id)
