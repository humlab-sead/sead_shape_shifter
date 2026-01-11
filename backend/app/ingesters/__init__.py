"""Ingester infrastructure for data ingestion into external systems."""

from backend.app.ingesters.protocol import (
    Ingester,
    IngesterConfig,
    IngesterMetadata,
    IngestionResult,
    ValidationResult,
)
from backend.app.ingesters.registry import Ingesters

# Import ingesters to trigger auto-registration
from backend.app.ingesters.sead import SeadIngester  # noqa: F401

__all__ = [
    "Ingester",
    "IngesterConfig",
    "IngesterMetadata",
    "IngestionResult",
    "ValidationResult",
    "Ingesters",
    "SeadIngester",
]
