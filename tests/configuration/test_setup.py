"""Tests for configuration setup helpers."""

from __future__ import annotations

import pytest

from src.configuration.config import Config
from src.configuration.provider import ConfigProvider, ConfigStore, MockConfigProvider, reset_config_provider, set_config_provider

# pylint: disable=redefined-outer-name


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
