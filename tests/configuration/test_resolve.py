"""Tests for configuration resolve helpers."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from src.configuration.config import Config
from src.configuration.provider import ConfigProvider, MockConfigProvider, set_config_provider
from src.configuration.resolve import Configurable, ConfigValue, inject_config

# pylint: disable=unused-argument,redefined-outer-name


@pytest.fixture()
def mock_provider():
    """Swap provider for tests and restore afterwards."""
    cfg = Config(data={"section": {"value": 5}})
    provider = MockConfigProvider(cfg)
    previous: ConfigProvider = set_config_provider(provider)
    yield cfg
    set_config_provider(previous)


def test_config_value_resolves_and_applies_after(mock_provider: Config) -> None:
    """ConfigValue resolves from provider and applies post-processing."""
    cv: ConfigValue[int] = ConfigValue("section:value", after=lambda v: v * 2)
    assert cv.resolve() == 10

    missing: ConfigValue[int] = ConfigValue("missing", default=3)
    assert missing.resolve() == 3

    with pytest.raises(ValueError):
        ConfigValue("missing", mandatory=True).resolve()


def test_config_value_supports_class_key(mock_provider: Config) -> None:
    """ConfigValue can instantiate a class when key is a type."""

    @dataclass
    class Sample:
        number: int = 1

    cv = ConfigValue(Sample)
    resolved = cv.resolve()
    assert isinstance(resolved, Sample)
    assert resolved.number == 1


def test_inject_config_resolves_defaults(mock_provider: Config) -> None:
    """inject_config should resolve default ConfigValue arguments."""

    @inject_config
    def fn(value: int | ConfigValue[int] = ConfigValue[int]("section:value", default=1)) -> ConfigValue[int] | int | None:
        return value

    assert fn() == 5
    assert fn(value=10) == 10


def test_configurable_resolves_fields(mock_provider: Config) -> None:
    """Configurable.resolve should replace ConfigValue fields in dataclasses."""

    @dataclass
    class Example(Configurable):
        value: int = field(default_factory=lambda: ConfigValue("section:value", default=1))  # type: ignore

    instance = Example()
    instance.resolve()

    assert instance.value == 5
