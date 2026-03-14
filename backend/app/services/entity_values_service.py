"""Service for managing external entity values (parquet/csv files)."""

import hashlib
from os import stat_result
from pathlib import Path
from typing import Any

import pandas as pd
from loguru import logger

from backend.app.models.project import Project
from backend.app.services.project_service import ProjectService, get_project_service
from backend.app.utils.fixed_schema import derive_fixed_schema


class EntityValuesResponse:
    """Response containing entity values data."""

    def __init__(
        self,
        columns: list[str],
        values: list[list[Any]],
        format: str,  # pylint: disable=redefined-builtin
        row_count: int,
        etag: str,
    ):
        self.columns: list[str] = columns
        self.values: list[list[Any]] = values
        self.format: str = format
        self.row_count: int = row_count
        self.etag: str = etag


class EntityValuesService:
    """Manage external entity values (parquet/csv files)."""

    def __init__(self, project_service: ProjectService | None = None):
        """Initialize service with optional project service dependency injection."""
        self.project_service: ProjectService = project_service or get_project_service()

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
        return project.folder / filename

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
        values: list[list[Any]] = df.values.tolist()

        # Generate etag
        etag: str = self._generate_etag(file_path)

        return columns, values, format_type, etag

    def _write_values_file(self, file_path: Path, columns: list[str], values: list[list[Any]], format_type: str | None) -> str:
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
        # Create parent directory if it doesn't exist
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Infer format from file extension if not specified
        if format_type is None:
            suffix: str = file_path.suffix.lower()
            format_type = "parquet" if suffix == ".parquet" else "csv"

        # Validate shape before handing off to pandas for clearer API errors.
        self._validate_values_shape(columns=columns, values=values)

        # Convert list[list] to DataFrame
        df = pd.DataFrame(values, columns=columns)

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

    def _validate_fixed_columns(self, entity_name: str, entity_data: dict[str, Any], columns: list[str]) -> None:
        """Require fixed-entity updates to use the authoritative full column order."""
        fixed_schema = derive_fixed_schema(entity_data)
        if not fixed_schema:
            return

        expected_columns: list[str] = fixed_schema["full_columns"]
        if columns != expected_columns:
            raise ValueError(
                f"Fixed entity '{entity_name}' must update values using authoritative columns {expected_columns}; " f"received {columns}"
            )

    def get_values(self, project_name: str, entity_name: str) -> EntityValuesResponse:
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

        # Read file
        columns, values, format_type, etag = self._read_values_file(file_path)

        return EntityValuesResponse(columns=columns, values=values, format=format_type, row_count=len(values), etag=etag)

    def update_values(
        self,
        project_name: str,
        entity_name: str,
        columns: list[str],
        values: list[list[Any]],
        format_type: str | None = None,
        if_match: str | None = None,
    ) -> EntityValuesResponse:
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

        self._validate_fixed_columns(entity_name, entity_data, columns)

        # Resolve file path
        file_path: Path = self._resolve_values_path(project_name, filename)

        # Validate etag if provided (optimistic locking)
        if if_match is not None and file_path.exists():
            if not self._validate_etag(file_path, if_match):
                current_etag: str = self._generate_etag(file_path)
                raise ValueError(f"ETag mismatch: expected '{if_match}', current '{current_etag}' (409 Conflict)")

        logger.info(f"Updating values at {file_path}")

        # Write file
        actual_format: str = self._write_values_file(file_path, columns, values, format_type)

        # Generate new etag after write
        new_etag: str = self._generate_etag(file_path)

        return EntityValuesResponse(columns=columns, values=values, format=actual_format, row_count=len(values), etag=new_etag)


def get_entity_values_service() -> EntityValuesService:
    """Get entity values service instance (dependency injection)."""
    return EntityValuesService()
