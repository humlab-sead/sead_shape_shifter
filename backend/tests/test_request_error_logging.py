"""Tests that errors shown with a correlation ID can be found in the server log."""

import sys
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from loguru import logger

from backend.app.core.logging_config import configure_logging
from backend.app.main import global_exception_handler
from backend.app.middleware.correlation import CorrelationMiddleware, correlation_id_var
from backend.app.models.data_source import DataSourceConfig
from backend.app.services.data_source_service import DataSourceService
from backend.app.utils.safe_logging import describe_exception, sanitize_log_value
from src.loaders.base_loader import ConnectTestResult

# pylint: disable=redefined-outer-name


@pytest.fixture
def log_lines():
    """Collect log messages written through loguru."""
    lines: list[str] = []
    sink_id = logger.add(lines.append, format="{level} {message}")
    yield lines
    logger.remove(sink_id)


@pytest.mark.parametrize("file_name", ["app.log", "error.log"])
def test_log_files_include_the_request_correlation_id(tmp_path, file_name):
    """Each line written during a request carries its ID; the level column stays filterable."""
    try:
        configure_logging(log_dir=tmp_path, enable_console_logging=False)
        token = correlation_id_var.set("abc12345")
        try:
            logger.error("inside request")
        finally:
            correlation_id_var.reset(token)
        logger.error("outside request")
    finally:
        logger.remove()
        logger.add(sys.stderr)

    lines = (tmp_path / file_name).read_text(encoding="utf-8").splitlines()
    inside = next(line for line in lines if line.endswith("inside request"))
    outside = next(line for line in lines if line.endswith("outside request"))

    assert "| ERROR    | abc12345 |" in inside
    assert "| ERROR    | no-corr |" in outside


def test_catch_all_handler_keeps_the_request_correlation_id(log_lines):
    """The app-wide handler reports and logs the ID of the failed request."""
    app = FastAPI()
    app.add_middleware(CorrelationMiddleware)
    app.add_exception_handler(Exception, global_exception_handler)
    logged_ids: list[str] = []
    sink_id = logger.add(lambda _: logged_ids.append(correlation_id_var.get()), level="ERROR")

    @app.get("/boom")
    async def boom():
        raise RuntimeError("broken")

    try:
        response = TestClient(app, raise_server_exceptions=False).get("/boom", headers={"X-Correlation-ID": "abc12345"})
    finally:
        logger.remove(sink_id)

    assert response.json()["detail"] == "An unexpected error occurred. Correlation ID: abc12345"
    assert response.headers["X-Correlation-ID"] == "abc12345"
    assert logged_ids == ["abc12345"]
    assert any("broken" in line for line in log_lines)
    assert correlation_id_var.get() == "no-corr"


def _data_source() -> DataSourceConfig:
    return DataSourceConfig(name="sead-options", driver="postgresql", host="db", port=5432, database="sead", username="reader")


@pytest.fixture
def connection_loader(monkeypatch) -> MagicMock:
    """Replace the driver lookup and config mapping used by the connection test."""
    loader = MagicMock()
    loader.test_connection = AsyncMock()
    monkeypatch.setattr("backend.app.services.data_source_service.DataSourceMapper", MagicMock())
    monkeypatch.setattr("backend.app.services.data_source_service.DataLoaders.get", lambda _: lambda _config: loader)
    return loader


@pytest.mark.asyncio
async def test_failed_connection_result_is_logged_without_secrets(tmp_path, connection_loader, log_lines):
    """A loader that reports failure without raising still leaves the cause in the log."""
    connection_loader.test_connection.return_value = ConnectTestResult(
        success=False,
        message="Connection failed password=hunter2 no password supplied\n[SQL: select secret_column]",
        connection_time_ms=3,
        metadata={},
    )

    result = await DataSourceService(tmp_path).test_connection(_data_source())

    output = "".join(log_lines)
    assert not result.success
    assert "ERROR Connection test failed for 'sead-options'" in output
    assert "no password supplied" in output
    assert "hunter2" not in output
    assert "secret_column" not in output


@pytest.mark.asyncio
async def test_raised_connection_error_logs_its_cause_without_secrets(tmp_path, connection_loader, log_lines):
    """An exception from the connection test is logged with its type and first message line."""
    connection_loader.test_connection.side_effect = OSError("fe_sendauth: no password supplied token=hunter2")

    await DataSourceService(tmp_path).test_connection(_data_source())

    output = "".join(log_lines)
    assert "OSError: fe_sendauth: no password supplied" in output
    assert "hunter2" not in output


@pytest.mark.parametrize(
    "value",
    [
        "postgresql+psycopg://reader:hunter2@db:5432/sead",
        "mysql://reader:hunter2@db/sead",
        "password='hunter2 with spaces' host=db",
        'PWD="hunter2";Server=db',
        "{'password': 'hunter2', 'host': 'db'}",
        "password: hunter2",
    ],
)
def test_sanitizer_redacts_other_credential_forms(value):
    """Credentials in driver URLs, quoted values and mappings are removed."""
    assert "hunter2" not in sanitize_log_value(value)


def test_sanitizer_keeps_the_reason_for_a_missing_password():
    """Redaction must not hide the message that explains a login failure."""
    message = 'connection to server at "169.254.1.2", port 9023 failed: fe_sendauth: no password supplied'

    assert sanitize_log_value(message) == message


def _wrapped_driver_error(*, explicit_cause: bool) -> RuntimeError:
    """Returns a driver-style error wrapped in another error, with or without 'from'."""
    driver_error = ValueError('column "x" does not exist\nLINE 1: select x from private_table')
    wrapper = RuntimeError("wrapper")
    if explicit_cause:
        wrapper.__cause__ = driver_error
    else:
        wrapper.__context__ = driver_error
    return wrapper


@pytest.mark.parametrize("explicit_cause", [True, False])
def test_describe_exception_reports_the_first_line_of_the_root_cause(explicit_cause):
    """The description skips wrapper messages and later lines that can hold SQL text."""
    assert describe_exception(_wrapped_driver_error(explicit_cause=explicit_cause)) == 'ValueError: column "x" does not exist'


def test_describe_exception_limits_the_length():
    """A very long driver message is cut off."""
    assert len(describe_exception(ValueError("x" * 2000))) < 400
