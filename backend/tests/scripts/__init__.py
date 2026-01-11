"""Test fixtures for CLI tests."""

import pytest


@pytest.fixture
def cli_runner():
    """Provide Click CLI test runner."""
    from click.testing import CliRunner

    return CliRunner()
