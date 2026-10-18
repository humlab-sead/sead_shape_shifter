"""Read-only access to the curated data provider registry.

The registry is a directory of reviewed YAML files, one file per data provider. The
service reads the whole directory on every call so a malformed file cannot disappear
from a partial result. It never writes provider records and never expands directives
or environment variables, because the stored values are literal contracts.
"""

from pathlib import Path

import yaml
from loguru import logger
from pydantic import ValidationError

from backend.app.models.data_provider import DataProvider, DataProviderSchema


class DataProviderRegistryError(RuntimeError):
    """Raised when the provider registry cannot be read or is not valid."""


class DataProviderService:
    """Reads provider records from a directory of reviewed YAML files."""

    def __init__(self, providers_dir: Path | str) -> None:
        """Store the configured registry directory."""
        self.providers_dir: Path = Path(providers_dir)

    def list_providers(self) -> list[DataProvider]:
        """Return every provider with its schemas sorted by provider and schema code."""
        return self._load_registry()

    def get_scope(self, code: str, provider_schema: str) -> DataProviderSchema | None:
        """Return the registered scope for one provider-schema pair, or None when it is not registered.

        The complete registry is validated first, so an unregistered pair is only
        reported after the directory is known to be valid.
        """
        for provider in self._load_registry():
            if provider.code != code:
                continue
            for schema in provider.schemas:
                if schema.provider_schema == provider_schema:
                    return schema
        return None

    def _load_registry(self) -> list[DataProvider]:
        """Load and validate every provider file, rejecting the whole registry on any fault."""
        directory = self.providers_dir
        if not directory.is_dir():
            error = DataProviderRegistryError(f"Data provider directory is missing or unreadable: {directory}")
            logger.error(str(error))
            raise error

        providers: list[DataProvider] = []
        provider_files: dict[str, Path] = {}
        scope_names: dict[str, Path] = {}

        for file_path in sorted(directory.glob("*.yml")):
            provider = self._read_provider_file(file_path)
            if provider.code in provider_files:
                error = DataProviderRegistryError(
                    f"Duplicate data provider code '{provider.code}' in {file_path} and {provider_files[provider.code]}"
                )
                logger.error(str(error))
                raise error
            provider_files[provider.code] = file_path

            for schema in provider.schemas:
                if schema.scope_name in scope_names:
                    error = DataProviderRegistryError(
                        f"Duplicate scope name '{schema.scope_name}' in {file_path} and {scope_names[schema.scope_name]}"
                    )
                    logger.error(str(error))
                    raise error
                scope_names[schema.scope_name] = file_path

            providers.append(provider.model_copy(update={"schemas": sorted(provider.schemas, key=lambda item: item.provider_schema)}))

        logger.debug(f"Read {len(providers)} data provider record(s) from {directory}")
        return sorted(providers, key=lambda provider: provider.code)

    def _read_provider_file(self, file_path: Path) -> DataProvider:
        """Read one provider file, translating read, YAML, and model faults into a registry error."""
        try:
            raw_text = file_path.read_text(encoding="utf-8")
        except OSError as exc:
            error = DataProviderRegistryError(f"Data provider file is unreadable: {file_path}")
            logger.error(str(error))
            raise error from exc

        try:
            data = yaml.safe_load(raw_text)
        except yaml.YAMLError as exc:
            error = DataProviderRegistryError(f"Data provider file is not valid YAML: {file_path}")
            logger.error(f"{error}: {exc}")
            raise error from exc

        if not isinstance(data, dict):
            error = DataProviderRegistryError(f"Data provider file must contain a mapping: {file_path}")
            logger.error(str(error))
            raise error

        try:
            return DataProvider.model_validate(data)
        except ValidationError as exc:
            error = DataProviderRegistryError(f"Data provider file is invalid: {file_path}: {exc}")
            logger.error(str(error))
            raise error from exc
