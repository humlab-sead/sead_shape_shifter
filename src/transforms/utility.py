import pandas as pd


def add_surrogate_id(target: pd.DataFrame, id_name: str) -> pd.DataFrame:
    """Add an integer surrogate ID starting at 1."""
    target = target.reset_index(drop=True).copy()
    target[id_name] = range(1, len(target) + 1)
    return target
