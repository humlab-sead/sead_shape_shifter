# Scripts

This directory contains CLI scripts for Shape Shifter workflows.

## Release Notes Drafting

The `prepare_copilot_release_notes.py` script prepares a user-facing release-notes draft for refinement with Copilot CLI.
The underlying `generate_user_release_notes.py` script also supports local `.env` loading for AI-related variables when they are not already exported.
Release-note bodies, Copilot prompts, and AI prompts are rendered from Jinja2 templates under `scripts/templates/`.

## `prepare_copilot_release_notes.py`

### Usage

```bash
python3 scripts/prepare_copilot_release_notes.py --version 1.24.0

# List versions available in CHANGELOG.md
python3 scripts/prepare_copilot_release_notes.py --list-versions
```

## `generate_user_release_notes.py`

### Quick Start

```bash
# Generate release notes for all missing versions since the last one
make release-notes-missing           # Uses heuristic mode (fast)
make release-notes-missing-ai        # Uses AI mode (requires API key)

# Generate release notes for a specific version
make release-notes VERSION=1.26.0    # Uses heuristic mode
make release-notes-ai VERSION=1.26.0 # Uses AI mode

# List all available versions
make release-notes-list
```

### Direct Usage

```bash
# List versions available in CHANGELOG.md
python3 scripts/generate_user_release_notes.py --list-versions

# Generate release notes for all missing versions (heuristic mode)
python3 scripts/generate_user_release_notes.py --generate-missing --force-heuristic

# Generate release notes for all missing versions (AI mode)
python3 scripts/generate_user_release_notes.py --generate-missing

# Generate release notes for a specific version
python3 scripts/generate_user_release_notes.py --version 1.26.0 --force-heuristic
```

### What It Does

- Generates a heuristic draft release note file using `generate_user_release_notes.py --force-heuristic`
- Writes the draft by default to `docs/whats-new/vX.Y.Z.md`
- Writes a ready-to-paste Copilot CLI prompt by default to `tmp/copilot-release-notes-vX.Y.Z.prompt.md`
- Uses a filtered user-visible summary as prompt context instead of the full raw changelog section
- Prints that prompt to stdout so it can be pasted directly into Copilot CLI

### Optional Arguments

- `--draft-output`: Custom path for the generated draft markdown file
- `--prompt-output`: Custom path for the generated Copilot prompt file
- `--list-versions`: Print release versions available in `CHANGELOG.md` and exit

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
