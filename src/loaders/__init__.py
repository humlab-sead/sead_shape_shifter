# type: ignore
from pathlib import Path

from .base_loader import DataLoader, DataLoaderRegistry, DataLoaders
from .duckdb_loader import duckdb_loader as _duckdb_loader_module  # noqa: F401 — triggers @DataLoaders.register

DataLoaders.scan(__name__, Path(__file__).parent)
