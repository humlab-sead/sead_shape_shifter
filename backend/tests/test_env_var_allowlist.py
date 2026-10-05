"""Regression tests for the environment-variable allowlist at the resolver boundary.

Phase 1 controls A1 and A1b: a stored or request-supplied ``${SECRET}`` must not
have its value expanded during project resolution, because resolved values are
returned to callers through entity preview. Approved names still resolve.

These exercise the same call both preview paths make in
``ShapeShiftService.preview_entity``: ``project.clone().resolve(**settings.env_opts)``.
"""

from __future__ import annotations

import pytest

from src.configuration.resolve import resolve_directives
from src.model import ShapeShiftProject


def _project() -> ShapeShiftProject:
    """Return a minimal project whose entity options reference an approved and an unapproved var."""
    cfg = {
        "metadata": {"name": "allowlist-test"},
        "entities": {
            "site": {
                "type": "sql",
                "options": {
                    "secret": "${MY_SECRET}",
                    "host": "${SEAD_HOST}",
                },
            }
        },
    }
    return ShapeShiftProject(cfg=cfg, filename="allowlist-test.yml")


class TestEnvOptsCarriesAllowlist:
    """Settings.env_opts must carry the approved-variable set to the resolver."""

    def test_allowed_vars_is_a_frozenset(self, settings) -> None:
        allowed = settings.env_opts["allowed_vars"]
        assert isinstance(allowed, frozenset)

    def test_allowed_vars_includes_legitimate_names(self, settings) -> None:
        allowed = settings.env_opts["allowed_vars"]
        assert {
            "APPLICATION_ROOT",
            "GLOBAL_DATA_DIR",
            "GLOBAL_DATA_SOURCE_DIR",
            "SEAD_HOST",
            "SEAD_PORT",
            "SEAD_DBNAME",
            "SEAD_USER",
        } <= allowed


class TestResolveBlocksUnapprovedVars:
    """Resolution through env_opts must not expand names outside the allowlist."""

    def test_unapproved_var_does_not_leak(self, settings, monkeypatch) -> None:
        monkeypatch.setenv("MY_SECRET", "super-secret-value")
        monkeypatch.setenv("SEAD_HOST", "db.internal")

        resolved = _project().resolve(filename="allowlist-test.yml", strict=True, **settings.env_opts)
        options = resolved.cfg["entities"]["site"]["options"]

        assert options["secret"] == ""
        assert "super-secret-value" not in str(resolved.cfg)

    def test_approved_var_still_resolves(self, settings, monkeypatch) -> None:
        monkeypatch.setenv("MY_SECRET", "super-secret-value")
        monkeypatch.setenv("SEAD_HOST", "db.internal")

        resolved = _project().resolve(filename="allowlist-test.yml", strict=True, **settings.env_opts)
        options = resolved.cfg["entities"]["site"]["options"]

        assert options["host"] == "db.internal"


class TestResolveDirectivesBoundary:
    """The resolve_directives boundary enforces allowed_vars directly."""

    def test_blocks_unapproved_when_allowlist_supplied(self) -> None:
        result = resolve_directives(
            {"host": "${SEAD_HOST}", "secret": "${MY_SECRET}"},
            allowed_vars=frozenset({"SEAD_HOST"}),
        )
        assert result["secret"] == ""

    def test_expands_everything_when_allowlist_none(self, monkeypatch) -> None:
        monkeypatch.setenv("MY_SECRET", "value")
        result = resolve_directives({"secret": "${MY_SECRET}"}, allowed_vars=None)
        assert result["secret"] == "value"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
