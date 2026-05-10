````markdown id="k2vj1t"
# DSL Extensibility Guide

## Overview

The DSL parser in `src/transforms/dsl.py` is designed to be easy to extend.

Adding a new expression type usually requires updates in four places:

1. AST
2. Parser
3. Validator
4. Evaluator

---

# Example: Adding Binary Operators

Goal:

```yaml
extra_columns:
  total: "=quantity * price"
  discount: "=price * 0.9"
````

---

# 1. Add AST Node

Define a new expression type.

```python id="twsvjt"
@dataclass(frozen=True)
class BinaryOp(Expr):
    operator: str
    left: Expr
    right: Expr
```

---

# 2. Update Parser

Teach the parser how to recognize operators.

Example:

```python id="m71qzy"
# Parse:
# a + b
# price * quantity

BinaryOp(
    operator="*",
    left=ColumnRef("price"),
    right=ColumnRef("quantity"),
)
```

The parser should also handle operator precedence:

* `*` and `/` before `+` and `-`
* parentheses when needed

---

# 3. Update Validator

Validate the new node type.

Example checks:

* both operands exist
* operand types are valid
* nesting depth is allowed

```python id="wfe15n"
if isinstance(expr, BinaryOp):
    self._validate(expr.left)
    self._validate(expr.right)
```

---

# 4. Update Evaluator

Execute the new expression.

```python id="6mjlwm"
if isinstance(expr, BinaryOp):
    left = self.eval(expr.left)
    right = self.eval(expr.right)

    return self.backend.binary_op(
        expr.operator,
        left,
        right,
    )
```

The evaluator delegates actual execution to the backend.

---

# Backend Support

The backend implements the operation itself.

```python id="01pjlwm"
def binary_op(operator, left, right):
    if operator == "+":
        return left + right

    if operator == "*":
        return left * right
```

This keeps the evaluator backend-agnostic.

---

# Other Possible Extensions

## Comparison Operators

```yaml
=is_valid == true
=price > 100
```

## Conditional Expressions

```yaml
=if(price > 100, "expensive", "cheap")
```

## String Templates

```yaml
=template("Hello {name}")
```

---

# Guidelines

## Keep AST Nodes Small

Prefer focused node types.

Good:

```python id="0ce0gm"
BinaryOp(operator="+", left=a, right=b)
```

Avoid large generic nodes with many modes and flags.

---

## Validate Early

* syntax errors → parser
* semantic errors → validator

---

## Keep Evaluator Abstract

The evaluator should not contain backend-specific logic.

Good:

```python id="jfq7kz"
return self.backend.binary_op(op, left, right)
```

Avoid direct pandas or SQL logic inside the evaluator.

---

# Testing

Test each layer independently:

| Layer     | What to Test        |
| --------- | ------------------- |
| Parser    | AST structure       |
| Validator | invalid expressions |
| Evaluator | execution results   |

---

# When to Extend the DSL

Add a new expression type when:

* syntax changes
* precedence rules are needed
* validation becomes specialized

Add a normal function when:

* `name(args)` syntax is enough
* no parser changes are required

Prefer functions first. Add syntax extensions only when they improve readability significantly.

---

# Summary

The DSL is intentionally simple and extensible.

Most extensions follow the same pattern:

1. Add AST node
2. Parse it
3. Validate it
4. Evaluate it

This keeps the parser maintainable while allowing gradual language growth.

```
