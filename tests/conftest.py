import sys
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import psycopg
import pytest
from loguru import logger

from src.configuration import Config, ConfigFactory, MockConfigProvider

# pylint: disable=unused-argument


@pytest.fixture(autouse=True, scope="session")
def setup_test_logging():
    """Configure logging for all tests with DEBUG level."""
    logger.remove()
    logger.add(sys.stderr, level="DEBUG", format="{time} | {level} | {name}:{function}:{line} - {message}")


class MockRow:
    """Mock psycopg.Row that can be converted to dict"""

    def __init__(self, data) -> None:
        self._data: dict = data if isinstance(data, dict) else dict(data)

    def keys(self):
        return self._data.keys()

    def values(self):
        return self._data.values()

    def items(self):
        return self._data.items()

    def __getitem__(self, key):
        return self._data[key]

    def __iter__(self):
        return iter(self._data.items())

    def __len__(self):
        return len(self._data)

    def __bool__(self):
        return bool(self._data)

    # Add these methods to make it more dict-like
    def get(self, key, default=None):
        return self._data.get(key, default)

    def __contains__(self, key):
        return key in self._data


def mock_strategy_with_get_details(mock_strategies, value: dict[str, str]) -> AsyncMock:
    mock_strategy = AsyncMock()
    mock_strategy.get_details.return_value = value
    mock_strategies.items.get.return_value = lambda: mock_strategy
    return mock_strategy


@pytest.fixture
def test_config() -> Config:
    """Provide test configuration"""

    async def async_mock_connection():
        mock_conn = AsyncMock(spec=psycopg.AsyncConnection)
        mock_cursor = AsyncMock(spec=psycopg.AsyncCursor)

        async def async_fetchone():
            mock_row_data = {
                "ID": 123,
                "Name": "Test Site",
                "Description": "A test archaeological site",
                "National ID": "TEST123",
                "Latitude": 59.8586,
                "Longitude": 17.6389,
            }
            return MockRow(mock_row_data)

        async def async_execute(query, params=None):
            pass

        mock_cursor.fetchone.side_effect = async_fetchone
        mock_cursor.execute.side_effect = async_execute
        mock_conn.cursor.return_value = mock_cursor
        return mock_conn

    factory: ConfigFactory = ConfigFactory()
    config: Config = factory.load(source="./tests/config/config.yml", context="default", env_filename="./tests/.env")  # type: ignore
    config.update(
        {
            "runtime": {
                "connection_factory": async_mock_connection,
            }
        }
    )
    return config
    # return Config(data={"options": {"id_base": "https://w3id.org/sead/id/"}, "runtime": {"connection_factory": async_mock_connection}})


class ExtendedMockConfigProvider(MockConfigProvider):
    """Extended MockConfigProvider that allows setting config after initialization"""

    def __init__(self, initial_config: Config) -> None:
        super().__init__(initial_config)

    def create_connection_mock(self, **kwargs) -> None:
        connection = create_connection_mock(**({"execute": None} | kwargs))
        self.get_config().update({"runtime:connection": connection})

    @property
    def connection_mock(self) -> MagicMock:
        return self.get_config().get("runtime:connection")

    @property
    def cursor_mock(self) -> MagicMock:
        if not self.connection_mock:
            raise ValueError("Connection mock not set up. Call create_connection_mock first.")

        return self.connection_mock.cursor.return_value.__aenter__.return_value


@pytest.fixture
def test_provider(test_config: Config) -> ExtendedMockConfigProvider:  # pylint: disable=redefined-outer-name
    """Provide TestConfigProvider with test configuration"""
    provider = ExtendedMockConfigProvider(test_config)
    return provider


def create_connection_mock(**method_returns: Any) -> AsyncMock:
    """
    Create an async psycopg connection mock whose cursor methods return given values.

    Example:
        mock_conn = create_connection_mock(
            fetchall=[{"id": 1, "name": "Alice"}],
            execute=None,
            fetchone={"id": 2, "name": "Bob"},
        )
    """
    mock_conn = AsyncMock(spec=psycopg.AsyncConnection)
    mock_cursor = AsyncMock(spec=psycopg.AsyncCursor)

    # Set up each requested async method to return the specified value
    for method_name, return_value in method_returns.items():
        method = getattr(mock_cursor, method_name)
        # Wrap lists of dicts into MockRow for convenience
        if isinstance(return_value, list) and return_value and isinstance(return_value[0], dict):
            return_value = [MockRow(r) for r in return_value]
        elif isinstance(return_value, dict):
            return_value = MockRow(return_value)
        method.return_value = return_value

    # Set up cursor context manager behavior
    cursor_context_manager = AsyncMock()
    cursor_context_manager.__aenter__.return_value = mock_cursor
    cursor_context_manager.__aexit__.return_value = None
    mock_conn.cursor.return_value = cursor_context_manager
    mock_conn.cursor_instance = mock_cursor
    return mock_conn
