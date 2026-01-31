import pandas as pd


def add_system_id(target: pd.DataFrame, id_name: str = "system_id") -> pd.DataFrame:
    """Add an auto-incrementing system_id column starting at 1.

    Args:
        target: DataFrame to add system_id to
        id_name: Column name for the system ID (default: "system_id")

    Returns:
        DataFrame with system_id column added
    """
    target = target.reset_index(drop=True).copy()
    target[id_name] = range(1, len(target) + 1)
    # put id_name as the first column
    cols: list[str] = [id_name] + [col for col in target.columns if col != id_name]
    target = target[cols]
    return target


# Backward compatibility alias
add_surrogate_id = add_system_id
