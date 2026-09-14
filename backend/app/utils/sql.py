import sqlparse
from sqlparse.sql import Identifier, IdentifierList, Statement
from sqlparse.tokens import DDL, DML, Keyword
from sqlparse.tokens import Wildcard as WildcardToken

from src.sql_policy import SQLSafetyResult, validate_read_only_sql

__all__ = ["SQLSafetyResult", "validate_read_only_sql"]

FROM_CLAUSE_KEYWORDS: set[str] = {
    "FROM",
    "JOIN",
    "INNER JOIN",
    "LEFT JOIN",
    "RIGHT JOIN",
    "FULL JOIN",
    "CROSS JOIN",
}


def _resolve_select_alias(identifier: Identifier) -> str:
    """Return effective output name for a SELECT-list identifier: alias > real_name > raw value."""
    alias = identifier.get_alias()
    if alias:
        return alias
    real_name = identifier.get_real_name()
    if real_name:
        return real_name
    return identifier.value.strip()


def has_wildcard_select(sql: str) -> bool:
    """Return True if the outermost SELECT clause projects all columns via * or table.*."""
    parsed = sqlparse.parse(sql.strip())
    if not parsed:
        return False
    statement = parsed[0]
    select_seen = False
    for token in statement.tokens:
        if token.ttype is DML and token.value.upper() == "SELECT":
            select_seen = True
            continue
        if not select_seen:
            continue
        if token.is_whitespace:
            continue
        if token.ttype is Keyword and token.value.upper() == "FROM":
            break
        # Bare *
        if token.ttype is WildcardToken:
            return True
        # table.* or any compound token that contains a wildcard
        if hasattr(token, "flatten") and any(t.ttype is WildcardToken for t in token.flatten()):
            return True
    return False


def extract_select_columns(sql: str) -> list[str]:
    """
    Extract projected column names/aliases from the outermost SELECT clause.

    For aliased expressions (``col AS alias``, ``COUNT(*) AS n``) the alias is returned.
    For plain column references (optionally table-qualified) the column name is returned.

    Raises:
        ValueError: If the query uses SELECT * or SELECT table.*.
    """
    if has_wildcard_select(sql):
        raise ValueError("SELECT * is not allowed for @internal queries — list column names explicitly.")

    parsed = sqlparse.parse(sql.strip())
    if not parsed:
        return []

    statement: Statement = parsed[0]
    columns: list[str] = []
    select_seen: bool = False

    for token in statement.tokens:
        if token.ttype is DML and token.value.upper() == "SELECT":
            select_seen = True
            continue
        if not select_seen:
            continue
        if token.is_whitespace:
            continue
        if token.ttype is Keyword and token.value.upper() in FROM_CLAUSE_KEYWORDS:
            break
        if isinstance(token, IdentifierList):
            for ident in token.get_identifiers():
                if isinstance(ident, Identifier):
                    columns.append(_resolve_select_alias(ident))
            break
        if isinstance(token, Identifier):
            columns.append(_resolve_select_alias(token))
            break

    return columns


def extract_tables(sql: str) -> list[str]:
    """
    Extract table names from an SQL query using sqlparse.

    Returns a sorted, deduplicated list of table names referenced in FROM/JOIN clauses.
    Handles Identifier objects, IdentifierLists, and bare name tokens (ttype is None).
    """
    parsed: tuple[Statement, ...] = sqlparse.parse(sql)
    tables: set[str] = set()

    for statement in parsed:
        from_seen: bool = False

        for token in statement.tokens:
            if token.ttype is Keyword and token.value.upper() in FROM_CLAUSE_KEYWORDS:
                from_seen = True
                continue

            if from_seen:
                if isinstance(token, IdentifierList):
                    for identifier in token.get_identifiers():
                        tables.add(identifier.get_real_name())
                elif isinstance(token, Identifier):
                    tables.add(token.get_real_name())
                elif token.ttype is Keyword:
                    from_seen = False
                elif token.ttype is None:
                    # Bare token — simple table name not wrapped in an Identifier object
                    table_name = token.value.strip('`"[]')
                    if "." in table_name:
                        table_name = table_name.split(".")[-1]
                    if table_name and not any(c in table_name for c in "(),"):
                        tables.add(table_name)

    return sorted(list(tables))


def get_statement_type(statement: Statement, forbidden_keywords: set[str] | None = None) -> str | None:
    """Return the SQL statement type (SELECT, INSERT, etc.) from a parsed statement."""
    for token in statement.tokens:
        if token.ttype is DML:
            return token.value.upper()
        if token.ttype is DDL:
            return token.value.upper()
        if forbidden_keywords and token.ttype is Keyword and token.value.upper() in forbidden_keywords:
            return token.value.upper()
    return None


def has_where_clause(statement: Statement) -> bool:
    """Return True if the statement contains a WHERE clause."""
    return any(t.ttype is Keyword and t.value.upper() == "WHERE" for t in statement.flatten())
