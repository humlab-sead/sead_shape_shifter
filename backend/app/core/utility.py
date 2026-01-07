from pandas.api.types import (
    CategoricalDtype,
    is_bool_dtype,
    is_datetime64_any_dtype,
    is_float_dtype,
    is_integer_dtype,
    is_string_dtype,
    is_timedelta64_dtype,
)


def friendly_dtype(dtype):

    if is_integer_dtype(dtype):
        return "integer"
    if is_float_dtype(dtype):
        return "decimal number"
    if is_bool_dtype(dtype):
        return "boolean"
    if is_datetime64_any_dtype(dtype):
        return "date/time"
    if is_timedelta64_dtype(dtype):
        return "duration"
    if isinstance(dtype, CategoricalDtype):
        return "category"
    if is_string_dtype(dtype):
        return "text"
    return "other"
