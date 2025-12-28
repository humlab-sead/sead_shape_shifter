"""Tests for configuration setup helpers."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.configuration import setup
from src.configuration.config import Config
from src.configuration.provider import ConfigProvider, ConfigStore, MockConfigProvider, reset_config_provider, set_config_provider


@pytest.fixture()
def reset_store_and_provider():
    """Reset global store/provider for isolation."""
    ConfigStore.reset_instance()
    reset_config_provider()
    yield
    ConfigStore.reset_instance()
    reset_config_provider()


@pytest.fixture()
def provider_with_config():
    """Use a mock provider for setup tests and restore afterwards."""
    cfg = Config(data={})
    previous: ConfigProvider = set_config_provider(MockConfigProvider(cfg))
    yield cfg
    set_config_provider(previous)


@pytest.mark.asyncio
async def test_setup_connection_factory_sets_runtime_entries(monkeypatch, provider_with_config: Config) -> None:
    """_setup_connection_factory should configure runtime dsn and connection factory."""
    cfg: Config = provider_with_config
    cfg.update({"options:database": {"user": "u", "password": "p"}})

    monkeypatch.setattr(setup, "create_db_uri", lambda **kwargs: "postgresql://uri")
    monkeypatch.setattr(setup.psycopg.AsyncConnection, "connect", AsyncMock(return_value="conn"))

    await setup._setup_connection_factory(cfg, db_opts_path="options:database")  # pylint: disable=protected-access

    assert cfg.get("runtime:dsn") == "postgresql://uri"
    factory = cfg.get("runtime:connection_factory")
    connection = await factory()  # type: ignore
    assert connection == "conn"
    assert cfg.get("runtime:connection") == "conn"


@pytest.mark.asyncio
async def test_get_connection_returns_existing(provider_with_config: Config) -> None:
    """get_connection should reuse existing connection without calling factory."""
    cfg = provider_with_config
    cfg.update({"runtime:connection": "existing"})

    connection = await setup.get_connection()

    assert connection == "existing"


@pytest.mark.asyncio
async def test_get_connection_missing_provider_raises(reset_store_and_provider) -> None:  # type: ignore
    """get_connection should raise when no config is available."""
    with pytest.raises(ValueError):
        await setup.get_connection()
