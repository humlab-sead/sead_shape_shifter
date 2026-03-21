# DSL Extensibility Guide

## Overview

The hand-written recursive descent parser in `src/transforms/dsl.py` is designed with extensibility in mind. Adding new expression types follows a consistent four-layer pattern across the codebase.

## Extension Points

Every new expression type requires changes in **4 places**:

1. **AST** - Add new node class
2. **Parser** - Parse the new syntax  
3. **Validator** - Validate the new expression
4. **Evaluator** - Execute the new expression

## Example: Adding Binary Operators

Let's add support for arithmetic operators: `+`, `-`, `*`, `/`

### Formula Examples
```yaml
extra_columns:
  total: "=quantity * price"
  discount: "=price * 0.9"
  net: "=price - discount"
```

### Step 1: Add AST Node

```python
# In src/transforms/dsl.py

@dataclass(frozen=True)
class BinaryOp(Expr):
    """Binary operation expression (e.g., a + b, x * y)."""
    operator: str  # "+", "-", "*", "/"
    left: Expr
    right: Expr
```

### Step 2: Update Parser

```python
# In src/transforms/dsl.py

# Add token types
class TokenType(Enum):
    # ... existing types ...
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()

# Update tokenizer patterns (order matters!)
class Tokenizer:
    PATTERNS = [
        (TokenType.STRING, r'''("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')'''),
        (TokenType.NAME, r'[a-zA-Z_][a-zA-Z0-9_]*'),
        (TokenType.INTEGER, r'-?\d+'),  # Must come before MINUS
        (TokenType.LPAREN, r'\('),
        (TokenType.RPAREN, r'\)'),
        (TokenType.COMMA, r','),
        (TokenType.EQUAL, r'='),
        (TokenType.PLUS, r'\+'),      # New
        (TokenType.MINUS, r'-'),      # New (after INTEGER to avoid conflict)
        (TokenType.STAR, r'\*'),      # New
        (TokenType.SLASH, r'/'),      # New
    ]

# Add parsing methods with operator precedence
class Parser:
    def parse_expr(self) -> Expr:
        """Parse an expression with operator precedence."""
        return self.parse_additive()
    
    def parse_additive(self) -> Expr:
        """Parse addition/subtraction (lowest precedence)."""
        left = self.parse_multiplicative()
        
        while self.check(TokenType.PLUS) or self.check(TokenType.MINUS):
            op_token = self.advance()
            operator = op_token.value
            right = self.parse_multiplicative()
            
            span = SourceSpan(
                line=left.span.line,
                column=left.span.column,
                end_line=right.span.end_line,
                end_column=right.span.end_column,
            )
            left = BinaryOp(span=span, operator=operator, left=left, right=right)
        
        return left
    
    def parse_multiplicative(self) -> Expr:
        """Parse multiplication/division (higher precedence)."""
        left = self.parse_primary()
        
        while self.check(TokenType.STAR) or self.check(TokenType.SLASH):
            op_token = self.advance()
            operator = op_token.value
            right = self.parse_primary()
            
            span = SourceSpan(
                line=left.span.line,
                column=left.span.column,
                end_line=right.span.end_line,
                end_column=right.span.end_column,
            )
            left = BinaryOp(span=span, operator=operator, left=left, right=right)
        
        return left
    
    def parse_primary(self) -> Expr:
        """Parse primary expressions (function_call, column_ref, literal, parens)."""
        # Handle parentheses
        if self.match(TokenType.LPAREN):
            expr = self.parse_expr()
            self.consume(TokenType.RPAREN)
            return expr
        
        # Original logic for function_call, column_ref, literal
        token = self.current()
        
        if token.type == TokenType.NAME and self.peek(1).type == TokenType.LPAREN:
            return self.parse_function_call()
        
        if token.type == TokenType.NAME:
            return self.parse_column_ref()
        
        return self.parse_literal()
```

### Step 3: Update Validator

Both implementations share the same validator:

```python
class Validator:
    def _validate(self, expr: Expr, depth: int) -> None:
        """Recursively validate an expression node."""
        if depth > self.config.max_depth:
            raise DSLValidationError(
                f"Expression nesting exceeds maximum depth of {self.config.max_depth}",
                span=expr.span,
            )

        if isinstance(expr, Literal):
            # ... existing validation ...
            return

        if isinstance(expr, ColumnRef):
            # ... existing validation ...
            return

        if isinstance(expr, Call):
            # ... existing validation ...
            return
        
        # NEW: Add BinaryOp validation
        if isinstance(expr, BinaryOp):
            # Validate operands are numeric types or columns
            self._validate(expr.left, depth + 1)
            self._validate(expr.right, depth + 1)
            
            # Optional: Type checking (if left is literal string, warn about arithmetic)
            if isinstance(expr.left, Literal) and isinstance(expr.left.value, str):
                raise DSLValidationError(
                    f"Binary operator '{expr.operator}' requires numeric operands",
                    span=expr.span,
                )
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
        if isinstance(expr, BinaryOp):
            return 1 + self._count_nodes(expr.left) + self._count_nodes(expr.right)
        return 1
```

### Step 4: Update Evaluator

```python
class Evaluator:
    def eval(self, expr: Expr) -> Any:
        if isinstance(expr, Literal):
            return self.backend.literal(expr.value)

        if isinstance(expr, ColumnRef):
            return self.backend.get_column(expr.name)

        if isinstance(expr, Call):
            # ... existing evaluation ...
            return self.backend.call(spec.impl_name, args, span=expr.span)
        
        # NEW: Add BinaryOp evaluation
        if isinstance(expr, BinaryOp):
            left_val = self.eval(expr.left)
            right_val = self.eval(expr.right)
            return self.backend.binary_op(expr.operator, left_val, right_val, span=expr.span)

        raise DSLEvaluationError(
            f"Unsupported expression node type: {type(expr).__name__}",
            span=expr.span,
        )
```

### Step 5: Update Backend

```python
class Backend(Protocol):
    def get_column(self, name: str) -> Any:
        ...

    def literal(self, value: Any) -> Any:
        ...

    def call(self, impl_name: str, args: list[Any], span: SourceSpan) -> Any:
        ...
    
    # NEW: Add binary operation
    def binary_op(self, operator: str, left: Any, right: Any, span: SourceSpan) -> Any:
        ...


class PandasStringBackend:
    def binary_op(self, operator: str, left: Any, right: Any, span: SourceSpan) -> Any:
        """Evaluate binary operation on pandas Series or scalars."""
        # Ensure both operands are Series for vectorized operations
        left_series = self._ensure_series(left)
        right_series = self._ensure_series(right)
        
        # Convert to numeric if needed
        left_numeric = pd.to_numeric(left_series, errors='coerce')
        right_numeric = pd.to_numeric(right_series, errors='coerce')
        
        try:
            if operator == "+":
                return left_numeric + right_numeric
            elif operator == "-":
                return left_numeric - right_numeric
            elif operator == "*":
                return left_numeric * right_numeric
            elif operator == "/":
                return left_numeric / right_numeric
            else:
                raise DSLEvaluationError(
                    f"Unknown binary operator: {operator}",
                    span=span,
                )
        except Exception as e:
            raise DSLEvaluationError(
                f"Failed to evaluate binary operation '{operator}': {e}",
                span=span,
            ) from e
```

## Other Extension Examples

### Conditional Expressions

```python
@dataclass(frozen=True)
class Conditional(Expr):
    """Ternary conditional: if(condition, true_value, false_value)."""
    condition: Expr
    true_value: Expr
    false_value: Expr

# Usage: =if(price > 100, 'expensive', 'cheap')
```

### String Interpolation

```python
@dataclass(frozen=True)
class StringTemplate(Expr):
    """String with embedded expressions: `Hello {name}`."""
    parts: list[str | Expr]  # Alternating static text and expressions

# Usage: =template('Hello {first_name} {last_name}!')
```

### Comparison Operators

```python
@dataclass(frozen=True)
class Comparison(Expr):
    """Comparison operation: ==, !=, <, >, <=, >=."""
    operator: str
    left: Expr
    right: Expr

# Usage: =coalesce(if(price < 100, 'cheap', 'expensive'), 'unknown')
```

## Comparison: Lark vs. Hand-written Extensibility

| Aspect | Lark | Hand-written | Winner |
|--------|------|--------------|--------|
| **Adding simple expressions** | ✅ Add grammar rule + transformer | ✅ Add parse method | 🟰 Tie |
| **Operator precedence** | ✅ Grammar handles naturally | ⚠️ Manual precedence climbing | ⭐ Lark |
| **Custom error messages** | ⚠️ Limited control | ✅ Full control | ⭐ Hand-written |
| **Debugging new rules** | ⚠️ Parser is opaque | ✅ Step through code | ⭐ Hand-written |
| **Grammar conflicts** | ⚠️ Can be cryptic | ✅ Explicit logic | ⭐ Hand-written |
| **Adding tokens** | ✅ Add to grammar | ✅ Add to patterns | 🟰 Tie |

## Best Practices for Extensions

### 1. Keep the AST Simple
```python
# ✅ Good: Focused node types
@dataclass(frozen=True)
class BinaryOp(Expr):
    operator: str
    left: Expr
    right: Expr

# ❌ Bad: Kitchen sink node
@dataclass(frozen=True)
class GeneralOp(Expr):
    type: str  # "binary", "unary", "ternary", ...
    operator: str
    operands: list[Expr]
    flags: dict[str, Any]
```

### 2. Validate Early
```python
# Validate in the parser (for syntax errors)
if operator not in ['+', '-', '*', '/']:
    raise DSLParseError(f"Unknown operator: {operator}", span=...)

# Validate in the validator (for semantic errors)
if operator in ['*', '/'] and isinstance(left, Literal) and isinstance(left.value, str):
    raise DSLValidationError("Cannot multiply strings", span=...)
```

### 3. Keep Backend Abstract
```python
# ✅ Good: Backend-agnostic
def eval(self, expr: BinaryOp) -> Any:
    left = self.eval(expr.left)
    right = self.eval(expr.right)
    return self.backend.binary_op(expr.operator, left, right, expr.span)

# ❌ Bad: Pandas-specific in evaluator
def eval(self, expr: BinaryOp) -> Any:
    left = self.eval(expr.left)
    right = self.eval(expr.right)
    # Directly using pandas here couples evaluator to pandas
    return pd.to_numeric(left) + pd.to_numeric(right)
```

### 4. Test Incrementally
```python
# Test each layer independently
def test_parse_binary_op():
    expr = parser.parse("=a + b")
    assert isinstance(expr, BinaryOp)
    assert expr.operator == "+"

def test_validate_binary_op():
    expr = BinaryOp(operator="+", left=col_a, right=col_b, span=...)
    validator.validate(expr)  # Should not raise

def test_evaluate_binary_op():
    df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
    result = engine.evaluate_formula("=a + b", df)
    assert list(result) == [4, 6]
```

## When to Extend vs. Add Functions

**Add new expression type when:**
- Syntax is fundamentally different (operators, conditionals)
- Requires operator precedence
- Needs special validation rules

**Add new function when:**
- Follows `name(args)` pattern
- Can be implemented via backend method
- No special syntax needed

**Example: Should `if` be an expression or function?**

```python
# Option 1: Function (easier)
"=if(price > 100, 'expensive', 'cheap')"
# Pros: Uses existing Call infrastructure
# Cons: `price > 100` must be a callable expression

# Option 2: Expression (more powerful)
"=price > 100 ? 'expensive' : 'cheap'"
# Pros: Natural syntax, no function call overhead
# Cons: Requires new AST node, parser logic, precedence rules
```

**Recommendation**: Start with functions, add expressions when syntax matters.

## Migration Strategy

If you need to extend the DSL:

1. **Start with hand-written parser** (for this simple DSL)
2. **Add new expression types as needed**
3. **Only switch to Lark if:**
   - Grammar becomes complex (15+ production rules)
   - Operator precedence becomes intricate
   - Multiple parser backends needed
   - Team gains Lark expertise

**Current DSL state**: 4 expression types (Literal, ColumnRef, Call, Formula wrapper)
**Complexity threshold**: ~10+ expression types before Lark's benefits outweigh costs

## Summary

Both implementations are **highly extensible**:
- ✅ Clean separation of concerns (parse → validate → evaluate)
- ✅ AST pattern is easy to extend
- ✅ Backend abstraction allows new execution strategies

**For this DSL**: Hand-written parser remains the better choice even with extensions, because:
- Grammar is still simple with a few operators
- Full control over precedence and error messages
- No dependency overhead
- Easier to debug and maintain

**Switch to Lark when**: Grammar complexity exceeds ~10 production rules with intricate precedence.
