
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


_NULL_SENTINEL_PREFIX = "__ss_null_key__"


def merge_with_null_safety(
    local_df: pd.DataFrame,
    remote_df: pd.DataFrame,
    allow_null_keys: bool = False,
    **opts,
) -> pd.DataFrame:
    """Perform a merge that treats nulls in merge keys as non-matching values.

    Supports merges configured with left_on/right_on.
    If null-safe handling is enabled and any merge key contains nulls,
    temporary left/right key columns are created with distinct sentinel values
    so nulls never match across the two DataFrames.

    Note:
        This implementation uses predictable temporary column names and string
        sentinels. That means two accepted edge-case risks remain:
        1. A DataFrame with pre-existing temp-column names may see those columns
           overwritten and then dropped from the merged result.
        2. Real key values equal to the generated sentinel strings may collide
           with null replacement values and produce false matches.
    """
    left_on: list[str] = list(opts.get("left_on") or [])
    right_on: list[str] = list(opts.get("right_on") or [])
    how: str = opts.get("how", "inner")

    if how == "cross" or not allow_null_keys or not left_on or not right_on:
        return pd.merge(local_df, remote_df, **opts)

    if len(left_on) != len(right_on):
        raise ValueError(f"Mismatched merge key counts: left_on={left_on}, right_on={right_on}")

    if not _has_nulls_in_columns(local_df, left_on) and not _has_nulls_in_columns(remote_df, right_on):
        return pd.merge(local_df, remote_df, **opts)

    merge_local_df, temp_left_on = _create_null_safe_merges(local_df, left_on, _NULL_SENTINEL_PREFIX, "left")
    merge_remote_df, temp_right_on = _create_null_safe_merges(remote_df, right_on, _NULL_SENTINEL_PREFIX, "right")
    merge_opts = opts | {"left_on": temp_left_on, "right_on": temp_right_on}

    merged_df: pd.DataFrame = pd.merge(merge_local_df, merge_remote_df, **merge_opts)

    temp_columns = [col for col in temp_left_on + temp_right_on if col in merged_df.columns]
    if temp_columns:
        merged_df = merged_df.drop(columns=temp_columns)

    return merged_df


def _create_null_safe_merges(
    df: pd.DataFrame,
    columns: list[str],
    sentinel_prefix: str,
    side: str,
) -> tuple[pd.DataFrame, list[str]]:
    """Create null-safe merge keys for the specified columns in the DataFrame."""
    merge_df: pd.DataFrame = df.copy()
    merge_columns: list[str] = []

    for index, key in enumerate(columns):
        merge_column: str = f"__nullsafe_merge_{side}_{index}__"
        sentinel: str = f"{sentinel_prefix}_{side}_{index}"
        merge_df[merge_column] = _build_null_safe_merge_key(merge_df[key], sentinel)
        merge_columns.append(merge_column)

    return merge_df, merge_columns


def _has_nulls_in_columns(df: pd.DataFrame, columns: list[str]) -> bool:
    return any(df[column].isna().any() for column in columns)


def _build_null_safe_merge_key(series: pd.Series, sentinel: str) -> pd.Series:
    return series.astype("object").where(series.notna(), sentinel)
