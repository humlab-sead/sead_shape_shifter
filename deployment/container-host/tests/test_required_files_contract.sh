#!/usr/bin/env bash
# Check that the release workflow's required-file contract and the host release
# manager's required-file list stay identical. Both are trusted copies of the
# same release contract, so a new runtime file must be added to both and to the
# bundle-contents test. Read-only: it extracts the two lists and compares them.
#
# Usage: bash deployment/container-host/tests/test_required_files_contract.sh
set -euo pipefail

g_test_dir="$(CDPATH='' cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
g_repo_root="$(CDPATH='' cd -- "$g_test_dir/../../.." && pwd)"
g_deployment_dir="$g_repo_root/deployment"
g_verifier="$g_deployment_dir/container-host/verify/verify_container_release.sh"
g_manager="$g_deployment_dir/container-host/deploy/manage_container_release.sh"

g_failures=0

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  g_failures=$((g_failures + 1))
}

pass() { printf 'ok: %s\n' "$*"; }

# Prints the entries between "<name>=(" and the following ")", with leading and
# trailing whitespace removed, one entry per line.
extract_required_files() {
  local file="$1" name="$2"
  awk -v name="$name" '
    index($0, name "=(") > 0 { inlist = 1; next }
    inlist && $0 ~ /^[[:space:]]*\)[[:space:]]*$/ { exit }
    inlist { print }
  ' "$file" | sed 's/^[[:space:]]*//; s/[[:space:]]*$//' | sed '/^$/d'
}

assert_list_excludes() {
  local who="$1" list="$2" forbidden="$3"
  if printf '%s\n' "$list" | grep -qxF -- "$forbidden"; then
    fail "$who required-file list contains $forbidden"
  else
    pass "$who required-file list excludes $forbidden"
  fi
}

echo "== required-file lists are present and non-empty =="
verifier_list="$(extract_required_files "$g_verifier" REQUIRED_FILES)"
manager_list="$(extract_required_files "$g_manager" g_required_files)"

if [[ -n "$verifier_list" ]]; then
  pass "the workflow verifier lists $(printf '%s\n' "$verifier_list" | wc -l | tr -d ' ') required files"
else
  fail "the workflow verifier has no REQUIRED_FILES list"
fi
if [[ -n "$manager_list" ]]; then
  pass "the release manager lists $(printf '%s\n' "$manager_list" | wc -l | tr -d ' ') required files"
else
  fail "the release manager has no g_required_files list"
fi

echo
echo "== the two lists are identical =="
if [[ "$verifier_list" == "$manager_list" ]]; then
  pass "the verifier and manager required-file lists match"
else
  fail "the verifier and manager required-file lists differ"
  printf '  workflow verifier:\n%s\n' "$verifier_list" >&2
  printf '  release manager:\n%s\n' "$manager_list" >&2
fi

echo
echo "== neither list carries host tooling, tests, or retired entries =="
for forbidden in scripts/verify/verify_container_release.sh scripts/deploy tests \
  scripts/service.sh scripts/adopt-project.sh scripts/move-project.sh \
  scripts/get-install.sh scripts/load-env.sh scripts/env-config.sh; do
  assert_list_excludes "the verifier" "$verifier_list" "$forbidden"
  assert_list_excludes "the manager" "$manager_list" "$forbidden"
done

echo
if ((g_failures > 0)); then
  printf '%d required-file contract check(s) failed\n' "$g_failures" >&2
  exit 1
fi
echo "All required-file contract checks passed"
