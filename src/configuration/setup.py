import os

import dotenv
import psycopg
from loguru import logger

from src.utility import configure_logging, create_db_uri

from .interface import ConfigLike
from .provider import ConfigStore, get_config_provider

dotenv.load_dotenv(dotenv_path=os.getenv("ENV_FILE", ".env"))


async def setup_config_store(
    filename: str | None = None,
    force: bool = False,
    env_prefix="SEAD_AUTHORITY",
    env_filename=".env",
    db_opts_path: str | None = "options:database",
) -> None:

    config_file: str | None = filename or os.getenv("CONFIG_FILE", "config.yml")

    store: ConfigStore = ConfigStore.get_instance()

    if store.is_configured() and not force:
        return

    store.configure_context(source=config_file, env_filename=env_filename, env_prefix=env_prefix)
    assert store.is_configured(), "Config Store failed to configure properly"

    cfg: ConfigLike | None = store.config()
    if not cfg:
        raise ValueError("Config Store did not return a config")

    cfg.update({"runtime:config_file": config_file, "runtime:env_file": env_filename})

    configure_logging(cfg.get("logging") or {})

    if db_opts_path:
        if not cfg.get(db_opts_path):
            logger.warning(f"Database options not found in default config at path '{db_opts_path}'")
        else:
            await _setup_connection_factory(cfg, db_opts_path=db_opts_path)

    logger.info("Config Store initialized successfully.")


async def connection_factory(cfg: ConfigLike, db_opts_path: str) -> psycopg.AsyncConnection:
    dsn: str = create_db_uri(**cfg.get(db_opts_path))
    if cfg.get("runtime:connection") is None:
        logger.info("Creating new database connection")
        con = await psycopg.AsyncConnection.connect(dsn)
        cfg.update({"runtime:connection": con})
        return con
    return cfg.get("runtime:connection")


async def _setup_connection_factory(cfg: ConfigLike, db_opts_path: str) -> None:
    dsn: str = create_db_uri(**cfg.get(db_opts_path))

    if not dsn:
        raise ValueError("Database DSN is not configured properly")

    cfg.update(
        {
            "runtime:connection": None,
            "runtime:dsn": dsn,
            "runtime:connection_factory": lambda: connection_factory(cfg, db_opts_path=db_opts_path),
        }
    )


async def get_connection() -> psycopg.AsyncConnection:
    """Get a database connection from the config"""
    cfg: ConfigLike = get_config_provider().get_config()
    if not cfg:
        raise ValueError("Config Store is not configured")
    if not cfg.get("runtime:connection"):
        _connection_factory = cfg.get("runtime:connection_factory")
        if not _connection_factory:
            raise ValueError("Connection factory is not configured")
        connection = await _connection_factory()
        cfg.update({"runtime:connection": connection})
    return cfg.get("runtime:connection")
