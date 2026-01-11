from __future__ import annotations

from fnmatch import fnmatch
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
from loguru import logger
from pandas._typing import Dtype

from src.configuration.resolve import ConfigValue

from .metadata import SchemaService, SeadSchema, Table
from .utility import Registry, pascal_to_snake_case, snake_to_pascal_case

if TYPE_CHECKING:
    from backend.app.ingesters.sead.submission import Submission


class PolicyRegistry(Registry[type["PolicyBase"]]):
    items: dict[str, type[PolicyBase]] = {}

    def get_sorted_items(self) -> list[type[PolicyBase]]:
        """Get the registered policies sorted by priority. Creaete an instance of each policy to get its priority."""
        return sorted(self.items.values(), key=lambda x: x(None, None, None).get_priority())  # type: ignore


UpdatePolicies: PolicyRegistry = PolicyRegistry()  # pylint: disable=invalid-name


class DisabledError(Exception):
    pass


class PolicyBase:

    def __init__(self, schema: SeadSchema, submission: Submission, service: SchemaService) -> None:
        self.schema: SeadSchema = schema
        self.service: SchemaService = service
        self.submission: Submission = submission
        self.logs: dict[str, str] = {}

    def get_id(self) -> str:
        return pascal_to_snake_case(self.__class__.__name__)

    def get_priority(self) -> int:
        return ConfigValue(f"policies.{self.get_id()}.priority").resolve() or 0

    def is_disabled(self) -> bool:
        return ConfigValue(f"policies.{self.get_id()}.disabled").resolve() or False

    def apply(self) -> None:
        """Applies the policy to the submission data."""
        if self.is_disabled():
            logger.info(f"Policy '{self.get_id()}' is disabled")
        try:
            self.update()
            for _, message in self.logs.items():
                logger.info(f"{message} (policy [{snake_to_pascal_case(self.get_id())}])")
        except:  # pylint: disable=bare-except
            logger.exception(f"Error applying policy ({snake_to_pascal_case(self.get_id())})")
            raise

    def update(self) -> None:
        raise NotImplementedError("Policy must implement _apply method")

    def log(self, table: str, message: str | None = None) -> None:
        self.logs[table] = message or self.get_id()


@UpdatePolicies.register(key="add_primary_key_column_if_missing")
class AddPrimaryKeyColumnIfMissingPolicy(PolicyBase):
    """Adds a primary key column to the DataFrame if it is missing"""

    def update(self) -> None:
        """For each table in index, add primary key column if missing."""
        for table_name, data in self.submission.data_tables.items():
            table: Table = self.schema.get_table(table_name)
            if table.pk_name not in data.columns:
                self.log(
                    table_name,
                    f"Added missing primary key column '{table_name}.{table.pk_name}' (assuming all new records)",
                )
                data[table.pk_name] = None


@UpdatePolicies.register(key="update_missing_foreign_key")
class UpdateMissingForeignKeyPolicy(PolicyBase):
    """Adds default FK value to DataFrame if it is missing"""

    def update(self) -> None:
        """For each table in index, add default foreign key value if missing."""
        for table_name, cfg in (ConfigValue(f"policies.{self.get_id()}").resolve() or {}).items():
            if table_name not in self.submission:
                return

            data: pd.DataFrame = self.submission[table_name]

            for fk_name, fk_value in cfg.items():
                if fk_name not in data.columns:
                    data[fk_name] = fk_value
                    self.log(table_name, f"Added missing column '{fk_name}' to '{table_name}' using value '{fk_value}'")
                elif data[fk_name].isnull().all():
                    data[fk_name] = fk_value
                    self.log(table_name, f"Added default value '{fk_value}' to '{fk_name}' in '{table_name}'")

                elif data[fk_name].isnull().any():
                    n_count: int = data[fk_name].isnull().sum()
                    data.loc[data[fk_name].isnull(), fk_name] = fk_value
                    self.log(
                        table_name,
                        f"Updated {n_count} missing values '{table_name}.{fk_name}' to '{fk_value}'",
                    )


@UpdatePolicies.register(key="add_identity_mapping_system_id_to_public_id")
class AddIdentityMappingSystemIdToPublicIdPolicy(PolicyBase):
    """Rule: if an FK table is missing then add the table using system_id as public_id.

    For table that is referenced by a foreign key,
        if the table is missing,
            add the table to the submission and assume that the table's system_id is the same as it's public primary key

    Assumptions:
        The foreign keys used in the submission MUST be equal to the public primary key of the table
        The rule (as default) is applied any table
    """

    def table_names(self) -> set[str]:
        includes: set[str] = set(ConfigValue(f"policies.{self.get_id()}.tables.include").resolve() or []) or set(self.schema.keys())
        excludes: set[str] = set(ConfigValue(f"policies.{self.get_id()}.tables.exclude").resolve() or [])
        return includes - excludes

    def update(self) -> None:

        for table_name in self.table_names():

            if table_name in self.submission:
                continue

            referenced_keys: list[int] = sorted(self.submission.get_referenced_keyset(self.schema, table_name))

            if not referenced_keys:
                continue

            table: Table = self.schema.get_table(table_name)

            public_primary_keys: set[int] = self.service.get_primary_key_values(table_name, table.pk_name)
            if set(referenced_keys) - public_primary_keys:
                logger.warning(
                    f"Table '{table_name}' has referenced keys that are not primary keys: {', '
                        .join(map(str, referenced_keys))}"
                )

            self.submission.data_tables[table_name] = pd.DataFrame({"system_id": referenced_keys, table.pk_name: list(referenced_keys)})

            self.log(
                table_name,
                f"Added table '{table_name}' with system_id/{table.pk_name} mapping ({len(referenced_keys)} keys)",
            )


@UpdatePolicies.register(key="update_types_based_on_sead_schema")
class UpdateTypesBasedOnSeadSchema(PolicyBase):
    """Rule: update data types based on SEAD schema

    For each table in the submission,
        update the data types of the columns based on the SEAD schema
    """

    def update(self) -> None:

        for table_name in self.submission.data_tables:

            data_table: pd.DataFrame = self.submission.data_tables[table_name]
            table: Table = self.schema.get_table(table_name)

            for column_name, column_spec in table.columns.items():

                if column_name not in data_table.columns:
                    continue

                if column_spec.data_type == "smallint":
                    data_table[column_name] = data_table[column_name].astype("Int16")
                elif column_spec.data_type == "integer":
                    data_table[column_name] = data_table[column_name].astype("Int32")
                elif column_spec.data_type == "bigint":
                    data_table[column_name] = data_table[column_name].astype("Int64")


# @UpdatePolicies.register(key="set_public_id_to_negative_system_id_for_new_lookups")
# class SetPublicIdToNegativeSystemIdForNewLookups(PolicyBase):
#     """Rule: assign temporary public primary key to new lookup table rows.

#     For new lookup table rows,
#         set the public primary key to the negative of the system_id
#             if all public primary keys are missing
#     In this case, the public primary key is assigned upon submission commit to the database
#     """

#     def update(self) -> None:

#         for table_name in self.submission.data_tables:

#             if not self.metadata[table_name].is_lookup:
#                 continue

#             data_table: pd.DataFrame = self.submission.data_tables[table_name]

#             pk_name: str = self.metadata[table_name].pk_name

#             if pk_name not in data_table.columns:
#                 continue

#             if data_table[pk_name].isnull().any():
#                 data_table.loc[data_table[pk_name].isnull(), pk_name] = -data_table['system_id']
#                 data_table[pk_name] = data_table[pk_name].astype(int)


@UpdatePolicies.register(key="set_system_id_to_public_id_if_missing")
class IfSystemIdIsMissingSetSystemIdToPublicId(PolicyBase):
    """Rule: assign temporary public primary key to new lookup table rows.

    For new lookup table rows,
        set the public primary key to the negative of the system_id
            if all public primary keys are missing
    In this case, the public primary key is assigned upon submission commit to the database
    """

    def update(self) -> None:
        """For each table in index, update system_id to public_id if isnan. This should be avoided though."""
        for table_name in self.submission.data_tables:

            data_table: pd.DataFrame = self.submission.data_tables[table_name]
            table: Table = self.schema.get_table(table_name)

            pk_name: str = table.pk_name

            if pk_name == "ceramics_id":
                pk_name = "ceramic_id"

            if data_table is None or pk_name not in data_table.columns:
                continue

            if "system_id" not in data_table.columns:
                raise ValueError(f'critical error Table {table_name} has no column named "system_id"')

            # Update system_id to public_id if isnan. This should be avoided though.
            data_table.loc[np.isnan(data_table.system_id), "system_id"] = data_table.loc[np.isnan(data_table.system_id), pk_name]
            self.log(table_name, f"Updated system_id to public_id for new records in '{table_name}'")


@UpdatePolicies.register(key="add_identity_mapping_to_foreign_key_table_if_missing")
class IfForeignKeyValueIsMissingAddIdentityMappingToForeignKeyTable(PolicyBase):
    """Any foreign key value that is missing in the submission is added to the foreign key table."""

    def fix_dtypes(self, data_table: pd.DataFrame) -> pd.DataFrame:
        """Fix data types of the column in the data table."""
        sead_column_dtypes: dict[str, Dtype] = self.schema.sead_column_dtypes
        for column_name in data_table.columns:
            if data_table[column_name].isnull().all():
                if sead_column_dtypes.get(column_name, None):
                    data_table[column_name] = data_table[column_name].astype(sead_column_dtypes[column_name])  # type: ignore
        return data_table

    def update(self) -> None:

        for table in self.schema.lookup_tables:

            table_name: str = table.table_name

            referenced_keys: list[int] = sorted(self.submission.get_referenced_keyset(self.schema, table_name))

            if not referenced_keys:
                continue

            if table_name not in self.submission:
                # This case is handled by another policy
                continue

            data_table: pd.DataFrame = self.submission.data_tables[table_name]
            pk_name: str = self.schema.get_table(table_name).pk_name

            missing_keys: list[int] = [k for k in referenced_keys if k not in data_table["system_id"].values]

            if not missing_keys:
                continue

            template: dict[str, int | None] = {c: None for c in data_table.columns}
            rows_to_add: list[dict[str, int | None]] = [
                template | {"system_id": system_id, pk_name: system_id} for system_id in missing_keys
            ]

            if len(rows_to_add) > 0:
                new_rows: pd.DataFrame = pd.DataFrame(rows_to_add)
                data_table = self.fix_dtypes(data_table)
                new_rows = self.fix_dtypes(new_rows)
                data_table = pd.DataFrame(rows_to_add) if len(data_table) == 0 else pd.concat([data_table, new_rows], ignore_index=True)

            self.submission.data_tables[table_name] = data_table

            self.log(
                table_name,
                f"Added missing PK keys to '{table_name}' with identity system_id/{pk_name} mapping: ({', '
                                    .join(map(str, missing_keys))})",
            )


@UpdatePolicies.register(key="drop_ignored_columns")
class DropIgnoredColumns(PolicyBase):
    """Rule: drop ignored columns from data so that they are excluded from uploaded submission data.
    This rule currently only applies "date_updated" and "*_uuid" columns.
    """

    def filter_columns(self, patterns: list[str], columns: pd.Index[str]) -> list[str]:
        """Filter out columns that are ignored."""
        return [c for c in columns if any(fnmatch(c, x) for x in patterns)]

    def update(self) -> None:
        """For each table in index, drop column if it is ignoderd."""

        drop_patterns: list[str] = ConfigValue(f"policies.{self.get_id()}.columns").resolve() or []

        if not drop_patterns:
            return

        for table_name, data in self.submission.data_tables.items():
            columns: list[str] = self.filter_columns(drop_patterns, data.columns)
            if not columns:
                continue

            data.drop(columns=columns, inplace=True)
            self.log(table_name, f"Dropped column(s) {', '.join(columns)} from {table_name}")


@UpdatePolicies.register(key="if_lookup_with_no_new_data_then_keep_only_system_id_public_id")
class IfLookupWithNoNewDataThenKeepOnlySystemIdPublicId(PolicyBase):
    """Rule: if table is a lookup table and no new data then drop all columns except
    system_id and public_id. The table has new data if any public PK (table.pk_name) is None or NaN
    """

    def update(self) -> None:
        """For each table in index, drop column if it is ignored."""

        for table_name in self.submission.data_tables:

            data_table: pd.DataFrame = self.submission.data_tables[table_name]
            table: Table = self.schema.get_table(table_name)

            if not table.is_lookup:
                continue

            if table.pk_name not in data_table.columns:
                continue

            if data_table[table.pk_name].isnull().any():
                continue

            columns_to_drop: list[str] = [c for c in data_table.columns if c not in ["system_id", table.pk_name]]

            if not columns_to_drop:
                continue

            data_table.drop(columns=columns_to_drop, inplace=True)
            self.log(table_name, f"Dropped column(s) {', '.join(columns_to_drop)} from {table_name}")
