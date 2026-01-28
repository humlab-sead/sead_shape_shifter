import sqlparse
from sqlparse.sql import IdentifierList, Identifier, Statement
from sqlparse.tokens import Keyword


def extract_tables(sql: str) -> list[str]:
    """
    Extract table names from an SQL query using sqlparse.

    Returns a set of table names (as they appear in the query).
    """
    parsed: tuple[Statement, ...] = sqlparse.parse(sql)
    tables: set[str] = set()

    for statement in parsed:
        from_seen = False

        for token in statement.tokens:
            if token.ttype is Keyword and token.value.upper() in {
                "FROM",
                "JOIN",
                "INNER JOIN",
                "LEFT JOIN",
                "RIGHT JOIN",
                "FULL JOIN",
                "CROSS JOIN",
            }:
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

    return sorted(list(tables))
