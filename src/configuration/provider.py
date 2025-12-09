import threading
from abc import ABC, abstractmethod
from typing import Any, Self

from src.utility import recursive_filter_dict, recursive_update

from .config import Config, ConfigFactory
from .interface import ConfigLike

# pylint: disable=global-statement


class ConfigStore:
    """A class to manage configuration files and contexts"""

    _instance: "ConfigStore | None" = None
    _lock = threading.Lock()

    def __init__(self):
        if ConfigStore._instance is not None:
            raise RuntimeError("ConfigStore is a singleton. Use get_instance()")
        self.store: dict[str, ConfigLike | None] = {"default": None}
        self.context: str = "default"

    @classmethod
    def get_instance(cls) -> "ConfigStore":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        assert cls._instance is not None
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton - useful for testing"""
        with cls._lock:
            cls._instance = None
            # Also reset the provider to singleton when resetting Config Store
            reset_config_provider()

    def is_configured(self, context: str | None = None) -> bool:
        return self.store.get(context or self.context) is not None

    def config(self, context: str | None = None) -> ConfigLike | None:
        ctx: str = context or self.context
        if not self.is_configured(ctx):
            raise ValueError(f"Config context '{ctx}' not properly initialized")

        return self.store[ctx]

    # Convenience class methods for backward compatibility
    @classmethod
    def is_configured_global(cls, context: str | None = None) -> bool:
        """Check if configuration is available (uses provider layer)"""
        return get_config_provider().is_configured(context)

    @classmethod
    def config_global(cls, context: str | None = None) -> ConfigLike:
        """Get configuration (uses provider layer)"""
        return get_config_provider().get_config(context)

    def configure_context(
        self,
        *,
        context: str = "default",
        source: ConfigLike | str | dict[str, Any] = "config.yml",
        env_filename: str | None = None,
        env_prefix: str | None = None,
        switch_to_context: bool = True,
    ) -> Self:
        if not self.store.get(context) and not source:
            raise ValueError(f"Config context {context} undefined, cannot initialize")

        if isinstance(source, (Config, ConfigLike)):
            self.set_config(context="context", cfg=source)
        else:
            cfg: ConfigLike = ConfigFactory().load(
                source=source or self.store.get(context),
                context=context,
                env_filename=env_filename,
                env_prefix=env_prefix,
            )

            self.set_config(context=context, cfg=cfg, switch_to_context=switch_to_context)
        return self

    def consolidate(
        self,
        opts: dict[str, Any],
        ignore_keys: set[str] | None = None,
        context: str = "default",
        section: str | None = None,
    ) -> Self:

        if not self.store.get(context):
            raise ValueError(f"Config context {context} undefined, cannot consolidate")

        if not section:
            raise ValueError("Config section cannot be undefined, cannot consolidate")

        ignore_keys = ignore_keys or set(opts.keys())

        cfg: ConfigLike | None = self.store[context]
        assert cfg is not None

        opts = recursive_update(
            opts,
            recursive_filter_dict(
                cfg.get(section, default={}),
                filter_keys=ignore_keys,
                filter_mode="exclude",
            ),
        )

        self.store[context].data[section] = opts  # type: ignore

        return self

    def set_config(
        self,
        cfg: ConfigLike,
        *,
        context: str = "default",
        switch_to_context: bool = True,
    ) -> ConfigLike | None:
        """Set configuration for the given context. Returns old config if it existed."""
        if not isinstance(cfg, ConfigLike):
            raise ValueError(f"Expected Config, found {type(cfg)}")
        old_config: ConfigLike | None = self.store.get(context)
        self.store[context] = cfg
        if switch_to_context:
            self.context = context
        return old_config


class ConfigProvider(ABC):
    """Abstract configuration provider for dependency injection"""

    @abstractmethod
    def get_config(self, context: str | None = None) -> ConfigLike:
        """Get configuration for the given context"""

    @abstractmethod
    def is_configured(self, context: str | None = None) -> bool:
        """Check if configuration exists for the given context"""

    @abstractmethod
    def set_config(self, config: ConfigLike, context: str | None = None) -> ConfigLike | None:
        """Set configuration for the given context"""


class SingletonConfigProvider(ConfigProvider):
    """Production config provider using Config Store singleton"""

    def get_config(self, context: str | None = None) -> ConfigLike:
        cfg: ConfigLike | None = ConfigStore.get_instance().config(context)
        if cfg is None:
            raise ValueError(f"Config context '{context or 'default'}' not properly initialized")
        return cfg

    def is_configured(self, context: str | None = None) -> bool:
        return ConfigStore.get_instance().is_configured(context)

    def set_config(self, config: ConfigLike, context: str | None = None) -> ConfigLike | None:
        return ConfigStore.get_instance().set_config(cfg=config, context=context or "default")


class MockConfigProvider(ConfigProvider):
    """Test config provider with controllable configuration.
    Note that the context parameter is ignored in this implementation."""

    def __init__(self, config: ConfigLike, context: str | None = "default"):
        self._config: ConfigLike = config
        self._context: str | None = context

    def get_config(self, context: str | None = None) -> ConfigLike:  # pylint: disable=unused-argument
        return self._config

    def set_config(self, config: ConfigLike, context: str | None = None) -> ConfigLike | None:  # pylint: disable=unused-argument
        old_config: ConfigLike | None = self._config
        self._config = config
        return old_config

    def is_configured(self, context: str | None = None) -> bool:  # pylint: disable=unused-argument
        return self._config is not None


# Global provider instance - can be swapped for testing
_current_provider: ConfigProvider = SingletonConfigProvider()
_provider_lock = threading.Lock()


def get_config_provider() -> ConfigProvider:
    """Get the current configuration provider"""
    return _current_provider


def set_config_provider(provider: ConfigProvider) -> ConfigProvider:
    """Set the current configuration provider (useful for testing)"""
    global _current_provider
    with _provider_lock:
        old_provider: ConfigProvider = _current_provider
        _current_provider = provider
        return old_provider


def reset_config_provider() -> None:
    """Reset to the default singleton provider"""
    global _current_provider
    with _provider_lock:
        _current_provider = SingletonConfigProvider()
