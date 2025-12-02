import pandas as pd
from src.arbodat.config_model import TableConfig
from src.arbodat.utility import add_surrogate_id
from .interface import DataLoader

class FixedLoader(DataLoader):
    """Loader for fixed data entities."""

    async def load(self, entity_name: str, table_cfg: TableConfig) -> pd.DataFrame:
        """Create a fixed data entity based on configuration."""

        if not table_cfg.is_fixed_data:
            raise ValueError(f"Entity '{entity_name}' is not configured as fixed data")

        if not table_cfg.values:
            raise ValueError(f"Fixed data entity '{entity_name}' has no values defined")

        data: pd.DataFrame

        if len(table_cfg.columns or []) <= 1:
            surrogate_name: str = table_cfg.surrogate_name
            if not surrogate_name:

                if len(table_cfg.columns or []) == 0:
                    raise ValueError(f"Fixed data entity '{entity_name}' must have a surrogate_name or one column defined")

                surrogate_name = table_cfg.columns[0]
            data: pd.DataFrame = pd.DataFrame({surrogate_name: table_cfg.values})
        else:
            # Multiple columns, values is a list of rows, all having the same length as columns
            if not isinstance(table_cfg.values, list) or not all(isinstance(row, list) for row in table_cfg.values):
                raise ValueError(f"Fixed data entity '{entity_name}' with multiple columns must have values as a list of lists")

            if not all(len(row) == len(table_cfg.columns) for row in table_cfg.values):
                raise ValueError(f"Fixed data entity '{entity_name}' has mismatched number of columns and values")

            data = pd.DataFrame(table_cfg.values, columns=table_cfg.columns)
            
        if table_cfg.surrogate_id:
            data = add_surrogate_id(data, table_cfg.surrogate_id)

        return data