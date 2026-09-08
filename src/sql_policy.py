"""Read-only SQL validation shared by core loaders and the backend."""

from dataclasses import dataclass

import sqlparse
from sqlparse.sql import Statement
from sqlparse.tokens import DDL, DML, Comment, Keyword

READ_ONLY_FORBIDDEN_KEYWORDS: set[str] = {
    "ANALYZE",
    "ALTER",
    "ATTACH",
    "BEGIN",
    "CALL",
    "CHECKPOINT",
    "COMMIT",
    "COPY",
    "CREATE",
    "DEALLOCATE",
    "DELETE",
    "DETACH",
    "DO",
    "DROP",
    "EXECUTE",
    "EXPORT",
    "GRANT",
    "IMPORT",
    "INSTALL",
    "INSERT",
    "LOAD",
    "MERGE",
    "PREPARE",
    "PRAGMA",
    "REPLACE",
    "RESET",
    "REVOKE",
    "ROLLBACK",
    "SET",
    "SHOW",
    "TRUNCATE",
    "UPDATE",
    "USE",
    "VACUUM",
}


@dataclass(frozen=True)
class SQLSafetyResult:
    """Result of validating SQL against the shared read-only execution policy."""

    statement_type: str | None
    errors: list[str]
    warnings: list[str]

    @property
    def is_valid(self) -> bool:
        """Return whether the query may be executed."""
        return not self.errors


def _has_executable_tokens(statement: Statement) -> bool:
    """Return whether a parsed statement contains executable tokens."""
    for token in statement.flatten():
        if token.is_whitespace or token.ttype in Comment or token.value == ";":
            continue
        return True
    return False


def _statement_type(statement: Statement) -> str | None:
    """Return the first SQL operation token in a statement."""
    for token in statement.flatten():
        if token.ttype in (DML, DDL):
            return token.value.upper()
        if token.ttype is Keyword and token.value.upper() in READ_ONLY_FORBIDDEN_KEYWORDS:
            return token.value.upper()
    return None


def _find_forbidden_operation(statement: Statement) -> str | None:
    """Return the first forbidden operation token, including nested query tokens."""
    for token in statement.flatten():
        if token.ttype in (DML, DDL, Keyword):
            operation = token.value.upper()
            if operation in READ_ONLY_FORBIDDEN_KEYWORDS:
                return operation
    return None


def validate_read_only_sql(sql: str) -> SQLSafetyResult:
    """Validate SQL as one read-only statement before database execution."""
    try:
        parsed = [statement for statement in sqlparse.parse(sql) if _has_executable_tokens(statement)]
    except Exception as exc:  # pylint: disable=broad-except
        return SQLSafetyResult(statement_type=None, errors=[f"SQL syntax error: {exc}"], warnings=[])

    if not parsed:
        return SQLSafetyResult(statement_type=None, errors=["Empty or invalid SQL query"], warnings=[])

    errors: list[str] = []
    statement_type = _statement_type(parsed[0])

    if len(parsed) > 1:
        errors.append("Multiple statements are not allowed.")

    for statement in parsed:
        forbidden_operation = _find_forbidden_operation(statement)
        if forbidden_operation:
            errors.append(f"SQL operation '{forbidden_operation}' is not allowed. Only read-only SELECT queries are permitted.")

        current_type = _statement_type(statement)
        if current_type is None:
            errors.append("Only SELECT queries are allowed; the SQL operation could not be classified safely.")
        elif current_type not in READ_ONLY_FORBIDDEN_KEYWORDS and current_type != "SELECT":
            errors.append(f"Only SELECT queries are allowed. Found '{current_type}' statement.")

    return SQLSafetyResult(statement_type=statement_type, errors=list(dict.fromkeys(errors)), warnings=[])


def ensure_read_only_sql(sql: str) -> None:
    """Raise ``ValueError`` when SQL is not permitted by the shared policy."""
    result = validate_read_only_sql(sql)
    if not result.is_valid:
        raise ValueError("Query contains prohibited operations: " + "; ".join(result.errors))
