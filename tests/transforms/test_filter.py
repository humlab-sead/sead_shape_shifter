"""Tests for filter transformations."""

import pandas as pd
import pytest

from src.model import TableConfig
from src.transforms.filter import ExistsInFilter, Filters, QueryFilter, apply_filters


class TestQueryFilter:
    """Tests for QueryFilter class."""

    def test_basic_query_filter_numeric_comparison(self):
        """Test basic numeric comparison query."""
        df = pd.DataFrame({"a": [1, 2, 3, 4, 5], "b": [10, 20, 30, 40, 50]})
        filter_cfg = {"type": "query", "query": "a > 2"}

        qf = QueryFilter()
        result = qf.apply(df, filter_cfg, {})

        expected = pd.DataFrame({"a": [3, 4, 5], "b": [30, 40, 50]}, index=[2, 3, 4])
        pd.testing.assert_frame_equal(result, expected)

    def test_query_filter_string_comparison(self):
        """Test string comparison query."""
        df = pd.DataFrame({"name": ["Alice", "Bob", "Charlie", "David"], "age": [25, 30, 35, 40]})
        filter_cfg = {"type": "query", "query": "name in ['Alice', 'Charlie']"}

        qf = QueryFilter()
        result = qf.apply(df, filter_cfg, {})

        expected = pd.DataFrame({"name": ["Alice", "Charlie"], "age": [25, 35]}, index=[0, 2])
        pd.testing.assert_frame_equal(result, expected)

    def test_query_filter_multiple_conditions(self):
        """Test query with multiple conditions using AND."""
        df = pd.DataFrame({"x": [1, 2, 3, 4, 5], "y": [5, 4, 3, 2, 1]})
        filter_cfg = {"type": "query", "query": "x > 2 and y < 4"}

        qf = QueryFilter()
        result = qf.apply(df, filter_cfg, {})

        expected = pd.DataFrame({"x": [3, 4, 5], "y": [3, 2, 1]}, index=[2, 3, 4])
        pd.testing.assert_frame_equal(result, expected)

    def test_query_filter_or_condition(self):
        """Test query with OR condition."""
        df = pd.DataFrame({"value": [1, 2, 3, 4, 5], "category": ["A", "B", "A", "C", "B"]})
        filter_cfg = {"type": "query", "query": "value < 2 or category == 'B'"}

        qf = QueryFilter()
        result = qf.apply(df, filter_cfg, {})

        expected = pd.DataFrame({"value": [1, 2, 5], "category": ["A", "B", "B"]}, index=[0, 1, 4])
        pd.testing.assert_frame_equal(result, expected)

    def test_query_filter_column_to_column_comparison(self):
        """Test query comparing two columns."""
        df = pd.DataFrame({"min_value": [1, 2, 3, 4, 5], "max_value": [3, 1, 5, 4, 6]})
        filter_cfg = {"type": "query", "query": "min_value < max_value"}

        qf = QueryFilter()
        result = qf.apply(df, filter_cfg, {})

        expected = pd.DataFrame({"min_value": [1, 3, 5], "max_value": [3, 5, 6]}, index=[0, 2, 4])
        pd.testing.assert_frame_equal(result, expected)

    def test_query_filter_backtick_column_names(self):
        """Test query with column names containing spaces (using backticks)."""
        df = pd.DataFrame({"column name": [1, 2, 3, 4, 5], "another column": [10, 20, 30, 40, 50]})
        filter_cfg = {"type": "query", "query": "`column name` > 2 and `another column` >= 30"}

        qf = QueryFilter()
        result = qf.apply(df, filter_cfg, {})

        expected = pd.DataFrame({"column name": [3, 4, 5], "another column": [30, 40, 50]}, index=[2, 3, 4])
        pd.testing.assert_frame_equal(result, expected)

    def test_query_filter_empty_result(self):
        """Test query that returns no rows."""
        df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        filter_cfg = {"type": "query", "query": "a > 10"}

        qf = QueryFilter()
        result = qf.apply(df, filter_cfg, {})

        assert len(result) == 0
        assert list(result.columns) == ["a", "b"]

    def test_query_filter_all_rows_match(self):
        """Test query that matches all rows."""
        df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        filter_cfg = {"type": "query", "query": "a > 0"}

        qf = QueryFilter()
        result = qf.apply(df, filter_cfg, {})

        pd.testing.assert_frame_equal(result, df)

    def test_query_filter_no_query_returns_original(self, caplog):
        """Test that missing query returns original dataframe with warning."""
        df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        filter_cfg = {"type": "query"}

        qf = QueryFilter()
        result = qf.apply(df, filter_cfg, {})

        pd.testing.assert_frame_equal(result, df)
        assert "no query defined" in caplog.text.lower()

    def test_query_filter_empty_query_returns_original(self, caplog):
        """Test that empty query string returns original dataframe with warning."""
        df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        filter_cfg = {"type": "query", "query": ""}

        qf = QueryFilter()
        result = qf.apply(df, filter_cfg, {})

        pd.testing.assert_frame_equal(result, df)
        assert "no query defined" in caplog.text.lower()

    def test_query_filter_invalid_query_raises_error(self):
        """Test that invalid query raises ValueError."""
        df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        filter_cfg = {"type": "query", "query": "invalid syntax >>>"}

        qf = QueryFilter()
        with pytest.raises(ValueError, match="Invalid query in filter"):
            qf.apply(df, filter_cfg, {})

    def test_query_filter_nonexistent_column_raises_error(self):
        """Test that query referencing non-existent column raises ValueError."""
        df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        filter_cfg = {"type": "query", "query": "nonexistent_column > 5"}

        qf = QueryFilter()
        with pytest.raises(ValueError, match="Invalid query in filter"):
            qf.apply(df, filter_cfg, {})

    def test_query_filter_with_isin(self):
        """Test query using isin() method."""
        df = pd.DataFrame({"status": ["active", "inactive", "pending", "active", "closed"], "count": [10, 20, 30, 40, 50]})
        filter_cfg = {"type": "query", "query": "status.isin(['active', 'pending'])"}

        qf = QueryFilter()
        result = qf.apply(df, filter_cfg, {})

        expected = pd.DataFrame({"status": ["active", "pending", "active"], "count": [10, 30, 40]}, index=[0, 2, 3])
        pd.testing.assert_frame_equal(result, expected)

    def test_query_filter_with_str_contains(self):
        """Test query using str.contains() method."""
        df = pd.DataFrame({"text": ["hello world", "goodbye world", "hello there", "test"], "value": [1, 2, 3, 4]})
        filter_cfg = {"type": "query", "query": "text.str.contains('hello')"}

        qf = QueryFilter()
        result = qf.apply(df, filter_cfg, {})

        expected = pd.DataFrame({"text": ["hello world", "hello there"], "value": [1, 3]}, index=[0, 2])
        pd.testing.assert_frame_equal(result, expected)

    def test_query_filter_with_nullable_columns(self):
        """Test query with nullable/NaN values."""
        df = pd.DataFrame({"a": [1, 2, None, 4, 5], "b": [10, None, 30, 40, 50]})
        filter_cfg = {"type": "query", "query": "a > 2"}

        qf = QueryFilter()
        result = qf.apply(df, filter_cfg, {})

        expected = pd.DataFrame({"a": [4.0, 5.0], "b": [40.0, 50.0]}, index=[3, 4])
        pd.testing.assert_frame_equal(result, expected)

    def test_query_filter_with_isna(self):
        """Test query using isna() method."""
        df = pd.DataFrame({"a": [1, None, 3, None, 5], "b": [10, 20, 30, 40, 50]})
        filter_cfg = {"type": "query", "query": "a.isna()"}

        qf = QueryFilter()
        result = qf.apply(df, filter_cfg, {})

        expected = pd.DataFrame({"a": [None, None], "b": [20, 40]}, index=[1, 3], dtype=object)
        expected["a"] = expected["a"].astype("float64")
        expected["b"] = expected["b"].astype("int64")
        pd.testing.assert_frame_equal(result, expected)

    def test_query_filter_with_notna(self):
        """Test query using notna() method."""
        df = pd.DataFrame({"a": [1, None, 3, None, 5], "b": [10, 20, 30, 40, 50]})
        filter_cfg = {"type": "query", "query": "a.notna()"}

        qf = QueryFilter()
        result = qf.apply(df, filter_cfg, {})

        expected = pd.DataFrame({"a": [1.0, 3.0, 5.0], "b": [10, 30, 50]}, index=[0, 2, 4])
        pd.testing.assert_frame_equal(result, expected)

    def test_query_filter_data_store_not_used(self):
        """Test that data_store parameter is ignored (not used by QueryFilter)."""
        df = pd.DataFrame({"a": [1, 2, 3, 4, 5]})
        filter_cfg = {"type": "query", "query": "a > 2"}
        data_store = {"other_entity": pd.DataFrame({"x": [1, 2, 3]})}

        qf = QueryFilter()
        result = qf.apply(df, filter_cfg, data_store)

        expected = pd.DataFrame({"a": [3, 4, 5]}, index=[2, 3, 4])
        pd.testing.assert_frame_equal(result, expected)


class TestExistsInFilter:
    """Tests for ExistsInFilter class."""

    def test_exists_in_filter_basic(self):
        """Test basic exists_in filter."""
        df = pd.DataFrame({"id": [1, 2, 3, 4, 5], "name": ["A", "B", "C", "D", "E"]})
        other_df = pd.DataFrame({"id": [2, 4, 6], "value": [20, 40, 60]})
        data_store = {"other": other_df}
        filter_cfg = {"type": "exists_in", "column": "id", "other_entity": "other"}

        ef = ExistsInFilter()
        result = ef.apply(df, filter_cfg, data_store)

        expected = pd.DataFrame({"id": [2, 4], "name": ["B", "D"]}, index=[1, 3])
        pd.testing.assert_frame_equal(result, expected)

    def test_exists_in_filter_different_columns(self):
        """Test exists_in filter with different column names."""
        df = pd.DataFrame({"local_id": [1, 2, 3, 4, 5], "name": ["A", "B", "C", "D", "E"]})
        other_df = pd.DataFrame({"remote_id": [2, 4, 6], "value": [20, 40, 60]})
        data_store = {"other": other_df}
        filter_cfg = {"type": "exists_in", "column": "local_id", "other_entity": "other", "other_column": "remote_id"}

        ef = ExistsInFilter()
        result = ef.apply(df, filter_cfg, data_store)

        expected = pd.DataFrame({"local_id": [2, 4], "name": ["B", "D"]}, index=[1, 3])
        pd.testing.assert_frame_equal(result, expected)

    def test_exists_in_filter_with_drop_duplicates(self):
        """Test exists_in filter with drop_duplicates option."""
        df = pd.DataFrame({"id": [1, 2, 2, 3, 3, 4], "name": ["A", "B", "B", "C", "C", "D"]})
        other_df = pd.DataFrame({"id": [2, 3, 4], "value": [20, 30, 40]})
        data_store = {"other": other_df}
        filter_cfg = {"type": "exists_in", "column": "id", "other_entity": "other", "drop_duplicates": ["id"]}

        ef = ExistsInFilter()
        result = ef.apply(df, filter_cfg, data_store)

        # Should keep only first occurrence of each id
        expected = pd.DataFrame({"id": [2, 3, 4], "name": ["B", "C", "D"]}, index=[1, 3, 5])
        pd.testing.assert_frame_equal(result, expected)

    def test_exists_in_filter_missing_column_raises_error(self):
        """Test that missing 'column' parameter raises ValueError."""
        df = pd.DataFrame({"id": [1, 2, 3]})
        data_store = {"other": pd.DataFrame({"id": [1, 2]})}
        filter_cfg = {"type": "exists_in", "other_entity": "other"}

        ef = ExistsInFilter()
        with pytest.raises(ValueError, match="requires 'column' and 'other_entity'"):
            ef.apply(df, filter_cfg, data_store)

    def test_exists_in_filter_missing_other_entity_raises_error(self):
        """Test that missing 'other_entity' parameter raises ValueError."""
        df = pd.DataFrame({"id": [1, 2, 3]})
        data_store = {}
        filter_cfg = {"type": "exists_in", "column": "id"}

        ef = ExistsInFilter()
        with pytest.raises(ValueError, match="requires 'column' and 'other_entity'"):
            ef.apply(df, filter_cfg, data_store)

    def test_exists_in_filter_unknown_entity_raises_error(self):
        """Test that referencing unknown entity raises ValueError."""
        df = pd.DataFrame({"id": [1, 2, 3]})
        data_store = {"other": pd.DataFrame({"id": [1, 2]})}
        filter_cfg = {"type": "exists_in", "column": "id", "other_entity": "nonexistent"}

        ef = ExistsInFilter()
        with pytest.raises(ValueError, match="references unknown entity"):
            ef.apply(df, filter_cfg, data_store)

    def test_exists_in_filter_empty_other_entity(self):
        """Test exists_in filter when other entity is empty."""
        df = pd.DataFrame({"id": [1, 2, 3], "name": ["A", "B", "C"]})
        other_df = pd.DataFrame({"id": []})
        data_store = {"other": other_df}
        filter_cfg = {"type": "exists_in", "column": "id", "other_entity": "other"}

        ef = ExistsInFilter()
        result = ef.apply(df, filter_cfg, data_store)

        # Should return empty dataframe with same columns
        assert len(result) == 0
        assert list(result.columns) == ["id", "name"]

    def test_exists_in_filter_no_matches(self):
        """Test exists_in filter when no values match."""
        df = pd.DataFrame({"id": [1, 2, 3], "name": ["A", "B", "C"]})
        other_df = pd.DataFrame({"id": [4, 5, 6], "value": [40, 50, 60]})
        data_store = {"other": other_df}
        filter_cfg = {"type": "exists_in", "column": "id", "other_entity": "other"}

        ef = ExistsInFilter()
        result = ef.apply(df, filter_cfg, data_store)

        assert len(result) == 0
        assert list(result.columns) == ["id", "name"]


class TestApplyFilters:
    """Tests for apply_filters function."""

    def test_apply_filters_single_query_filter(self):
        """Test applying a single query filter."""
        df = pd.DataFrame({"a": [1, 2, 3, 4, 5], "b": [10, 20, 30, 40, 50]})
        entities_cfg = {"test": {"filters": [{"type": "query", "query": "a > 2"}]}}
        cfg = TableConfig(entities_cfg=entities_cfg, entity_name="test")

        result = apply_filters("test", df, cfg, {})

        expected = pd.DataFrame({"a": [3, 4, 5], "b": [30, 40, 50]}, index=[2, 3, 4])
        pd.testing.assert_frame_equal(result, expected)

    def test_apply_filters_multiple_filters(self):
        """Test applying multiple filters in sequence."""
        df = pd.DataFrame({"a": [1, 2, 3, 4, 5], "b": [10, 20, 30, 40, 50]})
        entities_cfg = {"test": {"filters": [{"type": "query", "query": "a > 1"}, {"type": "query", "query": "b < 50"}]}}
        cfg = TableConfig(entities_cfg=entities_cfg, entity_name="test")

        result = apply_filters("test", df, cfg, {})

        expected = pd.DataFrame({"a": [2, 3, 4], "b": [20, 30, 40]}, index=[1, 2, 3])
        pd.testing.assert_frame_equal(result, expected)

    def test_apply_filters_no_filters(self):
        """Test that no filters returns original dataframe."""
        df = pd.DataFrame({"a": [1, 2, 3], "b": [10, 20, 30]})
        entities_cfg = {"test": {"filters": []}}
        cfg = TableConfig(entities_cfg=entities_cfg, entity_name="test")

        result = apply_filters("test", df, cfg, {})

        pd.testing.assert_frame_equal(result, df)

    def test_apply_filters_missing_type_logs_warning(self, caplog):
        """Test that filter without 'type' field logs warning."""
        df = pd.DataFrame({"a": [1, 2, 3], "b": [10, 20, 30]})
        entities_cfg = {"test": {"filters": [{"query": "a > 1"}]}}  # Missing 'type'
        cfg = TableConfig(entities_cfg=entities_cfg, entity_name="test")

        result = apply_filters("test", df, cfg, {})

        pd.testing.assert_frame_equal(result, df)
        assert "missing 'type' field" in caplog.text.lower()

    def test_apply_filters_unknown_type_raises_error(self):
        """Test that unknown filter type raises KeyError."""
        df = pd.DataFrame({"a": [1, 2, 3], "b": [10, 20, 30]})
        entities_cfg = {"test": {"filters": [{"type": "nonexistent_filter"}]}}
        cfg = TableConfig(entities_cfg=entities_cfg, entity_name="test")

        with pytest.raises(KeyError, match="is not registered"):
            apply_filters("test", df, cfg, {})

    def test_apply_filters_with_exists_in(self):
        """Test applying exists_in filter through apply_filters."""
        df = pd.DataFrame({"id": [1, 2, 3, 4, 5], "name": ["A", "B", "C", "D", "E"]})
        other_df = pd.DataFrame({"id": [2, 4], "value": [20, 40]})
        data_store = {"other": other_df}
        entities_cfg = {"test": {"filters": [{"type": "exists_in", "column": "id", "other_entity": "other"}]}}
        cfg = TableConfig(entities_cfg=entities_cfg, entity_name="test")

        result = apply_filters("test", df, cfg, data_store)

        expected = pd.DataFrame({"id": [2, 4], "name": ["B", "D"]}, index=[1, 3])
        pd.testing.assert_frame_equal(result, expected)

    def test_apply_filters_query_then_exists_in(self):
        """Test combining query and exists_in filters."""
        df = pd.DataFrame({"id": [1, 2, 3, 4, 5], "value": [10, 20, 30, 40, 50]})
        other_df = pd.DataFrame({"id": [2, 3, 4], "x": [1, 2, 3]})
        data_store = {"other": other_df}
        entities_cfg = {
            "test": {"filters": [{"type": "query", "query": "value >= 30"}, {"type": "exists_in", "column": "id", "other_entity": "other"}]}
        }
        cfg = TableConfig(entities_cfg=entities_cfg, entity_name="test")

        result = apply_filters("test", df, cfg, data_store)

        # First filter: value >= 30 -> [3, 4, 5]
        # Second filter: id in [2, 3, 4] -> [3, 4]
        expected = pd.DataFrame({"id": [3, 4], "value": [30, 40]}, index=[2, 3])
        pd.testing.assert_frame_equal(result, expected)


class TestFilterRegistry:
    """Tests for filter registry."""

    def test_query_filter_registered(self):
        """Test that QueryFilter is registered."""
        assert Filters.get("query") is not None
        assert Filters.get("query") == QueryFilter

    def test_exists_in_filter_registered(self):
        """Test that ExistsInFilter is registered."""
        assert Filters.get("exists_in") is not None
        assert Filters.get("exists_in") == ExistsInFilter

    def test_filter_registry_keys(self):
        """Test that expected filter keys are in registry."""
        keys = set(Filters.items.keys())
        assert "query" in keys
        assert "exists_in" in keys
