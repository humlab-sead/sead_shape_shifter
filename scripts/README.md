# Scripts

This directory contains CLI scripts for Shape Shifter workflows.

## Auto-Reconcile Script

The `auto_reconcile.py` script runs the entity reconciliation workflow from the command line.

### Usage

```bash
# Basic usage
python scripts/auto_reconcile.py PROJECT_NAME ENTITY_NAME

# Using make
make reconcile ARGS="PROJECT_NAME ENTITY_NAME"

# With custom threshold (0.90 = 90% confidence)
python scripts/auto_reconcile.py my_project site --threshold 0.90

# With custom service URL
python scripts/auto_reconcile.py my_project site --service-url http://localhost:8000

# With verbose logging
python scripts/auto_reconcile.py my_project site -v

# All options combined
python scripts/auto_reconcile.py my_project site \
    --threshold 0.90 \
    --max-candidates 5 \
    --service-url http://reconciliation:8000 \
    --verbose
```

### Options

- `--threshold, -t`: Auto-accept threshold (0.0-1.0). Default: 0.95
- `--max-candidates, -m`: Maximum candidates per query. Default: 3
- `--service-url, -s`: Reconciliation service URL. Default: from settings
- `--verbose, -v`: Enable verbose logging (DEBUG level)
- `--help`: Show help message

### Examples

**Reconcile site entity with high confidence threshold:**
```bash
python scripts/auto_reconcile.py arbodat_project site --threshold 0.98
```

**Reconcile with more candidate options:**
```bash
python scripts/auto_reconcile.py arbodat_project taxon --max-candidates 10
```

**Use custom reconciliation service:**
```bash
python scripts/auto_reconcile.py arbodat_project site \
    --service-url http://sead-reconciliation:8000
```

**Debug reconciliation issues:**
```bash
python scripts/auto_reconcile.py arbodat_project site -v
```

**Real workflow example:**
```bash
# 1. Check service health first
curl http://localhost:8000/reconcile

# 2. Run reconciliation with verbose output
python scripts/auto_reconcile.py arbodat-test site --verbose

# 3. Review the results
# Auto-accepted: matches with score >= 0.95 (default threshold)
# Needs review: matches with score 0.8-0.95
# Unmatched: no suitable candidates found

# 4. Adjust threshold if needed and re-run
python scripts/auto_reconcile.py arbodat-test site --threshold 0.90
```

### Exit Codes

- `0`: Success - reconciliation completed
- `1`: Unexpected error
- `2`: Warning - no queries processed
- `3`: Warning - all queries unmatched
- `4`: Entity not found in reconciliation config
- `5`: Bad request (e.g., unsaved changes)
- `6`: Service unavailable

### Output

The script provides formatted output showing:
- Total queries processed
- Auto-accepted matches (green)
- Matches needing review (yellow)
- Unmatched queries (red)
- Acceptance rate percentage
- Sample candidates (with `--verbose`)

### Requirements

The script reuses the existing reconciliation service code and requires:
- Python virtual environment activated
- Backend dependencies installed (`uv pip install -e ".[api]"`)
- Valid project configuration with reconciliation spec
- Running reconciliation service (check with health endpoint)

### Logging

All reconciliation operations are logged with the `[RECON]` prefix. To view logs:

```bash
# View all reconciliation logs
grep '\[RECON\]' logs/endpoint_errors.log

# Monitor in real-time
tail -f logs/endpoint_errors.log | grep '\[RECON\]'
```

### Integration with Make

The Makefile includes a convenient target:

```bash
# Using make
make reconcile ARGS="my_project site"
make reconcile ARGS="my_project site --threshold 0.90 -v"
```
