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
    )

    # Application
    PROJECT_NAME: str = "Shape Shifter Configuration Editor"
    VERSION: str = "0.1.0"
    ENVIRONMENT: Literal["development", "production", "test"] = "development"
    API_V1_PREFIX: str = "/api/v1"

    # CORS
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # Alternative frontend port
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]
    
    # CORS regex patterns for wildcard domains
    ALLOWED_ORIGIN_REGEX: str = r"https://.*\.(preview\.app\.github\.dev|devtunnels\.ms)"

    # File paths
    PROJECT_ROOT: Path = Path(__file__).parent.parent.parent.parent
    CONFIGURATIONS_DIR: Path = PROJECT_ROOT / "input"
    BACKUPS_DIR: Path = PROJECT_ROOT / "backups"

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


settings = get_settings()
