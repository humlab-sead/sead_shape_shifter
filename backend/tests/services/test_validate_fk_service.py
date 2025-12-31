"""Tests for ValidateForeignKeyService."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.app.models.shapeshift import PreviewResult
from backend.app.services import validate_fk_service
from backend.app.services.validate_fk_service import ValidateForeignKeyService
from src.model import ShapeShiftConfig

# pylint: disable=redefined-outer-name


@pytest.fixture(autouse=True)
def stub_app_state(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Stub ApplicationStateManager to avoid real state lookups."""
    state_manager = MagicMock()
    state_manager.get.return_value = None
    monkeypatch.setattr(validate_fk_service, "get_app_state_manager", lambda: state_manager)
    return state_manager


@pytest.fixture
def preview_service() -> AsyncMock:
    """Async preview service mock."""
    service = AsyncMock()
    service.preview_entity = AsyncMock()
    return service


def build_config(cardinality: str | None = "one_to_one") -> ShapeShiftConfig:
    """Create a ShapeShiftConfig with a single foreign key relationship."""
    constraints = {"cardinality": cardinality} if cardinality else {}
    cfg: dict = {
        "metadata": {"name": "fk_test"},
        "entities": {
            "orders": {
                "name": "orders",
                "type": "fixed",
                "columns": ["order_id", "customer_id", "amount"],
                "keys": ["order_id"],
                "foreign_keys": [
                    {
                        "entity": "customers",
                        "local_keys": ["customer_id"],
                        "remote_keys": ["id"],
                        "how": "left",
                        "constraints": constraints,
                    }
                ],
            },
            "customers": {
                "name": "customers",
                "type": "fixed",
                "columns": ["id", "name"],
                "keys": ["id"],
            },
        },
    }
    return ShapeShiftConfig(cfg=cfg, filename="test-config.yml")


def patch_config_resolution(monkeypatch: pytest.MonkeyPatch, config: ShapeShiftConfig) -> None:
    """Force ShapeShiftConfig.from_source to return provided config."""
    monkeypatch.setattr(validate_fk_service.ShapeShiftConfig, "from_source", staticmethod(lambda source: config))


@pytest.mark.asyncio
async def test_test_foreign_key_success(monkeypatch: pytest.MonkeyPatch, preview_service: AsyncMock) -> None:
    """Verify successful join with matching cardinality."""
    shapeshift_config = build_config(cardinality="one_to_one")
    patch_config_resolution(monkeypatch, shapeshift_config)
    service = ValidateForeignKeyService(preview_service=preview_service)

    local_rows = [
        {"order_id": 1, "customer_id": 1, "amount": 10.0},
        {"order_id": 2, "customer_id": 2, "amount": 20.0},
    ]
    remote_rows = [
        {"id": 1, "name": "Alice"},
        {"id": 2, "name": "Bob"},
    ]

    preview_service.preview_entity.side_effect = [
        PreviewResult(
            entity_name="orders",
            rows=local_rows,
            columns=[],
            total_rows_in_preview=len(local_rows),
            execution_time_ms=0,
        ),
        PreviewResult(
            entity_name="customers",
            rows=remote_rows,
            columns=[],
            total_rows_in_preview=len(remote_rows),
            execution_time_ms=0,
        ),
    ]

    result = await service.test_foreign_key("fk_test", "orders", foreign_key_index=0, sample_size=2)

    assert result.success is True
    assert result.statistics.matched_rows == 2
    assert result.statistics.unmatched_rows == 0
    assert result.cardinality.actual == "one_to_one"
    assert result.unmatched_sample == []
    assert result.warnings == []


@pytest.mark.asyncio
async def test_test_foreign_key_missing_local_key(monkeypatch: pytest.MonkeyPatch, preview_service: AsyncMock) -> None:
    """Raise when local preview data is missing join keys."""
    shapeshift_config = build_config(cardinality="many_to_one")
    patch_config_resolution(monkeypatch, shapeshift_config)
    service = ValidateForeignKeyService(preview_service=preview_service)

    preview_service.preview_entity.side_effect = [
        PreviewResult(
            entity_name="orders",
            rows=[{"order_id": 1, "amount": 10.0}],
            columns=[],
            total_rows_in_preview=1,
            execution_time_ms=0,
        ),
        PreviewResult(
            entity_name="customers",
            rows=[{"id": 1, "name": "Alice"}],
            columns=[],
            total_rows_in_preview=1,
            execution_time_ms=0,
        ),
    ]

    with pytest.raises(ValueError) as excinfo:
        await service.test_foreign_key("fk_test", "orders", foreign_key_index=0, sample_size=1)

    assert "Local keys not found" in str(excinfo.value)


@pytest.mark.asyncio
async def test_test_foreign_key_duplicate_matches(monkeypatch: pytest.MonkeyPatch, preview_service: AsyncMock) -> None:
    """Detect duplicate matches and mismatched cardinality recommendations."""
    shapeshift_config = build_config(cardinality="many_to_one")
    patch_config_resolution(monkeypatch, shapeshift_config)
    service = ValidateForeignKeyService(preview_service=preview_service)

    local_rows = [
        {"order_id": 1, "customer_id": 1, "amount": 5.0},
        {"order_id": 2, "customer_id": 1, "amount": 10.0},
    ]
    remote_rows = [
        {"id": 1, "name": "Alice"},
        {"id": 1, "name": "Alice II"},
    ]

    preview_service.preview_entity.side_effect = [
        PreviewResult(
            entity_name="orders",
            rows=local_rows,
            columns=[],
            total_rows_in_preview=len(local_rows),
            execution_time_ms=0,
        ),
        PreviewResult(
            entity_name="customers",
            rows=remote_rows,
            columns=[],
            total_rows_in_preview=len(remote_rows),
            execution_time_ms=0,
        ),
    ]

    result = await service.test_foreign_key("fk_test", "orders", foreign_key_index=0, sample_size=2)

    assert result.cardinality.actual == "one_to_many"
    assert result.statistics.duplicate_matches > 0
    assert result.success is False
    assert any("duplicate rows" in warning for warning in result.warnings)
    assert any("one_to_many" in recommendation for recommendation in result.recommendations)
