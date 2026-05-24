"""Deploy SQL generation for the SEAD change request ingester."""

from datetime import datetime
from io import StringIO
from numbers import Integral, Real
from typing import Any, Protocol, cast

import pandas as pd

from ingesters.sead_change_request.contracts import ChangeRequestPackage, DeployArtifact, SubmissionContext
from src.target_model.models import TargetModel


DEFAULT_DEPLOY_ARTIFACT_STRATEGY = "inline_insert"
COPY_CSV_DEPLOY_ARTIFACT_STRATEGY = "copy_csv"


class DeployArtifactStrategy(Protocol):
    """Strategy boundary for rendering deploy artifacts from a prepared change package."""

    def build_artifact(
        self,
        change_package: ChangeRequestPackage,
        target_model: TargetModel,
        submission_context: SubmissionContext,
    ) -> DeployArtifact:
        ...


class InlineInsertDeployStrategy:
    """Default Delivery 1 deploy strategy using inline INSERT statements."""

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
            for _, row in package_table.frame.iterrows():
                statements.append(_render_insert_statement(table_name, row))

        deploy_sql_lines = ["BEGIN;", "SET CONSTRAINTS ALL DEFERRED;"]
        deploy_sql_lines.extend(statements)
        deploy_sql_lines.append("COMMIT;")
        return _build_deploy_artifact_payload(
            strategy_name=self.strategy_name,
            submission_context=submission_context,
            deploy_sql="\n".join(deploy_sql_lines),
            statements=statements,
            artifact_metadata={"deploy_statement_count": len(statements)},
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

        for entity_name, package_table in change_package.tables.items():
            entity_spec = target_model.entities[entity_name]
            table_name = entity_spec.target_table or entity_name
            columns = _renderable_columns(package_table.frame)
            if not columns:
                continue

            relative_path = f"payload/{table_name}.csv"
            bundle_files[relative_path] = _render_csv_bundle_file(package_table.frame, columns)
            statements.append(_render_copy_statement(table_name, columns, relative_path))

        deploy_sql_lines = ["BEGIN;", "SET CONSTRAINTS ALL DEFERRED;"]
        deploy_sql_lines.extend(statements)
        deploy_sql_lines.append("COMMIT;")
        return _build_deploy_artifact_payload(
            strategy_name=self.strategy_name,
            submission_context=submission_context,
            deploy_sql="\n".join(deploy_sql_lines),
            statements=statements,
            artifact_metadata={
                "deploy_statement_count": len(statements),
                "bundle_file_count": len(bundle_files),
            },
            bundle_files=bundle_files,
        )


def build_deploy_artifact(
    change_package: ChangeRequestPackage,
    target_model: TargetModel,
    submission_context: SubmissionContext,
    strategy: DeployArtifactStrategy | str | None = None,
) -> DeployArtifact:
    """Build the first in-memory Delivery 1 deploy artifact."""
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
    """Build the explicit fail-loud Delivery 1 revert placeholder."""
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
    """Build the explicit fail-loud Delivery 1 verify placeholder."""
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
    deploy_sql: str,
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
        deploy_sql=deploy_sql,
        statements=statements,
        metadata=payload_metadata,
        revert_placeholder_sql=revert_placeholder_sql or _build_revert_placeholder_sql(),
        verify_placeholder_sql=verify_placeholder_sql or _build_verify_placeholder_sql(),
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
        "deploy_strategy": strategy_name,
        "non_revertible": True,
        "verify_placeholder": True,
        "submission_name": submission_context.submission_name,
        "project_name": submission_context.project_name,
        "binding_set_uuid": submission_context.binding_set_uuid,
        "change_request_name": submission_context.change_request_name,
    }


def _render_insert_statement(table_name: str, row: pd.Series) -> str:
    """Render a single INSERT statement from a materialized row."""
    columns = _renderable_columns(row)
    identifiers = ", ".join(_quote_identifier(column) for column in columns)
    values = ", ".join(_render_literal(row[column]) for column in columns)
    return f"INSERT INTO {_quote_identifier(table_name)} ({identifiers}) VALUES ({values});"


def _render_copy_statement(table_name: str, columns: list[str], relative_path: str) -> str:
    """Render a psql \\copy statement for a CSV sidecar file."""
    identifiers = ", ".join(_quote_identifier(column) for column in columns)
    return f"\\copy {_quote_identifier(table_name)} ({identifiers}) FROM '{_quote_copy_path(relative_path)}' WITH (FORMAT csv, HEADER true);"


def _render_csv_bundle_file(frame: pd.DataFrame, columns: list[str]) -> str:
    """Render a CSV payload sidecar file for a prepared table."""
    csv_frame = frame.loc[:, columns].copy()
    buffer = StringIO()
    csv_frame.to_csv(buffer, index=False, lineterminator="\n")
    return buffer.getvalue()


def _renderable_columns(row_like: pd.Series | pd.DataFrame) -> list[str]:
    """Return non-internal column names in stable order for artifact rendering."""
    return [str(column) for column in row_like.columns if not str(column).startswith("_")] if isinstance(row_like, pd.DataFrame) else [
        str(column) for column in row_like.index if not str(column).startswith("_")
    ]


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
