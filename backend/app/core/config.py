"""Application configuration."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


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
    PROJECT_NAME: str = "Shape Shifter Configuration Editor"
    VERSION: str = "9.9.9"
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
    ALLOWED_ORIGIN_REGEX: str = r"https://[a-zA-Z0-9\-]+\.(euw|eus|weu|neu|sasia|asia|[a-z]+)\.devtunnels\.ms$|https://[a-zA-Z0-9\-]+\.preview\.app\.github\.dev$"

    # File paths
    CONFIGURATIONS_DIR: Path = Path("./configurations")
    BACKUPS_DIR: Path = Path("./backups")

    # Validation
    MAX_ENTITIES_PER_CONFIG: int = 1000
    MAX_CONFIG_FILE_SIZE_MB: int = 10

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure directories exist
        self.CONFIGURATIONS_DIR.mkdir(exist_ok=True)
        self.BACKUPS_DIR.mkdir(exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings: Settings = get_settings()
