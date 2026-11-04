#!/usr/bin/env bash
set -euo pipefail

readonly repository="humlab-sead/sead_shape_shifter"
readonly source_branch="dev"
readonly target_branch="staging"
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly script_dir
repository_root="$(cd -- "${script_dir}/.." && pwd)"
readonly repository_root
readonly cli_path="${repository_root}/scripts/promote_dev_to_staging.sh"
readonly description_script="${repository_root}/scripts/update_pr_descriptions.py"
readonly provenance_script="${repository_root}/scripts/verify_promotion_provenance.sh"
readonly python="${repository_root}/.venv/bin/python"
cd -- "$repository_root"

usage() {
  cat <<'EOF'
Prepare and publish a dev-to-staging promotion pull request.

Usage:
  scripts/promote_dev_to_staging.sh prepare
  scripts/promote_dev_to_staging.sh publish <pull-request-number>

Commands:
  prepare             Fetch branches, verify provenance, create a draft promotion PR,
                      and generate its local description draft.
  publish <number>    Publish the reviewed description and mark the PR ready for review.
  -h, --help          Show this help.

After review and required checks pass, merge with:
  gh pr merge <pull-request-number> --merge
EOF
}

die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || die "Required command not found: $1"
}

validate_pull_request_number() {
  [[ "$1" =~ ^[1-9][0-9]*$ ]] || die "Pull request number must be a positive integer."
}

check_environment() {
  require_command git
  require_command gh
  [[ -x "$python" ]] || die "Python environment not found at ${python}; set up the repository .venv first."
  [[ -f "$description_script" ]] || die "Description script not found: ${description_script}"
  [[ -x "$provenance_script" ]] || die "Provenance script is not executable: ${provenance_script}"

  gh auth status --hostname github.com >/dev/null 2>&1 || die "Authenticate with 'gh auth login' first."

  local actual_repository
  actual_repository="$(gh repo view --json nameWithOwner --jq .nameWithOwner)" \
    || die "Could not determine the current GitHub repository."
  [[ "$actual_repository" == "$repository" ]] \
    || die "Run this script from ${repository}; current repository is ${actual_repository}."

  local origin_url
  origin_url="$(git remote get-url origin)" || die "Git remote 'origin' is required."
  [[ "$origin_url" =~ github\.com[:/]humlab-sead/sead_shape_shifter(\.git)?$ ]] \
    || die "Git remote 'origin' must point to ${repository}; found ${origin_url}."
}

fetch_branches() {
  if [[ "$(git rev-parse --is-shallow-repository)" == "true" ]]; then
    git fetch --unshallow origin
  else
    git fetch origin
  fi

  git show-ref --verify --quiet "refs/remotes/origin/${source_branch}" \
    || die "Remote branch origin/${source_branch} was not found."
  git show-ref --verify --quiet "refs/remotes/origin/${target_branch}" \
    || die "Remote branch origin/${target_branch} was not found."
}

verify_provenance() {
  local token
  token="$(gh auth token)" || die "Could not read the GitHub CLI authentication token."
  [[ -n "$token" ]] || die "GitHub CLI returned an empty authentication token."

  GH_TOKEN="$token" "$provenance_script" \
    --base "origin/${target_branch}" \
    --head "origin/${source_branch}"
}

prepare_promotion() {
  check_environment
  fetch_branches

  local existing_pr
  existing_pr="$(gh pr list \
    --repo "$repository" \
    --state open \
    --base "$target_branch" \
    --head "$source_branch" \
    --json number,url \
    --jq '.[0].url // empty')"
  [[ -z "$existing_pr" ]] || die "An open promotion PR already exists: ${existing_pr}"

  verify_provenance

  local pull_request_url
  pull_request_url="$(gh pr create \
    --repo "$repository" \
    --draft \
    --base "$target_branch" \
    --head "$source_branch" \
    --title "Promote dev to staging" \
    --body-file - <<'EOF'
<!-- promotion-pr -->
## Summary

Promotes `dev` into `staging`.

## Included PRs

Pending generation from the promotion branch history.

## User-facing release note

None - no user-visible change.

## Upgrade notes

None - no user action required.

## Validation

Not verified: validation results unavailable.
EOF
  )" || die "Could not create the draft promotion pull request."

  local pull_request_number
  pull_request_number="${pull_request_url##*/}"
  validate_pull_request_number "$pull_request_number"

  if ! "$python" "$description_script" "$pull_request_number" --draft; then
    die "Created ${pull_request_url}, but could not generate its description draft. Run: ${python} ${description_script} ${pull_request_number} --draft"
  fi

  printf '\nCreated draft promotion PR: %s\n' "$pull_request_url"
  printf 'Review or edit: %s/docs/whats-new/PRs/PR_%s.txt\n' "$repository_root" "$pull_request_number"
  printf 'Then publish it with: %s publish %s\n' "$cli_path" "$pull_request_number"
}

publish_promotion() {
  local pull_request_number="$1"
  validate_pull_request_number "$pull_request_number"
  check_environment

  local metadata
  metadata="$(gh pr view "$pull_request_number" \
    --repo "$repository" \
    --json state,baseRefName,headRefName,isDraft \
    --jq '[.state, .baseRefName, .headRefName, (.isDraft | tostring)] | @tsv')" \
    || die "Could not read pull request #${pull_request_number}."

  local state base_branch head_branch is_draft
  IFS=$'\t' read -r state base_branch head_branch is_draft <<< "$metadata"
  [[ "$state" == "OPEN" ]] || die "Pull request #${pull_request_number} is not open."
  [[ "$base_branch" == "$target_branch" && "$head_branch" == "$source_branch" ]] \
    || die "Pull request #${pull_request_number} is not a ${source_branch}-to-${target_branch} promotion."
  [[ "$is_draft" == "true" ]] || die "Pull request #${pull_request_number} is not a draft."

  local description_draft="${repository_root}/docs/whats-new/PRs/PR_${pull_request_number}.txt"
  [[ -f "$description_draft" ]] \
    || die "Description draft not found: ${description_draft}. Run the prepare command first."

  fetch_branches
  verify_provenance

  "$python" "$description_script" "$pull_request_number" --publish \
    || die "Could not publish the reviewed description for PR #${pull_request_number}."

  if ! gh pr ready "$pull_request_number" --repo "$repository"; then
    die "Description published, but PR #${pull_request_number} remains a draft. Run: gh pr ready ${pull_request_number}"
  fi

  printf 'Published the description and marked PR #%s ready for review.\n' "$pull_request_number"
  printf 'After required reviews and checks pass, merge with: gh pr merge %s --merge\n' "$pull_request_number"
}

main() {
  if [[ $# -eq 0 || "$1" == "-h" || "$1" == "--help" ]]; then
    usage
    return 0
  fi

  case "$1" in
    prepare)
      [[ $# -eq 1 ]] || die "The prepare command takes no arguments."
      prepare_promotion
      ;;
    publish)
      [[ $# -eq 2 ]] || die "Usage: scripts/promote_dev_to_staging.sh publish <pull-request-number>"
      publish_promotion "$2"
      ;;
    *)
      usage >&2
      die "Unknown command: $1"
      ;;
  esac
}

main "$@"
