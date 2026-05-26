"""SEAD change request ingester implementation."""

from ingesters.sead_change_request.collision_checks import CollisionCheckResult, check_materialized_collisions
from ingesters.sead_change_request.contracts import (
    ChangeRequestPackage,
    ChangeRequestTable,
    ChangeRowState,
    DeployArtifact,
    IdentityAssignment,
    IdentityResolutionResult,
    IdentityWorkPlan,
    MaterializationResult,
    MaterializedTable,
    PendingConfirmationReport,
    PlannedRowAction,
    PlannedTable,
    ResolvedIdentityTable,
    SourceTableBundle,
    SubmissionContext,
)
from ingesters.sead_change_request.identity_resolution import resolve_planned_tables
from ingesters.sead_change_request.identity_work import build_identity_work_plan
from ingesters.sead_change_request.ingester import SeadChangeRequestIngester
from ingesters.sead_change_request.materialization import materialize_resolved_tables
from ingesters.sead_change_request.orchestration import IdentityOrchestrationResult, orchestrate_identity_assignments
from ingesters.sead_change_request.package_builder import build_change_request_package
from ingesters.sead_change_request.planning import plan_table
from ingesters.sead_change_request.sql_builder import (
    COPY_CSV_DEPLOY_ARTIFACT_STRATEGY,
    DEFAULT_DEPLOY_ARTIFACT_STRATEGY,
    CopyCsvDeployStrategy,
    DeployArtifactStrategy,
    InlineInsertDeployStrategy,
    build_deploy_artifact,
    resolve_deploy_artifact_strategy,
)

__all__ = [
    "ChangeRequestPackage",
    "ChangeRequestTable",
    "ChangeRowState",
    "CollisionCheckResult",
    "COPY_CSV_DEPLOY_ARTIFACT_STRATEGY",
    "DEFAULT_DEPLOY_ARTIFACT_STRATEGY",
    "CopyCsvDeployStrategy",
    "DeployArtifact",
    "DeployArtifactStrategy",
    "IdentityAssignment",
    "IdentityOrchestrationResult",
    "IdentityResolutionResult",
    "IdentityWorkPlan",
    "MaterializationResult",
    "MaterializedTable",
    "PendingConfirmationReport",
    "PlannedRowAction",
    "PlannedTable",
    "ResolvedIdentityTable",
    "SeadChangeRequestIngester",
    "SourceTableBundle",
    "SubmissionContext",
    "InlineInsertDeployStrategy",
    "build_change_request_package",
    "build_deploy_artifact",
    "check_materialized_collisions",
    "materialize_resolved_tables",
    "orchestrate_identity_assignments",
    "resolve_planned_tables",
    "build_identity_work_plan",
    "plan_table",
    "resolve_deploy_artifact_strategy",
]
