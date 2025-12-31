"""Pydantic models for API requests and responses."""

from tkinter import E

from backend.app.models.data_source import (
    ColumnMetadata,
    DataSourceConfig,
    DataSourceStatus,
    DataSourceTestResult,
    ForeignKeyMetadata,
    TableMetadata,
    TableSchema,
)
from backend.app.models.driver_schema import (
    DriverSchemaResponse,
    FieldMetadataResponse,
)
from backend.app.models.entity import (
    AppendConfig,
    Entity,
    FilterConfig,
    ForeignKeyConfig,
    ForeignKeyConstraints,
    UnnestConfig,
)
from backend.app.models.entity_import import (
    EntityImportRequest,
    EntityImportResult,
    KeySuggestion,
)
from backend.app.models.fix import (
    FixAction,
    FixActionType,
    FixResult,
    FixSuggestion,
)
from backend.app.models.join_test import (
    CardinalityInfo,
    JoinStatistics,
    JoinTestError,
    JoinTestRequest,
    JoinTestResult,
    UnmatchedRow,
)
from backend.app.models.project import (
    Project,
    ProjectMetadata,
)
from backend.app.models.query import (
    QueryExecution,
    QueryPlan,
    QueryResult,
    QueryValidation,
)
from backend.app.models.reconciliation import (
    AutoReconcileResult,
    EntityReconciliationSpec,
    ReconciliationCandidate,
    ReconciliationConfig,
    ReconciliationMapping,
    ReconciliationSource,
)
from backend.app.models.shapeshift import (
    ColumnInfo,
    EntityPreviewError,
    PreviewRequest,
    PreviewResult,
)
from backend.app.models.suggestion import (
    DependencySuggestion,
    EntitySuggestions,
    ForeignKeySuggestion,
    SuggestionsRequest,
)
from backend.app.models.test_run import (
    EntityTestResult,
    OutputFormat,
    TestProgress,
    TestRunOptions,
    TestRunResult,
    TestRunStatus,
    ValidationIssue,
)
from backend.app.models.validation import (
    ValidationCategory,
    ValidationError,
    ValidationPriority,
    ValidationResult,
)
