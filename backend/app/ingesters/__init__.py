"""Ingester infrastructure for data ingestion into external systems.

Ingesters are now dynamically discovered from the top-level 'ingesters/' directory.
The registry's discover() method is called during application startup to load
available ingesters.
"""

from backend.app.ingesters.protocol import (
    Ingester,
    IngesterConfig,
    IngesterMetadata,
    IngestionResult,
    ValidationResult,
)
from backend.app.ingesters.registry import Ingesters

# Note: Ingester implementations are no longer imported here.
# They are dynamically discovered at application startup via Ingesters.discover()

__all__ = [
    "Ingester",
    "IngesterConfig",
    "IngesterMetadata",
    "IngestionResult",
    "ValidationResult",
    "Ingesters",
]
