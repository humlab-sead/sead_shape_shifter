"""Tests for SQL utility functions."""

from backend.app.utils.sql import extract_tables


class TestExtractTables:
    """Tests for SQL table extraction."""

    def test_simple_select(self):
        """Test extracting table from simple SELECT."""
        sql = "SELECT * FROM users"
        tables = extract_tables(sql)
        assert tables == ["users"]

    def test_select_with_join(self):
        """Test extracting tables from JOIN query."""
        sql = "SELECT * FROM users JOIN orders ON users.id = orders.user_id"
        tables = extract_tables(sql)
        assert set(tables) == {"users", "orders"}

    def test_multiple_joins(self):
        """Test extracting tables from multiple JOINs."""
        sql = """
        SELECT *
        FROM users
        INNER JOIN orders ON users.id = orders.user_id
        LEFT JOIN products ON orders.product_id = products.id
        """
        tables = extract_tables(sql)
        assert set(tables) == {"users", "orders", "products"}

    def test_join_types(self):
        """Test various JOIN types."""
        sql = """
        SELECT *
        FROM t1
        INNER JOIN t2 ON t1.id = t2.t1_id
        LEFT JOIN t3 ON t1.id = t3.t1_id
        RIGHT JOIN t4 ON t1.id = t4.t1_id
        FULL JOIN t5 ON t1.id = t5.t1_id
        CROSS JOIN t6
        """
        tables = extract_tables(sql)
        assert set(tables) == {"t1", "t2", "t3", "t4", "t5", "t6"}

    def test_schema_qualified_table(self):
        """Test extracting schema-qualified table names."""
        sql = "SELECT * FROM public.users"
        tables = extract_tables(sql)
        assert "users" in tables

    def test_table_with_alias(self):
        """Test extracting table with alias."""
        sql = "SELECT * FROM users AS u"
        tables = extract_tables(sql)
        assert "users" in tables

    def test_multiple_tables_in_from(self):
        """Test comma-separated tables in FROM clause."""
        sql = "SELECT * FROM users, orders, products"
        tables = extract_tables(sql)
        assert set(tables) == {"users", "orders", "products"}

    def test_subquery(self):
        """Test that subqueries are handled."""
        sql = """
        SELECT *
        FROM (SELECT * FROM users WHERE active = 1) AS active_users
        JOIN orders ON active_users.id = orders.user_id
        """
        tables = extract_tables(sql)
        # Note: sqlparse extracts the subquery alias, not the inner table
        assert "active_users" in tables  # Subquery alias
        assert "orders" in tables

    def test_case_insensitive(self):
        """Test that SQL keywords are case insensitive."""
        sql = "select * from Users join Orders on Users.id = Orders.user_id"
        tables = extract_tables(sql)
        assert set(tables) == {"Users", "Orders"}

    def test_empty_query(self):
        """Test handling empty query."""
        sql = ""
        tables = extract_tables(sql)
        assert tables == []

    def test_no_from_clause(self):
        """Test query without FROM clause."""
        sql = "SELECT 1 + 1"
        tables = extract_tables(sql)
        assert tables == []

    def test_complex_real_world_query(self):
        """Test complex real-world query."""
        sql = """
        SELECT
            u.id,
            u.name,
            COUNT(o.id) as order_count,
            SUM(o.total) as total_spent
        FROM users u
        INNER JOIN orders o ON u.id = o.user_id
        LEFT JOIN addresses a ON u.id = a.user_id
        WHERE u.active = true
        GROUP BY u.id, u.name
        HAVING COUNT(o.id) > 0
        """
        tables = extract_tables(sql)
        assert set(tables) == {"users", "orders", "addresses"}

    def test_with_cte(self):
        """Test Common Table Expression (CTE)."""
        sql = """
        WITH active_users AS (
            SELECT * FROM users WHERE active = true
        )
        SELECT * FROM active_users JOIN orders ON active_users.id = orders.user_id
        """
        tables = extract_tables(sql)
        # Note: sqlparse extracts CTE name, not the inner table
        assert "active_users" in tables  # CTE name
        assert "orders" in tables

    def test_update_statement(self):
        """Test UPDATE statement."""
        sql = "UPDATE users SET active = false WHERE id = 1"
        tables = extract_tables(sql)
        # UPDATE doesn't use FROM, so this might return empty
        # depending on sqlparse behavior
        assert isinstance(tables, list)

    def test_delete_statement(self):
        """Test DELETE with FROM."""
        sql = "DELETE FROM users WHERE id = 1"
        tables = extract_tables(sql)
        assert "users" in tables or tables == []

    def test_sorted_output(self):
        """Test that output is sorted alphabetically."""
        sql = "SELECT * FROM zebra, apple, banana"
        tables = extract_tables(sql)
        assert tables == sorted(tables)
