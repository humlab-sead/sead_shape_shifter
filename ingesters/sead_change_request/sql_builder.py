"""Deploy SQL generation for the SEAD change request ingester."""

import gzip
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from io import StringIO
from numbers import Integral, Real
from typing import Any, Protocol, cast

import pandas as pd

from ingesters.sead_change_request.contracts import (
    ChangeRequestPackage,
    ChangeRequestTable,
    ChangeRowState,
    DeployArtifact,
    PlannedRowAction,
    SubmissionContext,
    resolve_bundle_name,
)
from src.target_model.models import TargetModel

DEFAULT_DEPLOY_ARTIFACT_STRATEGY = "inline_insert"
COPY_CSV_DEPLOY_ARTIFACT_STRATEGY = "copy_csv"
SAFE_BUNDLE_TABLE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_]+$")


class DeployArtifactStrategy(Protocol):
    """Strategy boundary for rendering deploy artifacts from a prepared change package."""

    def build_artifact(
        self,
        change_package: ChangeRequestPackage,
        target_model: TargetModel,
        submission_context: SubmissionContext,
    ) -> DeployArtifact: ...


class InlineInsertDeployStrategy:
    """Default deploy strategy that uses inline INSERT statements."""

    strategy_name = DEFAULT_DEPLOY_ARTIFACT_STRATEGY

    def build_artifact(
        self,
        change_package: ChangeRequestPackage,
        target_model: TargetModel,
        submission_context: SubmissionContext,
    ) -> DeployArtifact:
        statements: list[str] = []

        for entity_name, package_table in change_package.tables.items():
            entity_spec = target_model.entities[entity_name]
            table_name = entity_spec.target_table or entity_name
            for row_index, row in package_table.frame.iterrows():
                if _is_update_row(package_table, row_index):
                    statements.append(_render_update_statement(table_name, row, entity_spec.public_id))
                else:
                    statements.append(_render_insert_statement(table_name, row))

        deploy_sql_lines = ["BEGIN;", "SET CONSTRAINTS ALL DEFERRED;"]
        deploy_sql_lines.extend(statements)
        deploy_sql_lines.append("COMMIT;")
        return _build_deploy_artifact_payload(
            strategy_name=self.strategy_name,
            submission_context=submission_context,
            deploy_sql_body="\n".join(deploy_sql_lines),
            statements=statements,
            artifact_metadata={
                "deploy_statement_count": len(statements),
                **_common_contract_metadata(submission_context, statements=statements, bundle_files={}),
            },
        )


class CopyCsvDeployStrategy:
    """CSV plus \\copy deploy strategy for artifact-oriented bulk loading."""

    strategy_name = COPY_CSV_DEPLOY_ARTIFACT_STRATEGY

    def build_artifact(
        self,
        change_package: ChangeRequestPackage,
        target_model: TargetModel,
        submission_context: SubmissionContext,
    ) -> DeployArtifact:
        statements: list[str] = []
        bundle_files: dict[str, str] = {}
        emitted_table_order: list[str] = []
        emitted_row_counts: dict[str, int] = {}

        for entity_name, package_table in change_package.tables.items():
            entity_spec = target_model.entities[entity_name]
            table_name = entity_spec.target_table or entity_name
            insert_mask, update_mask = _package_row_masks(package_table)

            if bool(insert_mask.any()):
                columns = _renderable_columns(package_table.frame.loc[insert_mask])
                if columns:
                    bundle_name = _artifact_directory_name(submission_context)
                    payload_relative_path = _build_bundle_payload_relative_path(bundle_name, table_name)
                    bundle_files[f"deploy/{payload_relative_path}"] = _render_copy_csv_bundle_file(
                        package_table.frame.loc[insert_mask], columns
                    )
                    emitted_table_order.append(table_name)
                    emitted_row_counts[table_name] = len(package_table.frame.loc[insert_mask].index)
                    statements.append(_render_copy_statement(table_name, columns, payload_relative_path))

            if bool(update_mask.any()):
                for row_index, row in package_table.frame.loc[update_mask].iterrows():
                    statements.append(_render_update_statement(table_name, row, entity_spec.public_id))

        deploy_sql_lines = ["BEGIN;", "SET CONSTRAINTS ALL DEFERRED;"]
        deploy_sql_lines.extend(statements)
        deploy_sql_lines.append("COMMIT;")
        return _build_deploy_artifact_payload(
            strategy_name=self.strategy_name,
            submission_context=submission_context,
            deploy_sql_body="\n".join(deploy_sql_lines),
            statements=statements,
            artifact_metadata={
                "deploy_statement_count": len(statements),
                "bundle_file_count": len(bundle_files),
                **_common_contract_metadata(
                    submission_context,
                    statements=statements,
                    bundle_files=bundle_files,
                    table_order=emitted_table_order,
                    row_counts=emitted_row_counts,
                ),
            },
            bundle_files=bundle_files,
        )


def build_deploy_artifact(
    change_package: ChangeRequestPackage,
    target_model: TargetModel,
    submission_context: SubmissionContext,
    strategy: DeployArtifactStrategy | str | None = None,
) -> DeployArtifact:
    """Build the in-memory deploy artifact."""
    resolved_strategy = resolve_deploy_artifact_strategy(strategy)
    return resolved_strategy.build_artifact(change_package, target_model, submission_context)


def resolve_deploy_artifact_strategy(strategy: DeployArtifactStrategy | str | None = None) -> DeployArtifactStrategy:
    """Resolve the configured deploy artifact strategy to a concrete renderer."""
    if strategy is None:
        return InlineInsertDeployStrategy()

    if isinstance(strategy, str):
        normalized_strategy = strategy.strip().lower()
        if normalized_strategy == DEFAULT_DEPLOY_ARTIFACT_STRATEGY:
            return InlineInsertDeployStrategy()
        if normalized_strategy == COPY_CSV_DEPLOY_ARTIFACT_STRATEGY:
            return CopyCsvDeployStrategy()
        raise ValueError(
            "Unsupported deploy strategy "
            f"'{strategy}'; expected '{DEFAULT_DEPLOY_ARTIFACT_STRATEGY}' or '{COPY_CSV_DEPLOY_ARTIFACT_STRATEGY}'"
        )

    return strategy


def _build_revert_placeholder_sql() -> str:
    """Build the revert placeholder that fails loudly."""
    return "\n".join(
        [
            "BEGIN;",
            "DO $$ BEGIN",
            "    RAISE EXCEPTION 'Rollback is not implemented for this Delivery 1 change package.';",
            "END $$;",
            "ROLLBACK;",
        ]
    )


def _build_verify_placeholder_sql() -> str:
    """Build the verify placeholder that fails loudly."""
    return "\n".join(
        [
            "BEGIN;",
            "DO $$ BEGIN",
            "    RAISE EXCEPTION 'Verification is not implemented for this Delivery 1 change package.';",
            "END $$;",
            "ROLLBACK;",
        ]
    )


def _build_deploy_artifact_payload(
    *,
    strategy_name: str,
    submission_context: SubmissionContext,
    deploy_sql_body: str,
    statements: list[str],
    artifact_metadata: dict[str, object] | None = None,
    metadata: dict[str, object] | None = None,
    revert_placeholder_sql: str | None = None,
    verify_placeholder_sql: str | None = None,
    bundle_files: dict[str, str] | None = None,
) -> DeployArtifact:
    """Build a deploy artifact with shared metadata for all renderer strategies."""
    payload_metadata = _base_deploy_metadata(submission_context, strategy_name)
    if metadata:
        payload_metadata.update(metadata)

    payload_artifact_metadata = _base_deploy_artifact_metadata(submission_context, strategy_name)
    if artifact_metadata:
        payload_artifact_metadata.update(artifact_metadata)

    return DeployArtifact(
        deploy_sql=_render_sql_file("deploy", submission_context, deploy_sql_body),
        statements=statements,
        metadata=payload_metadata,
        revert_sql=_render_sql_file("revert", submission_context, revert_placeholder_sql or _build_revert_placeholder_sql()),
        verify_sql=_render_sql_file("verify", submission_context, verify_placeholder_sql or _build_verify_placeholder_sql()),
        metadata_artifact=payload_artifact_metadata,
        bundle_files=bundle_files or {},
    )


def _base_deploy_metadata(submission_context: SubmissionContext, strategy_name: str) -> dict[str, object]:
    """Build the shared runtime metadata for a rendered deploy artifact."""
    return {
        "submission_name": submission_context.submission_name,
        "project_name": submission_context.project_name,
        "timestamp": submission_context.timestamp.isoformat(),
        "binding_set_uuid": submission_context.binding_set_uuid,
        "change_request_name": submission_context.change_request_name,
        "deploy_strategy": strategy_name,
        "non_revertible": True,
        "verify_placeholder": True,
    }


def _base_deploy_artifact_metadata(submission_context: SubmissionContext, strategy_name: str) -> dict[str, object]:
    """Build the shared persisted metadata artifact payload for a rendered deploy artifact."""
    return {
        "artifact_type": "delivery_1_change_package",
        "contract_version": 1,
        "deploy_strategy": strategy_name,
        "non_revertible": True,
        "verify_placeholder": True,
        "submission_name": submission_context.submission_name,
        "project_name": submission_context.project_name,
        "binding_set_uuid": submission_context.binding_set_uuid,
        "change_request_name": submission_context.change_request_name,
        "cr_name": _artifact_directory_name(submission_context),
        "datatype": _resolved_datatype(submission_context),
        "identifier": _resolved_identifier(submission_context),
        "dispatch_date": submission_context.timestamp.date().isoformat(),
        "description": _resolved_description(submission_context),
        "issue_number": _resolved_issue_number(submission_context),
    }


def _common_contract_metadata(
    submission_context: SubmissionContext,  # pylint: disable=unused-argument
    *,
    statements: list[str],
    bundle_files: dict[str, str],
    table_order: list[str] | None = None,
    row_counts: dict[str, int] | None = None,
) -> dict[str, object]:
    """Build the shared contract metadata expected in the manifest."""
    file_paths = sorted(bundle_files)
    checksums = {path: sha256(encode_bundle_file_content(path, content)).hexdigest() for path, content in bundle_files.items()}
    resolved_row_counts = row_counts or {}
    resolved_table_order = table_order or []
    return {
        "files": file_paths,
        "checksums": checksums,
        "row_counts": resolved_row_counts,
        "table_order": resolved_table_order,
        "payload_format": "csv",
        "payload_encoding": "utf-8",
        "payload_delimiter": "\t",
        "payload_compression": "gzip" if bundle_files else None,
        "header_row": False,
        "payload_null_rule": "unquoted_empty_field",
        "payload_empty_string_rule": "quoted_empty_field",
        "sccs_runtime_assumption": "psql+zcat",
        "statement_count": len(statements),
    }


def _render_sql_file(file_type: str, submission_context: SubmissionContext, body: str) -> str:
    """Render a CR SQL file with the standard metadata header."""
    header_lines = [
        f"-- {file_type} {_resolved_datatype(submission_context)}: {_artifact_directory_name(submission_context)}",
        "/***************************************************************************",
        f"  Author            {_resolved_author(submission_context)}",
        f"  Date              {submission_context.timestamp.date().isoformat()}",
        f"  Description       {_resolved_description(submission_context)}",
        ("  Issue             " f"https://github.com/humlab-sead/sead_change_control/issues/{_resolved_issue_number(submission_context)}"),
        "***************************************************************************/",
        "",
    ]
    return "\n".join(header_lines) + body


def _resolved_datatype(submission_context: SubmissionContext) -> str:
    return submission_context.datatype or submission_context.project_name


def _resolved_identifier(submission_context: SubmissionContext) -> str:
    return submission_context.identifier or _artifact_directory_name(submission_context)


def _resolved_description(submission_context: SubmissionContext) -> str:
    return submission_context.description or submission_context.submission_name


def _resolved_issue_number(submission_context: SubmissionContext) -> str:
    return submission_context.issue_number or "NNN"


def _resolved_author(submission_context: SubmissionContext) -> str:
    return submission_context.author or "unknown"


def _render_insert_statement(table_name: str, row: pd.Series) -> str:
    """Render a single INSERT statement from a projected row."""
    columns = _renderable_columns(row)
    identifiers = ", ".join(_quote_identifier(column) for column in columns)
    values = ", ".join(_render_literal(row[column]) for column in columns)
    return f"INSERT INTO {_quote_identifier(table_name)} ({identifiers}) VALUES ({values});"


def _render_update_statement(table_name: str, row: pd.Series, public_id_column: str | None) -> str:
    """Render a single UPDATE statement for an accepted existing-row update."""
    if not public_id_column:
        raise ValueError(f"Cannot render update statement for '{table_name}' without public_id metadata")
    if public_id_column not in row.index:
        raise ValueError(
            f"Cannot render update statement for '{table_name}' because '{public_id_column}' is missing from the projected row"
        )

    set_columns = _update_assignment_columns(row, public_id_column)
    if not set_columns:
        raise ValueError(f"Cannot render update statement for '{table_name}' because no mutable columns were available")

    assignments = ", ".join(f"{_quote_identifier(column)} = {_render_literal(row[column])}" for column in set_columns)
    where_clause = f"{_quote_identifier(public_id_column)} = {_render_literal(row[public_id_column])}"
    return f"UPDATE {_quote_identifier(table_name)} SET {assignments} WHERE {where_clause};"


def _render_copy_statement(table_name: str, columns: list[str], relative_path: str) -> str:
    """Render a psql \\copy statement for a CSV sidecar file."""
    identifiers = ", ".join(_quote_identifier(column) for column in columns)
    return (
        f"\\copy {_quote_identifier(table_name)} ({identifiers}) "
        f"FROM program 'zcat -qac {_quote_copy_path(relative_path)}' "
        "WITH (FORMAT csv, DELIMITER E'\\t', ENCODING 'utf-8');"
    )


def _render_copy_csv_bundle_file(frame: pd.DataFrame, columns: list[str]) -> str:
    """Render a tab-delimited PostgreSQL CSV payload sidecar file for a prepared table."""
    buffer = StringIO()

    for _, row in frame.loc[:, columns].iterrows():
        rendered_fields = [_render_copy_csv_field(row[column]) for column in columns]
        buffer.write("\t".join(rendered_fields))
        buffer.write("\n")

    return buffer.getvalue()


def _render_copy_csv_field(value: object) -> str:
    """Render one field according to the hardened copy_csv contract."""
    scalar_value = cast(Any, value)
    if value is None or pd.isna(scalar_value):
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, Integral):
        return str(value)
    if isinstance(value, Real):
        return _render_copy_csv_real(value)
    if isinstance(value, pd.Timestamp):
        return _quote_copy_csv_text(_render_copy_csv_timestamp(value))
    if isinstance(value, datetime):
        return _quote_copy_csv_text(value.isoformat())

    return _quote_copy_csv_text(str(value))


def _render_copy_csv_timestamp(value: pd.Timestamp) -> str:
    """Render pandas timestamps using the hardened copy_csv date-only contract."""
    if (
        value.tz is None  #  pylint: disable=too-many-boolean-expressions
        and value.hour == 0
        and value.minute == 0
        and value.second == 0
        and value.microsecond == 0
        and value.nanosecond == 0
    ):
        return value.date().isoformat()

    return value.isoformat()


def _render_copy_csv_real(value: Real) -> str:
    """Render real numbers without scientific notation while preserving input precision."""
    rendered = str(value)

    if "e" in rendered.lower():
        try:
            rendered = format(Decimal(rendered), "f")
        except InvalidOperation:
            rendered = format(value, "f")

    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")

    return "0" if rendered == "-0" else rendered


def _renderable_columns(row_like: pd.Series | pd.DataFrame) -> list[str]:
    """Return non-internal column names in stable order for artifact rendering."""
    if isinstance(row_like, pd.DataFrame):
        return [
            str(column)
            for column in row_like.columns
            if not str(column).startswith("_") and not str(column).endswith("__existing") and str(column) != "system_id"
        ]
    return [
        str(column)
        for column in row_like.index
        if not str(column).startswith("_") and not str(column).endswith("__existing") and str(column) != "system_id"
    ]


def _package_row_masks(package_table: ChangeRequestTable) -> tuple[pd.Series, pd.Series]:
    """Return the insert and update masks for one packaged table."""
    insert_mask = package_table.row_states.isin({ChangeRowState.NEWLY_ALLOCATED_ENTITY, ChangeRowState.DERIVED_BRIDGE_ROW})
    update_mask = pd.Series(False, index=package_table.frame.index)
    if package_table.planned_actions is not None:
        update_mask = package_table.planned_actions == PlannedRowAction.UPDATE_EXISTING_CANDIDATE
    return insert_mask, update_mask


def _is_update_row(package_table: ChangeRequestTable, row_index: object) -> bool:
    """Return True when one packaged row should be rendered as an UPDATE statement."""
    if package_table.planned_actions is None:
        return False
    return package_table.planned_actions.loc[row_index] == PlannedRowAction.UPDATE_EXISTING_CANDIDATE


def _update_assignment_columns(row: pd.Series, public_id_column: str) -> list[str]:
    """Return the columns that should be updated for one existing-row update."""
    columns: list[str] = []
    for column_name in row.index:
        if str(column_name).startswith("_"):
            continue
        if column_name in {public_id_column, "system_id"}:
            continue
        if str(column_name).endswith("__existing"):
            continue
        if f"{column_name}__existing" not in row.index:
            continue
        columns.append(str(column_name))
    return columns


def _quote_identifier(identifier: str) -> str:
    escaped = identifier.replace('"', '""')
    return f'"{escaped}"'


def _render_literal(value: object) -> str:
    scalar_value = cast(Any, value)
    if value is None or pd.isna(scalar_value):
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, Integral):
        return str(value)
    if isinstance(value, Real):
        return repr(value)
    if isinstance(value, (datetime, pd.Timestamp)):
        return _quote_string(value.isoformat())
    return _quote_string(str(value))


def _quote_string(value: str) -> str:
    escaped = value.replace("'", "''")
    return f"'{escaped}'"


def _quote_copy_path(value: str) -> str:
    """Escape a relative artifact path for use inside a quoted \\copy path literal."""
    return value.replace("'", "''")


def _quote_copy_csv_text(value: str) -> str:
    """Quote and escape text according to PostgreSQL CSV rules with tab delimiter."""
    if value == "":
        return '""'

    needs_quotes = any(character in value for character in ("\t", "\n", "\r", '"'))
    escaped = value.replace('"', '""')
    return f'"{escaped}"' if needs_quotes else escaped


def encode_bundle_file_content(relative_path: str, content: str) -> bytes:
    """Encode bundle content exactly as it will be written to disk."""
    encoded = content.encode("utf-8")
    if relative_path.endswith(".gz"):
        return gzip.compress(encoded, mtime=0)
    return encoded


def _build_bundle_payload_relative_path(bundle_name: str, table_name: str) -> str:
    """Build a safe relative payload path for a rendered CSV sidecar."""
    validated_table_name = _validate_bundle_table_name(table_name)
    return f"{bundle_name}/{validated_table_name}.gz"


def _validate_bundle_table_name(table_name: str) -> str:
    """Reject table names that are unsafe to embed in bundle paths or shell commands."""
    if SAFE_BUNDLE_TABLE_NAME_PATTERN.fullmatch(table_name):
        return table_name

    raise ValueError("Unsafe table name " f"'{table_name}' for copy_csv deploy artifact; expected only letters, digits, and underscores")


def _artifact_directory_name(submission_context: SubmissionContext) -> str:
    """Build the artifact directory name used by emitted deploy bundles."""
    return resolve_bundle_name(submission_context)
