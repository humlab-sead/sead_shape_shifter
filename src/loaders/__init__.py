# type: ignore
from pathlib import Path

from .base_loader import DataLoader, DataLoaderRegistry, DataLoaders

DataLoaders.scan(__name__, Path(__file__).parent)
