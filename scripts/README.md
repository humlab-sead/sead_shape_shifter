# Scripts

This directory contains CLI scripts for Shape Shifter workflows.

## Normalizing Entity Key Order

`sort_project_yaml.py` re-orders each entity's keys in a project file the way a full
project save does (`type`, `source`, `system_id`, `public_id`, `keys`, `columns`,
`values`, …). Use it before comparing two versions of a project file so that key-order
noise does not hide real changes. It is registered as the `sort-project` console script:

```bash
# Print the sorted project to stdout
sort-project data/projects/example/shapeshifter.yml > sorted.yml

# Rewrite the file in place
sort-project --inplace data/projects/example/shapeshifter.yml
```

Without an activated virtualenv, run it through `uv` or the module path:

```bash
uv run sort-project --inplace data/projects/example/shapeshifter.yml
uv run python scripts/sort_project_yaml.py data/projects/example/shapeshifter.yml
```

The script reformats only; it runs no project validation. The `sort-project` command
exists only after installing the project in editable mode (`make install`), so rerun
that after changing `[project.scripts]` in `pyproject.toml`.

## Printing a Target Model Entity

`print_target_model_entity.py` prints one entity specification from a target model YAML file:

```bash
python scripts/print_target_model_entity.py \
  --spec resources/target_models/sead_standard_model.yml \
  --entity data_type
```

## Release Notes Drafting

The `prepare_copilot_release_notes.py` script prepares a user-facing release-notes draft for refinement with Copilot CLI.
The `generate_whats_new.py` script builds the release-note file from the authored user-facing and upgrade-note sections of merged PR descriptions. It uses `CHANGELOG.md` only for the selected version's date and prior-version cutoff. If an AI API key is configured, it consolidates overlapping PR notes; otherwise it preserves the authored notes. The older `generate_user_release_notes.py` script remains available for changelog-derived drafts.

For the latest version in `CHANGELOG.md`, the PR-based generator also adds a `Pending Release` snapshot of PRs merged into `staging` after the latest PR merged into `main`, including their authored notes. It uses `gh pr list`, so `gh` must be installed and authenticated. See [the What's New workflow](../docs/whats-new/README.md).

## `prepare_copilot_release_notes.py`

### Usage

```bash
python3 scripts/prepare_copilot_release_notes.py --version 1.24.0

# List versions available in CHANGELOG.md
python3 scripts/prepare_copilot_release_notes.py --list-versions
```

## `generate_whats_new.py`

### Usage

```bash
# Generate notes from merged PR descriptions (heuristic fallback)
make release-notes VERSION=2.5.0

# Allow configured AI to consolidate overlapping notes
make release-notes-ai VERSION=2.5.0

# Direct usage
python3 scripts/generate_whats_new.py --version 2.5.0
```

The script requires authenticated `gh` access to merged PRs. It replaces the output file on each run. See [the What's New workflow](../docs/whats-new/README.md) for the version-selection and pending-staging behavior.

## `generate_user_release_notes.py` (legacy changelog-based generator)

The legacy generator remains available for listing versions and producing drafts directly from changelog entries.

### Quick Start

```bash
# Generate release notes for all missing versions since the last one
make release-notes-missing
make release-notes-missing-ai

# List versions available in CHANGELOG.md
make release-notes-list

# Generate release notes for all missing versions (heuristic mode)
python3 scripts/generate_user_release_notes.py --generate-missing --force-heuristic

# Generate release notes for all missing versions (AI mode)
python3 scripts/generate_user_release_notes.py --generate-missing

# Generate release notes for a specific version
python3 scripts/generate_user_release_notes.py --version 1.26.0 --force-heuristic
```

### What It Does

- Reads the selected release section from `CHANGELOG.md` and writes `docs/whats-new/vX.Y.Z.md` by default.
- Drafts highlights, new features, improvements, and fixes using local heuristics or AI. Use `--force-heuristic` to skip AI.
- Adds the `Pending Release` PR snapshot only when generating the latest changelog version. `--generate-missing` includes it only if that changelog version is among the versions being generated.
- Replaces the output file on each run. Review the generated content and reapply any manual edits after regenerating.
- Can update the matching GitHub Release body when run with `--update-github-release`.

### Optional Arguments

- `--version X.Y.Z`: Generate one release note file.
- `--generate-missing`: Generate files for missing changelog versions.
- `--list-versions`: Print release versions available in `CHANGELOG.md` and exit.
- `--output PATH`: Write the generated note to a custom path.
- `--force-heuristic`: Do not use AI drafting.
- `--update-github-release`: Update the matching GitHub Release body via `gh`.

## Deployment Scripts

These scripts package the deployment steps from the container deployment guide into reusable command-line helpers. They are host tools: run them from a repository checkout. They live in `deployment/container-host/`, outside the `deployment/container/` release bundle, so they are never shipped in a release archive.

### `deploy_environment.sh`

Deploy the project for a dedicated environment user and start the container stack.

```bash
# Deploy a single environment user
deployment/container-host/deploy/deploy_environment.sh shapeshifter-test

# Override the repository branch and host port
deployment/container-host/deploy/deploy_environment.sh shapeshifter-prod --branch main --host-port 8013
```

### `install_nginx_reverse_proxy.sh`

Install an NGINX vhost for HTTPS traffic to the Podman service. A TLS
certificate must exist first; until then install the HTTP-only bootstrap
vhost and obtain the certificate with it:

```bash
# Run as root
sudo deployment/container-host/deploy/install_nginx_reverse_proxy.sh --bootstrap shapeshifter.example.com
sudo certbot certonly --webroot -w /var/www/html -d shapeshifter.example.com
sudo deployment/container-host/deploy/install_nginx_reverse_proxy.sh shapeshifter.example.com 8012
```

### `install_systemd_service.sh`

Install and enable the user-level systemd service for the container.

```bash
deployment/container-host/deploy/install_systemd_service.sh shapeshifter-test
```

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

## Recording a Reviewed SIMS Site No-Match

The `record_sims_site_no_match.py` script records an explicitly reviewed site no-match in a Shape Shifter project. It checks that the selected source row exists exactly once and has no accepted target ID, then verifies the saved `will_not_match` mapping. It does not call SIMS or allocate an ID.

The script requires the reviewer to supply snapshot details, a reason, and a non-empty reconciliation evidence file. It defaults to a dry run. It only accepts `disposable` or `staging`; disposable runs must use a loopback API URL. Production is not supported.

```bash
python scripts/record_sims_site_no_match.py \
  --base-url http://127.0.0.1:8012 \
  --environment disposable \
  --project my_project \
  --target-field site_name \
  --source-value "Site with no match" \
  --snapshot-id sead-staging-2026-10-02 \
  --snapshot-at 2026-10-02T10:00:00Z \
  --site-row-count 3462 \
  --reviewer "Reviewer name" \
  --reason "Reviewed all candidates; none identifies this site." \
  --evidence tmp/site-reconciliation-review.json

# After reviewing the dry-run checks:
python scripts/record_sims_site_no_match.py \
  --base-url http://127.0.0.1:8012 \
  --environment disposable \
  --project my_project \
  --target-field site_name \
  --source-value "Site with no match" \
  --snapshot-id sead-staging-2026-10-02 \
  --snapshot-at 2026-10-02T10:00:00Z \
  --site-row-count 3462 \
  --reviewer "Reviewer name" \
  --reason "Reviewed all candidates; none identifies this site." \
  --evidence tmp/site-reconciliation-review.json \
  --confirm-allocation-strategy \
  --approve-no-match \
  --apply
```

If the API requires a bearer token, provide it through `SHAPE_SHIFTER_API_TOKEN`; do not pass credentials as command-line arguments. The script stores the evidence file's SHA-256, snapshot details, reviewer, and reason in the reconciliation mapping notes. Run it against the Shape Shifter project configured for the same SEAD snapshot that supplied the reviewed candidates.

The script hashes but does not interpret the evidence file, and it cannot independently confirm which environment, snapshot, or target-model strategy the API uses. Before applying, verify that the project uses the reviewed SEAD snapshot and that its effective strategy permits allocation after a miss; `--confirm-allocation-strategy` records this operator check but does not inspect the model. The reviewer must also check that the evidence covers this exact source value and snapshot.
