import numpy as np
import pandas as pd


def add_system_id(target: pd.DataFrame, id_name: str = "system_id") -> pd.DataFrame:
    """Add or preserve system_id column with stable identity values.

    If the column already exists, existing values are preserved and nulls
    are filled with sequential values starting from max(existing) + 1.
    If the column doesn't exist, creates sequential values starting at 1.

    This ensures system_id stability for fixed entities where FK relationships
    depend on consistent identity values across operations.

    Args:
        target: DataFrame to add/update system_id
        id_name: Column name for the system ID (default: "system_id")

    Returns:
        DataFrame with system_id column added/updated as first column
    """
    target = target.reset_index(drop=True).copy()

    if id_name in target.columns:
        # Preserve existing values, fill nulls with sequential values
        existing_values: pd.Series = target[id_name]

        # Convert to nullable Int64 to handle NaN/None properly
        if not pd.api.types.is_integer_dtype(existing_values):
            existing_values = pd.to_numeric(existing_values, errors="coerce")

        # Find max existing value (excluding nulls)
        valid_values: pd.Series = existing_values.dropna()
        max_value: int = int(valid_values.max()) if len(valid_values) > 0 else 0

        # Fill nulls with sequential values starting from max + 1
        null_mask: pd.Series = existing_values.isna()
        null_count: int = null_mask.sum()

        if null_count > 0:
            fill_values = range(max_value + 1, max_value + null_count + 1)
            target.loc[null_mask, id_name] = list(fill_values)

        # Ensure column is integer type
        target[id_name] = target[id_name].astype(int)
    else:
        # Column doesn't exist - create sequential values starting at 1
        target[id_name] = range(1, len(target) + 1)

    # Put id_name as the first column
    cols: list[str] = [id_name] + [col for col in target.columns if col != id_name]
    target = target[cols]

    return target


# Backward compatibility alias
add_surrogate_id = add_system_id
