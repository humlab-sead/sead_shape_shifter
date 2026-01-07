from collections.abc import Sequence
from typing import Any

import pandas as pd
import pyproj

from . import Transformer, Transformers


def to_wgs84(src_crs: str | pd.Series, x: float | pd.Series, y: float | pd.Series) -> tuple[float | pd.Series, float | pd.Series]:
    """
    Transform a single (x, y) from the given coordinate system to WGS84 lon/lat.
    """
    return to_crs(src_crs, "EPSG:4326", x, y)


def to_crs(
    src_crs: str | pd.Series, dst_crs: str, x: float | pd.Series, y: float | pd.Series
) -> tuple[float | pd.Series, float | pd.Series]:
    """
    Transform a single (x, y) from the given src system to the given dst system.
    """

    if isinstance(src_crs, str) and isinstance(dst_crs, str) and src_crs == dst_crs:
        return x, y

    transformer: pyproj.Transformer = pyproj.Transformer.from_crs(src_crs, dst_crs, always_xy=True)
    x_new, y_new = transformer.transform(x, y)
    return x_new, y_new


@Transformers.register(key="geo_split")
class TransformSplitLatLong(Transformer):
    """
    Transform a column with geographical points stored as a single
    'lat,lon' string into two separate float columns: '<col>_lat' and '<col>_lon'.

    Example input values:
        "63.825, 20.263"
        "48.8566, 2.3522"
    """

    def apply(
        self,
        data: pd.DataFrame,
        columns: Sequence[str] | str,
        *,
        sep: str = ",",
        lat_suffix: str = "_lat",
        lon_suffix: str = "_lon",
        **opts: Any,
    ) -> pd.DataFrame:
        """
        Parameters
        ----------
        data :
            Input DataFrame.
        columns :
            Single column name or sequence with exactly one column name containing
            'lat{sep}lon' strings.
        sep :
            Separator between latitude and longitude in the string. Default: ",".
        lat_suffix :
            Suffix for the latitude column name. Default: "_lat".
        lon_suffix :
            Suffix for the longitude column name. Default: "_lon".

        Returns
        -------
        pd.DataFrame
            A new DataFrame with two additional float columns:
            '<col><lat_suffix>' and '<col><lon_suffix>'.
        """
        if isinstance(columns, str):
            columns = [columns]

        if len(columns) != 1:
            raise ValueError("Transform 'geo_split' requires exactly one column name")

        col: str = columns[0]
        if col not in data.columns:
            raise KeyError(f"Column {col!r} not found in DataFrame")

        df: pd.DataFrame = data.copy()

        s: pd.Series[str] = df[col].astype("string")

        split: pd.DataFrame = s.str.split(sep, n=1, expand=True)

        if split.shape[1] != 2:
            raise ValueError(
                f"Expected exactly one '{sep}' in values of column {col!r}, " f"but got {split.shape[1]} parts after splitting"
            )

        lat_raw: pd.Series[str] = split[0].str.strip()
        lon_raw: pd.Series[str] = split[1].str.strip()

        try:
            lat: pd.Series[float] = pd.to_numeric(lat_raw, errors="raise")
            lon: pd.Series[float] = pd.to_numeric(lon_raw, errors="raise")
        except Exception as e:
            # Try to identify a problematic value for a clearer message
            bad_lat: list[str] = lat_raw[~lat_raw.str.match(r"^[+-]?\d+(\.\d+)?$", na=True)].iloc[:5].tolist()
            bad_lon: list[str] = lon_raw[~lon_raw.str.match(r"^[+-]?\d+(\.\d+)?$", na=True)].iloc[:5].tolist()
            raise ValueError(
                f"Error parsing lat/lon floats from column {col!r}. " f"Example problematic lat values: {bad_lat}, lon values: {bad_lon}"
            ) from e

        df[f"{col}{lat_suffix}"] = lat
        df[f"{col}{lon_suffix}"] = lon

        return df


@Transformers.register(key="geo_convert_crs")
class ConvertCRS(Transformer):
    """
    Transform coordinate columns from a specified coordinate system to another coordinate system.
    """

    def apply(self, data: pd.DataFrame, columns: Sequence[str] | str, **opts: Any) -> pd.DataFrame:
        """
        Parameters
        ----------
        data :
            Input DataFrame.
        columns : Exactly two column names with X and Y coordinates.
        src_crs_label_column :
            Column name containing the source coordinate system label.
        src_crs :
            Source coordinate system in EPSG code or proj string, ignored if src_crs_label_column is provided.
        dst_crs :
            Destination coordinate system in EPSG code or proj string.
        lon_column :
            Output column name for longitude. Default: "lon".
        lat_column :
            Output column name for latitude. Default: "lat".

        Returns
        -------
        pd.DataFrame
            A new DataFrame with additional 'lon' and 'lat' columns in WGS84.
        """
        src_crs_label_column: str | None = opts.get("src_crs_label_column")
        src_crs: str | pd.Series[str] | None = opts.get("src_crs")
        dst_crs: str | None = opts.get("dst_crs")
        lon_column: str | None = opts.get("lon_column", "lon")
        lat_column: str | None = opts.get("lat_column", "lat")
        if dst_crs is None:
            raise ValueError("Transform 'geo_convert_crs' requires 'dst_crs' option")
        if not isinstance(columns, (list, tuple)) or len(columns) != 2:
            raise ValueError("Transform 'geo_convert_crs' requires exactly two column names: x and y")

        df: pd.DataFrame = data.copy()
        lon_source_column, lat_source_column = columns
        resolved_src_crs: pd.Series[str] | str | None = (
            df[src_crs_label_column] if src_crs_label_column and src_crs_label_column in df.columns else src_crs
        )
        assert resolved_src_crs is not None, "Source CRS could not be resolved"

        lon_new, lat_new = to_crs(resolved_src_crs, dst_crs, df[lon_source_column], df[lat_source_column])

        lon_target_column = lon_column if lon_column else lon_source_column
        lat_target_column = lat_column if lat_column else lat_source_column

        df[lon_target_column] = lon_new
        df[lat_target_column] = lat_new

        return df
