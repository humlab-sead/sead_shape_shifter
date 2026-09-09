---
agent: agent
description: Create a new constraint or data validator following Shape Shifter patterns
---

Create a `{VALIDATOR_TYPE}` validator for `{VALIDATION_PURPOSE}`.

Choose one of the two validator types below and follow its pattern:

---

## Constraint Validator (config-level, pre/post-merge stage)

**File**: `src/constraints.py`

```python
from src.constraints import ConstraintValidator, Validators

@Validators.register(key="{validator_key}", stage="{pre-merge|post-merge}")
class {ValidatorName}(ConstraintValidator):
    def validate(self, config: dict, entity_name: str | None = None) -> list[dict]:
        issues = []
        # Validation logic here
        return issues
```

Issue structure:
```python
{
    "severity": "error|warning|info",
    "entity": entity_name,
    "field": field_name,
    "message": "Description",
    "code": "ERROR_CODE",
    "suggestion": "How to fix",
}
```

- **pre-merge**: validates before entity merges with inherited config
- **post-merge**: validates after full entity config resolution

**Tests** go in `tests/test_constraints.py`.

---

## Data Validator (data-level, pure domain function)

**File**: `src/validators/data_validators.py`

```python
import pandas as pd

class {ValidatorName}:
    @staticmethod
    def validate(df: pd.DataFrame, {params}, entity_name: str) -> list[ValidationIssue]:
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

**Tests** go in `backend/tests/test_validation.py` using plain DataFrames — no mocks needed.

---

## Related Documentation
- [validation.instructions.md](../instructions/features/validation.instructions.md)
- [DESIGN.md](../../docs/DESIGN.md)
