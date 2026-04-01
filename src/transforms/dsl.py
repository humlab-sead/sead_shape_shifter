"""
dsl.py

A hand-written recursive descent parser for the formula DSL used in extra_columns.

Implementation:
- Zero dependencies (stdlib + pandas only)
- Hand-written tokenizer and recursive descent parser
- ~300 lines of parsing logic
- Fast and transparent

Features:
- Narrow formula syntax: =concat(first_name, ' ', last_name)
- No Python eval
- No Pandas API exposure
- Whitelisted functions only
- Source locations for user-friendly errors
- Validation phase separate from evaluation phase
- Backend abstraction with Pandas implementation

Grammar:
    formula      ::= "=" expr
    expr         ::= function_call | column_ref | literal
    function_call::= NAME "(" [arg_list] ")"
    arg_list     ::= expr ("," expr)*
    column_ref   ::= NAME
    literal      ::= STRING | INTEGER | "null" | "true" | "false"
    NAME         ::= [a-zA-Z_][a-zA-Z0-9_]*
    STRING       ::= '"' ... '"' | "'" ... "'"
    INTEGER      ::= [0-9]+ | "-" [0-9]+

Example:
    from src.transforms.dsl import FormulaEngine

    engine = FormulaEngine()
    df = pd.DataFrame({"first": ["Ada"], "last": ["Lovelace"]})
    df["fullname"] = engine.evaluate_formula("=concat(first, ' ', last)", df)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Callable, Iterable, Protocol

import pandas as pd

# ============================================================================
# Error types
# ============================================================================


@dataclass(frozen=True)
class SourceSpan:
    line: int
    column: int
    end_line: int
    end_column: int

    def format(self) -> str:
        return f"line {self.line}, column {self.column}"


class DSLException(Exception):
    """Base class for user-facing DSL exceptions."""

    def __init__(self, message: str, span: SourceSpan | None = None) -> None:
        self.message: str = message
        self.span: SourceSpan | None = span
        if span is None:
            super().__init__(message)
        else:
            super().__init__(f"{message} ({span.format()})")


class DSLParseError(DSLException):
    pass


class DSLValidationError(DSLException):
    pass


class DSLEvaluationError(DSLException):
    pass


# ============================================================================
# AST
# ============================================================================


@dataclass(frozen=True)
class Expr:
    """Base class for all expression nodes."""

    span: SourceSpan


@dataclass(frozen=True)
class Literal(Expr):
    """Literal value (string, int, bool, or null)."""

    value: Any


@dataclass(frozen=True)
class ColumnRef(Expr):
    """Reference to a column by name."""

    name: str


@dataclass(frozen=True)
class Call(Expr):
    """Function call expression."""

    name: str
    args: list[Expr]


# ============================================================================
# Helper Functions
# ============================================================================


def extract_column_references(expr: Expr) -> set[str]:
    """Extract all column references from an expression AST.

    Args:
        expr: Expression AST node

    Returns:
        Set of column names referenced in the expression

    Examples:
        >>> parser = Parser()
        >>> ast = parser.parse("concat(first_name, ' ', last_name)")
        >>> extract_column_references(ast)
        {'first_name', 'last_name'}
        >>>
        >>> ast = parser.parse("'constant'")
        >>> extract_column_references(ast)
        set()
    """
    if isinstance(expr, ColumnRef):
        return {expr.name}
    if isinstance(expr, Literal):
        return set()
    if isinstance(expr, Call):
        refs = set()
        for arg in expr.args:
            refs.update(extract_column_references(arg))
        return refs
    return set()


# ============================================================================
# Tokenizer
# ============================================================================


class TokenType(Enum):
    """Token types for the DSL."""

    NAME = auto()
    STRING = auto()
    INTEGER = auto()
    LPAREN = auto()
    RPAREN = auto()
    COMMA = auto()
    EQUAL = auto()
    EOF = auto()


@dataclass(frozen=True)
class Token:
    """A token with position information."""

    type: TokenType
    value: str
    span: SourceSpan


class Tokenizer:
    """Hand-written tokenizer for the formula DSL."""

    # Token patterns (order matters - longer matches first)
    PATTERNS = [
        (TokenType.STRING, r"""("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')"""),
        (TokenType.INTEGER, r"-?\d+"),
        (TokenType.NAME, r"[a-zA-Z_][a-zA-Z0-9_]*"),
        (TokenType.LPAREN, r"\("),
        (TokenType.RPAREN, r"\)"),
        (TokenType.COMMA, r","),
        (TokenType.EQUAL, r"="),
    ]

    def __init__(self, source: str) -> None:
        self.source: str = source
        self.pos: int = 0
        self.line: int = 1
        self.column: int = 1
        self.tokens: list[Token] = []
        self._tokenize()

    def _tokenize(self) -> None:
        """Tokenize the entire source string."""
        while self.pos < len(self.source):
            # Skip whitespace
            if self.source[self.pos].isspace():
                if self.source[self.pos] == "\n":
                    self.line += 1
                    self.column = 1
                else:
                    self.column += 1
                self.pos += 1
                continue

            # Try to match token patterns
            matched = False
            for token_type, pattern in self.PATTERNS:
                regex = re.compile(pattern)
                match = regex.match(self.source, self.pos)
                if match:
                    value = match.group(0)
                    span = SourceSpan(
                        line=self.line,
                        column=self.column,
                        end_line=self.line,
                        end_column=self.column + len(value),
                    )
                    self.tokens.append(Token(type=token_type, value=value, span=span))
                    self.pos = match.end()
                    self.column += len(value)
                    matched = True
                    break

            if not matched:
                span = SourceSpan(
                    line=self.line,
                    column=self.column,
                    end_line=self.line,
                    end_column=self.column + 1,
                )
                raise DSLParseError(
                    f"Unexpected character: {self.source[self.pos]!r}",
                    span=span,
                )

        # Add EOF token
        span = SourceSpan(
            line=self.line,
            column=self.column,
            end_line=self.line,
            end_column=self.column,
        )
        self.tokens.append(Token(type=TokenType.EOF, value="", span=span))


# ============================================================================
# Parser
# ============================================================================


class Parser:
    """Hand-written recursive descent parser."""

    def __init__(self, tokens: list[Token]) -> None:
        self.tokens: list[Token] = tokens
        self.pos: int = 0

    def parse(self) -> Expr:
        """Parse a formula starting with '='."""
        if not self.match(TokenType.EQUAL):
            raise DSLParseError(
                "Formula must start with '='",
                span=self.current().span,
            )
        expr = self.parse_expr()
        if not self.match(TokenType.EOF):
            raise DSLParseError(
                f"Unexpected token after expression: {self.current().value!r}",
                span=self.current().span,
            )
        return expr

    def parse_expr(self) -> Expr:
        """Parse an expression: function_call | column_ref | literal."""
        token = self.current()

        # Check for function call: NAME followed by "("
        if token.type == TokenType.NAME and self.peek(1).type == TokenType.LPAREN:
            return self.parse_function_call()

        # Check for reserved literal keywords (null, true, false)
        if token.type == TokenType.NAME and token.value in ("null", "true", "false"):
            return self.parse_literal()

        # Check for column reference: NAME not followed by "("
        if token.type == TokenType.NAME:
            return self.parse_column_ref()

        # Otherwise try literal
        return self.parse_literal()

    def parse_function_call(self) -> Call:
        """Parse a function call: NAME "(" [arg_list] ")"."""
        name_token = self.consume(TokenType.NAME)
        start_span = name_token.span

        self.consume(TokenType.LPAREN)

        # Parse arguments
        args: list[Expr] = []
        if not self.check(TokenType.RPAREN):
            args.append(self.parse_expr())
            while self.match(TokenType.COMMA):
                args.append(self.parse_expr())

        rparen_token = self.consume(TokenType.RPAREN)

        # Combine span from function name to closing paren
        span = SourceSpan(
            line=start_span.line,
            column=start_span.column,
            end_line=rparen_token.span.end_line,
            end_column=rparen_token.span.end_column,
        )

        return Call(span=span, name=name_token.value, args=args)

    def parse_column_ref(self) -> ColumnRef:
        """Parse a column reference: NAME."""
        token = self.consume(TokenType.NAME)
        return ColumnRef(span=token.span, name=token.value)

    def parse_literal(self) -> Literal:
        """Parse a literal: STRING | INTEGER | null | true | false."""
        token = self.current()

        if token.type == TokenType.STRING:
            self.advance()
            # Unescape the string (remove quotes and handle escapes)
            value = self._unescape_string(token.value)
            return Literal(span=token.span, value=value)

        if token.type == TokenType.INTEGER:
            self.advance()
            return Literal(span=token.span, value=int(token.value))

        if token.type == TokenType.NAME:
            self.advance()
            if token.value == "null":
                return Literal(span=token.span, value=None)
            if token.value == "true":
                return Literal(span=token.span, value=True)
            if token.value == "false":
                return Literal(span=token.span, value=False)
            # If we're here, it's an unexpected name
            raise DSLParseError(
                f"Unexpected identifier: {token.value!r}. Expected a literal, column, or function call.",
                span=token.span,
            )

        raise DSLParseError(
            f"Expected literal, got {token.type.name}",
            span=token.span,
        )

    def _unescape_string(self, s: str) -> str:
        """Unescape a string literal (remove quotes, handle escapes)."""
        # Remove surrounding quotes
        if len(s) >= 2 and s[0] in ('"', "'") and s[-1] == s[0]:
            s = s[1:-1]

        # Handle escape sequences
        s = s.replace("\\n", "\n")
        s = s.replace("\\t", "\t")
        s = s.replace("\\r", "\r")
        s = s.replace("\\\\", "\\")
        s = s.replace("\\'", "'")
        s = s.replace('\\"', '"')

        return s

    # ---- Token navigation helpers ----

    def current(self) -> Token:
        """Get the current token."""
        return self.tokens[self.pos]

    def peek(self, offset: int = 1) -> Token:
        """Peek ahead at a token."""
        pos = self.pos + offset
        if pos >= len(self.tokens):
            return self.tokens[-1]  # Return EOF
        return self.tokens[pos]

    def advance(self) -> Token:
        """Consume and return the current token."""
        token = self.current()
        if token.type != TokenType.EOF:
            self.pos += 1
        return token

    def check(self, token_type: TokenType) -> bool:
        """Check if current token matches type (without consuming)."""
        return self.current().type == token_type

    def match(self, token_type: TokenType) -> bool:
        """Check and consume if current token matches type."""
        if self.check(token_type):
            self.advance()
            return True
        return False

    def consume(self, token_type: TokenType) -> Token:
        """Consume a token of the expected type or error."""
        token = self.current()
        if token.type != token_type:
            raise DSLParseError(
                f"Expected {token_type.name}, got {token.type.name}",
                span=token.span,
            )
        return self.advance()


class FormulaParser:
    """High-level parser interface."""

    def parse(self, source: str) -> Expr:
        """Parse a formula string into an AST."""
        try:
            tokenizer = Tokenizer(source)
            parser = Parser(tokenizer.tokens)
            return parser.parse()
        except DSLException:
            raise
        except Exception as e:
            raise DSLParseError(f"Parse error: {e}") from e


# ============================================================================
# Function specifications and validation
# ============================================================================


@dataclass(frozen=True)
class FunctionSpec:
    """Specification for a function in the DSL."""

    name: str
    impl_name: str
    exact_args: int | None = None
    min_args: int | None = None
    max_args: int | None = None
    description: str = ""


def validate_arity(spec: FunctionSpec, argc: int, span: SourceSpan) -> None:
    """Validate the number of arguments for a function call."""
    if spec.exact_args is not None and argc != spec.exact_args:
        raise DSLValidationError(
            f"Function '{spec.name}' expects exactly {spec.exact_args} arguments, got {argc}",
            span=span,
        )
    if spec.min_args is not None and argc < spec.min_args:
        raise DSLValidationError(
            f"Function '{spec.name}' expects at least {spec.min_args} arguments, got {argc}",
            span=span,
        )
    if spec.max_args is not None and argc > spec.max_args:
        raise DSLValidationError(
            f"Function '{spec.name}' expects at most {spec.max_args} arguments, got {argc}",
            span=span,
        )


@dataclass(frozen=True)
class ValidationConfig:
    """Configuration for the validator."""

    max_depth: int = 20
    max_total_nodes: int = 500
    max_string_literal_length: int = 10_000


class Validator:
    """Validator for expressions in the DSL."""

    def __init__(
        self,
        allowed_columns: set[str],
        functions: dict[str, FunctionSpec],
        config: ValidationConfig | None = None,
    ) -> None:
        self.allowed_columns: set[str] = allowed_columns
        self.functions: dict[str, FunctionSpec] = functions
        self.config: ValidationConfig = config or ValidationConfig()

    def validate(self, expr: Expr) -> None:
        """Validate the expression against the allowed columns, functions, and config."""
        self._validate(expr, depth=1)
        total_nodes: int = self._count_nodes(expr)
        if total_nodes > self.config.max_total_nodes:
            raise DSLValidationError(
                f"Expression is too complex: {total_nodes} AST nodes exceeds " f"limit of {self.config.max_total_nodes}",
                span=expr.span,
            )

    def _validate(self, expr: Expr, depth: int) -> None:
        """Recursively validate an expression node."""
        if depth > self.config.max_depth:
            raise DSLValidationError(
                f"Expression nesting exceeds maximum depth of {self.config.max_depth}",
                span=expr.span,
            )

        if isinstance(expr, Literal):
            if isinstance(expr.value, str) and len(expr.value) > self.config.max_string_literal_length:
                raise DSLValidationError(
                    f"String literal exceeds maximum length of " f"{self.config.max_string_literal_length}",
                    span=expr.span,
                )
            return

        if isinstance(expr, ColumnRef):
            if expr.name not in self.allowed_columns:
                raise DSLValidationError(
                    f"Unknown column '{expr.name}'",
                    span=expr.span,
                )
            return

        if isinstance(expr, Call):
            spec: FunctionSpec | None = self.functions.get(expr.name)
            if spec is None:
                allowed = ", ".join(sorted(self.functions))
                raise DSLValidationError(
                    f"Unknown function '{expr.name}'. Allowed functions: {allowed}",
                    span=expr.span,
                )
            validate_arity(spec, len(expr.args), expr.span)
            for arg in expr.args:
                self._validate(arg, depth + 1)
            return

        raise DSLValidationError(
            f"Unsupported expression node type: {type(expr).__name__}",
            span=expr.span,
        )

    def _count_nodes(self, expr: Expr) -> int:
        """Count the number of nodes in an expression."""
        if isinstance(expr, (Literal, ColumnRef)):
            return 1
        if isinstance(expr, Call):
            return 1 + sum(self._count_nodes(arg) for arg in expr.args)
        return 1


# ============================================================================
# Backend abstraction
# ============================================================================


class Backend(Protocol):
    def get_column(self, name: str) -> Any: ...

    def literal(self, value: Any) -> Any: ...

    def call(self, impl_name: str, args: list[Any], span: SourceSpan) -> Any: ...


# ============================================================================
# Pandas backend
# ============================================================================


class PandasStringBackend:
    """
    Backend that evaluates DSL functions against a Pandas DataFrame.

    Evaluation values are either:
    - scalar literals
    - pd.Series
    """

    def __init__(self, df: pd.DataFrame):
        self.df: pd.DataFrame = df
        self._dispatch: dict[str, Callable[..., Any]] = {
            "concat": self._fn_concat,
            "upper": self._fn_upper,
            "lower": self._fn_lower,
            "trim": self._fn_trim,
            "substr": self._fn_substr,
            "coalesce": self._fn_coalesce,
        }

    def get_column(self, name: str) -> pd.Series:
        try:
            return self.df[name]
        except KeyError as e:
            raise DSLEvaluationError(f"Column '{name}' does not exist") from e

    def literal(self, value: Any) -> Any:
        return value

    def call(self, impl_name: str, args: list[Any], span: SourceSpan) -> Any:
        fn = self._dispatch.get(impl_name)
        if fn is None:
            raise DSLEvaluationError(f"No backend implementation for '{impl_name}'", span=span)
        try:
            return fn(*args)
        except DSLException:
            raise
        except Exception as e:
            raise DSLEvaluationError(
                f"Failed to evaluate function '{impl_name}': {e}",
                span=span,
            ) from e

    # ---- helpers ---------------------------------------------------------

    def _is_series(self, value: Any) -> bool:
        return isinstance(value, pd.Series)

    def _ensure_series(self, value: Any) -> pd.Series:
        if isinstance(value, pd.Series):
            return value
        return pd.Series([value] * len(self.df), index=self.df.index)

    def _to_nullable_string_series(self, value: Any) -> pd.Series:
        s = self._ensure_series(value)
        return s.astype("string")

    def _require_scalar_int(self, value: Any, fn_name: str) -> int:
        if isinstance(value, pd.Series):
            raise DSLEvaluationError(f"Function '{fn_name}' requires integer literal arguments, not column references")
        try:
            return int(value)
        except Exception as e:
            raise DSLEvaluationError(f"Function '{fn_name}' expected an integer argument, got {value!r}") from e

    # ---- functions -------------------------------------------------------

    def _fn_concat(self, *args: Any) -> pd.Series:
        if not args:
            raise DSLEvaluationError("concat expects at least one argument")

        series_args: list[pd.Series] = [self._to_nullable_string_series(arg) for arg in args]
        result: pd.Series = series_args[0]
        for s in series_args[1:]:
            result = result.str.cat(s, na_rep="")
        return result

    def _fn_upper(self, value: Any) -> pd.Series:
        return self._to_nullable_string_series(value).str.upper()

    def _fn_lower(self, value: Any) -> pd.Series:
        return self._to_nullable_string_series(value).str.lower()

    def _fn_trim(self, value: Any) -> pd.Series:
        return self._to_nullable_string_series(value).str.strip()

    def _fn_substr(self, value: Any, start: Any, length: Any) -> pd.Series:
        s = self._to_nullable_string_series(value)
        start_i: int = self._require_scalar_int(start, "substr")
        length_i: int = self._require_scalar_int(length, "substr")
        if length_i < 0:
            raise DSLEvaluationError("Function 'substr' requires non-negative length")
        return s.str.slice(start_i, start_i + length_i)

    def _fn_coalesce(self, *args: Any) -> pd.Series:
        if not args:
            raise DSLEvaluationError("coalesce expects at least one argument")

        result: pd.Series = self._ensure_series(args[0])
        for arg in args[1:]:
            other: pd.Series = self._ensure_series(arg)
            result = result.where(result.notna(), other)
        return result


# ============================================================================
# Evaluator
# ============================================================================


class Evaluator:
    def __init__(self, backend: Backend, functions: dict[str, FunctionSpec]) -> None:
        self.backend: Backend = backend
        self.functions: dict[str, FunctionSpec] = functions

    def eval(self, expr: Expr) -> Any:
        if isinstance(expr, Literal):
            return self.backend.literal(expr.value)

        if isinstance(expr, ColumnRef):
            return self.backend.get_column(expr.name)

        if isinstance(expr, Call):
            spec: FunctionSpec | None = self.functions.get(expr.name)
            if spec is None:
                raise DSLEvaluationError(
                    f"Unknown function '{expr.name}'",
                    span=expr.span,
                )
            args: list[Any] = [self.eval(arg) for arg in expr.args]
            return self.backend.call(spec.impl_name, args, span=expr.span)

        raise DSLEvaluationError(
            f"Unsupported expression node type: {type(expr).__name__}",
            span=expr.span,
        )


# ============================================================================
# Public engine
# ============================================================================


DEFAULT_FUNCTIONS: dict[str, FunctionSpec] = {
    "concat": FunctionSpec(
        name="concat",
        impl_name="concat",
        min_args=1,
        description="Concatenate arguments as strings",
    ),
    "upper": FunctionSpec(
        name="upper",
        impl_name="upper",
        exact_args=1,
        description="Uppercase a string",
    ),
    "lower": FunctionSpec(
        name="lower",
        impl_name="lower",
        exact_args=1,
        description="Lowercase a string",
    ),
    "trim": FunctionSpec(
        name="trim",
        impl_name="trim",
        exact_args=1,
        description="Trim leading and trailing whitespace",
    ),
    "substr": FunctionSpec(
        name="substr",
        impl_name="substr",
        exact_args=3,
        description="Substring by start and length",
    ),
    "coalesce": FunctionSpec(
        name="coalesce",
        impl_name="coalesce",
        min_args=1,
        description="Return first non-null value",
    ),
}


class FormulaEngine:
    def __init__(
        self,
        functions: dict[str, FunctionSpec] | None = None,
        validation_config: ValidationConfig | None = None,
    ) -> None:
        self.functions: dict[str, FunctionSpec] = functions or DEFAULT_FUNCTIONS
        self.validation_config: ValidationConfig = validation_config or ValidationConfig()
        self.parser = FormulaParser()

    def parse(self, source: str) -> Expr:
        return self.parser.parse(source)

    def validate(self, expr: Expr, allowed_columns: Iterable[str]) -> None:
        validator = Validator(
            allowed_columns=set(allowed_columns),
            functions=self.functions,
            config=self.validation_config,
        )
        validator.validate(expr)

    def evaluate(self, expr: Expr, df: pd.DataFrame) -> Any:
        backend = PandasStringBackend(df)
        evaluator = Evaluator(backend=backend, functions=self.functions)
        return evaluator.eval(expr)

    def compile(self, source: str, allowed_columns: Iterable[str]) -> Expr:
        expr: Expr = self.parse(source)
        self.validate(expr, allowed_columns)
        return expr

    def evaluate_formula(self, source: str, df: pd.DataFrame) -> Any:
        expr: Expr = self.compile(source, df.columns)
        return self.evaluate(expr, df)

    def apply_extra_columns(
        self,
        df: pd.DataFrame,
        formulas: dict[str, str],
        in_place: bool = False,
    ) -> pd.DataFrame:
        out: pd.DataFrame = df if in_place else df.copy()
        for target_col, source in formulas.items():
            expr: Expr = self.compile(source, out.columns)
            out[target_col] = self.evaluate(expr, out)
        return out


# ============================================================================
# Demo
# ============================================================================


def _demo() -> None:
    df: pd.DataFrame = pd.DataFrame(
        {
            "first_name": ["Ada", "Grace", None, "Katherine"],
            "last_name": ["Lovelace", "Hopper", "Unknown", "Johnson"],
            "code": [" x1 ", "ab-2 ", None, " z9"],
            "display_name": [None, "Rear Admiral Hopper", None, None],
            "site_name": ["London", "Arlington", None, "Hampton"],
            "country": ["UK", "US", None, "US"],
        }
    )

    extra_columns: dict[str, str] = {
        "fullname": "=concat(first_name, ' ', last_name)",
        "initials": "=concat(upper(substr(first_name, 0, 1)), upper(substr(last_name, 0, 1)))",
        "normalized_code": "=upper(trim(code))",
        "label": "=coalesce(display_name, concat(site_name, ' (', country, ')'), 'Unknown')",
    }

    engine = FormulaEngine()
    result: pd.DataFrame = engine.apply_extra_columns(df, extra_columns, in_place=False)

    print("Input:")
    print(df)
    print()
    print("Output:")
    print(result)
    print()
    print("Selected columns:")
    print(result[["fullname", "initials", "normalized_code", "label"]])


if __name__ == "__main__":
    _demo()
