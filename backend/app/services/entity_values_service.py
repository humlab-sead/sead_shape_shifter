"""Service for managing external entity values (parquet/csv files)."""

import hashlib
from os import stat_result
from pathlib import Path
from typing import Any

import pandas as pd
from loguru import logger

from backend.app.mappers.project_mapper import ProjectMapper
from backend.app.middleware.correlation import get_correlation_id
from backend.app.models.mapping_sync import MappingSyncPending
from backend.app.models.project import Project
from backend.app.services.fixed_entity_mapping_change_service import (
    FixedEntityMappingChangeService,
    get_fixed_entity_mapping_change_service,
)
from backend.app.services.fixed_entity_mapping_sync_service import FixedEntityMappingSyncService
from backend.app.services.project_service import ProjectService, get_project_service
from backend.app.utils.fixed_schema import build_legacy_fixed_full_columns, derive_fixed_schema
from src.path_resolution import resolve_contained_path
from src.reconciliation.fixed_entity_mapping_changes import RowSnapshot
from src.types.fixed_entity_types import normalize_fixed_entity_column_types, resolve_fixed_entity_column_type


def _normalized_isnan_values(df: pd.DataFrame) -> list[list[object]]:
    """Convert pandas extension dtypes / nullable values to Python objects
    Replace pd.NA, np.nan, pd.NaT with None for JSON serialization and consistent API behavior."""
    return df.astype(object).where(pd.notna(df), None).values.tolist()


class EntityValuesData:
    """Response containing entity values data."""

    def __init__(
        self,
        columns: list[str],
        values: list[list[Any]],
        format: str,  # pylint: disable=redefined-builtin
        row_count: int,
        etag: str,
        mapping_sync: MappingSyncPending | None = None,
    ):
        self.columns: list[str] = columns
        self.values: list[list[Any]] = values
        self.format: str = format
        self.row_count: int = row_count
        self.etag: str = etag
        self.mapping_sync: MappingSyncPending | None = mapping_sync


class EntityValuesService:
    """Manage external entity values (parquet/csv files)."""

    def __init__(
        self,
        project_service: ProjectService | None = None,
        mapping_change_service: FixedEntityMappingChangeService | None = None,
        mapping_sync_service: FixedEntityMappingSyncService | None = None,
    ):
        """Initialize service with optional project service dependency injection."""
        self.project_service: ProjectService = project_service or get_project_service()
        self.mapping_change_service: FixedEntityMappingChangeService = mapping_change_service or get_fixed_entity_mapping_change_service()
        self.mapping_sync_service = mapping_sync_service or FixedEntityMappingSyncService(self.mapping_change_service.manager)

    def _generate_etag(self, file_path: Path) -> str:
        """
        Generate etag for file based on mtime and size.

        Args:
            file_path: Path to values file

        Returns:
            Etag string (hex hash of mtime+size)
        """
        stat: stat_result = file_path.stat()
        etag_input: str = f"{stat.st_mtime}:{stat.st_size}"
        return hashlib.md5(etag_input.encode()).hexdigest()

    def _validate_etag(self, file_path: Path, expected_etag: str) -> bool:
        """
        Validate etag matches current file state.

        Args:
            file_path: Path to values file
            expected_etag: Expected etag from client

        Returns:
            True if etag matches, False otherwise
        """
        current_etag: str = self._generate_etag(file_path)
        return current_etag == expected_etag

    def _parse_load_directive(self, values: Any) -> str | None:
        """
        Extract filename from @load: directive.

        Args:
            values: Entity values field (can be string or array)

        Returns:
            Filename if @load: directive found, None otherwise
        """
        if isinstance(values, str) and values.startswith("@load:"):
            return values[6:].strip()  # Strip "@load:" prefix
        return None

    def _resolve_values_path(self, project_name: str, filename: str) -> Path:
        """
        Resolve full path to values file.

        Args:
            project_name: Project name
            filename: Filename from @load: directive (e.g., "materialized/feature_type.parquet")

        Returns:
            Full path to values file
        """
        project: Project = self.project_service.load_project(project_name)
        try:
            return resolve_contained_path(filename, project.folder)
        except ValueError as exc:
            raise ValueError(f"Values file path is outside project '{project_name}'") from exc

    def _resolve_project_path(self, project_name: str) -> str | None:
        """Return the project file path used to load the mapping sidecar."""
        project: Project = self.project_service.load_project(project_name)
        return project.filename

    def _load_previous_fixed_rows(
        self,
        file_path: Path,
        entity_name: str,
        entity_data: dict[str, Any],
    ) -> tuple[list[str], list[list[Any]]]:
        """Return the previously stored fixed rows in canonical order, or empty.

        A not-yet-created values file yields an empty prior snapshot so the
        comparison treats every written row as an addition.
        """
        if not file_path.exists():
            return [], []
        columns, values, _format_type, _etag = self._read_values_file(file_path)
        return self._normalize_fixed_stored_values(entity_name, entity_data, columns, values)

    def _read_values_file(self, file_path: Path) -> tuple[list[str], list[list[Any]], str, str]:
        """
        Read values from parquet or CSV file.

        Args:
            file_path: Path to values file

        Returns:
            Tuple of (columns, values, format, etag)

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format not supported
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Values file not found: {file_path}")

        suffix: str = file_path.suffix.lower()

        if suffix == ".parquet":
            df: pd.DataFrame = pd.read_parquet(file_path)
            format_type = "parquet"
        elif suffix in (".csv", ".tsv"):
            df = pd.read_csv(file_path)
            format_type = "csv"
        else:
            raise ValueError(f"Unsupported file format: {suffix}")

        # Convert DataFrame to list[list] format
        columns: list[str] = df.columns.tolist()
        values: list[list[Any]] = _normalized_isnan_values(df)

        # Generate etag
        etag: str = self._generate_etag(file_path)

        return columns, values, format_type, etag

    @staticmethod
    def _build_dataframe_for_storage(
        columns: list[str],
        values: list[list[Any]],
        column_types: dict[str, str] | None = None,
    ) -> pd.DataFrame:
        """Build a dataframe with stable dtypes for fixed-entity sidecar storage."""
        column_index = pd.Index(columns)

        if not column_types:
            return pd.DataFrame(values, columns=pd.Index(columns))

        normalized_column_types = normalize_fixed_entity_column_types("<external_values>", columns, column_types)
        series_map: dict[str, pd.Series] = {}

        for idx, column in enumerate(columns):
            column_values = [row[idx] for row in values]
            target_type: str = resolve_fixed_entity_column_type(column, normalized_column_types)

            if target_type == "int":
                series_map[column] = pd.Series(pd.array(column_values, dtype="Int64"), name=column)
            elif target_type == "float":
                series_map[column] = pd.Series(pd.array(column_values, dtype="Float64"), name=column)
            elif target_type == "bool":
                series_map[column] = pd.Series(pd.array(column_values, dtype="boolean"), name=column)
            elif target_type in {"date", "string"}:
                series_map[column] = pd.Series(pd.array(column_values, dtype="string"), name=column)
            else:
                series_map[column] = pd.Series(column_values, name=column)

        return pd.DataFrame(series_map, columns=column_index)

    def _write_values_file(
        self,
        file_path: Path,
        columns: list[str],
        values: list[list[Any]],
        format_type: str | None,
        column_types: dict[str, str] | None = None,
    ) -> str:
        """
        Write values to parquet or CSV file.

        Args:
            file_path: Path to values file
            columns: Column names
            values: Row data
            format_type: Storage format (parquet/csv) or None to infer from file_path

        Returns:
            Actual format used
        """
        # Infer format from file extension if not specified
        if format_type is None:
            suffix: str = file_path.suffix.lower()
            format_type = "parquet" if suffix == ".parquet" else "csv"

        # Validate shape before creating directories or handing off to pandas for clearer API errors.
        self._validate_values_shape(columns=columns, values=values)

        # Create parent directory if it doesn't exist
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert list[list] to DataFrame using stable dtypes when column types are known.
        df = self._build_dataframe_for_storage(columns, values, column_types)

        # Write based on format
        if format_type == "parquet":
            df.to_parquet(file_path, index=False)
        else:  # csv
            df.to_csv(file_path, index=False)

        logger.info(f"Wrote {len(values)} rows to {file_path} ({format_type})")
        return format_type

    def _validate_values_shape(self, columns: list[str], values: list[list[Any]]) -> None:
        """Validate that each row width matches the declared columns."""
        expected_width: int = len(columns)

        for idx, row in enumerate(values):
            if not isinstance(row, list):
                raise ValueError(f"Invalid values payload at row {idx}: expected list, got {type(row).__name__}")

            actual_width: int = len(row)
            if actual_width != expected_width:
                raise ValueError(
                    "Column/value width mismatch: "
                    f"expected {expected_width} columns ({columns}), "
                    f"but row {idx} has {actual_width} values"
                )

    @staticmethod
    def _normalize_fixed_request_columns(
        entity_name: str,
        entity_data: dict[str, Any],
        columns: list[str],
    ) -> list[str]:
        """Resolve the authoritative fixed column order for an incoming values request.

        Accepts the authoritative order or the exact recognized legacy order and
        rejects unknown, duplicate, or incomplete column names. Non-fixed
        entities are returned unchanged.
        """
        fixed_schema = derive_fixed_schema(entity_data)
        if not fixed_schema:
            return list(columns)

        full_columns: list[str] = list(fixed_schema["full_columns"])

        missing_keys: list[str] = [key for key in fixed_schema["key_columns"] if key not in full_columns]
        if missing_keys:
            raise ValueError(
                f"Fixed entity '{entity_name}' has business key(s) {missing_keys} that are not produced; "
                f"expected positional column order: {full_columns}"
            )

        if not all(isinstance(column, str) for column in columns):
            raise ValueError(f"Fixed entity '{entity_name}' values request must use string column names; received {columns}")

        if len(set(columns)) != len(columns):
            raise ValueError(f"Fixed entity '{entity_name}' values request has duplicate column names; received {columns}")

        legacy_columns: list[str] = build_legacy_fixed_full_columns(entity_data)
        if columns != full_columns and columns != legacy_columns:
            raise ValueError(
                f"Fixed entity '{entity_name}' must update values using the expected positional column order "
                f"{full_columns}; received {columns}"
            )

        if set(columns) != set(full_columns):
            unknown_columns: list[str] = sorted(set(columns) - set(full_columns))
            missing_columns: list[str] = sorted(set(full_columns) - set(columns))
            raise ValueError(
                f"Fixed entity '{entity_name}' values request columns do not match produced fields; "
                f"unknown {unknown_columns}, missing {missing_columns}; expected positional column order: {full_columns}"
            )

        return full_columns

    @staticmethod
    def _reorder_rows_by_name(
        request_columns: list[str],
        target_columns: list[str],
        values: list[list[Any]],
    ) -> list[list[Any]]:
        """Reorder row cells to the target column order by matching column names."""
        if request_columns == target_columns:
            return values

        index_by_name: dict[str, int] = {column: index for index, column in enumerate(request_columns)}
        return [[row[index_by_name[column]] for column in target_columns] for row in values]

    @staticmethod
    def _normalize_fixed_stored_values(
        entity_name: str,
        entity_data: dict[str, Any],
        columns: list[str],
        values: list[list[Any]],
    ) -> tuple[list[str], list[list[Any]]]:
        """Return stored fixed values in the authoritative order without writing the file."""
        fixed_schema = derive_fixed_schema(entity_data)
        if not fixed_schema:
            return list(columns), values

        full_columns: list[str] = list(fixed_schema["full_columns"])
        if columns == full_columns:
            return full_columns, values

        if len(set(columns)) != len(columns) or set(columns) != set(full_columns):
            missing_columns: list[str] = sorted(set(full_columns) - set(columns))
            raise ValueError(
                f"Fixed entity '{entity_name}' stored values use columns {columns} that do not match the expected "
                f"positional column order {full_columns}; missing fields: {missing_columns}"
            )

        return full_columns, EntityValuesService._reorder_rows_by_name(columns, full_columns, values)

    def get_values(self, project_name: str, entity_name: str) -> EntityValuesData:
        """
        Get external values for entity with @load: directive.

        Args:
            project_name: Project name
            entity_name: Entity name

        Returns:
            Entity values response

        Raises:
            ValueError: If entity doesn't have @load: directive
            FileNotFoundError: If values file not found
        """
        # Load entity config
        entity_data: dict[str, Any] = self.project_service.get_entity_by_name(project_name, entity_name)
        values_field: Any | None = entity_data.get("values")

        # Parse @load: directive
        filename: str | None = self._parse_load_directive(values_field)
        if not filename:
            raise ValueError(f"Entity '{entity_name}' does not have @load: directive (values: {values_field})")

        # Resolve file path
        file_path: Path = self._resolve_values_path(project_name, filename)
        logger.debug(f"Loading values from {file_path}")

        # Read file and present fixed values in the authoritative column order without writing.
        columns, values, format_type, etag = self._read_values_file(file_path)
        columns, values = self._normalize_fixed_stored_values(entity_name, entity_data, columns, values)

        return EntityValuesData(columns=columns, values=values, format=format_type, row_count=len(values), etag=etag)

    def update_values(
        self,
        project_name: str,
        entity_name: str,
        columns: list[str],
        values: list[list[Any]],
        format_type: str | None = None,
        if_match: str | None = None,
        column_types: dict[str, str] | None = None,
    ) -> EntityValuesData:
        """Update external values and mapping links under the project lock."""
        with self.project_service._get_lock(project_name):
            return self._update_values_locked(
                project_name,
                entity_name,
                columns,
                values,
                format_type=format_type,
                if_match=if_match,
                column_types=column_types,
            )

    def _update_values_locked(
        self,
        project_name: str,
        entity_name: str,
        columns: list[str],
        values: list[list[Any]],
        format_type: str | None = None,
        if_match: str | None = None,
        column_types: dict[str, str] | None = None,
    ) -> EntityValuesData:
        """
        Update external values for entity with @load: directive.

        Args:
            project_name: Project name
            entity_name: Entity name
            columns: Column names
            values: Row data
            format_type: Preferred storage format (parquet/csv) or None to keep existing
            if_match: Expected etag for optimistic locking (optional)

        Returns:
            Entity values response

        Raises:
            ValueError: If entity doesn't have @load: directive or if etag mismatch (409)
        """
        # Load entity config
        entity_data: dict[str, Any] = self.project_service.get_entity_by_name(project_name, entity_name)
        values_field: Any | None = entity_data.get("values")

        # Parse @load: directive
        filename: str | None = self._parse_load_directive(values_field)
        if not filename:
            raise ValueError(f"Entity '{entity_name}' does not have @load: directive (values: {values_field})")

        # Validate and normalize the request before any file write or directory creation.
        self._validate_values_shape(columns=columns, values=values)
        normalized_columns: list[str] = EntityValuesService._normalize_fixed_request_columns(entity_name, entity_data, columns)
        normalized_values: list[list[Any]] = EntityValuesService._reorder_rows_by_name(columns, normalized_columns, values)

        # Resolve file path
        file_path: Path = self._resolve_values_path(project_name, filename)

        # Validate etag if provided (optimistic locking)
        if if_match is not None and file_path.exists():
            if not self._validate_etag(file_path, if_match):
                current_etag: str = self._generate_etag(file_path)
                raise ValueError(f"ETag mismatch: expected '{if_match}', current '{current_etag}' (409 Conflict)")

        # Validate fixed-row mapping inputs against the stored rows before any write.
        # Raises ValueError, which the route maps to HTTP 422, so no file or
        # directory is created after a mapping-validation failure.
        change_set = None
        mapping_snapshot = None
        project_path = self._resolve_project_path(project_name)
        if derive_fixed_schema(entity_data):
            previous_columns, previous_values = self._load_previous_fixed_rows(file_path, entity_name, entity_data)
            if isinstance(project_path, str) and project_path:
                mapping_snapshot = self.mapping_sync_service.load_snapshot(project_path)
            change_set = self.mapping_change_service.compute_change_set(
                entity_name=entity_name,
                project_path=project_path,
                entity_config=entity_data,
                previous_columns=previous_columns,
                previous_values=previous_values,
                current_columns=normalized_columns,
                current_values=normalized_values,
                mapping_catalog=mapping_snapshot.catalog if mapping_snapshot is not None else None,
            )
            if not isinstance(project_path, str) or not project_path:
                raise ValueError(f"Cannot save fixed entity '{entity_name}' because its project file path is missing")

        logger.info(f"Updating values at {file_path}")

        # Write file
        actual_format: str = self._write_values_file(file_path, normalized_columns, normalized_values, format_type, column_types)

        # Generate new etag after write
        new_etag: str = self._generate_etag(file_path)

        # Rows are persisted. A sidecar write failure becomes a pending result
        # with a retryable mapping_sync payload instead of a failed request.
        mapping_sync: MappingSyncPending | None = None
        if change_set is not None and mapping_snapshot is not None and project_path:
            sync_result = self.mapping_sync_service.apply_change_set(
                change_set=change_set,
                snapshot=mapping_snapshot,
                project_path=project_path,
                row_version=new_etag,
                created_by=get_correlation_id(),
            )
            if sync_result.error is not None:
                mapping_sync = ProjectMapper.fixed_change_set_to_pending(
                    change_set,
                    project=project_name,
                    entity=entity_name,
                    storage_kind="external",
                    row_version=sync_result.row_version,
                    sidecar_version=sync_result.sidecar_version,
                )

        return EntityValuesData(
            columns=normalized_columns,
            values=normalized_values,
            format=actual_format,
            row_count=len(normalized_values),
            etag=new_etag,
            mapping_sync=mapping_sync,
        )

    def load_saved_fixed_snapshot(self, project_name: str, entity_name: str) -> RowSnapshot:
        """Read the currently saved external fixed rows for retry comparison.

        The caller must hold the project lock. Returns an empty snapshot when the
        values file does not exist yet so every written row counts as an addition.
        """
        entity_data: dict[str, Any] = self.project_service.get_entity_by_name(project_name, entity_name)
        filename: str | None = self._parse_load_directive(entity_data.get("values"))
        if not filename:
            raise ValueError(f"Entity '{entity_name}' does not have @load: directive (values: {entity_data.get('values')})")
        file_path: Path = self._resolve_values_path(project_name, filename)
        columns, values = self._load_previous_fixed_rows(file_path, entity_name, entity_data)
        return RowSnapshot(columns=list(columns), values=[list(row) for row in values])


def get_entity_values_service() -> EntityValuesService:
    """Get entity values service instance (dependency injection)."""
    return EntityValuesService()
