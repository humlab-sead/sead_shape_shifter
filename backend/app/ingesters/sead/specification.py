import abc
from dataclasses import dataclass, field
from fnmatch import fnmatch
from functools import cached_property

import numpy as np
import pandas as pd
from loguru import logger

from src.configuration.resolve import ConfigValue

from .metadata import Column, SeadSchema, Table
from .submission import Submission
from .utility import Registry, log_decorator


class SpecificationRegistry(Registry[type["SpecificationBase"]]):
    items: dict[str, type["SpecificationBase"]] = {}


# pylint: disable=unused-argument, arguments-differ


@dataclass
class SpecificationMessages:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    infos: list[str] = field(default_factory=list)

    def uniqify(self) -> None:
        self.errors = sorted(set(self.errors))
        self.warnings = sorted(set(self.warnings))
        self.infos = sorted(set(self.infos))

    def __str__(self) -> str:
        msgs: str = ""
        if len(self.errors) > 0:
            msgs += f"Errors: \n{'\n'.join(self.errors)}\n"
        if len(self.warnings) > 0:
            msgs += f"Warnings: \n{'\n'.join(self.warnings)}\n"
        if len(self.infos) > 0:
            msgs += f"Infos: \n{'\n'.join(self.infos)}\n"
        return msgs

    def merge(self, other: "SpecificationMessages") -> None:
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        self.infos.extend(other.infos)


class SpecificationError(Exception):
    def __init__(self, messages: SpecificationMessages | str) -> None:
        super().__init__("Submission specification failed")
        self.messages: SpecificationMessages = (
            messages if isinstance(messages, SpecificationMessages) else SpecificationMessages(errors=[messages])
        )


class SpecificationBase(abc.ABC):
    def __init__(self, schema: SeadSchema, ignore_columns: list[str] | None = None) -> None:
        self.schema: SeadSchema = schema
        self.messages: SpecificationMessages = SpecificationMessages()
        self.ignore_columns: list[str] = ignore_columns or ConfigValue("options:ignore_columns").resolve() or []

    def is_ignored(self, column_name: str) -> bool:
        return any(fnmatch(column_name, x) for x in self.ignore_columns)

    @property
    def errors(self) -> list[str]:
        return self.messages.errors

    @property
    def warnings(self) -> list[str]:
        return self.messages.warnings

    @property
    def infos(self) -> list[str]:
        return self.messages.infos

    def clear(self) -> None:
        self.messages.errors = []
        self.messages.warnings = []
        self.messages.infos = []

    def warn(self, message: str) -> None:
        self.warnings.append(f"{message}")

    def error(self, message: str) -> None:
        self.errors.append(f"{message}")

    def info(self, message: str) -> None:
        self.infos.append(f"{message}")

    def get_columns(self, table_name: str) -> list[Column]:
        return [
            column for column in self.schema[table_name].columns.values() if not self.is_ignored(column.column_name)
        ]

    @abc.abstractmethod
    def is_satisfied_by(self, submission: Submission, **kwargs) -> bool: ...

    def has_errors(self) -> bool:
        return len(self.errors) > 0

    def has_warnings(self) -> bool:
        return len(self.warnings) > 0

    def merge(self, other: "SpecificationBase") -> None:
        self.messages.merge(other.messages)


class SubmissionSpecification(SpecificationBase):
    """Specification class that tests validity of submission"""

    def __init__(
        self,
        schema: SeadSchema,
        *,
        ignore_columns: list[str] | None = None,
        raise_errors: bool = True,
    ) -> None:
        super().__init__(schema, ignore_columns)
        self.raise_errors: bool = raise_errors

    @log_decorator(enter_message=" ---> checking submission...", exit_message=" ---> submission checked", level="DEBUG")
    def is_satisfied_by(self, submission: Submission, **kwargs) -> bool:  # pylint: disable=unused-argument
        """
        Check if the given submission satisfies all the specifications defined in the SpecificationRegistry.

        Parameters:
            submission (SubmissionData): The submission data to be checked.
            _ (str, optional): Ignored argument. Defaults to None.

        Returns:
            bool: True if all the specifications are satisfied, False otherwise.
        """
        self.clear()
        ignore_columns = self.ignore_columns or ConfigValue("options:ignore_columns").resolve() or []
        for cls in SpecificationRegistry.items.values():
            specification: SpecificationBase = cls(self.schema, ignore_columns=self.ignore_columns)
            for table_name in submission.data_tables.keys():
                specification.is_satisfied_by(submission, table_name=table_name, ignore_columns=ignore_columns)
            self.merge(specification)

        self.messages.uniqify()

        self.log_messages()

        if self.raise_errors and self.has_errors:
            raise SpecificationError(self.messages)

        return not self.has_errors()

    def log_messages(self) -> None:
        for message in self.errors:
            logger.error(message)
        for message in self.warnings:
            logger.warning(message)
        for message in self.infos:
            logger.info(message)


@SpecificationRegistry.register(key="table_exists")
class SubmissionTableExistsSpecification(SpecificationBase):
    """Specification class that tests if table exists in submission"""

    def is_satisfied_by(self, submission: Submission, *, table_name: str, **kwargs) -> bool:
        if table_name not in submission:
            self.error(f"Table '{table_name}' not defined as submission table")
        return not self.has_errors()


@SpecificationRegistry.register(key="column_types")
class ColumnTypesSpecification(SpecificationBase):
    TYPE_COMPATIBILITY_MATRIX: set[tuple[str, str]] = {
        ("bigint", "int64"),
        ("character varying", "object"),
        ("date", "datetime64[ns]"),
        ("date", "object"),
        ("integer", "float64"),
        ("integer", "int64"),
        ("integer", "int32"),
        ("numeric", "float64"),
        ("numeric", "int64"),
        ("smallint", "float64"),
        ("smallint", "int64"),
        ("text", "object"),
        ("timestamp with time zone", "datetime64[ns]"),
        ("timestamp with time zone", "object"),
        ("timestamp without time zone", "object"),
        #  ('character varying', 'datetime64[ns]')
    }

    def is_satisfied_by(self, submission: Submission, *, table_name: str, **kwargs) -> bool:
        data_table: pd.DataFrame = submission.data_tables[table_name]
        if len(data_table) == 0:
            """Cannot determine type if table is empty"""
            return not self.has_errors()

        for column in self.get_columns(table_name):
            if column.column_name not in data_table.columns:
                continue
            data_column_type: str = data_table.dtypes[column.column_name].name
            if all(data_table[column.column_name].isna()):
                continue
            if (column.data_type.lower(), data_column_type.lower()) not in self.TYPE_COMPATIBILITY_MATRIX:
                self.warn(
                    f"type clash: {table_name}.{
                    column.column_name} {column.data_type}<=>{data_column_type}"
                )
        return not self.has_errors()


@SpecificationRegistry.register(key="table_types")
class SubmissionTableTypesSpecification(SpecificationBase):
    NUMERIC_TYPES: list[str] = ["numeric", "integer", "smallint"]

    def is_satisfied_by(self, submission: Submission, *, table_name: str, **kwargs) -> bool:
        data_table: pd.DataFrame = submission.data_tables[table_name]
        for column in self.get_columns(table_name):
            if column.column_name not in data_table.columns:
                continue

            if column.data_type not in self.NUMERIC_TYPES:
                continue

            series: pd.Series = data_table[column.column_name]
            is_real = pd.Series(np.isreal(series.to_numpy()), index=series.index)
            ok_mask = series.notna() & is_real

            if not ok_mask.all():
                error_values = " ".join(list(set(series[~ok_mask])))[:200]
                self.error(
                    f"Column '{table_name}.{
                    column.column_name}' has non-numeric values: '{error_values}'"
                )
        return not self.has_errors()


@SpecificationRegistry.register(key="has_primary_key")
class HasPrimaryKeySpecification(SpecificationBase):
    def is_satisfied_by(self, submission: Submission, *, table_name: str, **kwargs) -> bool:
        data_table: pd.DataFrame = submission.data_tables[table_name]
        if self.schema[table_name].pk_name not in data_table.columns:
            self.error(
                f"Primary key column '{table_name}.{
                    self.schema[table_name].pk_name}' (table metadata) not in data columns."
            )

        if not any(c.is_pk for c in self.schema[table_name].columns.values()):
            self.error(f"Table '{table_name}' has no column with PK constraint")

        return not self.has_errors()


@SpecificationRegistry.register(key="has_system_id")
class HasSystemIdSpecification(SpecificationBase):
    def is_satisfied_by(self, submission: Submission, *, table_name: str, **kwargs) -> bool:
        # Must have a system identity
        # if not submission.has_system_id(table_name):
        data_table: pd.DataFrame = submission.data_tables[table_name]

        if "system_id" not in data_table.columns:
            self.error(f"Table {table_name} has no system id data column")
            return not self.has_errors()

        if data_table["system_id"].isna().any():
            self.error(f"Table {table_name} has missing system id values")

        try:
            # duplicate_mask = data_table[~data_table.system_id.isna()].duplicated('system_id')
            duplicate_mask: pd.Series = data_table.duplicated("system_id")
            duplicates: list[int] = [int(x) for x in set(data_table[duplicate_mask].system_id)]
            if len(duplicates) > 0:
                error_values: str = " ".join([str(x) for x in duplicates])[:200]
                self.error(f"Table {table_name} has DUPLICATE system ids: {error_values}")
        except Exception as _:  # pylint: disable=broad-except
            self.warn(f"Duplicate check of {table_name}.system_id failed")

        return not self.has_errors()


@SpecificationRegistry.register(key="id_column_has_constraint")
class IdColumnHasConstraintSpecification(SpecificationBase):
    def is_satisfied_by(self, submission: Submission, *, table_name: str, **kwargs) -> bool:
        for column in self.get_columns(table_name):
            if column.column_name[-3:] == "_id" and not (column.is_fk or column.is_pk):
                self.warn(f'Column {table_name}.{column.column_name}: ends with "_id" but NOT marked as PK/FK')

        return not self.has_errors()


@SpecificationRegistry.register(key="foreign_key_columns_has_values")
class ForeignKeyColumnsHasValuesSpecification(SpecificationBase):
    def is_satisfied_by(self, submission: Submission, *, table_name: str, **kwargs) -> bool:
        """Foreign key columns must have values"""
        data_table: pd.DataFrame = submission.data_tables[table_name]

        if len(data_table) == 0:
            return not self.has_errors()

        if submission.is_lookup(table_name):
            if not submission.has_new_rows(table_name):
                return not self.has_errors()

        # Only check new rows (otherwise it's just a system id to public id mapping)
        pk_name: str = submission.schema.get_table(table_name).pk_name
        is_new_rows: pd.Series = data_table[pk_name].isnull()

        for column in self.get_columns(table_name):

            if not column.is_fk:
                continue

            if column.column_name not in data_table.columns:
                if not column.is_nullable:
                    self.error(f"Foreign key column '{table_name}.{column.column_name}' not in data")
                else:
                    self.info(f"Foreign key column '{table_name}.{column.column_name}' not in data (but is nullable)")
                continue

            s = data_table.loc[is_new_rows, column.column_name]
            has_nan: bool = bool(s.isna().any())
            all_nan: bool = bool(s.isna().all())

            if all_nan and not column.is_nullable:
                self.error(f"Foreign key column '{table_name}.{column.column_name}' has no values")

            if has_nan and not column.is_nullable:
                self.error(f"Non-nullable foreign key column '{table_name}.{column.column_name}' has missing values")

        return not self.has_errors()


@SpecificationRegistry.register(key="foreign_key_exists_as_primary_key")
class ForeignKeyExistsAsPrimaryKeySpecification(SpecificationBase):
    def is_satisfied_by(self, submission: Submission, *, table_name: str, **kwargs) -> bool:
        """All submission tables MUST have a non null "system_id" """
        data_table: pd.DataFrame = submission.data_tables[table_name]
        if len(data_table) == 0:
            return not self.has_errors()

        if submission.is_lookup(table_name):
            if not submission.has_new_rows(table_name):
                return not self.has_errors()
        for column in self.get_columns(table_name):

            if not column.is_fk:
                continue

            if column.column_name not in data_table.columns:
                if column.is_nullable:
                    self.warn(f"Foreign key column '{table_name}.{column.column_name}' not in data (but is nullable)")
                else:
                    self.error(f"Foreign key column '{table_name}.{column.column_name}' not in data")
                continue

            fk_has_data: bool = not data_table[column.column_name].isnull().all()

            fk_table_name: str | None = column.fk_table_name

            if not fk_table_name:
                self.error(f"Foreign key column '{table_name}.{column.column_name}' has no FK table defined")
                continue

            if fk_table_name not in submission.data_tables:
                msg: str = f"Foreign key table '{fk_table_name}' referenced by '{table_name}'"
                if column.is_nullable and not fk_has_data:
                    self.warn(f"{msg} missing in data (but is nullable)")
                elif column.is_nullable:
                    self.error(f"{msg} FK has values but target table not found in submission")
                else:
                    self.error(f"{msg} missing in data and NOT nullable")
                continue
            fk_table: Table = self.schema[fk_table_name]
            if fk_table.is_lookup:
                continue
            # fk_table: pd.DataFrame = submission.data_tables[fk_table_name]
            # if fk_table is None:
            #     self.warn(f"ERROR Table {fk_table_name} referenced as FK in data by {
            #           table_name} but not found in submission.")
            #     continue
            # if not fk_system_id.isin(fk_table.system_id).all():
            #     self.warn(
            #         f"ERROR FK value {table_name}.{
            #               column_spec.column_name} has values not found as PK in {fk_table_name}"
            #     )

        return not self.has_errors()


@SpecificationRegistry.register(key="no_missing_column")
class NoMissingColumnSpecification(SpecificationBase):
    def is_satisfied_by(self, submission: Submission, *, table_name: str, **kwargs) -> bool:
        """All fields in metadata.Table.Fields MUST exist in DataTable.columns"""

        data_table: pd.DataFrame | None = submission.data_tables[table_name] if table_name in submission else None
        meta_table: Table = self.schema[table_name]

        data_column_names: list[str] = (
            sorted(data_table.columns.values.tolist()) if data_table is not None and table_name in self.schema else []
        )

        if set(data_column_names) == {"system_id", meta_table.pk_name}:
            """This is a lookup table with only system_id and public_id"""
            return not self.has_errors()

        missing_column_names: set[str] = set(
            x for x in meta_table.column_names(skip_nullable=True) if not self.is_ignored(x)
        ) - set(data_column_names)

        if len(missing_column_names) > 0:
            self.error(
                f"Table {table_name} has MISSING NON-NULLABLE data columns: {', '.join(sorted(missing_column_names))}"
            )

        missing_nullable_column_names: set[str] = set(
            x for x in meta_table.nullable_column_names() if not self.is_ignored(x)
        ) - set(data_column_names)

        if len(missing_nullable_column_names) > 0:
            self.info(
                f"Table {table_name} has missing nullable columns: {', '.join(sorted(missing_nullable_column_names))}"
            )

        extra_column_names = list(
            set(x for x in data_column_names if not self.is_ignored(x))
            - set(meta_table.column_names(skip_nullable=False))
            - set(["system_id"])
        )

        if len(extra_column_names) > 0:
            self.warn(f"Table {table_name} has EXTRA data columns: {', '.join(extra_column_names)}")

        return not self.has_errors()


@SpecificationRegistry.register(key="non_nullable_column_has_value")
class NonNullableColumnHasValueSpecification(SpecificationBase):
    def is_satisfied_by(self, submission: Submission, *, table_name: str, **kwargs) -> bool:
        """
        Checks that non-nullable columns have values.
        Records that has a public_id value greater than 0 are ignored since they already exists in the database.
        """

        if table_name not in submission or table_name not in self.schema:
            return not self.has_errors()

        data: pd.DataFrame = submission.data_tables[table_name]
        table: Table = self.schema[table_name]

        non_nullable_columns: set[str] = {
            x
            for x in data.columns
            if x in table.column_names(skip_nullable=True)
            and not self.is_ignored(x)
            and not table.columns[x].is_pk
            and not table.columns[x].is_fk
            and x != "system_id"
        }

        new_records: pd.DataFrame = data[~(data[table.pk_name] > 0) | data[table.pk_name].isnull()]

        if len(new_records) == 0:
            return not self.has_errors()

        for column_name in non_nullable_columns:
            if new_records[column_name].isnull().any():
                self.error(f"Table {table_name} has NULL values in non-nullable column {column_name}")
        return not self.has_errors()


# DISABLED: @SpecificationRegistry.register(key="new_lookup_data_not_allowed")
class NewLookupDataIsNotAllowedSpecification(SpecificationBase):
    DISABLED: bool = True

    def is_satisfied_by(self, submission: Submission, *, table_name: str, **kwargs) -> bool:
        if self.DISABLED:
            logger.warning("NewLookupDataIsNotAllowedSpecification is disabled")
            return not self.has_errors()

        if table_name not in submission:
            return not self.has_errors()

        if not self.schema[table_name].is_lookup:
            return not self.has_errors()

        data_table: pd.DataFrame = submission.data_tables[table_name]

        pk_name: str = self.schema[table_name].pk_name

        if pk_name not in data_table.columns:
            self.error(f"Table {table_name} is missing primary key column {pk_name}")
            return not self.has_errors()

        if data_table[pk_name].isnull().any():
            self.error(f"Table {table_name}, new values not allowed for lookup table.")

        return not self.has_errors()


@SpecificationRegistry.register(key="keyed_by_table_name")
class KeyedByTableNameSpecification(SpecificationBase):
    """Verify that `table_name` is a SEAD table (and not an Excel abbreviated sheet name)"""

    @cached_property
    def aliased_table_names(self) -> set[str]:
        return {t.excel_sheet for t in self.schema.aliased_tables}

    def is_satisfied_by(self, submission: Submission, *, table_name: str, **kwargs) -> bool:

        if table_name in self.aliased_table_names:
            self.error(f"Table {table_name} is keyed by excel sheet name for aliased table")
        return not self.has_errors()
