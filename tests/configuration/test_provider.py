"""Tests for configuration provider and store."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.configuration.provider import ConfigProvider
from src.configuration.config import Config
from src.configuration.provider import (
    ConfigStore,
    MockConfigProvider,
    get_config_provider,
    reset_config_provider,
    set_config_provider,
)
from src.configuration.interface import ConfigLike


@pytest.fixture(autouse=True)
def reset_store_and_provider():
    """Ensure singleton store/provider are reset between tests."""
    ConfigStore.reset_instance()
    reset_config_provider()
    yield
    ConfigStore.reset_instance()
    reset_config_provider()


def test_configure_context_loads_file(tmp_path: Path) -> None:
    """ConfigStore loads a YAML file and tracks context."""
    cfg_file: Path = tmp_path / "config.yml"
    cfg_file.write_text("section:\n  key: value\n", encoding="utf-8")

    store: ConfigStore = ConfigStore.get_instance()
    store.configure_context(context="ctx", source=str(cfg_file), env_filename=None, env_prefix=None)

    assert store.is_configured("ctx") is True
    assert store.context == "ctx"
    cfg: ConfigLike | None = store.config("ctx")

    assert isinstance(cfg, Config)
    assert cfg.data is not None
    assert cfg.data["section"]["key"] == "value"
    assert isinstance(cfg, ConfigLike)


def test_consolidate_merges_with_existing_config() -> None:
    """Consolidate should merge new options and keep non-ignored keys."""
    cfg = Config(data={"options": {"a": 1, "b": 2}})
    store: ConfigStore = ConfigStore.get_instance()
    store.set_config(cfg, context="ctx")

    store.consolidate({"a": 10}, context="ctx", section="options")

    assert cfg.data["options"] == {"a": 10, "b": 2}


def test_set_config_provider_swaps_and_restores() -> None:
    """set_config_provider should return previous provider and allow restore."""
    mock_cfg = Config(data={"section": {"key": "value"}})
    new_provider = MockConfigProvider(mock_cfg)

    previous: ConfigProvider = set_config_provider(new_provider)
    try:
        assert get_config_provider() is new_provider
        assert get_config_provider().get_config().data["section"]["key"] == "value"
    finally:
        set_config_provider(previous)

    assert get_config_provider() is previous
