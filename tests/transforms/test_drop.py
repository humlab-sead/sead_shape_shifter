# test_drop_empty_rows.py
from loguru import logger
import pandas as pd

from src.transforms.drop import drop_empty_rows


def test_subset_false_returns_same_object():
    df = pd.DataFrame({"a": [1, None], "b": [None, None]})
    out = drop_empty_rows(data=df, entity_name="X", subset=False)
    assert out is df  # exact same object (no work)


def test_subset_none_drops_rows_where_all_columns_empty():
    df = pd.DataFrame(
        {
            "a": [None, 1, None],
            "b": [None, None, "x"],
        }
    )
    out = drop_empty_rows(data=df, entity_name="X", subset=None, treat_empty_strings_as_na=True)
    # row 0 is fully empty -> dropped; rows 1 and 2 kept
    assert out.reset_index(drop=True).equals(df.loc[[1, 2]].reset_index(drop=True))


def test_subset_true_equivalent_to_none():
    df = pd.DataFrame({"a": [None, 1], "b": [None, None]})
    out_none = drop_empty_rows(data=df, entity_name="X", subset=None)
    out_true = drop_empty_rows(data=df, entity_name="X", subset=True)
    assert out_true.reset_index(drop=True).equals(out_none.reset_index(drop=True))


def test_treat_empty_strings_as_na_all_columns():
    df = pd.DataFrame({"a": ["", "x"], "b": [None, None]})
    out = drop_empty_rows(data=df, entity_name="X", subset=None, treat_empty_strings_as_na=True)
    # first row becomes (NA, NA) -> dropped
    assert out.reset_index(drop=True).equals(df.loc[[1]].reset_index(drop=True))


def test_do_not_treat_empty_strings_as_na_all_columns():
    df = pd.DataFrame({"a": ["", "x"], "b": [None, None]})
    out = drop_empty_rows(data=df, entity_name="X", subset=None, treat_empty_strings_as_na=False)
    # empty string is not NA => row 0 is NOT all-empty => kept
    assert out.reset_index(drop=True).equals(df.reset_index(drop=True))


def test_subset_list_only_considers_given_columns():
    df = pd.DataFrame(
        {
            "a": [None, None, "x"],
            "b": [None, "keep", None],
            "c": [1, 2, 3],
        }
    )
    # Consider only a and b for "all empty" check.
    # row 0: a=None, b=None => dropped (even though c=1 is non-empty)
    # row 1: a=None, b="keep" => kept
    # row 2: a="x", b=None => kept
    out = drop_empty_rows(data=df, entity_name="X", subset=["a", "b"])
    assert out.reset_index(drop=True).equals(df.loc[[1, 2]].reset_index(drop=True))


def test_subset_list_treat_empty_strings_as_na_within_subset_only():
    df = pd.DataFrame(
        {
            "a": ["", "x"],
            "b": [None, None],
            "c": ["not_used", "not_used"],
        }
    )
    out = drop_empty_rows(data=df, entity_name="X", subset=["a", "b"], treat_empty_strings_as_na=True)
    # row 0: a="" -> NA, b=None -> NA => dropped
    assert out.reset_index(drop=True).equals(df.loc[[1]].reset_index(drop=True))


def test_subset_dict_replaces_specified_values_and_drops_all_empty_in_subset():
    df = pd.DataFrame(
        {
            "a": ["", "ok", "ok"],
            "b": ["-", "-", "v"],
            "c": [1, 2, 3],
        }
    )
    # treat "-" in b as empty; treat "" in a as empty too (via treat_empty_strings_as_na)
    out = drop_empty_rows(
        data=df,
        entity_name="X",
        subset={"a": [], "b": ["-"]},
        treat_empty_strings_as_na=True,
    )
    # row 0: a="" -> NA, b="-" -> NA => dropped (subset a,b all empty)
    # row 1: a="ok", b="-" -> b becomes NA but a non-empty => kept
    # row 2: a="ok", b="v" => kept
    assert out.index.tolist() == [1, 2]


def test_subset_dict_without_treating_empty_strings_as_na():
    df = pd.DataFrame({"a": ["", "ok"], "b": ["-", "-"]})
    out = drop_empty_rows(
        data=df,
        entity_name="X",
        subset={"a": [], "b": ["-"]},
        treat_empty_strings_as_na=False,
    )
    # Only "-" is considered empty. "" is NOT treated as empty here.
    # row 0: a="" (non-empty), b="-" -> NA => subset not all empty => kept
    # row 1: a="ok", b="-" -> NA => kept
    assert out.index.tolist() == [0, 1]


def test_missing_subset_columns_logs_warning_and_returns_original():
    df = pd.DataFrame({"a": [None], "b": [None]})

    messages: list[str] = []
    sink_id: int = logger.add(messages.append, level="WARNING")

    try:
        out: pd.DataFrame = drop_empty_rows(data=df, entity_name="Ent", subset=["a", "nope"])
    finally:
        logger.remove(sink_id)

    assert out is df
    assert any("nope" in m for m in messages)


def test_subset_empty_list_behaves_like_dropna_on_no_columns_keeps_all():
    # Edge case: subset=[] means "check nothing" -> dropna(subset=[], how='all') keeps all rows
    df = pd.DataFrame({"a": [None, None], "b": [None, "x"]})
    out: pd.DataFrame = drop_empty_rows(data=df, entity_name="X", subset=[])
    assert out.reset_index(drop=True).equals(df.reset_index(drop=True))
