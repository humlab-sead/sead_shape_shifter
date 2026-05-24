"""Deploy SQL generation for the SEAD change request ingester."""

from datetime import datetime
from numbers import Integral, Real

import pandas as pd

from ingesters.sead_change_request.contracts import ChangeRequestPackage, DeployArtifact, SubmissionContext
from src.target_model.models import TargetModel


def build_deploy_artifact(
    change_package: ChangeRequestPackage, target_model: TargetModel, submission_context: SubmissionContext
) -> DeployArtifact:
    """Build the first in-memory Delivery 1 deploy artifact."""
    statements: list[str] = []

    for entity_name, package_table in change_package.tables.items():
        entity_spec = target_model.entities[entity_name]
        table_name = entity_spec.target_table or entity_name
        for _, row in package_table.frame.iterrows():
            statements.append(_render_insert_statement(table_name, row))

    deploy_sql_lines = ["BEGIN;", "SET CONSTRAINTS ALL DEFERRED;"]
    deploy_sql_lines.extend(statements)
    deploy_sql_lines.append("COMMIT;")

    metadata = {
        "submission_name": submission_context.submission_name,
        "project_name": submission_context.project_name,
        "timestamp": submission_context.timestamp.isoformat(),
        "binding_set_uuid": submission_context.binding_set_uuid,
        "change_request_name": submission_context.change_request_name,
        "non_revertible": True,
        "verify_placeholder": True,
    }
    revert_placeholder_sql = _build_revert_placeholder_sql()
    verify_placeholder_sql = _build_verify_placeholder_sql()
    metadata_artifact = {
        "artifact_type": "delivery_1_change_package",
        "deploy_statement_count": len(statements),
        "non_revertible": True,
        "verify_placeholder": True,
        "submission_name": submission_context.submission_name,
        "project_name": submission_context.project_name,
        "binding_set_uuid": submission_context.binding_set_uuid,
        "change_request_name": submission_context.change_request_name,
    }
    return DeployArtifact(
        deploy_sql="\n".join(deploy_sql_lines),
        statements=statements,
        metadata=metadata,
        revert_placeholder_sql=revert_placeholder_sql,
        verify_placeholder_sql=verify_placeholder_sql,
        metadata_artifact=metadata_artifact,
    )


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


def _render_insert_statement(table_name: str, row: pd.Series) -> str:
    """Render a single INSERT statement from a materialized row."""
    columns = [column for column in row.index if not str(column).startswith("_")]
    identifiers = ", ".join(_quote_identifier(column) for column in columns)
    values = ", ".join(_render_literal(row[column]) for column in columns)
    return f"INSERT INTO {_quote_identifier(table_name)} ({identifiers}) VALUES ({values});"


def _quote_identifier(identifier: str) -> str:
    escaped = identifier.replace('"', '""')
    return f'"{escaped}"'


def _render_literal(value: object) -> str:
    if value is None or pd.isna(value):
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
