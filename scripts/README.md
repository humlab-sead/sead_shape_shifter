# Scripts

This directory contains CLI scripts for Shape Shifter workflows.

## Disposable PostgreSQL Container

`spinup_disposable_postgres.py` starts a throwaway PostgreSQL container with podman
for the loopback integration tests that read `SEAD_DISPOSABLE_POSTGRES_*`. The
container binds to loopback only, holds no real data, and the tests create and drop
their own schemas in it.

```bash
# Start (or reuse) the container and print the export lines
uv run python scripts/spinup_disposable_postgres.py up

# Print only the export lines, for eval
eval "$(uv run python scripts/spinup_disposable_postgres.py env)"

# Check container readiness, then remove the container and its data
uv run python scripts/spinup_disposable_postgres.py status
uv run python scripts/spinup_disposable_postgres.py down
```

The same actions are available as Make targets: `make pg-disposable-up`,
`pg-disposable-env`, `pg-disposable-status`, and `pg-disposable-down`.

## Profiling Project Normalization

`profile_normalization.py` profiles normalization for `data/projects/copy_strucke_MS`
by default. It reports elapsed time and output size for each entity, then shows the
most expensive functions by cumulative and self time. The script reads source data
and does not write normalized output files.

Because normalization is asynchronous, use the per-entity wall times for end-to-end
comparisons. `cProfile` cumulative times can include time spent awaiting async work.

```bash
# Profile the default project
uv run python scripts/profile_normalization.py

# Save a profile for interactive inspection
uv run python scripts/profile_normalization.py --out tmp/copy_strucke_MS.prof
uv run snakeviz tmp/copy_strucke_MS.prof

# Profile another project configuration
uv run python scripts/profile_normalization.py --project data/projects/example/shapeshifter.yml
```

The script loads `data/test.env` and `data/.env` using the same precedence as
`profile_validation.py`.

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
The `generate_whats_new.py` script builds the release-note file from the authored user-facing and upgrade-note sections of merged pull requests. It selects pull requests by commit ancestry: a pull request ships in release `Rn` when its merge commit is reachable from the release ref (`vRn` when the tag exists, otherwise `HEAD`) and not from the previous release ref. It reads pull requests whose base branch is `dev`, `staging`, or `main`, so feature pull requests are included even though they never target `main`. `CHANGELOG.md` supplies only the version date and previous version. If an AI API key is configured, it consolidates overlapping notes; otherwise it preserves the authored notes. The older `generate_user_release_notes.py` script remains available for changelog-derived drafts.

Promotion pull requests carry the `<!-- promotion-pr -->` marker and contribute no notes of their own, so promoted changes are never reported twice. Every run writes a rolling pending snapshot to `docs/whats-new/PENDING.md`; it never adds pending changes to a versioned note or GitHub release body. It uses `gh pr list` and `git rev-list`, so `gh` must be authenticated and full history and tags must be available. See [the What's New workflow](../docs/whats-new/README.md).

Generate a release draft manually with:

```bash
python3 scripts/generate_whats_new.py --version X.Y.Z
```

Use `--current-ref`, `--previous-tag`, or `--source-branches` when you need a custom release window.

The release-note generators and standard PR-description drafting can use shared provider settings from the repository-root `.env` or process environment:

- `REPO_SCRIPTS_DEFAULT_MODEL`
- `REPO_SCRIPTS_DEFAULT_PROVIDER_TYPE`
- `REPO_SCRIPTS_DEFAULT_PROVIDER_BASE_URL`
- `REPO_SCRIPTS_DEFAULT_PROVIDER_KEY`
- `RELEASE_NOTES_API_TIMEOUT` (default: 60 seconds; release-note generators only)

Use provider type `openai` or `openai-compatible` and an API-root base URL, such as one ending in `/v1`. The generators append `/chat/completions`. There are no built-in provider defaults; incomplete or unsupported settings produce a warning and a non-AI draft. `COPILOT_PROVIDER_*` environment variables override the shared `.env` settings. Standard PR drafting requires these settings; promotion PRs do not need a model. The script does not read VS Code's secret store.

For a changelog-based draft and Copilot CLI prompt:

```bash
python3 scripts/prepare_copilot_release_notes.py --version X.Y.Z
```

## `update_pr_descriptions.py`

### Usage

```bash
# Draft into docs/whats-new/PRs/PR_<number>.txt
python3 scripts/update_pr_descriptions.py 620-634 --draft

# Override the detected included pull requests for a promotion
python3 scripts/update_pr_descriptions.py 627 --draft --included-prs 621,626

# Record commits that reached the base branch without a pull request
python3 scripts/update_pr_descriptions.py 620-634 --draft --include-orphaned

# Remove terminal escape sequences from existing drafts, without publishing
python3 scripts/update_pr_descriptions.py 620-634 --clean-drafts

# List every detected commit instead of filtering housekeeping
python3 scripts/update_pr_descriptions.py 620-634 --draft --include-orphaned --show-all-orphaned

# Publish the reviewed files
python3 scripts/update_pr_descriptions.py 620-634 --publish
```

Promotion pull requests (`dev` into `staging`, or `staging` into `main`) are drafted from branch history without a model, listing the pull requests merged into the source branch and absent from the target branch.

`--include-orphaned` appends a `Detected orphaned commits` section covering the commits pushed to the base branch between the previous merged pull request and this one. Generated output, release bookkeeping, documentation-only commits, and contributor configuration are filtered out of that section by default, and the filtered counts stay visible in the section and on standard error. See [the What's New workflow](../docs/whats-new/README.md#recording-commits-without-a-pull-request).

## `create_change_pr.py`

`create_change_pr.py` moves uncommitted work onto a branch and merges it into
`dev` through a pull request. Run it whenever a change touches `scripts/`,
`src/`, `backend/`, `frontend/`, `ingesters/`, `tests/`, or
`.github/workflows/`, because those paths need pull request provenance before
`dev` can be promoted. See the
[promotion guard workflow](../.github/workflows/promotion-guard.yml).

```bash
# Show the branch, commit message, file list, and pull request body first
uv run python scripts/create_change_pr.py \
  --type chore --scope deps \
  --subject "upgrade dev tooling and adapt code to new checks" \
  --path uv.lock --path src/loaders --path src/specifications \
  --validation "uv run pylint -j 0 src tests backend ingesters: exit 0" \
  --dry-run

# Create the branch, commit, push, open the pull request, and merge it
uv run python scripts/create_change_pr.py \
  --type chore --scope deps \
  --subject "upgrade dev tooling and adapt code to new checks" \
  --path uv.lock --path src/loaders --path src/specifications

# Open the pull request and stop before merging
uv run python scripts/create_change_pr.py \
  --type fix --subject "reject blank entity keys" \
  --path src/validators --no-merge

# Stage the whole working tree when every pending change is one logical commit
uv run python scripts/create_change_pr.py \
  --type feat --scope workflow \
  --subject "add script and skill for change pull requests" \
  --all --generate-description

# Report the default pylint and pytest lines instead of typing them
uv run python scripts/create_change_pr.py \
  --type fix --subject "reject blank entity keys" \
  --path src/validators --default-validation

# Let Copilot draft the commit subject from the pending diff
uv run python scripts/create_change_pr.py \
  --generate-subject --all --default-validation --dry-run
```

The script stages only the paths given with `--path`, so unrelated work stays
uncommitted. `--all` stages every pending change instead, for the case where the
whole working tree is one logical commit; it is mutually exclusive with `--path`.
Both modes refuse the literal blanket values such as `.`, reject a dirty index,
and refuse `staging` and `main` as targets because those are promotion branches.
The pull request body uses the four sections required by
[.github/pull_request_template.md](../.github/pull_request_template.md);
`--release-note`, `--upgrade-notes`, and `--validation` supply the content that
the author knows, and the template fallback text is used otherwise.

`--generate-description` runs `update_pr_descriptions.py` for the new pull
request once it exists, so the Copilot-written description replaces the scaffold
body. That step needs the Copilot provider settings described above. The draft
file it writes under `docs/whats-new/PRs/` is committed and pushed to the pull
request branch by default, as a second commit named
`docs(whats-new): record the description for pull request #<n>`, because the
repository tracks those files. Pass `--no-commit-description-draft` to leave the
file untracked instead.

`--default-validation` adds the two repository default lines,
`uv run pylint -j 0 src tests backend ingesters: exit 0` and
`pytest: all passed`, before any `--validation` lines you pass. The script never
runs those checks, so it records text you are responsible for having verified.
Run both commands yourself first, and pass `--validation` for narrower or
different evidence.

`--generate-subject` drafts the commit subject from the pending changes with
Copilot CLI, so `--type`, `--scope`, and `--subject` can be omitted. It sends the
status list, the tracked diff, and a short preview of each new untracked file,
because a plain `git diff` omits new files. The result still passes the same
checks as a hand-written subject, and `--subject` and `--generate-subject` are
mutually exclusive. The call happens before the commit, so `--dry-run` shows the
subject it would use. A generation failure stops the run and asks for
`--subject`.

## `draft_all_pr_descriptions.py`

### Usage

```bash
# Show the plan without writing anything
python3 scripts/draft_all_pr_descriptions.py --dry-run

# Draft every merged pull request that has no draft file yet
python3 scripts/draft_all_pr_descriptions.py

# Redraft everything, newest first, in batches of 10
python3 scripts/draft_all_pr_descriptions.py --force --newest-first --batch-size 10

# Retry a malformed model response up to three times per pull request
python3 scripts/draft_all_pr_descriptions.py --attempts 3

# Include closed and open pull requests, newest first
python3 scripts/draft_all_pr_descriptions.py --state all --newest-first
```

Enumerates pull requests with `gh pr list` and drives `update_pr_descriptions.py` with `--draft --include-orphaned`. Existing drafts are kept unless `--force` is given, so an interrupted run resumes and a later run retries only missing drafts. `--batch-size` controls how many pull requests each invocation receives. `--limit` caps the run size, `--fail-fast` stops after the first failing batch, and `--no-preflight` skips the Copilot configuration check for promotion-only sets. It never publishes. See [the What's New workflow](../docs/whats-new/README.md#drafting-every-pull-request).

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

The script requires authenticated `gh` access to merged PRs. It replaces the versioned output file and refreshes `PENDING.md` on each run. See [the What's New workflow](../docs/whats-new/README.md).

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
- Replaces the output file on each run. Review the generated content and reapply any manual edits after regenerating.
- Can update the matching GitHub Release body when run with `--update-github-release`.

### Optional Arguments

- `--version X.Y.Z`: Generate one release note file.
- `--generate-missing`: Generate files for missing changelog versions.
- `--list-versions`: Print release versions available in `CHANGELOG.md` and exit.
- `--output PATH`: Write the generated note to a custom path.
- `--force-heuristic`: Do not use AI drafting.
- `--update-github-release`: Update the matching GitHub Release body via `gh`.

## `verify_promotion_provenance.sh`

Fails a promotion when code changes were pushed straight to the source branch instead of arriving through a pull request. Direct pushes have no review record and cannot appear in generated release notes, because the generator reads merged pull requests only.

### Quick Start

```bash
# Check a dev into staging promotion before opening the pull request
GH_TOKEN=$(gh auth token) scripts/verify_promotion_provenance.sh \
  --base origin/staging --head origin/dev

# Check one explicit range
scripts/verify_promotion_provenance.sh --base 7a90e566 --head f4c8a177
```

### What It Does

- Walks the first-parent chain from `--head` back to `--base`. That chain is the source branch's own history.
- Passes merge commits whose subject is `Merge pull request #<n>`, and does not inspect the commits they merge.
- Treats every other commit on the chain as a squash merge, rebase merge, or direct push. It passes when GitHub associates the commit with a pull request whose base branch is not `staging` or `main`. Promotion pull requests are ignored, because merging a promotion associates it with every commit it carries.
- Reports each failing commit, its subject, and the protected paths it changes. Writes a Markdown summary to `GITHUB_STEP_SUMMARY` when that variable is set.

### Protected Paths

`scripts/`, `src/`, `backend/`, `frontend/`, `ingesters/`, `tests/`, and `.github/workflows/`. Override with the colon-separated `PROTECTED_PATHS` environment variable, for example `PROTECTED_PATHS="src/:backend/"` to check only backend code.

### Exit Codes

- `0`: every commit touching a protected path carries pull request provenance.
- `1`: at least one such commit has none.
- `2`: usage error, unknown ref, or failed GitHub API request.

### Automation

`.github/workflows/promotion-guard.yml` runs the script on pull requests into `staging` and `main`. The workflow is advisory until it is added as a required status check on the repository ruleset. Commits already on the target branch are outside the range, so the check reports only what a promotion adds.

### Known Limitation

Squash and rebase merges pass only if GitHub still associates the resulting commit with its pull request. Merge commits are recognised from their subject and do not depend on that association, which is how this repository currently merges pull requests.

A pull request cannot repair an earlier direct push. Opening a pull request from a branch that contains the pushed commit associates that commit with the pull request while the branch exists, but the association disappears once the branch is merged and deleted. Fix a reported commit by reverting it through a pull request and re-applying the change on its own branch, or promote it with an explicit override.

## Promoting `dev` to `staging`

Use `make promote-dev-to-staging` or `promote_dev_to_staging.sh` to verify
commit provenance, create a draft promotion pull request, and prepare its
description from branch history:

```bash
# Create the draft PR and generate its local description
make promote-dev-to-staging

# Or run the script directly
scripts/promote_dev_to_staging.sh prepare

# Review or edit docs/whats-new/PRs/PR_<number>.txt, then publish it
scripts/promote_dev_to_staging.sh publish <pull-request-number>
```

The script requires authenticated `gh` access, the repository `.venv`, and an
`origin` remote pointing to `humlab-sead/sead_shape_shifter`. It does not merge
the pull request. After required reviews and checks pass, merge it with:

```bash
gh pr merge <pull-request-number> --merge
```

If `dev` changes after the description draft is generated, regenerate and review
the draft before publishing it:

```bash
.venv/bin/python scripts/update_pr_descriptions.py <pull-request-number> --draft --force
```

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
