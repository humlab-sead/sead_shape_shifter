"""Application configuration."""

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Import version from package
from backend.app import __version__

# pylint: disable=invalid-name

DEFAULT_APPLICATION_ROOT: Path = Path(os.getenv("SHAPE_SHIFTER_APPLICATION_ROOT", Path.cwd())).resolve()

DEFAULT_ENV_FILE: Path = Path(os.getenv("SHAPE_SHIFTER_ENV_FILE", DEFAULT_APPLICATION_ROOT / ".env")).resolve()


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=str(DEFAULT_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
        env_prefix="SHAPE_SHIFTER_",
    )
    APPLICATION_ROOT: Path = DEFAULT_APPLICATION_ROOT
    APPLICATION_NAME: str = "Shape Shifter Project Editor"
    VERSION: str = __version__
    ENVIRONMENT: Literal["development", "production", "test"] = "development"
    API_V1_PREFIX: str = "/api/v1"

    # Reverse-proxy authentication
    # Enable this in deployments where nginx authenticates the user and forwards the verified identity.
    TRUSTED_PROXY_AUTH_ENABLED: bool = False
    TRUSTED_PROXY_AUTH_HEADER: str = "X-Authenticated-User"
    DEVELOPMENT_PRINCIPAL_ID: str | None = None

    # Authorization storage and bootstrap
    AUTHORIZATION_DATABASE_PATH: Path = Path("state/authorization.sqlite3")
    AUTHORIZATION_BOOTSTRAP_ADMIN_PRINCIPALS: list[str] = []

    # CORS
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # Alternative frontend port
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]

    # Remote origins must be explicitly configured for the deployment.
    ALLOWED_ORIGIN_REGEX: str | None = None

    # File paths
    PROJECTS_DIR: Path = Path("projects")

    # Shared data paths for project portability (converted to absolute in model_post_init)
    GLOBAL_DATA_DIR: Path = Path("shared/shared-data")
    GLOBAL_DATA_SOURCE_DIR: Path = Path("shared/data-sources")

    # Logging configuration
    LOG_DIR: Path = Path("logs")
    LOG_LEVEL: str = "INFO"
    LOG_FILE_ENABLED: bool = True
    LOG_CONSOLE_ENABLED: bool = True
    LOG_ROTATION: str = "10 MB"
    LOG_RETENTION: str = "30 days"
    LOG_COMPRESSION: str = "zip"
    LOG_FILTER_FRAMEWORK_FRAMES: bool = True

    # Services
    RECONCILIATION_SERVICE_URL: str = "http://localhost:8000"
    SIMS_SERVICE_URL: str = "http://localhost:8000"  # sead_authority_service base URL for /identity endpoints

    # Suggestions
    ENABLE_FK_SUGGESTIONS: bool = False

    # Ingester configuration
    INGESTER_PATHS: list[str] = ["ingesters"]
    ENABLED_INGESTERS: list[str] | None = None  # None = all discovered ingesters

    MATERIALIZATION_INLINE_THRESHOLD: int = 20  # Rows below which data is stored inline in YAML

    @model_validator(mode="after")
    def validate_production_authentication(self) -> "Settings":
        """Require trusted-proxy authentication for production settings."""
        if self.ENVIRONMENT == "production" and not self.TRUSTED_PROXY_AUTH_ENABLED:
            raise ValueError("TRUSTED_PROXY_AUTH_ENABLED must be true in production")
        if self.ENVIRONMENT == "production" and self.DEVELOPMENT_PRINCIPAL_ID:
            raise ValueError("DEVELOPMENT_PRINCIPAL_ID is only allowed in development and test")
        if self.ENVIRONMENT == "production" and not any(
            principal_id.strip() for principal_id in self.AUTHORIZATION_BOOTSTRAP_ADMIN_PRINCIPALS
        ):
            raise ValueError("AUTHORIZATION_BOOTSTRAP_ADMIN_PRINCIPALS must include at least one administrator in production")
        return self

    @model_validator(mode="after")
    def resolve_paths(self) -> "Settings":
        """Resolve relative paths against APPLICATION_ROOT and ensure directories exist."""

        self.APPLICATION_ROOT = self.APPLICATION_ROOT.resolve()

        self.PROJECTS_DIR = self._resolve_under_root(self.PROJECTS_DIR)
        self.LOG_DIR = self._resolve_under_root(self.LOG_DIR)
        self.GLOBAL_DATA_DIR = self._resolve_under_root(self.GLOBAL_DATA_DIR)
        self.GLOBAL_DATA_SOURCE_DIR = self._resolve_under_root(self.GLOBAL_DATA_SOURCE_DIR)
        self.AUTHORIZATION_DATABASE_PATH = self._resolve_under_root(self.AUTHORIZATION_DATABASE_PATH)

        protected_directories = (
            self.PROJECTS_DIR,
            self.LOG_DIR,
            self.GLOBAL_DATA_DIR,
            self.GLOBAL_DATA_SOURCE_DIR,
        )
        if any(self.AUTHORIZATION_DATABASE_PATH.is_relative_to(directory) for directory in protected_directories):
            raise ValueError("AUTHORIZATION_DATABASE_PATH must be outside project, log, and shared-data directories")
        self.AUTHORIZATION_DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

        for path in (
            self.PROJECTS_DIR,
            self.LOG_DIR,
            self.GLOBAL_DATA_DIR,
            self.GLOBAL_DATA_SOURCE_DIR,
        ):
            path.mkdir(parents=True, exist_ok=True)

        return self

    def _resolve_under_root(self, value: Path) -> Path:
        """Resolve a path against the repository root when it is relative."""
        path = Path(value)
        if path.is_absolute():
            return path
        return (self.APPLICATION_ROOT / path).resolve()

    @property
    def env_prefix(self) -> str:
        """Get full environment variable name with prefix."""
        return self.model_config.get("env_prefix", "")

    @property
    def env_file(self) -> str:
        """Get full environment variable name with prefix."""
        return str(self.model_config.get("env_file", ""))

    @property
    def projects_root(self) -> Path:
        """Get projects root directory path."""
        return self.PROJECTS_DIR

    @property
    def application_root(self) -> Path:
        """Get application root directory path."""
        return self.APPLICATION_ROOT

    @property
    def global_data_dir(self) -> Path:
        """Get global data directory path."""
        return self.GLOBAL_DATA_DIR

    @property
    def global_data_source_dir(self) -> Path:
        """Get global data source directory path."""
        return self.GLOBAL_DATA_SOURCE_DIR

    @property
    def env_opts(self) -> dict[str, str]:
        """Get environment options."""
        return {
            "env_file": self.env_file,
            "env_prefix": self.env_prefix,
            "runtime_root": str(self.APPLICATION_ROOT),
            "application_root_env_var": "APPLICATION_ROOT",
        }

    @property
    def reconciliation_service_url(self) -> str:
        """Get reconciliation service URL."""
        return self.RECONCILIATION_SERVICE_URL

    def enable_fk_suggestions(self) -> None:
        """Check if foreign key suggestions are enabled."""
        self.ENABLE_FK_SUGGESTIONS = True

    def disable_fk_suggestions(self) -> None:
        """Disable foreign key suggestions."""
        self.ENABLE_FK_SUGGESTIONS = False


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings: Settings = get_settings()
