---
agent: agent
description: Create a new constraint or data validator following Shape Shifter patterns
---

Create a `{VALIDATOR_TYPE}` validator for `{VALIDATION_PURPOSE}`.

Choose one of the two validator types below and follow its pattern:

---

## Constraint Validator (foreign-key check during linking)

**File**: `src/specifications/constraints.py`

```python
@Validators.register(key="{constraint_key}", stage="{stage}")
class {ValidatorName}(ConstraintValidator):
    """{What the check rejects.}"""

    def is_applicable(self) -> bool:
        return ...  # read self.constraints or self.runtime_options

    def validate(self, context: ValidationContext) -> None:
        if ...:
            self.handle_violation("{message}")
```

- Use a stage that existing validators in the file use (for example `pre-merge`).
- `handle_violation()` raises `ForeignKeyConstraintViolation` or logs it.

**Tests** go in `tests/specifications/test_constraints.py`.

---

## Data Validator (data-level, pure domain function)

**File**: `src/validators/data_validators.py`

```python
import pandas as pd

class {ValidatorName}:
    @staticmethod
    def validate(df: pd.DataFrame, {params}, entity_name: str) -> list[DataValidationIssue]:
        """Pure function — receives data, returns issues."""
        issues = []
        # Validation logic here
        return issues
```

Wire into `backend/app/validators/data_validation_orchestrator.py` via injected `DataFetchStrategy`.

Rules:
- Validators receive data — they do not fetch it
- No infrastructure imports in `src/validators/`
- Orchestration (fetch + call + collect) lives in the backend layer

**Tests** go in `tests/validators/test_data_validators.py` using plain DataFrames — no mocks needed.

---

## Related Documentation
- [validation.instructions.md](../instructions/features/validation.instructions.md)
- [DESIGN.md](../../docs/DESIGN.md)
