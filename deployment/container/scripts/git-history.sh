#!/usr/bin/env bash
# Record the deployment user's home directory in a local git repository.
#
# One run creates at most one commit per project directory, one commit for each
# shared group (config, container, shared data, state), and one commit for
# everything else. A path with no changes is skipped, so a run that finds no
# changes creates no commit.
#
# The repository is local only. Configuration files hold deployment
# credentials, so a configured git remote stops the run unless
# GIT_HISTORY_ALLOW_REMOTE=1 is set.
#
# The run refuses to record anything while paths that should stay out of history
# are still not ignored: the application's own snapshot files, derived
# materialized output, runtime logs, deletion archives and the state database.
#
# Usage: git-history.sh [--init] [--dry-run] [--tag-run] [--quiet] [--help]
#
# Environment (all optional):
#   GIT_HISTORY_ROOT                 repository root (default: $HOME)
#   GIT_HISTORY_AUTHOR_NAME          repository-local commit name
#   GIT_HISTORY_AUTHOR_EMAIL         repository-local commit email
#   GIT_HISTORY_LATEST_TAG           moving tag for the newest commit
#                                    (default: backup/latest; an empty value disables it)
#   GIT_HISTORY_MAX_REPO_MB          warn above this repository size (default: 2048)
#   GIT_HISTORY_ALLOW_IGNORE_GAPS=1  record a run although recommended paths are not ignored
#   GIT_HISTORY_ALLOW_REMOTE=1       record a run although a git remote is configured
#
# CONFIG_DIR, DATA_DIR and CONTAINER_DATA_DIR resolve exactly as in the other
# scripts in this directory, so deployment.env decides which directories are
# recorded.
set -euo pipefail

SCRIPT_DIR="$(
    CDPATH=''
    cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd
)"
# shellcheck source=_load-env.sh
. "$SCRIPT_DIR/_load-env.sh"

# Project archive zips are themselves backups of deleted projects, so the
# scheduled history keeps the live projects only.
SKIPPED_PROJECT_DIR="archived"

usage() {
    cat <<EOF
Usage: $(basename -- "${BASH_SOURCE[0]}") [options]

Record the current state of the deployment home directory in a local git
repository: one commit per project directory, one per shared group, then one for
everything else. Unchanged paths produce no commit.

Options:
  --init      Create the repository (and a starter .gitignore) when it is missing
  --dry-run   Report what would be recorded without writing a commit
  --tag-run   Also create a tag named backup/<run id> when the run commits
  --quiet     Print only warnings and errors
  -h, --help  Show this help

The repository root is \${GIT_HISTORY_ROOT:-$HOME}; CONFIG_DIR and DATA_DIR
resolve from \$CONFIG_DIR/deployment.env.

Examples:
  scripts/git-history.sh --dry-run
  scripts/git-history.sh --init
  make git-history DRY_RUN=1
EOF
}

log() {
    [ "$quiet" -eq 1 ] || printf '%s\n' "$*"
}

warn() {
    printf 'warning: %s\n' "$*" >&2
}

die() {
    printf 'error: %s\n' "$*" >&2
    exit 1
}

# Print a path relative to the repository root, or return 1 when the path is
# outside it. The scheduled history is one repository per home directory, so a
# configured data directory elsewhere is a configuration mistake rather than
# something to record from here.
relative_to_root() {
    local real
    real="$(CDPATH='' cd -- "$1" 2>/dev/null && pwd -P)" || return 1
    case "$real" in
        "$ROOT"/*) printf '%s\n' "${real#"$ROOT"/}" ;;
        *) return 1 ;;
    esac
}

# Record one commit for the given paths. Returns without writing anything when
# the paths hold no change. Called with:
#   record_paths <subject> <operation> <path>...
record_paths() {
    local subject="$1" operation="$2"
    shift 2
    local paths=("$@")
    local pending count

    if [ "$dry_run" -eq 1 ]; then
        pending="$(git -C "$ROOT" status --porcelain --untracked-files=all -- "${paths[@]}" 2>/dev/null || true)"
        [ -n "$pending" ] || return 0
        count="$(printf '%s\n' "$pending" | wc -l | tr -d ' ')"
        log "--dry-run: ${subject} (${count} paths)"
        return 0
    fi

    git -C "$ROOT" add -A -- "${paths[@]}"
    if git -C "$ROOT" diff --cached --quiet -- "${paths[@]}"; then
        return 0
    fi

    count="$(git -C "$ROOT" diff --cached --name-only -- "${paths[@]}" | wc -l | tr -d ' ')"
    git -C "$ROOT" commit --quiet \
        -m "$subject" \
        -m "$(printf 'Operation: %s\nScope: %s\nRun-Id: %s\nHost: %s\nUser: %s\nRecorded: %s' \
            "$operation" "$*" "$run_id" "$host" "$operator" "$recorded_at")" \
        -- "${paths[@]}"

    commits=$((commits + 1))
    log "recorded ${subject} (${count} paths)"
}

# Record one group directory when it exists.
record_group() {
    local rel="$1" subject="$2" operation="$3"
    if [ ! -e "$ROOT/$rel" ]; then
        log "skip ${rel}: not present"
        return 0
    fi
    record_paths "$subject" "$operation" "$rel"
}

init=0
dry_run=0
tag_run=0
quiet=0

for arg in "$@"; do
    case "$arg" in
        --init) init=1 ;;
        --dry-run) dry_run=1 ;;
        --tag-run) tag_run=1 ;;
        --quiet) quiet=1 ;;
        -h | --help)
            usage
            exit 0
            ;;
        *)
            printf 'error: unknown argument: %s\n' "$arg" >&2
            usage >&2
            exit 64
            ;;
    esac
done

command -v git >/dev/null 2>&1 || die "git is not on PATH"
command -v flock >/dev/null 2>&1 || warn "flock is not on PATH; overlapping runs are not prevented"

ROOT="${GIT_HISTORY_ROOT:-$HOME}"
[ -d "$ROOT" ] || die "repository root does not exist: $ROOT"
ROOT="$(CDPATH='' cd -- "$ROOT" && pwd -P)"

data_rel="$(relative_to_root "$DATA_DIR")" ||
    die "DATA_DIR ($DATA_DIR) is outside the repository root ($ROOT)"
config_rel="$(relative_to_root "$CONFIG_DIR")" ||
    die "CONFIG_DIR ($CONFIG_DIR) is outside the repository root ($ROOT)"

if [ ! -d "$ROOT/.git" ]; then
    [ "$init" -eq 1 ] || die "$ROOT is not a git repository; run with --init to create one"
    git init --quiet --initial-branch=main "$ROOT"
    log "initialized repository at $ROOT"
    ignore_template="$SCRIPT_DIR/../resources/git-history.gitignore"
    if [ ! -f "$ROOT/.gitignore" ] && [ -f "$ignore_template" ]; then
        # The template names the data directory through a placeholder, so the
        # patterns match whatever DATA_DIR resolves to rather than assuming the
        # default layout.
        sed "s|@DATA_DIR@|$data_rel|g" "$ignore_template" >"$ROOT/.gitignore"
        log "wrote $ROOT/.gitignore from $ignore_template"
    fi
fi

# Keep the repository self-contained: commits carry their own identity instead
# of borrowing the host account's personal git configuration.
if [ -z "$(git -C "$ROOT" config --local --get user.name || true)" ]; then
    git -C "$ROOT" config --local user.name "${GIT_HISTORY_AUTHOR_NAME:-Shape Shifter Backup}"
fi
if [ -z "$(git -C "$ROOT" config --local --get user.email || true)" ]; then
    git -C "$ROOT" config --local user.email "${GIT_HISTORY_AUTHOR_EMAIL:-shape-shifter-backup@localhost}"
fi
if [ -z "$(git -C "$ROOT" config --local --get core.autocrlf || true)" ]; then
    git -C "$ROOT" config --local core.autocrlf false
fi

if [ -n "$(git -C "$ROOT" config --get-regexp '^remote\..*\.url' || true)" ] &&
    [ "${GIT_HISTORY_ALLOW_REMOTE:-0}" != "1" ]; then
    die "the repository has a remote configured and this home directory holds deployment credentials; set GIT_HISTORY_ALLOW_REMOTE=1 to record anyway"
fi

# Paths that must never enter history. git check-ignore reports whether the
# current .gitignore already covers each sample, so any equivalent pattern is
# accepted.
ignore_samples=(
    "backup/"
    "$data_rel/backups/"
    "$data_rel/logs/"
    "$data_rel/tmp/"
    "$data_rel/output/"
    "$data_rel/projects/$SKIPPED_PROJECT_DIR/"
    "$data_rel/projects/example/backups/"
    "$data_rel/projects/example/materialized/"
    "$data_rel/projects/example/outputs/"
    "$data_rel/state/authorization.sqlite3"
    "$data_rel/projects/example/shapeshifter.yml.tmp"
)
missing_ignores=()
for sample in "${ignore_samples[@]}"; do
    git -C "$ROOT" check-ignore -q -- "$sample" || missing_ignores+=("$sample")
done
if [ "${#missing_ignores[@]}" -gt 0 ]; then
    {
        printf 'warning: paths that should stay out of history are not ignored:\n'
        printf '  %s\n' "${missing_ignores[@]}"
        printf 'Compare with %s, keep any local lines, and remove index entries\n' \
            "$SCRIPT_DIR/../resources/git-history.gitignore"
        printf 'that were already recorded with: git rm -r --cached <path>\n'
    } >&2
    [ "${GIT_HISTORY_ALLOW_IGNORE_GAPS:-0}" = "1" ] ||
        die "refusing to record a run that would commit snapshot, derived or credential-adjacent paths (set GIT_HISTORY_ALLOW_IGNORE_GAPS=1 to override)"
fi

if command -v flock >/dev/null 2>&1; then
    exec 9>"$ROOT/.git/git-history.lock"
    if ! flock -n 9; then
        log "another run holds $ROOT/.git/git-history.lock; exiting"
        exit 0
    fi
fi

# A killed run can leave git's own lock behind and block every later run.
index_lock="$ROOT/.git/index.lock"
if [ -e "$index_lock" ]; then
    if [ -n "$(find "$index_lock" -maxdepth 0 -mmin +15 2>/dev/null)" ]; then
        warn "removing stale git lock older than 15 minutes: $index_lock"
        rm -f "$index_lock"
    else
        die "git lock is held: $index_lock"
    fi
fi

host="$(uname -n)"
operator="$(id -un)"
run_id="$(date +%Y%m%dT%H%M%S)"
recorded_at="$(date --iso-8601=seconds)"
commits=0

# One commit per project directory, so a project's history stays readable and
# one project's churn does not bury another's.
projects_rel="$data_rel/projects"
if [ -d "$ROOT/$projects_rel" ]; then
    for project_dir in "$ROOT/$projects_rel"/*/; do
        [ -d "$project_dir" ] || continue
        name="$(basename -- "${project_dir%/}")"
        [ "$name" = "$SKIPPED_PROJECT_DIR" ] && continue
        rel="$(relative_to_root "$project_dir")" || {
            warn "skipping ${project_dir}: outside $ROOT"
            continue
        }
        record_paths "project: ${name}" "snapshot.project" "$rel"
    done
else
    log "skip ${projects_rel}: not present"
fi

# Deployment configuration, the deployed release files, shared data and runtime
# state change for different reasons, so each group gets its own commit.
record_group "$config_rel" "config: deployment configuration" "snapshot.config"
record_group "container" "container: deployed release files" "snapshot.container"
record_group "$data_rel/shared" "shared: shared data and target models" "snapshot.shared"
record_group "$data_rel/state" "state: runtime state" "snapshot.state"

# Whatever is left: new uploads at the home root, ignore-file edits, and files
# written while the run was in progress.
record_paths "environment: remaining changes" "snapshot.environment" "."

if [ "$dry_run" -eq 0 ] && [ "$commits" -gt 0 ]; then
    latest_tag="${GIT_HISTORY_LATEST_TAG-backup/latest}"
    if [ -n "$latest_tag" ]; then
        git -C "$ROOT" tag -f "$latest_tag" >/dev/null
    fi
    if [ "$tag_run" -eq 1 ]; then
        # Timestamped tags stay unique even when two runs start in the same
        # second, so a manual run never overwrites a scheduled run's tag.
        run_tag="backup/${run_id}"
        suffix=1
        while git -C "$ROOT" rev-parse -q --verify "refs/tags/${run_tag}" >/dev/null; do
            suffix=$((suffix + 1))
            run_tag="backup/${run_id}-${suffix}"
        done
        git -C "$ROOT" tag "$run_tag"
    fi
fi

if [ "$dry_run" -eq 0 ] && [ -d "$ROOT/.git" ]; then
    size_mb="$(du -sm "$ROOT/.git" | cut -f1)"
    if [ "$size_mb" -gt "${GIT_HISTORY_MAX_REPO_MB:-2048}" ]; then
        warn "repository is ${size_mb} MB, above GIT_HISTORY_MAX_REPO_MB; history is append-only, so plan a manual gc or a fresh repository"
    fi
fi

if [ "$dry_run" -eq 1 ]; then
    log "dry run complete for $run_id; nothing written"
else
    log "run $run_id complete: ${commits} commit(s)"
fi
