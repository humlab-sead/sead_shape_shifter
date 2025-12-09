"""Unit tests for arbodat dispatch module."""

from pathlib import Path
from unittest.mock import Mock, patch

import pandas as pd
import pytest

from src.arbodat.dispatch import CSVDispatcher, DatabaseDispatcher, Dispatcher, Dispatchers, DispatchRegistry, ExcelDispatcher
from src.configuration import MockConfigProvider
from src.utility import Registry
from tests.decorators import with_test_config

# pylint: disable=unused-argument


class TestDispatchRegistry:
    """Tests for DispatchRegistry class."""

    def test_dispatch_registry_inherits_from_registry(self):
        """Test that DispatchRegistry inherits from Registry."""

        assert issubclass(DispatchRegistry, Registry)

    def test_dispatch_registry_has_items(self):
        """Test that DispatchRegistry has items dict."""
        registry = DispatchRegistry()
        assert hasattr(registry, "items")
        assert isinstance(registry.items, dict)

    def test_dispatchers_singleton_exists(self):
        """Test that Dispatchers singleton exists."""
        assert Dispatchers is not None
        assert isinstance(Dispatchers, DispatchRegistry)

    def test_dispatchers_has_registered_dispatchers(self):
        """Test that Dispatchers has the expected dispatchers registered."""
        assert Dispatchers.is_registered("csv")
        assert Dispatchers.is_registered("xlsx")
        assert Dispatchers.is_registered("db")

    def test_dispatchers_get_csv(self):
        """Test getting CSV dispatcher from registry."""
        dispatcher = Dispatchers.get("csv")
        assert dispatcher is CSVDispatcher

    def test_dispatchers_get_xlsx(self):
        """Test getting Excel dispatcher from registry."""
        dispatcher = Dispatchers.get("xlsx")
        assert dispatcher is ExcelDispatcher

    def test_dispatchers_get_db(self):
        """Test getting Database dispatcher from registry."""
        dispatcher = Dispatchers.get("db")
        assert dispatcher is DatabaseDispatcher

    def test_dispatchers_get_nonexistent_raises_error(self):
        """Test that getting nonexistent dispatcher raises KeyError."""
        with pytest.raises(KeyError, match="not registered"):
            Dispatchers.get("nonexistent")


class TestDispatcherProtocol:
    """Tests for Dispatcher Protocol."""

    def test_dispatcher_protocol_has_dispatch_method(self):
        """Test that Dispatcher protocol defines dispatch method."""
        assert hasattr(Dispatcher, "dispatch")

    def test_csv_dispatcher_implements_protocol(self):
        """Test that CSVDispatcher implements Dispatcher protocol."""
        dispatcher = CSVDispatcher()
        assert hasattr(dispatcher, "dispatch")
        assert callable(dispatcher.dispatch)

    def test_excel_dispatcher_implements_protocol(self):
        """Test that ExcelDispatcher implements Dispatcher protocol."""
        dispatcher = ExcelDispatcher()
        assert hasattr(dispatcher, "dispatch")
        assert callable(dispatcher.dispatch)

    def test_database_dispatcher_implements_protocol(self):
        """Test that DatabaseDispatcher implements Dispatcher protocol."""
        dispatcher = DatabaseDispatcher()
        assert hasattr(dispatcher, "dispatch")
        assert callable(dispatcher.dispatch)


class TestCSVDispatcher:
    """Tests for CSVDispatcher class."""

    def test_csv_dispatcher_instantiation(self):
        """Test creating a CSVDispatcher instance."""
        dispatcher = CSVDispatcher()
        assert dispatcher is not None

    def test_csv_dispatcher_creates_directory(self, tmp_path: Path):
        """Test that CSVDispatcher creates the output directory."""
        dispatcher = CSVDispatcher()
        output_dir = tmp_path / "csv_output"
        data = {"table1": pd.DataFrame({"col1": [1, 2], "col2": ["a", "b"]})}

        dispatcher.dispatch(str(output_dir), data)

        assert output_dir.exists()
        assert output_dir.is_dir()

    def test_csv_dispatcher_creates_csv_files(self, tmp_path: Path):
        """Test that CSVDispatcher creates CSV files for each table."""
        dispatcher = CSVDispatcher()
        output_dir = tmp_path / "csv_output"
        data = {
            "table1": pd.DataFrame({"col1": [1, 2], "col2": ["a", "b"]}),
            "table2": pd.DataFrame({"col3": [3, 4], "col4": ["c", "d"]}),
        }

        dispatcher.dispatch(str(output_dir), data)

        assert (output_dir / "table1.csv").exists()
        assert (output_dir / "table2.csv").exists()

    def test_csv_dispatcher_file_contents(self, tmp_path: Path):
        """Test that CSV files contain correct data."""
        dispatcher = CSVDispatcher()
        output_dir = tmp_path / "csv_output"
        df = pd.DataFrame({"col1": [1, 2, 3], "col2": ["a", "b", "c"]})
        data = {"test_table": df}

        dispatcher.dispatch(str(output_dir), data)

        result_df = pd.read_csv(output_dir / "test_table.csv")
        pd.testing.assert_frame_equal(result_df, df)

    def test_csv_dispatcher_no_index_in_output(self, tmp_path: Path):
        """Test that CSV files are written without index."""
        dispatcher = CSVDispatcher()
        output_dir = tmp_path / "csv_output"
        data = {"table1": pd.DataFrame({"col1": [1, 2]})}

        dispatcher.dispatch(str(output_dir), data)

        # Read the file and check it doesn't have an unnamed index column
        with open(output_dir / "table1.csv", encoding="utf-8") as f:
            first_line = f.readline()
            assert "Unnamed" not in first_line
            assert first_line.strip() == "col1"

    def test_csv_dispatcher_empty_dataframe(self, tmp_path: Path):
        """Test dispatching empty DataFrame."""
        dispatcher = CSVDispatcher()
        output_dir = tmp_path / "csv_output"
        data = {"empty_table": pd.DataFrame()}

        dispatcher.dispatch(str(output_dir), data)

        assert (output_dir / "empty_table.csv").exists()

    def test_csv_dispatcher_multiple_tables(self, tmp_path: Path):
        """Test dispatching multiple tables."""
        dispatcher = CSVDispatcher()
        output_dir = tmp_path / "csv_output"
        data = {
            "table1": pd.DataFrame({"a": [1, 2]}),
            "table2": pd.DataFrame({"b": [3, 4]}),
            "table3": pd.DataFrame({"c": [5, 6]}),
        }

        dispatcher.dispatch(str(output_dir), data)

        assert len(list(output_dir.glob("*.csv"))) == 3

    def test_csv_dispatcher_overwrites_existing_directory(self, tmp_path: Path):
        """Test that dispatcher works with existing directory."""
        dispatcher = CSVDispatcher()
        output_dir = tmp_path / "csv_output"
        output_dir.mkdir(parents=True, exist_ok=True)

        data = {"table1": pd.DataFrame({"col1": [1, 2]})}
        dispatcher.dispatch(str(output_dir), data)

        assert (output_dir / "table1.csv").exists()


class TestExcelDispatcher:
    """Tests for ExcelDispatcher class."""

    def test_excel_dispatcher_instantiation(self):
        """Test creating an ExcelDispatcher instance."""
        dispatcher = ExcelDispatcher()
        assert dispatcher is not None

    def test_excel_dispatcher_creates_excel_file(self, tmp_path: Path):
        """Test that ExcelDispatcher creates an Excel file."""
        dispatcher = ExcelDispatcher()
        output_file = tmp_path / "output.xlsx"
        data = {"table1": pd.DataFrame({"col1": [1, 2], "col2": ["a", "b"]})}

        dispatcher.dispatch(str(output_file), data)

        assert output_file.exists()

    def test_excel_dispatcher_creates_sheets(self, tmp_path: Path):
        """Test that ExcelDispatcher creates sheets for each table."""
        dispatcher = ExcelDispatcher()
        output_file = tmp_path / "output.xlsx"
        data = {
            "table1": pd.DataFrame({"col1": [1, 2]}),
            "table2": pd.DataFrame({"col2": [3, 4]}),
        }

        dispatcher.dispatch(str(output_file), data)

        # Read back and verify sheets exist
        excel_file = pd.ExcelFile(output_file)
        assert "table1" in excel_file.sheet_names
        assert "table2" in excel_file.sheet_names

    def test_excel_dispatcher_sheet_contents(self, tmp_path: Path):
        """Test that Excel sheets contain correct data."""
        dispatcher = ExcelDispatcher()
        output_file = tmp_path / "output.xlsx"
        df = pd.DataFrame({"col1": [1, 2, 3], "col2": ["a", "b", "c"]})
        data = {"test_sheet": df}

        dispatcher.dispatch(str(output_file), data)

        result_df = pd.read_excel(output_file, sheet_name="test_sheet")
        pd.testing.assert_frame_equal(result_df, df)

    def test_excel_dispatcher_no_index_in_output(self, tmp_path: Path):
        """Test that Excel sheets are written without index."""
        dispatcher = ExcelDispatcher()
        output_file = tmp_path / "output.xlsx"
        data = {"table1": pd.DataFrame({"col1": [1, 2]})}

        dispatcher.dispatch(str(output_file), data)

        result_df = pd.read_excel(output_file, sheet_name="table1")
        assert "Unnamed" not in result_df.columns

    def test_excel_dispatcher_empty_dataframe(self, tmp_path: Path):
        """Test dispatching empty DataFrame to Excel."""
        dispatcher = ExcelDispatcher()
        output_file = tmp_path / "output.xlsx"
        data = {"empty_sheet": pd.DataFrame()}

        dispatcher.dispatch(str(output_file), data)

        assert output_file.exists()
        excel_file = pd.ExcelFile(output_file)
        assert "empty_sheet" in excel_file.sheet_names

    def test_excel_dispatcher_multiple_sheets(self, tmp_path: Path):
        """Test dispatching multiple tables as sheets."""
        dispatcher = ExcelDispatcher()
        output_file = tmp_path / "output.xlsx"
        data = {
            "sheet1": pd.DataFrame({"a": [1, 2]}),
            "sheet2": pd.DataFrame({"b": [3, 4]}),
            "sheet3": pd.DataFrame({"c": [5, 6]}),
        }

        dispatcher.dispatch(str(output_file), data)

        excel_file = pd.ExcelFile(output_file)
        assert len(excel_file.sheet_names) == 3

    def test_excel_dispatcher_uses_openpyxl_engine(self, tmp_path: Path):
        """Test that ExcelDispatcher uses openpyxl engine."""
        dispatcher = ExcelDispatcher()
        output_file = tmp_path / "output.xlsx"
        data = {"table1": pd.DataFrame({"col1": [1, 2]})}

        with patch("pandas.ExcelWriter") as mock_writer:
            mock_writer.return_value.__enter__ = Mock()
            mock_writer.return_value.__exit__ = Mock()

            dispatcher.dispatch(str(output_file), data)

            mock_writer.assert_called_once_with(str(output_file), engine="openpyxl")


class TestDatabaseDispatcher:
    """Tests for DatabaseDispatcher class."""

    def test_database_dispatcher_instantiation(self):
        """Test creating a DatabaseDispatcher instance."""
        dispatcher = DatabaseDispatcher()
        assert dispatcher is not None

    @with_test_config
    @patch("src.arbodat.dispatch.create_db_uri")
    @patch("sqlalchemy.create_engine")
    def test_database_dispatcher_gets_config(self, mock_create_engine, mock_create_uri, test_provider: MockConfigProvider):
        """Test that DatabaseDispatcher calls create_db_uri."""
        dispatcher = DatabaseDispatcher()
        data = {"table1": pd.DataFrame({"col1": [1, 2]})}

        # Setup mocks
        mock_create_uri.return_value = "postgresql://user@localhost:5432/db"
        mock_engine = Mock()
        mock_connection = Mock()
        mock_engine.begin.return_value.__enter__ = Mock(return_value=mock_connection)
        mock_engine.begin.return_value.__exit__ = Mock()
        mock_create_engine.return_value = mock_engine

        with patch.object(pd.DataFrame, "to_sql"):
            dispatcher.dispatch("target", data)

        # Just verify that create_db_uri was called
        mock_create_uri.assert_called_once()

    @with_test_config
    @patch("src.arbodat.dispatch.create_db_uri")
    @patch("sqlalchemy.create_engine")
    def test_database_dispatcher_creates_db_uri(self, mock_create_engine, mock_create_uri, test_provider: MockConfigProvider):
        """Test that DatabaseDispatcher creates database URI."""
        dispatcher = DatabaseDispatcher()
        data = {"table1": pd.DataFrame({"col1": [1, 2]})}

        mock_create_uri.return_value = "postgresql://testuser@localhost:5432/testdb"
        mock_engine = Mock()
        mock_connection = Mock()
        mock_engine.begin.return_value.__enter__ = Mock(return_value=mock_connection)
        mock_engine.begin.return_value.__exit__ = Mock()
        mock_create_engine.return_value = mock_engine

        with patch.object(pd.DataFrame, "to_sql"):
            dispatcher.dispatch("target", data)

        # Verify create_db_uri was called
        mock_create_uri.assert_called_once()

    @with_test_config
    @patch("src.arbodat.dispatch.create_db_uri")
    @patch("sqlalchemy.create_engine")
    def test_database_dispatcher_creates_engine(self, mock_create_engine, mock_create_uri, test_provider: MockConfigProvider):
        """Test that DatabaseDispatcher creates SQLAlchemy engine."""
        dispatcher = DatabaseDispatcher()
        data = {"table1": pd.DataFrame({"col1": [1, 2]})}

        db_url = "postgresql://user@localhost:5432/db"
        mock_create_uri.return_value = db_url
        mock_engine = Mock()
        mock_connection = Mock()
        mock_engine.begin.return_value.__enter__ = Mock(return_value=mock_connection)
        mock_engine.begin.return_value.__exit__ = Mock()
        mock_create_engine.return_value = mock_engine

        with patch.object(pd.DataFrame, "to_sql"):
            dispatcher.dispatch("target", data)

        mock_create_engine.assert_called_once_with(url=db_url)

    @with_test_config
    @patch("src.arbodat.dispatch.create_db_uri")
    @patch("sqlalchemy.create_engine")
    def test_database_dispatcher_writes_tables(self, mock_create_engine, mock_create_uri, test_provider: MockConfigProvider):
        """Test that DatabaseDispatcher writes all tables to database."""
        dispatcher = DatabaseDispatcher()
        df1 = pd.DataFrame({"col1": [1, 2]})
        df2 = pd.DataFrame({"col2": [3, 4]})
        data = {"table1": df1, "table2": df2}

        mock_create_uri.return_value = "postgresql://user@localhost:5432/db"
        mock_engine = Mock()
        mock_connection = Mock()
        mock_engine.begin.return_value.__enter__ = Mock(return_value=mock_connection)
        mock_engine.begin.return_value.__exit__ = Mock()
        mock_create_engine.return_value = mock_engine

        with patch.object(pd.DataFrame, "to_sql") as mock_to_sql:
            dispatcher.dispatch("target", data)

            assert mock_to_sql.call_count == 2

    @with_test_config
    @patch("src.arbodat.dispatch.create_db_uri")
    @patch("sqlalchemy.create_engine")
    def test_database_dispatcher_replaces_existing_tables(self, mock_create_engine, mock_create_uri, test_provider: MockConfigProvider):
        """Test that DatabaseDispatcher replaces existing tables."""
        dispatcher = DatabaseDispatcher()
        data = {"table1": pd.DataFrame({"col1": [1, 2]})}

        mock_create_uri.return_value = "postgresql://user@localhost:5432/db"
        mock_engine = Mock()
        mock_connection = Mock()
        mock_engine.begin.return_value.__enter__ = Mock(return_value=mock_connection)
        mock_engine.begin.return_value.__exit__ = Mock()
        mock_create_engine.return_value = mock_engine

        with patch.object(pd.DataFrame, "to_sql") as mock_to_sql:
            dispatcher.dispatch("target", data)

            # Verify if_exists parameter is set to "replace"
            call_kwargs = mock_to_sql.call_args[1]
            assert call_kwargs["if_exists"] == "replace"

    @with_test_config
    @patch("src.arbodat.dispatch.create_db_uri")
    @patch("sqlalchemy.create_engine")
    def test_database_dispatcher_no_index_in_output(self, mock_create_engine, mock_create_uri, test_provider: MockConfigProvider):
        """Test that DatabaseDispatcher writes tables without index."""
        dispatcher = DatabaseDispatcher()
        data = {"table1": pd.DataFrame({"col1": [1, 2]})}

        mock_create_uri.return_value = "postgresql://user@localhost:5432/db"
        mock_engine = Mock()
        mock_connection = Mock()
        mock_engine.begin.return_value.__enter__ = Mock(return_value=mock_connection)
        mock_engine.begin.return_value.__exit__ = Mock()
        mock_create_engine.return_value = mock_engine

        with patch.object(pd.DataFrame, "to_sql") as mock_to_sql:
            dispatcher.dispatch("target", data)

            # Verify index parameter is set to False
            call_kwargs = mock_to_sql.call_args[1]
            assert call_kwargs["index"] is False

    @with_test_config
    @patch("src.arbodat.dispatch.create_db_uri")
    @patch("sqlalchemy.create_engine")
    def test_database_dispatcher_uses_transaction(self, mock_create_engine, mock_create_uri, test_provider: MockConfigProvider):
        """Test that DatabaseDispatcher uses transaction context."""
        dispatcher = DatabaseDispatcher()
        data = {"table1": pd.DataFrame({"col1": [1, 2]})}

        mock_create_uri.return_value = "postgresql://user@localhost:5432/db"
        mock_engine = Mock()
        mock_connection = Mock()
        mock_engine.begin.return_value.__enter__ = Mock(return_value=mock_connection)
        mock_engine.begin.return_value.__exit__ = Mock()
        mock_create_engine.return_value = mock_engine

        with patch.object(pd.DataFrame, "to_sql"):
            dispatcher.dispatch("target", data)

            # Verify begin() was called to start transaction
            mock_engine.begin.assert_called_once()

    @with_test_config
    @patch("src.arbodat.dispatch.create_db_uri")
    @patch("sqlalchemy.create_engine")
    def test_database_dispatcher_uses_create_db_uri(self, mock_create_engine, mock_create_uri, test_provider: MockConfigProvider):
        """Test that DatabaseDispatcher calls create_db_uri to build connection string."""
        dispatcher = DatabaseDispatcher()
        data = {"table1": pd.DataFrame({"col1": [1, 2]})}

        mock_create_uri.return_value = "postgresql://user@localhost:5432/db"
        mock_engine = Mock()
        mock_connection = Mock()
        mock_engine.begin.return_value.__enter__ = Mock(return_value=mock_connection)
        mock_engine.begin.return_value.__exit__ = Mock()
        mock_create_engine.return_value = mock_engine

        with patch.object(pd.DataFrame, "to_sql"):
            dispatcher.dispatch("target", data)

            # Should call create_db_uri
            mock_create_uri.assert_called_once()


class TestIntegration:
    """Integration tests for dispatcher workflow."""

    def test_csv_dispatcher_round_trip(self, tmp_path: Path):
        """Test writing and reading CSV data maintains integrity."""
        dispatcher = CSVDispatcher()
        output_dir = tmp_path / "csv_output"

        original_df = pd.DataFrame(
            {
                "id": [1, 2, 3],
                "name": ["Alice", "Bob", "Charlie"],
                "value": [10.5, 20.3, 30.7],
            }
        )
        data = {"test_table": original_df}

        dispatcher.dispatch(str(output_dir), data)

        # Read back and verify
        result_df = pd.read_csv(output_dir / "test_table.csv")
        pd.testing.assert_frame_equal(result_df, original_df)

    def test_excel_dispatcher_round_trip(self, tmp_path: Path):
        """Test writing and reading Excel data maintains integrity."""
        dispatcher = ExcelDispatcher()
        output_file = tmp_path / "output.xlsx"

        original_df = pd.DataFrame(
            {
                "id": [1, 2, 3],
                "name": ["Alice", "Bob", "Charlie"],
                "value": [10.5, 20.3, 30.7],
            }
        )
        data = {"test_sheet": original_df}

        dispatcher.dispatch(str(output_file), data)

        # Read back and verify
        result_df = pd.read_excel(output_file, sheet_name="test_sheet")
        pd.testing.assert_frame_equal(result_df, original_df)

    def test_dispatchers_registry_workflow(self):
        """Test getting and using dispatchers from registry."""
        # Get each dispatcher type from registry
        csv_dispatcher_cls = Dispatchers.get("csv")
        xlsx_dispatcher_cls = Dispatchers.get("xlsx")
        db_dispatcher_cls = Dispatchers.get("db")

        # Verify they can be instantiated
        csv_dispatcher = csv_dispatcher_cls()
        xlsx_dispatcher = xlsx_dispatcher_cls()
        db_dispatcher = db_dispatcher_cls()

        assert isinstance(csv_dispatcher, CSVDispatcher)
        assert isinstance(xlsx_dispatcher, ExcelDispatcher)
        assert isinstance(db_dispatcher, DatabaseDispatcher)

    def test_multiple_tables_csv(self, tmp_path: Path):
        """Test dispatching multiple related tables to CSV."""
        dispatcher = CSVDispatcher()
        output_dir = tmp_path / "csv_output"

        data = {
            "users": pd.DataFrame({"user_id": [1, 2], "name": ["Alice", "Bob"]}),
            "orders": pd.DataFrame({"order_id": [1, 2], "user_id": [1, 2], "amount": [100, 200]}),
            "products": pd.DataFrame({"product_id": [1, 2], "name": ["Widget", "Gadget"]}),
        }

        dispatcher.dispatch(str(output_dir), data)

        # Verify all tables were created
        assert (output_dir / "users.csv").exists()
        assert (output_dir / "orders.csv").exists()
        assert (output_dir / "products.csv").exists()

    def test_multiple_tables_excel(self, tmp_path: Path):
        """Test dispatching multiple related tables to Excel sheets."""
        dispatcher = ExcelDispatcher()
        output_file = tmp_path / "output.xlsx"

        data = {
            "users": pd.DataFrame({"user_id": [1, 2], "name": ["Alice", "Bob"]}),
            "orders": pd.DataFrame({"order_id": [1, 2], "user_id": [1, 2], "amount": [100, 200]}),
            "products": pd.DataFrame({"product_id": [1, 2], "name": ["Widget", "Gadget"]}),
        }

        dispatcher.dispatch(str(output_file), data)

        # Verify all sheets were created
        excel_file = pd.ExcelFile(output_file)
        assert "users" in excel_file.sheet_names
        assert "orders" in excel_file.sheet_names
        assert "products" in excel_file.sheet_names
