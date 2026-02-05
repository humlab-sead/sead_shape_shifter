"""Application configuration."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

# Import version from package
from backend.app import __version__

# pylint: disable=invalid-name


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
        env_prefix="SHAPE_SHIFTER_",
    )
    PROJECT_ROOT: Path = Path(__file__).parent.parent.parent
    PROJECT_NAME: str = "Shape Shifter Project Editor"
    VERSION: str = __version__
    ENVIRONMENT: Literal["development", "production", "test"] = "development"
    API_V1_PREFIX: str = "/api/v1"

    # CORS
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # Alternative frontend port
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "https://tgx7q4bq-5173.euw.devtunnels.ms",  # DevTunnels frontend
        "https://tgx7q4bq-8012.euw.devtunnels.ms",  # DevTunnels backend
    ]

    # CORS regex patterns for wildcard domains (allows any devtunnel or github dev preview)
    # Pattern matches: https://anything-port.region.devtunnels.ms
    ALLOWED_ORIGIN_REGEX: str = (
        r"https://[a-zA-Z0-9\-]+\.(euw|eus|weu|neu|sasia|asia|[a-z]+)\.devtunnels\.ms$|https://[a-zA-Z0-9\-]+\.preview\.app\.github\.dev$"
    )

    # File paths
    PROJECTS_DIR: Path = Path("./projects")
    BACKUPS_DIR: Path = Path("./backups")
    LOGS_DIR: Path = Path("./logs")
    LOG_DIR: Path = LOGS_DIR  # Alias for backward compatibility

    # Logging configuration
    LOG_LEVEL: str = "INFO"
    LOG_FILE_ENABLED: bool = True
    LOG_CONSOLE_ENABLED: bool = True
    LOG_ROTATION: str = "10 MB"
    LOG_RETENTION: str = "30 days"
    LOG_COMPRESSION: str = "zip"

    # Services
    RECONCILIATION_SERVICE_URL: str = "http://localhost:8000"

    # Suggestions
    ENABLE_FK_SUGGESTIONS: bool = False

    # Ingester configuration
    INGESTER_PATHS: list[str] = ["ingesters"]
    ENABLED_INGESTERS: list[str] | None = None  # None = all discovered ingesters

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure directories exist
        self.PROJECTS_DIR.mkdir(exist_ok=True)
        self.BACKUPS_DIR.mkdir(exist_ok=True)
        self.LOGS_DIR.mkdir(exist_ok=True)

    @property
    def env_prefix(self) -> str:
        """Get full environment variable name with prefix."""
        return self.model_config.get("env_prefix", "")

    @property
    def env_file(self) -> str:
        """Get full environment variable name with prefix."""
        return str(self.model_config.get("env_file", ""))

    @property
    def projects_dir(self) -> Path:
        """Get configurations directory path."""
        return self.PROJECTS_DIR

    @property
    def project_root(self) -> Path:
        """Get project root directory path."""
        return self.PROJECT_ROOT

    @property
    def env_opts(self) -> dict[str, str]:
        """Get environment options."""
        return {"env_file": self.env_file, "env_prefix": self.env_prefix}

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
