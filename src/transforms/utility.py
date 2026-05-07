import pandas as pd
from loguru import logger


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
    use_null_safe_merge: bool | None = None,
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
    if use_null_safe_merge is None:
        use_null_safe_merge = allow_null_keys

    # Coerce incompatible merge-key dtypes before any merge path.
    # Handles the common case of YAML-sourced string values joining against
    # integer columns loaded from a database.
    if left_on and right_on:
        local_df, remote_df = _coerce_compatible_merge_key_dtypes(local_df, remote_df, left_on, right_on)

    if how == "cross" or not use_null_safe_merge or not left_on or not right_on:
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


def _coerce_compatible_merge_key_dtypes(
    local_df: pd.DataFrame,
    remote_df: pd.DataFrame,
    left_on: list[str],
    right_on: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Coerce incompatible merge-key dtypes to compatible types where safely possible.

    When one join-key column is numeric (int/float) and the paired column is object
    (string), attempts to cast the object column to numeric via ``pd.to_numeric``.
    The cast is only applied when it introduces no additional null values, i.e. all
    non-null string values are valid numbers.

    This handles the common case of YAML-sourced integer values that pandas reads as
    strings (e.g. ``'1'``) joining against database integer columns.

    Returns copies of the DataFrames only when a coercion is actually performed;
    otherwise returns the originals unchanged.
    """
    local_modified: bool = False
    remote_modified: bool = False

    for left_key, right_key in zip(left_on, right_on):
        if left_key not in local_df.columns or right_key not in remote_df.columns:
            continue

        left_col: pd.Series  = local_df[left_key]
        right_col: pd.Series = remote_df[right_key]
        left_numeric: bool = pd.api.types.is_numeric_dtype(left_col)
        right_numeric: bool = pd.api.types.is_numeric_dtype(right_col)

        if left_numeric == right_numeric:
            continue  # both numeric or both non-numeric — nothing to do

        if left_numeric and not right_numeric:
            coerced: pd.Series = pd.to_numeric(right_col, errors="coerce")
            if coerced.isna().sum() == right_col.isna().sum():
                if not remote_modified:
                    remote_df = remote_df.copy()
                    remote_modified = True
                logger.debug(f"Coerced merge key '{right_key}' from object to numeric for join compatibility")
                remote_df[right_key] = coerced
        else:
            coerced: pd.Series = pd.to_numeric(left_col, errors="coerce")
            if coerced.isna().sum() == left_col.isna().sum():
                if not local_modified:
                    local_df = local_df.copy()
                    local_modified = True
                logger.debug(f"Coerced merge key '{left_key}' from object to numeric for join compatibility")
                local_df[left_key] = coerced

    return local_df, remote_df


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
