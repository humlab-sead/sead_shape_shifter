from typing import TYPE_CHECKING, Any

import pandas as pd
from loguru import logger

from src.transforms.utility import add_surrogate_id
from src.loaders.base_loader import ConnectTestResult

from .base_loader import DataLoader, DataLoaders

if TYPE_CHECKING:
    from src.model import TableConfig


@DataLoaders.register(key=["fixed", "data"])
class FixedLoader(DataLoader):
    """Loader for fixed data entities."""

    async def load(self, entity_name: str, table_cfg: "TableConfig") -> pd.DataFrame:
        """Create a fixed data entity based on configuration."""

        self.validate(entity_name, table_cfg)

        data: pd.DataFrame

        values: list[list[Any]] = table_cfg.safe_values
        columns: list[str] = table_cfg.safe_columns

        if len(columns) == 0 and len(values) == 0:
            logger.warning(f"Fixed data entity '{entity_name}' has no columns or values defined, returning empty DataFrame")
            return pd.DataFrame()

        data = pd.DataFrame(table_cfg.safe_values, columns=table_cfg.safe_columns)

        if table_cfg.surrogate_id:
            if table_cfg.surrogate_id not in data.columns:
                data = add_surrogate_id(data, table_cfg.surrogate_id)

        return data

    def validate(self, entity_name: str, table_cfg: "TableConfig") -> None:
        """Validate the fixed data entity configuration."""
        from src.specifications.entity import FixedEntityFieldsSpecification  # pylint: disable=import-outside-toplevel

        spec = FixedEntityFieldsSpecification({"metadata": {}, "entities": table_cfg.entities_cfg})
        is_valid: bool = spec.is_satisfied_by(entity_name=table_cfg.entity_name)

        if not is_valid:
            raise ValueError(f"Table '{entity_name}' failed validation {spec.get_report()}.")

    async def test_connection(self) -> ConnectTestResult:
        return ConnectTestResult.create_empty(success=True)
