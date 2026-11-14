#!/usr/bin/env bash
#
# Verify that code changes in a promotion pull request were introduced through
# their own pull request rather than pushed straight to the source branch.
#
# Usage:
#   scripts/verify_promotion_provenance.sh --base <ref> [--head <ref>]
#
# Run locally before opening a promotion pull request, for example:
#   GH_TOKEN=$(gh auth token) scripts/verify_promotion_provenance.sh \
#       --base origin/staging --head origin/dev
#
# How commits are classified:
#
#   * The script walks the first-parent chain from the head commit back to the
#     base commit. That chain is the branch's own history.
#   * A merge commit whose subject is `Merge pull request #<n>` arrived through
#     a pull request, so it passes and the commits it merges are not inspected
#     individually.
#   * Any other commit on the chain is either a squash or rebase merge, or a
#     direct push. It passes when GitHub associates it with a pull request whose
#     base branch is not a promotion target (`staging` or `main`).
#
# Historical commits are not re-reported: a promotion compares the target branch
# tip with the source branch tip, so commits already on the target are outside
# the range.
#
# Exit codes: 0 pass, 1 provenance violations, 2 usage or GitHub API failure.

set -euo pipefail

readonly DEFAULT_PROTECTED_PATHS="scripts/:src/:backend/:frontend/:ingesters/:tests/:.github/workflows/"
readonly PROMOTION_BASE_BRANCHES="staging main"
readonly LOCAL_COMMIT_BLOCKED_BRANCHES="dev staging main"
readonly PULL_REQUEST_MERGE_SUBJECT='^Merge pull request #[0-9]+'
readonly SUMMARY_TITLE="Promotion provenance"

usage() {
  cat <<'EOF'
Verify that commits touching code paths in a promotion carry pull request provenance.

Usage:
  verify_promotion_provenance.sh --base <ref> [--head <ref>]
  verify_promotion_provenance.sh --check-local-commit

Options:
  --base <ref>   Commit or branch the promotion targets. Required.
  --head <ref>   Commit or branch the promotion introduces. Defaults to HEAD.
  --check-local-commit  Check staged paths against the local branch policy.
  -h, --help     Print this help.

Environment:
  GH_TOKEN          Token used for GitHub API reads. Required unless gh is authenticated.
  GITHUB_REPOSITORY Owner/name override. Defaults to the repository detected by gh.
  PROTECTED_PATHS   Colon-separated path prefixes that require provenance.
                    Defaults to:
                      scripts/:src/:backend/:frontend/:ingesters/:tests/:.github/workflows/
EOF
}

die() {
  printf 'error: %s\n' "$*" >&2
  exit 2
}

note() {
  printf '%s\n' "$*"
}

# Print resolved pull request base branches for one commit, one per line.
pull_request_bases() {
  local sha="$1"
  gh api "repos/${repository}/commits/${sha}/pulls" --paginate --jq '.[].base.ref'
}

# Return 0 when the commit belongs to a pull request that is not a promotion.
has_independent_pull_request() {
  local sha="$1"
  local bases base

  if ! bases="$(pull_request_bases "$sha")"; then
    return 2
  fi

  while IFS= read -r base; do
    [[ -z "$base" ]] && continue
    case " ${PROMOTION_BASE_BRANCHES} " in
      *" ${base} "*) continue ;;
    esac
    return 0
  done <<< "${bases}"

  return 1
}

# Print the paths one commit changes, one per line.
changed_paths() {
  git show --pretty=format: --name-only --no-renames -m --first-parent "$1" | sed '/^$/d'
}

parent_count() {
  local parents
  parents="$(git log -1 --format='%P' "$1")"
  if [[ -z "$parents" ]]; then
    printf '0\n'
    return
  fi
  # shellcheck disable=SC2086 # Word splitting counts the parent hashes.
  set -- $parents
  printf '%s\n' "$#"
}

is_protected_path() {
  local path="$1" prefix
  for prefix in "${protected_prefixes[@]}"; do
    [[ -n "$prefix" && "$path" == "${prefix}"* ]] && return 0
  done
  return 1
}

check_local_commit() {
  local branch path
  local -a matched_paths=()

  branch="$(git symbolic-ref --quiet --short HEAD)" || return 0
  case " ${LOCAL_COMMIT_BLOCKED_BRANCHES} " in
    *" ${branch} "*) ;;
    *) return 0 ;;
  esac

  while IFS= read -r -d '' path; do
    is_protected_path "$path" && matched_paths+=("$path")
  done < <(git diff --cached --name-only --no-renames -z)

  [[ ${#matched_paths[@]} -gt 0 ]] || return 0

  printf 'Commit blocked on branch "%s"; protected paths require a pull request:\n' "$branch" >&2
  printf '  %s\n' "${matched_paths[@]}" >&2
  printf 'Create a feature branch and merge it through a pull request.\n' >&2
  return 1
}

base_ref=""
head_ref="HEAD"
local_commit_mode=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --base)
      [[ $# -ge 2 && -n "$2" ]] || die "--base requires a value"
      base_ref="$2"
      shift 2
      ;;
    --head)
      [[ $# -ge 2 && -n "$2" ]] || die "--head requires a value"
      head_ref="$2"
      shift 2
      ;;
    --check-local-commit)
      local_commit_mode=true
      shift
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      die "unknown argument: $1"
      ;;
  esac
done

command -v git >/dev/null || die "git is required"

IFS=':' read -r -a protected_prefixes <<< "${PROTECTED_PATHS:-${DEFAULT_PROTECTED_PATHS}}"
[[ ${#protected_prefixes[@]} -gt 0 ]] || die "PROTECTED_PATHS is empty"

if [[ "$local_commit_mode" == true ]]; then
  [[ -z "$base_ref" ]] || die "--base cannot be used with --check-local-commit"
  if check_local_commit; then
    exit 0
  else
    exit 1
  fi
fi

[[ -n "$base_ref" ]] || {
  usage >&2
  die "--base is required"
}

command -v gh >/dev/null || die "the GitHub CLI (gh) is required"

if ! git rev-parse --verify --quiet "${base_ref}^{commit}" >/dev/null; then
  die "unknown base ref: ${base_ref}"
fi
if ! git rev-parse --verify --quiet "${head_ref}^{commit}" >/dev/null; then
  die "unknown head ref: ${head_ref}"
fi

repository="${GITHUB_REPOSITORY:-}"
if [[ -z "$repository" ]]; then
  repository="$(gh repo view --json nameWithOwner --jq '.nameWithOwner')" || die "cannot determine repository; set GITHUB_REPOSITORY"
fi

mapfile -t chain < <(git rev-list --first-parent "${base_ref}..${head_ref}")

if [[ ${#chain[@]} -eq 0 ]]; then
  note "No commits between ${base_ref} and ${head_ref}; nothing to verify."
  exit 0
fi

violation_shas=()
violation_subjects=()
violation_paths=()
verified=0

for sha in "${chain[@]}"; do
  subject="$(git log -1 --format=%s "$sha")"

  if [[ "$(parent_count "$sha")" -gt 1 && "${subject}" =~ ${PULL_REQUEST_MERGE_SUBJECT} ]]; then
    continue
  fi

  matched_paths=()
  while IFS= read -r path; do
    is_protected_path "$path" && matched_paths+=("$path")
  done < <(changed_paths "$sha")

  [[ ${#matched_paths[@]} -eq 0 ]] && continue

  verified=$((verified + 1))

  provenance_status=0
  if has_independent_pull_request "$sha"; then
    continue
  else
    provenance_status=$?
  fi

  if [[ "$provenance_status" -eq 2 ]]; then
    die "GitHub API request failed for ${sha}; cannot verify pull request provenance"
  fi

  violation_shas+=("$sha")
  violation_subjects+=("${subject}")
  violation_paths+=("$(printf '%s, ' "${matched_paths[@]}" | sed 's/, $//')")
done

if [[ ${#violation_shas[@]} -eq 0 ]]; then
  note "Verified ${verified} commit(s) touching protected paths; all carry pull request provenance."
  if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
    {
      printf '## %s\n\n' "$SUMMARY_TITLE"
      printf 'Passed. %s commit(s) touch protected paths and all carry pull request provenance.\n' "$verified"
    } >> "$GITHUB_STEP_SUMMARY"
  fi
  exit 0
fi

note ""
note "Commits changing protected paths without their own pull request:"
note ""

for index in "${!violation_shas[@]}"; do
  sha="${violation_shas[$index]}"
  short="${sha:0:8}"
  note "  ${short} ${violation_subjects[$index]}"
  note "      ${violation_paths[$index]}"
  if [[ -n "${GITHUB_ACTIONS:-}" ]]; then
    printf '::error title=Missing pull request provenance::%s %s changes %s\n' \
      "$short" "${violation_subjects[$index]}" "${violation_paths[$index]}"
  fi
done

note ""
note "These commits were added to the source branch without a pull request, so they"
note "have no review record and cannot appear in generated release notes. Move the"
note "change to a feature branch and merge it with a pull request before promoting."
note ""
note "Protected path prefixes: ${protected_prefixes[*]}"

if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
  # Backticks below are Markdown delimiters, not shell expansions.
  # shellcheck disable=SC2016
  {
    printf '## %s\n\n' "$SUMMARY_TITLE"
    printf 'Failed. %s of %s commit(s) touching protected paths have no pull request provenance.\n\n' \
      "${#violation_shas[@]}" "$verified"
    printf '| Commit | Subject | Protected paths |\n'
    printf '| --- | --- | --- |\n'
    for index in "${!violation_shas[@]}"; do
      printf '| `%s` | %s | %s |\n' \
        "${violation_shas[$index]:0:8}" "${violation_subjects[$index]}" "${violation_paths[$index]}"
    done
    printf '\nAdd the change through a pull request before promoting.\n'
  } >> "$GITHUB_STEP_SUMMARY"
fi

exit 1
