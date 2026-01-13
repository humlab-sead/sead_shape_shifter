"""Test fixtures for CLI tests."""

import pytest
from click.testing import CliRunner


@pytest.fixture
def cli_runner():
    """Provide Click CLI test runner."""

    return CliRunner()
